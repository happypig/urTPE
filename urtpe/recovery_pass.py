# -*- coding: utf-8 -*-
"""The recovery pass: resolve marked truncated rows via the city's APIs (tasks 4.5, 5.1).

Runs inside the single-writer ingestion pass, between extraction and
cleansing/merge, only under ``--recover-truncated``. Every row resolves to one of
two outcomes — recovered (with provenance, entering the normal flow) or residual
(excluded and named, exactly the plain exclusion path) — and a source failure
degrades per-row instead of aborting the run:

* an ashx failure means identity could not be confirmed → residual;
* a GeoServer failure after identity closed means only the list stayed unknown →
  fragment + ``partial`` (D-D's fail-safe).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from urtpe import recovery as R
from urtpe.recovery_sources import AshxClient, GeoServerClient, SourceUnavailable

_GEO_ENDPOINT = "zonegeo.udd.gov.taipei/geoserver (WFS)"
_ASHX_ENDPOINT = "gis.uro.taipei/ashx"


@dataclass
class RecoveryOutcome:
    recovered: list[dict] = field(default_factory=list)
    residuals: list[dict] = field(default_factory=list)
    audit: list[str] = field(default_factory=list)


def default_clients() -> tuple[AshxClient, GeoServerClient]:
    return AshxClient(), GeoServerClient()


def recover_marked_rows(marked: list[dict], ashx: AshxClient | None = None,
                        geoserver: GeoServerClient | None = None,
                        memo_source=None) -> RecoveryOutcome:
    """Resolve every marked row; never raise for a source failure.

    ``memo_source`` is the 168 list's 核定公告 date source (a callable
    ``case_id -> iso date or ""``). It is a **flag**, never a date source: the
    核定公告 date is a different date from the 核定日期, and it is empty for
    every case where the publication's date and the platform's date disagree
    (measured 2026-11-06). It is read only when a row's date was recovered.
    """
    ashx = ashx if ashx is not None else AshxClient()
    geoserver = geoserver if geoserver is not None else GeoServerClient()
    outcome = RecoveryOutcome()
    for row in marked:
        recno = row.get("recno") or "?"
        try:
            recovered, audit = _recover_one(row, ashx, geoserver, memo_source)
        except SourceUnavailable as exc:
            outcome.residuals.append(row)
            outcome.audit.append(
                f"編號 {recno}: INCOMPLETE — recovery source unavailable ({exc})")
            continue
        if recovered is None:
            outcome.residuals.append(row)
        else:
            outcome.recovered.append(recovered)
        outcome.audit.append(audit)
    return outcome


def _recover_date(row: dict, ashx: AshxClient,
                  memo_source=None) -> tuple[dict | None, str]:
    """Recover a row whose 核定日期 cell the publisher left empty (D9f-1).

    The mirror image of the 地號 path: the row's identity is intact (its 案名
    and its 地號 cell are complete) and the DATE is what is missing. So the
    candidate is chosen by the name alone — same unit, the declared counts
    agree, the stage ordinal agrees, the track set equals the row's — and the
    accepted candidates must agree on exactly ONE approval date.

    Zero or several dates leave the row a residual: the date would be a guess.

    The 168 list's 核定公告 date is compared as a **second confirmation** and a
    disagreement is recorded as a review flag (D9f-2). The recovered date
    itself comes from the city's own approval date.
    """
    recno = row.get("recno") or "?"
    name = row.get("name") or ""
    identity = R.parse_identity(R.nfkc(name))
    if identity is None:
        return None, (f"編號 {recno}: INCOMPLETE — the 案名 carries no "
                      f"parseable land core")

    family = ashx.case_family(identity.section, identity.mono, identity.suno)
    hits = [c for c in family if R.name_only_candidate(identity, name, c)]
    for cand in hits:
        cid = cand.get("api_case_id") or ""
        if cid:
            top = ashx.case_top(cid)
            cand["uro_chk_date"] = str(top.get("uro_chk_date") or "")
            cand["uro_chk_date2"] = str(top.get("uro_chk_date2") or "")
    iso, cases, seen = R.recover_date_from_name(identity, name, hits)
    if not iso:
        if seen:
            return None, (f"編號 {recno}: INCOMPLETE — the named cases carry "
                          f"{len(seen)} different approval dates "
                          f"({', '.join(seen)}); the date would be a guess")
        return None, (f"編號 {recno}: INCOMPLETE — no candidate carried an "
                      f"approval date ({len(family)} family members, "
                      f"{len(hits)} name hits)")

    # the 168 list's 核定公告 date: a second confirmation, never the source
    memo = ""
    if memo_source is not None:
        for cid in cases:
            try:
                memo = memo_source(cid) or ""
            except Exception:
                memo = ""
            if memo:
                break
    flags = {
        "partial": False,
        "normalized": [],
        "ambiguous-zone": False,
        "date-pm1": False,
        "similarity-band": False,
    }
    recovered = {k: v for k, v in row.items()
                 if k not in ("source_fault", "fault_cause")}
    recovered["date"] = iso
    recovered["recovery"] = {
        "cases": cases,
        "api_cases": cases,
        "endpoint": _ASHX_ENDPOINT,
        "date_result": "exact",
        "date_field": "uro_chk_date/uro_chk_date2",
        "list_source": "the 案名 alone (the 核定日期 cell was empty)",
        "flags": flags,
        "recovered_field": "核定日期",
        "memo_date": memo,
    }
    if memo and memo != iso:
        flags["memo-disagrees"] = True
    audit = (f"編號 {recno}: RECOVERED 核定日期 {iso} "
             f"(cases {','.join(cases) or '?'}, from the 案名 alone)")
    if memo:
        audit += (f", 核定公告 {memo}"
                  + (" — DISAGREES, flagged" if memo != iso else " — agrees"))
    return recovered, audit


def _geo_keys(case_id: str) -> list[str]:
    """Candidate boundary ids for an accepted case: its own id and, when
    suffixed, the base id (R089601-01 → R089601; the suffix distinguishes stage
    groups, and both were measured to carry polygons)."""
    base = re.sub(r"-\d+$", "", case_id)
    keys = [case_id] if case_id else []
    if base and base != case_id:
        keys.append(base)
    return keys


def _recover_one(row: dict, ashx: AshxClient,
                 geoserver: GeoServerClient,
                 memo_source=None) -> tuple[dict | None, str]:
    recno = row.get("recno") or "?"
    if row.get("source_fault") == "truncated_date_cell":
        return _recover_date(row, ashx, memo_source)
    identity = R.parse_identity(row.get("name") or "")
    if identity is None:
        return None, f"編號 {recno}: INCOMPLETE — the 案名 carries no parseable land core"
    iso, _parts = _to_iso(row.get("date") or "")
    if not iso:
        return None, f"編號 {recno}: INCOMPLETE — the 核定日期 does not parse"

    family = ashx.case_family(identity.section, identity.mono, identity.suno)
    # get_project168_top only for name-matching candidates (the measured budget:
    # ≤ 83 requests for 15 rows, poc_findings.md T5)
    hits = [c for c in family if _name_hit(identity, c)]
    dated = list(hits)
    for cand in dated:
        if cand["api_case_id"]:
            top = ashx.case_top(cand["api_case_id"])
            cand["uro_chk_date"] = str(top.get("uro_chk_date") or "")
            cand["uro_chk_date2"] = str(top.get("uro_chk_date2") or "")
    match = R.match_row(identity, iso, dated)
    if match.status != "matched":
        return None, (f"編號 {recno}: INCOMPLETE — no candidate satisfied the four "
                      f"checks ({len(family)} family members, {len(dated)} name hits)")

    cases = [c["case_id"] for c in match.cases if c.get("case_id")]
    flags = {
        "partial": False,
        "normalized": [],
        "ambiguous-zone": "ambiguous-zone" in match.flags,
        "date-pm1": "date-pm1" in match.flags,
        "similarity-band": "similarity-band" in match.flags,
    }

    land = row.get("land") or ""
    list_source = "gazette fragment (partial)"
    declared = identity.declared_count
    repairs: list[str] = []
    if declared is None:
        flags["partial"] = True
    else:
        # try every accepted case; prefer a reconstruction that closes, and keep
        # the first repaired fragment otherwise (a GIS-verified typo is repaired
        # with a flag even when the list stays partial — the 美仁段 outcome)
        closed_result = None
        fallback = None
        for cand in match.cases:
            result = _try_completion(land, cand, identity, declared, geoserver)
            if result is None:
                continue
            repaired_land, repair_pairs, closed = result
            if closed:
                closed_result = (repaired_land, repair_pairs)
                break
            fallback = fallback or (repaired_land, repair_pairs)
        if closed_result:
            repaired_land, repair_pairs = closed_result
            land = repaired_land
            list_source = "gazette fragment + GIS tail"
            repairs = [f"{o}→{n}" for o, n in repair_pairs]
        else:
            flags["partial"] = True
            if fallback:
                repaired_land, repair_pairs = fallback
                land = repaired_land
                repairs = [f"{o}→{n}" for o, n in repair_pairs]
        flags["normalized"] = repairs

    provenance = {
        "cases": cases,
        "api_cases": [c["api_case_id"] for c in match.cases if c.get("api_case_id")],
        "endpoint": _ASHX_ENDPOINT,
        "date_result": match.cases[0]["date_result"],
        "date_field": match.cases[0]["date_field"],
        "list_source": list_source,
        "flags": flags,
    }
    if repairs or list_source == "gazette fragment + GIS tail":
        provenance["endpoint"] = f"{_ASHX_ENDPOINT} + {_GEO_ENDPOINT}"
    recovered = {k: v for k, v in row.items()
                 if k not in ("source_fault", "fault_cause")}
    recovered["land"] = land
    recovered["recovery"] = provenance

    bits = [f"cases {','.join(cases) or '?'}",
            f"date {provenance['date_result']} ({provenance['date_field']})",
            f"list {list_source}"]
    if flags["normalized"]:
        bits.append("normalized " + ";".join(flags["normalized"]))
    audit = f"編號 {recno}: RECOVERED " + ", ".join(bits)
    return recovered, audit


def _try_completion(land: str, cand: dict, identity: R.RowIdentity, declared: int,
                    geoserver: GeoServerClient):
    """Attempt the GIS reconstruction for one accepted case.

    Returns (repaired_land, repairs, closed) when the case carries a boundary
    polygon — the fragment's typos are repaired (D-F) whether or not the
    reconstruction closes — and None when there is no geometry context at all.
    Numeric-form ids are skipped without a request: the boundary layer is
    R-form only (measured, T8).
    """
    for key in _geo_keys(str(cand.get("case_id") or "")):
        if not key.startswith("R"):
            continue
        unit = geoserver.unit_geometry(key, identity.section)
        if not unit.candidates:
            continue  # no polygon under this id; try the next key/case
        repaired, repairs = R.repair_fragment(land, unit.section_parcels,
                                              set(unit.candidates))
        done = R.complete_unit_list(repaired, set(unit.candidates), declared)
        if done.ok:
            # the calibrated rule closed the count: render the whole list as a
            # 地號 cell in the published shape
            return R.rebuild_land_cell(land, done.parcels, declared), repairs, True
        # the count did not close or the fragment was not contained: never pick
        # a subset to force it (T8 refuse-to-ambiguous) — return the repaired
        # fragment for the caller's partial path
        return repaired, repairs, done.ok
    return None


def _name_hit(identity: R.RowIdentity, cand: dict) -> bool:
    """Checks 1–3 on the family row, before spending a get_project168_top call."""
    name = R.normalize_name(cand.get("case_name") or "")
    if not (identity.district in name and identity.section in name):
        return False
    if not (identity.count_fragment and identity.count_fragment in name):
        return False
    if identity.address_core and identity.address_core in name:
        return True
    return R.name_similarity(identity.name, name) >= R.LINK_THRESHOLD


def _to_iso(cell: str) -> tuple[str | None, tuple[int, int, int] | None]:
    from urtpe.extract import to_iso

    return to_iso(cell)
