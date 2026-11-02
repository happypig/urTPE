#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the link caches whose cases were awaiting approval when last written.

A project cache is written once and returned on every later emission without
re-fetching, so a case approved after that moment never reaches the payload:
`_match_case_by_date` finds no matching case, the per-node attach falls to the
positional fallback (`city_case_ids[0]`), and the node wears the wrong case —
which then drives the graph's row order (measured on 通化段四小段-336,
refresh-awaiting-approval-caches).

This pass re-fetches ONLY the projects whose cached cases carry an
application-for-approval date and no approval date — the state a case is in
between applying and receiving approval. Measured 2026-11-02: 21 of 726 projects.
Every other cached field is preserved.

Single-writer rule (AGENTS.md): do not run this while an ingestion or a sweep
owns the cache.

    python scripts/refresh_awaiting_caches.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    cached_cases_awaiting_approval,
    refresh_project,
    resolve_cache_dir,
)


def select_candidates(cache_dir: Path) -> list[str]:
    """Projects whose cached cases await an approval — no API call needed."""
    out: list[str] = []
    for entry in sorted(cache_dir.iterdir()):
        rf = entry / "result.json"
        if not rf.is_file():
            continue
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # refresh-case-status D5: a case closed without approval is no reason to
        # re-fetch, so the cached statuses go to the selector too.
        # supersede-headerless-cases D5: a 無-header or superseded case is no
        # reason either.
        if cached_cases_awaiting_approval(data.get("case_milestones"),
                                          data.get("case_schedules"),
                                          data.get("case_headers"),
                                          data.get("superseded_by")):
            out.append(str(data.get("project_id") or entry.name))
    return out


def load_search_keys(payload: Path) -> dict[str, tuple[str, str, str]]:
    """{project_id: (section, first_parcel, anchor 案名)} from the emitted payload.

    supersede-headerless-cases D4: the same inputs discovery searched with — the
    anchor record's 地段, first 地號 and 案名 (which corroborates a named-area
    case). Read, never parsed from project_id: the id churns and 6 do not parse.
    """
    if not payload.is_file():
        return {}
    text = payload.read_text(encoding="utf-8").strip()
    doc = json.loads(text[len("window.PROJECTS ="):].rstrip().rstrip(";"))
    keys: dict[str, tuple[str, str, str]] = {}
    for p in doc.get("projects", []):
        anchor = next((n for n in p.get("nodes", [])
                       if n.get("recno") == p.get("anchor_recno")), None)
        if anchor and anchor.get("section") and anchor.get("first_parcel"):
            keys[p["project_id"]] = (anchor["section"], str(anchor["first_parcel"]),
                                     anchor.get("case_name") or "")
    return keys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(ROOT / "data" / ".link_cache"))
    ap.add_argument("--payload", default=str(ROOT / "viewer" / "projects.data.js"),
                    help="emitted payload the anchor search keys are read from")
    ap.add_argument("--dry-run", action="store_true",
                    help="list the candidates and stop")
    args = ap.parse_args(argv)

    cache_dir = Path(args.cache)
    if not cache_dir.is_dir():
        print(f"no cache directory at {cache_dir}", file=sys.stderr)
        return 1

    candidates = select_candidates(cache_dir)
    print(f"candidates (a case awaits approval): {len(candidates)}")
    if args.dry_run:
        for pid in candidates:
            print(f"  {pid}")
        return 0

    failures = 0
    totals = {"updated": 0, "status_changes": 0, "removed": 0, "conflicts": 0,
              "closed": 0, "still_awaiting": 0, "added": 0, "superseded": 0,
              "no_successor": 0, "ambiguous": 0}
    keys = load_search_keys(Path(args.payload))
    not_searched = 0
    for pid in candidates:
        report = refresh_project(cache_dir, pid, search_key=keys.get(pid))
        if report.get("error"):
            failures += 1
            print(f"  FAILED {pid}: {report['error']}", file=sys.stderr)
            continue
        for key in totals:
            totals[key] += len(report.get(key) or [])
        for u in report["updated"]:
            print(f"  {pid}\n    {u['case_id']}: {u['was'] or '(none)'} -> {u['核定日期']}")
        # refresh-case-status-and-drop-withdrawn-fields: each status change names
        # the header NAME it came from; each dropped date and each kept
        # approval-date conflict is printed — the effect must be auditable.
        for c in report.get("status_changes") or []:
            print(f"  {pid}: status {c['case_id']}: {c['was'] or '(none)'} -> "
                  f"{c['now'] or '(cleared)'}  [NAME {c['name'] or '(empty)'}]")
        for r in report.get("removed") or []:
            print(f"  {pid}: removed {r['case_id']} {r['label']} {r['was']} "
                  f"(no longer on the platform)")
        for r in report.get("conflicts") or []:
            print(f"  {pid}: CONFLICT {r['case_id']} {r['label']} {r['was']} "
                  f"absent from the platform reply; kept")
        if report.get("not_searched"):
            not_searched += 1
            print(f"  {pid}: not searched (no anchor 地段/地號 in the payload)")
        for a in report.get("added") or []:
            print(f"  {pid}: ADDED {a['case_id']} [{a['schedule'] or '(no status)'}] "
                  f"[NAME {a['name'] or '(empty)'}]")
        for sp in report.get("superseded") or []:
            diff = ", ".join(sp.get("differs") or []) or "none"
            print(f"  {pid}: superseded {sp['case_id']} -> {sp['by']} "
                  f"(header 無, re-filed; dates that differ: {diff})")
        if report.get("no_successor"):
            print(f"  {pid}: header 無, no successor found: {', '.join(report['no_successor'])}")
        if report.get("ambiguous"):
            print(f"  {pid}: header 無, ambiguous successor: {', '.join(report['ambiguous'])}")
        if report.get("closed"):
            print(f"  {pid}: closed without approval: {', '.join(report['closed'])}")
        if report["still_awaiting"]:
            print(f"  {pid}: still awaiting approval: {', '.join(report['still_awaiting'])}")

    print(f"\n{len(candidates)} project(s); {totals['updated']} approval date(s) updated; "
          f"{totals['status_changes']} status change(s); {totals['removed']} date(s) removed; "
          f"{totals['conflicts']} conflict(s); {totals['closed']} case(s) closed without "
          f"approval; {totals['still_awaiting']} case(s) still awaiting; "
          f"{totals['added']} case(s) added by search; {totals['superseded']} superseded; "
          f"{totals['no_successor']} 無 without successor; {totals['ambiguous']} ambiguous; "
          f"{not_searched} not searched; {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
