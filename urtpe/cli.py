"""Command-line entry point for the urban-renewal PDF pipeline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from urtpe import cleanse as cleanse_mod
from urtpe import corpus as corpus_mod
from urtpe import emission as emission_mod
from urtpe import extract as extract_mod
from urtpe import graph as graph_mod
from urtpe import io as io_mod
from urtpe import ledger as ledger_mod
from urtpe import links as links_mod
from urtpe import lock as lock_mod
from urtpe import merge as merge_mod
from urtpe import reconcile as reconcile_mod
from urtpe import ordering as ordering_mod
from urtpe import report as report_mod
from urtpe import tripwire as tripwire_mod
from urtpe import viewer as viewer_mod
from urtpe.archive import GazetteArchive, DEFAULT_ARCHIVE_ROOT
from urtpe.links import FALLBACK_MAPPING_FILE  # the single path definition (P2.3)
from urtpe.models import CleanRecord, Project


def add_fallback_mapping(land_core: str, view_id: str, case_id: str) -> None:
    """Add a fallback mapping for land_core -> view_id + case_id."""
    mapping = {}
    if FALLBACK_MAPPING_FILE.exists():
        try:
            mapping = json.loads(FALLBACK_MAPPING_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if land_core not in mapping:
        mapping[land_core] = {"view_id": view_id, "case_ids": []}

    if case_id not in mapping[land_core]["case_ids"]:
        mapping[land_core]["case_ids"].append(case_id)

    mapping[land_core]["view_id"] = view_id

    FALLBACK_MAPPING_FILE.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Write to file instead of printing to avoid encoding issues
    with open("add_mapping.log", "w", encoding="utf-8") as f:
        f.write(f"Added mapping: {land_core} -> view_id={view_id}, case_ids={mapping[land_core]['case_ids']}\n")


def _normalise_flags(flags) -> list[str]:
    """The node's review flags with the date each one quotes normalised.

    The unplaced-node flag quotes the node's own date, which reached it in
    whatever form the pipeline held: slash-western from the PDF (97/1/2),
    ISO from a --from-js rebuild. The flag text then changed between runs, so
    the duplicate collapse (by exact text) stopped working and the same
    finding appeared twice in two spellings — 15 nodes carried it after the
    D7 re-emit. Normalising the date on load makes the text a function of
    the node, so the copies collapse again.
    """
    from urtpe.links import _flag_date

    out = []
    for f in flags or []:
        text = str(f)
        out.append(re.sub(r"日期:([0-9/.-]+)", lambda m: "日期:" + _flag_date(m.group(1)),
                          text))
    return out


def _load_projects_from_js(js_path: str) -> tuple[list[Project], dict]:
    """Load projects and metadata from projects.data.js."""
    text = Path(js_path).read_text(encoding="utf-8")
    json_text = re.sub(r"^window\.PROJECTS\s*=\s*", "", text.strip())
    json_text = re.sub(r";\s*$", "", json_text)
    doc = json.loads(json_text)

    projects = []
    for pg in doc["projects"]:
        # Extract district from project_id as fallback: "{district}-{section}..."
        project_district = pg["project_id"].split("-")[0] if "-" in pg["project_id"] else ""
        members = []
        for node in pg["nodes"]:
            # Fallback to project-level district if node lacks it
            node_district = node.get("district", "") or project_district
            # D14 (inspection-batchD): district_land round-trips as-is. The old
            # `or node_district` coerced an emitted '' into the node's district
            # on the first --from-js run, and later runs carried that value
            # forward (4 nodes: 153, 382, 926, 928 — the land cells print
            # 臺北X區 with no 市, so DISTRICT_RE reads ''). The fallback applies
            # only when the key is ABSENT (older payloads).
            node_district_land = (node["district_land"]
                                  if "district_land" in node else node_district)
            
            # Derive iso_date: graph.py emits date=iso_date, so node.date may
            # already be ISO (YYYY-MM-DD). Only ROC-format strings need conversion.
            #
            # ymd has to be derived here too. The emitter never writes a `ymd` key, so the
            # old `node.get("ymd", (0,0,0))` gave every node (0,0,0) and _sort's
            # (ymd, recno) key silently degraded to 編號 order -- the AGENTS.md trap, and
            # self-perpetuating because --from-js reads its own output. 1407 (2005-02-24)
            # rendered above 1362 (2008-01-02) purely because 1362 sorts first by 編號.
            # to_iso() only parses slashes, so an ISO node is split here rather than
            # round-tripped through it.
            node_date = node.get("date", "")
            node_iso_date = node.get("iso_date", "")
            node_ymd = tuple(node["ymd"]) if node.get("ymd") else None
            if node_ymd is None:
                from urtpe.cleanse import roc_to_iso
                iso, ymd = roc_to_iso(node_date)
                if iso:
                    node_iso_date = node_iso_date or iso
                    node_ymd = tuple(ymd) if ymd else (0, 0, 0)
                else:
                    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", node_date)
                    if m_iso:
                        node_iso_date = node_iso_date or node_date
                        node_ymd = (int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            if node_ymd is None:
                node_ymd = (0, 0, 0)
            
            rec = CleanRecord(
                recno=node["recno"],
                date=node_date,
                iso_date=node_iso_date,
                ymd=node_ymd,
                district=node_district,
                district_land=node_district_land,
                name=node.get("case_name", node.get("name", "")),
                name_raw=node.get("name_raw", ""),
                land=node.get("land", ""),
                section=node.get("section", ""),
                first_parcel=node.get("first_parcel", ""),
                parcels=node.get("parcels", []),
                aliases=node.get("aliases", {}),
                land_count=node.get("land_count"),
                orig_count=node.get("orig_count"),
                named_anchor=node.get("named_anchor", ""),
                area_section=node.get("area_section", ""),
                stage=node.get("stage", ""),
                # Derive on load when the key is absent (emit-stage-index): older
                # emissions never wrote stage_index, so the -1 default collapsed
                # section-branch grouping on every rebuild. Same rule as the
                # cleanser (_stage), the same pattern as the ymd fix above.
                stage_index=(node["stage_index"] if "stage_index" in node
                             else (cleanse_mod._stage(node.get("stage") or "")[1])),
                track=node.get("track", ""),
                implementer=node.get("implementer", ""),
                planner=node.get("planner", ""),
                auto_fixes=node.get("auto_fixes", []),
                review_flags=_normalise_flags(node.get("review_flags", [])),
            )
            # Restore optional emitted state so --from-js round-trips are
            # lossless even without --links (attach overwrites when it runs)
            if node.get("implementation"):
                rec.implementation = dict(node["implementation"])
            # D14 (inspection-batchD): the §10 per-track sub-stages and the
            # recovery provenance were dropped by the loader, so every rebuild
            # lost them (533 sub-stage nodes, 4 recovery nodes). They are read
            # back exactly as emitted.
            if node.get("stage_事業計畫") is not None:
                rec.stage_事業計畫 = node["stage_事業計畫"]
            if node.get("stage_權利變換") is not None:
                rec.stage_權利變換 = node["stage_權利變換"]
            if node.get("recovery"):
                rec.recovery = dict(node["recovery"])
            if node.get("links"):
                rec.links = dict(node["links"])
                # D1 (inspection-batchD): pre-rename payloads carried the
                # orphan's per-case Taipei ashx milestones under the false key
                # `milestones_national`. Alias it on load so old emissions keep
                # rendering; project-level dicts are untouched (they ARE
                # national).
                if "milestones_taipei_case" not in rec.links and node.get("virtual"):
                    old = rec.links.pop("milestones_national", None)
                    if old is not None:
                        rec.links["milestones_taipei_case"] = old
            members.append(rec)
        project = Project(
            project_id=pg["project_id"],
            anchor_recno=pg["anchor_recno"],
            members=members,
        )
        if pg.get("implementation"):
            project.implementation = dict(pg["implementation"])
        if pg.get("rewards"):
            project.rewards = dict(pg["rewards"])
        projects.append(project)

    meta = {
        "generated_at": doc.get("generated_at", ""),
        "source": doc.get("source", ""),
        "published_date": doc.get("published_date", ""),
        "thresholds": doc.get("thresholds", {"link": merge_mod.LINK_THRESHOLD, "flag": merge_mod.FLAG_THRESHOLD}),
    }
    return projects, meta


def _ingest_pdf(pdf: str, outdir: str, *, archive_root=None, use_archive: bool = True, ledger_path=None,
                previous_projects: list[str] | None = None,
                allow_reconcile_block: bool = False, strict_reconcile: bool = False,
                recover_truncated: bool = False) -> dict:
    """Archive -> read -> tripwire -> reconcile -> cleanse -> ledger -> merge.

    Every gate runs before the first artifact is written, so a refused ingestion
    leaves raw.tsv, clean.tsv, merged.tsv, projects.json and the viewer data exactly
    as they were. Nothing here is incremental: a full rebuild is ~45 s and is the
    only way a reader change reaches historical records uniformly.

    The archive is on by default: without it there is nothing to reconcile against,
    which is precisely the state this pipeline was in before the change.
    """
    result: dict = {"pdf": pdf}

    # --- archive -----------------------------------------------------------
    gazette_id = extract_mod.gazette_id_for(pdf)
    archive = GazetteArchive(archive_root) if use_archive else None
    result["gazette_id"] = gazette_id
    print(f"[INFO] gazette_id: {gazette_id}")

    # Archive damage is reported, never fatal. `verify()` had no production caller
    # until 2026-10-07, so a member that went missing, was replaced, or appeared with
    # no index entry produced a normal-looking run and exit 0 — which is how the loss
    # of 核定案件-2026-09-24.pdf went unnoticed. It must not block: a missing older
    # gazette does not invalidate the one being ingested, and this gate cannot repair
    # the archive, so refusing would turn a filesystem accident into a permanent halt.
    if archive is not None:
        for problem in archive.verify():
            print(f"[WARN] archive: {problem}")

    # --- read --------------------------------------------------------------
    # A publisher-truncated 地號 cell can sometimes be completed from another
    # approval of the same unit elsewhere in the archive. The corpus is built lazily
    # and cached, so an ordinary rebuild does not re-read every gazette.
    #
    # The predecessor is read through the same seam, with a corpus of its own that
    # excludes it rather than the incoming publication. Measured on 1151006
    # (2026-10-07): the incoming side recovered 14 records the predecessor's side
    # excluded, and the reconciler published that as net change +18 against a true
    # +4, plus 13 historical rows as "edited" that the city never edited. Each side
    # is completed by every *other* archived publication, which is the only reading
    # under which the two totals describe the publisher rather than the reader.
    archive_members: list[tuple[str, Path]] = []

    def _corpus_excluding(gazette_id: str) -> list[dict]:
        return corpus_mod.build_corpus(
            archive_members, exclude=str(gazette_id),
            cache_dir=(Path(outdir).parent / ".corpus_cache"))

    corpus = []
    corpus_note = ""
    try:
        arch = GazetteArchive(archive_root) if archive_root else GazetteArchive()
        seen = set()
        root = Path(arch.root)
        for e in arch.entries():
            fp = root / e.filename
            if e.filename in seen or not fp.exists():
                continue
            seen.add(e.filename)
            archive_members.append((e.published_date or e.gazette_id, fp))
        corpus = _corpus_excluding(extract_mod.gazette_id_for(pdf))
        corpus_note = f"{len(corpus)} candidate rows"
    except Exception as exc:  # an unreadable archive must not block ingestion
        print(f"[WARN] completion corpus unavailable: {exc}")

    records, extract_meta = extract_mod.extract_pdf_with_meta(
        pdf, corpus=corpus, retain_truncated=recover_truncated)
    if not records:
        raise SystemExit("[ERROR] no records parsed")
    print(f"[INFO] read {len(records)} records ({extract_meta.get('calendar', '?')} calendar)")
    excluded_recnos = {
        int(v) for v in (extract_meta.get("excluded_recnos") or "").split(",")
        if v.strip().isdigit()
    }
    if excluded_recnos:
        by_tail = int(extract_meta.get("excluded_by_tail") or "0")
        by_count = int(extract_meta.get("excluded_by_count") or "0")
        print(f"[WARN] {len(excluded_recnos)} record(s) excluded: the publisher "
              f"truncated their 地號 cell and the remainder is not in the PDF "
              f"({by_tail} caught by the cell tail, {by_count} by the declared "
              f"parcel count; 編號 {', '.join(str(v) for v in sorted(excluded_recnos))})")

    # --- recovery pass (opt-in; recover-truncated-rows-via-api) -------------
    # Retained truncated rows bypass cleansing/merge (tasks 3.2): the pass either
    # resolves them — provenance attached, entering the flow as normal records —
    # or abandons them back into the plain exclusion path, named in the report.
    # A run without the flag never constructs a client and never sends a request.
    recovery_outcome = None
    if recover_truncated:
        marked = [r for r in records if r.get("source_fault")]
        if marked:
            from urtpe import recovery_pass as recovery_pass_mod
            ashx, geoserver = recovery_pass_mod.default_clients()
            # D9f-2: the 168 list's 核定公告 date is a SECOND CONFIRMATION for
            # a recovered date, never its source. The source is built only when
            # a row's date was actually recovered, so a run that recovers no
            # date sends no request for the list.
            memo_source = None
            if any(r.get("source_fault") == "truncated_date_cell" for r in marked):
                memo_source = links_mod.memo_date_source()
            recovery_outcome = recovery_pass_mod.recover_marked_rows(
                marked, ashx, geoserver, memo_source=memo_source)
            records = [r for r in records if not r.get("source_fault")] \
                + recovery_outcome.recovered
            print(f"[INFO] recovery: {len(recovery_outcome.recovered)} recovered, "
                  f"{len(recovery_outcome.residuals)} residual "
                  f"of {len(marked)} truncated row(s)")
            for line in recovery_outcome.audit:
                print(f"  {line}")
        else:
            recovery_outcome = None

    # --- tripwire ----------------------------------------------------------
    # Residual rows (the recovery pass abandoned them) rejoin the plain exclusion
    # path: absent from `records`, their 編號 explained to the contiguity check.
    if recovery_outcome is not None:
        excluded_recnos |= {int(r["recno"]) for r in recovery_outcome.residuals
                            if str(r.get("recno") or "").isdigit()}
    tw = tripwire_mod.Tripwire()
    pages = _page_count(pdf)
    faults = tw.check(records, pages=pages,
                      tables_found=int(extract_meta.get("tables_found", "0") or 0),
                      duplicate_recnos=int(extract_meta.get("duplicate_recnos", 0)),
                      excluded_recnos=excluded_recnos)
    # raw.tsv carries every row the publication held: resolved recoveries as
    # normal records, abandoned ones still marked (their parse_error names the
    # fault), so the raw TSV stays a complete, honest reading of the PDF.
    raw_recs = extract_mod.to_raw_records(
        records + (recovery_outcome.residuals if recovery_outcome else []))
    # D14(b): the district enum is the corpus's own 行政區 column, collected
    # here and passed to the cleanser, so the 地號 cell's district is read
    # against what the city publishes rather than against a hard-coded list.
    districts = cleanse_mod.collect_districts(raw_recs)
    clean = cleanse_mod.cleanse_all(raw_recs, districts)
    projects = merge_mod.merge(clean)
    tw_result = tripwire_mod.TripwireResult(
        ok=not faults, faults=faults,
        calendar=extract_meta.get("calendar", "unknown"),
        record_count=len(records), project_count=len(projects),
        duplicate_recnos=int(extract_meta.get("duplicate_recnos", 0)),
        excluded_recnos=sorted(excluded_recnos),
    )
    print(tw_result.report())
    if faults:
        raise tripwire_mod.TripwireFailure(tw_result)

    # --- census gate (wire-standing-checks) ---------------------------------
    # The merge partition must be total and disjoint over the cleansed records,
    # and the emitted count must agree with them. A violation is data
    # corruption, not absence, so it blocks under the same exit-4 contract as
    # the extraction faults — and it evaluates here, before any artifact is
    # written (the audit's Appendix A assertion, wired as a gate).
    census_faults = tw.check_partition(clean, projects)
    if census_faults:
        faults.extend(census_faults)
        for f in census_faults:
            print(f"[CENSUS] {f}", file=sys.stderr)
        tw_result = tripwire_mod.TripwireResult(
            ok=False, faults=faults,
            calendar=extract_meta.get("calendar", "unknown"),
            record_count=len(records), project_count=len(projects),
            duplicate_recnos=int(extract_meta.get("duplicate_recnos", 0)),
            excluded_recnos=sorted(excluded_recnos),
        )
        raise tripwire_mod.TripwireFailure(tw_result)

    # --- reconcile against the archived predecessor ------------------------
    reconciliation = None
    if archive is not None:
        prev_id = archive.predecessor_of(gazette_id)
        previous = None
        # Three states, not two. A predecessor the index records but whose document is
        # not held is named in the report rather than quietly replaced by an earlier
        # publication: comparing across that gap reports one publication's changes as
        # another's. Measured 2026-10-07 — with 09-24 absent, reconciling 10-01 against
        # 08-27 produced 19 re-dated, 16 edited and 41 vanished rows plus a
        # `roc -> gregorian` calendar change, none of which were 10-01's, and
        # `blocking: []` recorded none of that.
        unavailable_note = ""
        if prev_id:
            prev_path = archive.path_of(prev_id)
            if prev_path is None:
                unavailable_note = (
                    f"previous gazette {prev_id} is recorded but its document is not "
                    f"held; nothing to compare against")
                print(f"[WARN] {unavailable_note}")
            else:
                try:
                    previous, _ = extract_mod.extract_pdf_with_meta(
                        str(prev_path), strict=False,
                        corpus=_corpus_excluding(prev_id))
                except Exception as exc:  # a corrupt archive member must not block ingest
                    print(f"[WARN] archived predecessor {prev_id} unreadable: {exc}")
                    unavailable_note = (
                        f"previous gazette {prev_id} is recorded but could not be read "
                        f"({exc}); nothing to compare against")
        ledger = ledger_mod.CorrectionLedger(ledger_path) if ledger_path else None
        reconciliation = reconcile_mod.reconcile(
            previous, records,
            previous_id=prev_id, current_id=gazette_id,
            previous_projects=previous_projects,
            current_projects=[p.project_id for p in projects],
            accepted_removals=ledger.accepted_removals() if ledger else set(),
            recovered_records=recovery_outcome.recovered if recovery_outcome else None,
            strict=strict_reconcile,
            unavailable_note=unavailable_note,
        )
        print(reconciliation.report())
        # Persisted, so the comparison outlives this process. Without it the conclusion
        # exists only on a screen, and "trusted across two consecutive ingestions" is not
        # a judgement anyone can make about output that was never written down.
        try:
            from urtpe.changeset import ChangeSetStore, write_change_set
            cs_path = write_change_set(
                ChangeSetStore(Path(archive.root) / "change_sets"),
                reconciliation,
                recorded_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"))
            print(f"change set written: {cs_path}")
        except Exception as exc:  # a persistence failure must not fail an otherwise sound ingest
            print(f"[WARN] could not persist the change set: {exc}")
        if reconciliation.blocking and not allow_reconcile_block:
            print("[ERROR] reconciliation found unexplained changes; refusing to write",
                  file=sys.stderr)
            for b in reconciliation.blocking:
                print(f"  - {b}", file=sys.stderr)
            raise SystemExit(2)

    # --- ledger ------------------------------------------------------------
    # Applies on every PDF ingest (D5): the parser default names the live
    # ledger, so `ledger_path` is falsy only on an explicit empty-string opt-out.
    ledger_outcome = None
    if ledger_path:
        ledger = ledger_mod.CorrectionLedger(ledger_path)
        ledger_outcome = ledger.apply(clean, key_of=ledger_mod.default_key)
        # A correction to an identity-bearing field must be reflected in
        # identities, and a confirmed merge (LedgerOutcome.confirmed_pairs)
        # unions its pair before scoring (D5, ledger-confirm-merge).
        projects = merge_mod.merge(clean, confirmed_pairs=ledger_outcome.confirmed_pairs)
        print(ledger_outcome.report())

    # --- archive write-back ------------------------------------------------
    if archive is not None:
        dest, entry = archive.record_ingest(
            pdf, gazette_id,
            published_date=extract_meta.get("published_date", gazette_id),
            record_count=len(records), project_count=len(projects),
            calendar=extract_meta.get("calendar", ""), source_path=pdf,
        )
        print(f"[INFO] archived to {dest}")

        # The publication's own ordering indicator, recorded with its denominator.
        # A departure count is meaningless alone — the same document read with a
        # single-calendar parser reports zero — and an entry left at -1 reads as
        # "never measured" rather than as a measurement. `archive.record_ordering`
        # existed for this and nothing called it, so every real ingestion wrote -1
        # and the trend could only be re-derived by hand from the PDFs. Computed
        # from the records just read rather than by re-reading the document.
        iso_dates = [extract_mod.to_iso(r.get("date") or "")[0] for r in records]
        violations, _worst, _sorted = ordering_mod.departures_from_descending(iso_dates)
        dated = sum(1 for d in iso_dates if d)
        archive.record_ordering(gazette_id, violations, dated)
        print("[INFO] date order: %d departure(s) from descending approval date "
              "across %d dated records" % (violations, dated))

    meta = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": pdf,
        "gazette_id": gazette_id,
        "thresholds": {"link": merge_mod.LINK_THRESHOLD, "flag": merge_mod.FLAG_THRESHOLD},
    }
    if extract_meta.get("published_date"):
        meta["published_date"] = extract_meta["published_date"]

    result.update(raw_recs=raw_recs, clean=clean, projects=projects, meta=meta,
                  tripwire=tw_result, reconciliation=reconciliation,
                  ledger=ledger_outcome, recovery=recovery_outcome)
    return result


def _page_count(pdf: str) -> int:
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        return len(doc)
    finally:
        doc.close()


def _run(pdf: str, outdir: str, no_tsv: bool, viewer_dir: str | None = None, links: bool = False, from_js: str | None = None, fresh: bool = False, playwright: bool = False,
         archive_root=None, use_archive: bool = True, ledger_path=None, allow_reconcile_block: bool = False,
         previous_projects: list[str] | None = None, strict_reconcile: bool = False,
         recover_truncated: bool = False) -> None:
    # Single-writer rule (2026-08-24: four concurrent runs wiped 47 caches).
    # Taken before the first read so a losing run cannot populate the cache it is
    # about to destroy. Covers the archive and ledger as well as outdir.
    with lock_mod.SingleWriterLock(outdir):
        _run_locked(pdf, outdir, no_tsv, viewer_dir, links, from_js, fresh, playwright,
                    archive_root, use_archive, ledger_path, allow_reconcile_block,
                    previous_projects, strict_reconcile, recover_truncated)


def _run_locked(pdf: str, outdir: str, no_tsv: bool, viewer_dir: str | None = None, links: bool = False, from_js: str | None = None, fresh: bool = False, playwright: bool = False,
                archive_root=None, use_archive: bool = True, ledger_path=None, allow_reconcile_block: bool = False,
                previous_projects: list[str] | None = None, strict_reconcile: bool = False,
                recover_truncated: bool = False) -> None:
    # Load projects from JS (primary) or PDF
    if from_js:
        print(f"[INFO] Loading projects from {from_js}")
        projects, meta = _load_projects_from_js(from_js)
        raw_recs = []
        clean = []
        extract_meta = {"published_date": meta.get("published_date", "")}
        tripwire_result = None
        reconciliation = None
        ledger_outcome = None
        recovery_outcome = None
    else:
        ingested = _ingest_pdf(pdf, outdir, archive_root=archive_root,
                               use_archive=use_archive, ledger_path=ledger_path,
                               previous_projects=previous_projects,
                               allow_reconcile_block=allow_reconcile_block,
                               strict_reconcile=strict_reconcile,
                               recover_truncated=recover_truncated)
        projects = ingested["projects"]
        meta = ingested["meta"]
        raw_recs = ingested["raw_recs"]
        clean = ingested["clean"]
        extract_meta = {"published_date": meta.get("published_date", "")}
        tripwire_result = ingested["tripwire"]
        reconciliation = ingested["reconciliation"]
        ledger_outcome = ingested["ledger"]
        recovery_outcome = ingested.get("recovery")

    # Run link discovery if requested
    link_results = {}
    if links:
        from urtpe.coverage import coverage_guard
        from urtpe import permit_sources

        # building-permit-adapter (S15): the 使照 witness's index builds once
        # per run (download cached under the archive root by SHA-256); a
        # failed download reports and the run proceeds without the witness.
        permit_index = permit_sources.load_permit_index(
            archive_root or DEFAULT_ARCHIVE_ROOT)

        if playwright:
            print("[INFO] Running Playwright-based link discovery (experimental)...")
            discovery = links_mod.LinksDiscovery(cache_dir=f"{outdir}/.link_cache")
            # Coverage guard (§12 #1): abort a cache-wiping job before the
            # viewer can be emitted on the regressed state.
            with coverage_guard(Path(f"{outdir}/.link_cache"), [p.project_id for p in projects]):
                link_results = discovery.run(projects, fresh=fresh, use_playwright=True)
        else:
            print("[INFO] Running link discovery with fallback JSON mapping (recommended)...")
            discovery = links_mod.LinksDiscovery(cache_dir=f"{outdir}/.link_cache")
            with coverage_guard(Path(f"{outdir}/.link_cache"), [p.project_id for p in projects]):
                link_results = discovery.run(projects, fresh=fresh)
        discovery.write_crawl_log(link_results, f"{outdir}/crawl_log.tsv")
        # Cache-freshness report (refresh-awaiting-approval-caches D3): a cache
        # written before this gazette cannot know an approval published since, so
        # the lag is named once here rather than discovered in the viewer. The
        # signal is the cache file's mtime — no cache stores a publication date.
        gazette_date = meta.get("published_date") or meta.get("gazette_id") or ""
        if gazette_date:
            stale = sum(
                1 for p in projects
                if links_mod.cache_is_stale_for(f"{outdir}/.link_cache",
                                                p.project_id, gazette_date))
            if stale:
                print(f"[INFO] {stale} of {len(projects)} link caches predate this "
                      f"gazette ({gazette_date}); their cases' newer approvals may be "
                      f"missing — run scripts/refresh_awaiting_caches.py to re-fetch "
                      f"the affected ones")
        resolved = sum(1 for r in link_results.values() if r.status != 'unresolved')
        unresolved = sum(1 for r in link_results.values() if r.status == 'unresolved')
        errors = sum(1 for r in link_results.values() if r.status == 'error')
        print(f"  Done: {resolved} resolved, {unresolved} unresolved, {errors} errors")

    doc = graph_mod.build_graph_document(projects, meta, link_results,
                                         permit_index=(permit_index if links else None))

    # --- emission-fault check (wire-standing-checks) ------------------------
    # Called on every emission path, after link data would have been attached
    # and before anything is written. Wholesale absence of link data is a
    # fault of the run; partial coverage is not. Warning, not refusal --
    # --links stays advisory by design (D5).
    emission_faults = emission_mod.emission_faults(doc["projects"])
    for f in emission_faults:
        print(f"[EMISSION] {f}", file=sys.stderr)

    report = report_mod.review_report(
        raw_recs, clean, projects,
        link_threshold=merge_mod.LINK_THRESHOLD,
        flag_threshold=merge_mod.FLAG_THRESHOLD,
        ledger_outcome=ledger_outcome,
        reconciliation=reconciliation,
        tripwire=tripwire_result,
        recovery=recovery_outcome if recover_truncated else None,
        emission=emission_faults,
    )
    io_mod.write_text(f"{outdir}/review_report.txt", report)

    io_mod.write_json(f"{outdir}/projects.json", doc)

    if not no_tsv and not from_js:
        io_mod.write_text(f"{outdir}/raw.tsv", io_mod.raw_to_tsv(raw_recs))
        io_mod.write_text(f"{outdir}/clean.tsv", io_mod.clean_to_tsv(clean))
        io_mod.write_text(f"{outdir}/merged.tsv", io_mod.merged_to_tsv(projects))
        print(f"raw.tsv: {len(raw_recs)} records")
        print(f"clean.tsv: {len(clean)} records")
        print(f"merged.tsv: {len(clean)} records / {len(projects)} projects")

    total = sum(len(p.members) for p in projects)
    multi = [p for p in projects if len(p.members) > 1]
    print(f"Projects: {len(projects)} (multi-record {len(multi)}) / Total records {total}")
    print(f"review_report.txt, projects.json written to {outdir}")

    if viewer_dir:
        path = viewer_mod.write_projects_js(viewer_dir, doc)
        print(f"Viewer data written to {path}")
        faults = viewer_mod.consistency_faults(doc, path)
        if faults:
            for f in faults:
                print(f"[WARN] {f}", file=sys.stderr)
    else:
        # A run against the repository's own tree refreshes its viewer whether or
        # not a target was named. Leaving this to an optional flag let the page
        # keep serving a dataset an abandoned publication had produced.
        sibling = _repo_viewer_dir(outdir)
        if sibling:
            path = viewer_mod.write_projects_js(sibling, doc)
            print(f"Viewer data written to {path}")


def _repo_viewer_dir(outdir: str) -> str | None:
    """The viewer directory belonging to this output tree, if the tree is ours.

    Identified by an index.html beside the output directory: a scratch run writes
    to a temp directory with no viewer, so it must not reach into the repository.
    """
    candidate = os.path.join(os.path.dirname(os.path.abspath(outdir)), "viewer")
    if os.path.exists(os.path.join(candidate, "index.html")):
        return candidate
    return None


def _build_parser() -> argparse.ArgumentParser:
    """The CLI's argument wiring, split from main() so tests can parse argv
    without running an ingest (the --ledger default is a contract, D5)."""
    parser = argparse.ArgumentParser(description="臺北市都市更新核定案件 PDF 管線")
    parser.add_argument("pdf", nargs="?", default="", help="來源 PDF 路徑 (不需提供若使用 --from-js)")
    parser.add_argument("-o", "--outdir", default="data", help="輸出目錄 (預設 data)")
    parser.add_argument("--no-tsv", action="store_true", help="不輸出 TSV（僅 JSON 圖）")
    parser.add_argument("--viewer", metavar="DIR", default=None,
                        help="同步輸出 viewer/projects.data.js 至指定目錄")
    parser.add_argument("--links", action="store_true", help="啟用官方連結發現 (使用 fallback JSON 映射，推薦)")
    parser.add_argument("--playwright", action="store_true", help="使用 Playwright 自動化爬取 (實驗性，需正確的源資料)")
    parser.add_argument("--fresh", action="store_true", help="強制重新爬取入口網索引與快取頁面")
    parser.add_argument("--from-js", metavar="PATH", default=None,
                        help="從既有 projects.data.js 載入專案資料 (略過 PDF 解析)")
    parser.add_argument("--add-mapping-file", metavar="PATH", default=None,
                        help="從 JSON 文件新增 fallback 映射 (包含 land_core, view_id, case_id)")
    parser.add_argument("--archive-root", metavar="DIR", default=None,
                        help="gazette 封存目錄 (預設為 repo 外的 urtpe-gazettes)")
    parser.add_argument("--no-archive", action="store_true",
                        help="停用封存與 reconciliation (不建議)")
    # The ledger applies on every PDF ingest (D5, ledger-confirm-merge): an
    # operator cannot drop every correction by omitting the option. An explicit
    # empty string still opts out (forensic runs); an absent file reports 0.
    parser.add_argument("--ledger", metavar="PATH",
                        default=str(ledger_mod.DEFAULT_LEDGER_PATH),
                        help="人工修正 ledger 路徑 (JSONL, append-only; 預設 "
                             "urtpe-gazettes/corrections.jsonl，可用 URTPE_LEDGER 覆寫；"
                             "空字串停用)")
    parser.add_argument("--allow-reconcile-block", action="store_true",
                        help="即使 reconciliation 發現未解釋的變更也繼續寫出 (危險)")
    parser.add_argument("--recover-truncated", action="store_true",
                        help="復原被出版方截斷的地號列：自 gis.uro ashx 與 UDD GeoServer "
                             "以四項檢查重新識別並補全 (opt-in；不加此旗標輸出不變)")
    parser.add_argument("--strict-reconcile", action="store_true",
                        help="歷史列消失也視為阻擋 (需 ledger 已記錄接受)")
    parser.add_argument("--archive-only", action="store_true",
                        help="只封存 PDF，不執行完整 pipeline")
    parser.add_argument("--previous-projects-from", metavar="PATH", default=None,
                        help="用於辨識 project_id 搬移的上一版 projects.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.add_mapping_file:
        with open(args.add_mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        add_fallback_mapping(mapping_data['land_core'], mapping_data['view_id'], mapping_data['case_id'])
        return 0

    if not args.from_js and not args.pdf:
        parser.error("需要提供 PDF 路徑或使用 --from-js 指定 projects.data.js")

    if args.archive_only:
        if not args.pdf:
            parser.error("--archive-only 需要 PDF 路徑")
        root = GazetteArchive(args.archive_root)
        gid = extract_mod.gazette_id_for(args.pdf)
        dest, entry = root.record_ingest(
            args.pdf, gid,
            published_date=extract_mod.find_published_date(args.pdf) or gid,
            source_path=args.pdf,
        )
        print(f"archived {gid} -> {dest}")
        print(f"index entries: {len(root.entries())}")
        return 0

    previous_projects = None
    if args.previous_projects_from:
        prev = json.loads(Path(args.previous_projects_from).read_text(encoding="utf-8"))
        previous_projects = [p["project_id"] for p in prev.get("projects", [])]

    try:
        _run(args.pdf or "", args.outdir, args.no_tsv, args.viewer, args.links, args.from_js,
             args.fresh, args.playwright,
             archive_root=args.archive_root, use_archive=not args.no_archive,
             ledger_path=args.ledger,
             allow_reconcile_block=args.allow_reconcile_block,
             previous_projects=previous_projects, strict_reconcile=args.strict_reconcile,
             recover_truncated=args.recover_truncated)
    except extract_mod.TableStructureError as exc:
        # The reader refused the document; nothing was written.
        print(str(exc), file=sys.stderr)
        return 3
    except tripwire_mod.TripwireFailure as exc:
        # The extraction was not provably complete; nothing was written.
        print(str(exc), file=sys.stderr)
        return 4
    except lock_mod.LockHeld as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())