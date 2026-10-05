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
from urtpe import extract as extract_mod
from urtpe import graph as graph_mod
from urtpe import io as io_mod
from urtpe import ledger as ledger_mod
from urtpe import links as links_mod
from urtpe import lock as lock_mod
from urtpe import merge as merge_mod
from urtpe import reconcile as reconcile_mod
from urtpe import report as report_mod
from urtpe import tripwire as tripwire_mod
from urtpe import viewer as viewer_mod
from urtpe.archive import GazetteArchive
from urtpe.models import CleanRecord, Project

# Fallback mapping file path
FALLBACK_MAPPING_FILE = Path("data/taipei_case_ids.json")


def add_fallback_mapping(land_core: str, view_id: str, case_id: str) -> None:
    """Add a fallback mapping for land_core -> view_id + case_id."""
    mapping = {}
    if Path("data/taipei_case_ids.json").exists():
        try:
            mapping = json.loads(Path("data/taipei_case_ids.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if land_core not in mapping:
        mapping[land_core] = {"view_id": view_id, "case_ids": []}

    if case_id not in mapping[land_core]["case_ids"]:
        mapping[land_core]["case_ids"].append(case_id)

    mapping[land_core]["view_id"] = view_id

    Path("data/taipei_case_ids.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Write to file instead of printing to avoid encoding issues
    with open("add_mapping.log", "w", encoding="utf-8") as f:
        f.write(f"Added mapping: {land_core} -> view_id={view_id}, case_ids={mapping[land_core]['case_ids']}\n")


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
            if (node.get("orphan") or node.get("recno", 0) < 0
                    or node.get("stage") == "孤兒節點"):
                continue
            # Fallback to project-level district if node lacks it
            node_district = node.get("district", "") or project_district
            node_district_land = node.get("district_land", "") or node_district
            
            # Derive iso_date: graph.py emits date=iso_date, so node.date may
            # already be ISO (YYYY-MM-DD). Only ROC-format strings need conversion.
            node_date = node.get("date", "")
            node_iso_date = node.get("iso_date", "")
            if not node_iso_date and node_date:
                if re.match(r"^\d{4}-\d{2}-\d{2}$", node_date):
                    node_iso_date = node_date  # already ISO — keep as-is
                else:
                    from urtpe.cleanse import roc_to_iso
                    iso, _ = roc_to_iso(node_date)
                    node_iso_date = iso or ""
            
            rec = CleanRecord(
                recno=node["recno"],
                date=node_date,
                iso_date=node_iso_date,
                ymd=tuple(node.get("ymd", (0, 0, 0))) if "ymd" in node else (0, 0, 0),
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
                stage_index=node.get("stage_index", -1),
                track=node.get("track", ""),
                implementer=node.get("implementer", ""),
                planner=node.get("planner", ""),
                auto_fixes=node.get("auto_fixes", []),
                review_flags=node.get("review_flags", []),
            )
            # Restore optional emitted state so --from-js round-trips are
            # lossless even without --links (attach overwrites when it runs)
            if node.get("implementation"):
                rec.implementation = dict(node["implementation"])
            if node.get("links"):
                rec.links = dict(node["links"])
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
                allow_reconcile_block: bool = False, strict_reconcile: bool = False) -> dict:
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

    # --- read --------------------------------------------------------------
    records, extract_meta = extract_mod.extract_pdf_with_meta(pdf)
    if not records:
        raise SystemExit("[ERROR] no records parsed")
    print(f"[INFO] read {len(records)} records ({extract_meta.get('calendar', '?')} calendar)")
    excluded_recnos = {
        int(v) for v in (extract_meta.get("excluded_recnos") or "").split(",")
        if v.strip().isdigit()
    }
    if excluded_recnos:
        print(f"[WARN] {len(excluded_recnos)} record(s) excluded: the publisher "
              f"truncated their 地號 cell and the remainder is not in the PDF "
              f"(編號 {', '.join(str(v) for v in sorted(excluded_recnos))})")

    # --- tripwire ----------------------------------------------------------
    tw = tripwire_mod.Tripwire()
    pages = _page_count(pdf)
    faults = tw.check(records, pages=pages, tables_found=pages,
                      duplicate_recnos=int(extract_meta.get("duplicate_recnos", 0)),
                      excluded_recnos=excluded_recnos)
    raw_recs = extract_mod.to_raw_records(records)
    clean = cleanse_mod.cleanse_all(raw_recs)
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

    # --- reconcile against the archived predecessor ------------------------
    reconciliation = None
    if archive is not None:
        prev_id = archive.predecessor_of(gazette_id)
        previous = None
        if prev_id:
            prev_path = archive.path_of(prev_id)
            if prev_path is not None:
                try:
                    previous, _ = extract_mod.extract_pdf_with_meta(str(prev_path), strict=False)
                except Exception as exc:  # a corrupt archive member must not block ingest
                    print(f"[WARN] archived predecessor {prev_id} unreadable: {exc}")
        ledger = ledger_mod.CorrectionLedger(ledger_path) if ledger_path else None
        reconciliation = reconcile_mod.reconcile(
            previous, records,
            previous_id=prev_id, current_id=gazette_id,
            previous_projects=previous_projects,
            current_projects=[p.project_id for p in projects],
            accepted_removals=ledger.accepted_removals() if ledger else set(),
            strict=strict_reconcile,
        )
        print(reconciliation.report())
        if reconciliation.blocking and not allow_reconcile_block:
            print("[ERROR] reconciliation found unexplained changes; refusing to write",
                  file=sys.stderr)
            for b in reconciliation.blocking:
                print(f"  - {b}", file=sys.stderr)
            raise SystemExit(2)

    # --- ledger ------------------------------------------------------------
    ledger_outcome = None
    if ledger_path:
        ledger = ledger_mod.CorrectionLedger(ledger_path)
        ledger_outcome = ledger.apply(clean, key_of=ledger_mod.default_key)
        # A correction to an identity-bearing field must be reflected in identities.
        projects = merge_mod.merge(clean)
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
                  ledger=ledger_outcome)
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
         previous_projects: list[str] | None = None, strict_reconcile: bool = False) -> None:
    # Single-writer rule (2026-08-24: four concurrent runs wiped 47 caches).
    # Taken before the first read so a losing run cannot populate the cache it is
    # about to destroy. Covers the archive and ledger as well as outdir.
    with lock_mod.SingleWriterLock(outdir):
        _run_locked(pdf, outdir, no_tsv, viewer_dir, links, from_js, fresh, playwright,
                    archive_root, use_archive, ledger_path, allow_reconcile_block,
                    previous_projects, strict_reconcile)


def _run_locked(pdf: str, outdir: str, no_tsv: bool, viewer_dir: str | None = None, links: bool = False, from_js: str | None = None, fresh: bool = False, playwright: bool = False,
                archive_root=None, use_archive: bool = True, ledger_path=None, allow_reconcile_block: bool = False,
                previous_projects: list[str] | None = None, strict_reconcile: bool = False) -> None:
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
    else:
        ingested = _ingest_pdf(pdf, outdir, archive_root=archive_root,
                               use_archive=use_archive, ledger_path=ledger_path,
                               previous_projects=previous_projects,
                               allow_reconcile_block=allow_reconcile_block,
                               strict_reconcile=strict_reconcile)
        projects = ingested["projects"]
        meta = ingested["meta"]
        raw_recs = ingested["raw_recs"]
        clean = ingested["clean"]
        extract_meta = {"published_date": meta.get("published_date", "")}
        tripwire_result = ingested["tripwire"]
        reconciliation = ingested["reconciliation"]
        ledger_outcome = ingested["ledger"]

    # Run link discovery if requested
    link_results = {}
    if links:
        from urtpe.coverage import coverage_guard

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
        resolved = sum(1 for r in link_results.values() if r.status != 'unresolved')
        unresolved = sum(1 for r in link_results.values() if r.status == 'unresolved')
        errors = sum(1 for r in link_results.values() if r.status == 'error')
        print(f"  Done: {resolved} resolved, {unresolved} unresolved, {errors} errors")

    report = report_mod.review_report(
        raw_recs, clean, projects,
        link_threshold=merge_mod.LINK_THRESHOLD,
        flag_threshold=merge_mod.FLAG_THRESHOLD,
        ledger_outcome=ledger_outcome,
        reconciliation=reconciliation,
        tripwire=tripwire_result,
    )
    io_mod.write_text(f"{outdir}/review_report.txt", report)

    doc = graph_mod.build_graph_document(projects, meta, link_results)
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


def main(argv: list[str] | None = None) -> int:
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
    parser.add_argument("--ledger", metavar="PATH", default=None,
                        help="人工修正 ledger 路徑 (JSONL, append-only)")
    parser.add_argument("--allow-reconcile-block", action="store_true",
                        help="即使 reconciliation 發現未解釋的變更也繼續寫出 (危險)")
    parser.add_argument("--strict-reconcile", action="store_true",
                        help="歷史列消失也視為阻擋 (需 ledger 已記錄接受)")
    parser.add_argument("--archive-only", action="store_true",
                        help="只封存 PDF，不執行完整 pipeline")
    parser.add_argument("--previous-projects-from", metavar="PATH", default=None,
                        help="用於辨識 project_id 搬移的上一版 projects.json")
    args = parser.parse_args(argv)

    if args.add_mapping_file:
        import json
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
             previous_projects=previous_projects, strict_reconcile=args.strict_reconcile)
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