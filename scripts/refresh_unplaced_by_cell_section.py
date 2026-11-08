#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bind-the-unplaced-by-searching-the-cell-section: refresh the 7 projects.

The 7 projects of docs/coverage-report.html 問題一 carry no city case id: their
11 nodes carry the flag 節點未能對應平台案件. The widened land-core comparison
(the change's group 2) lets the resolver read a unit whose 案名 and 地號
columns disagree about the 段小段, and the portal's title search (group 5)
reaches a unit the parcel search does not index at all.

This driver refreshes those 7 projects' caches, one at a time, under the
single-writer lock. It writes into ``data/.link_cache/`` only.

    python scripts/refresh_unplaced_by_cell_section.py [--dry-run] [--delay 1.2]

Live: the city's parcel-search, header, milestones and 168-list endpoints, and
the national portal's title search. >= ``--delay`` seconds between requests.
The requests carry a generic browser User-Agent and no contact address.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    fetch_portal_title_search,
    refresh_project,
)
from urtpe.lock import SingleWriterLock  # noqa: E402

CACHE_DIR = ROOT / "data" / ".link_cache"

# the 11 nodes of the 7 unplaced projects, and the case the live search found
# for each (probe_missing_case_ids.py, live 2026-11-07)
UNPLACED_RECNO = {122, 204, 551, 706, 993, 483, 1081, 669, 1170, 1433, 1333}
FOUND = {
    122: "10305021", 204: "11005053", 551: "10611051", 706: "10405235",
    993: "10011301", 483: "10903061", 1081: "10111171", 669: "10111173",
    1170: "10002141", 1433: "09102220", 1333: "09102221",
}

_last_request = [0.0]


def _pace(delay: float) -> None:
    """Keep the requests >= delay apart (the standing live-request rule)."""
    now = time.monotonic()
    wait = delay - (now - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.monotonic()


def _search_key(project: dict) -> tuple:
    """The (section, first parcel, anchor name, every parcel, cell section)
    the refresh searches by.

    The 4th element is the unit's own parcel list: the city indexes a case
    under whichever parcel it lists first, and that is not always the unit's
    first (臨沂段三小段412's case is indexed under 414, 復興段一小段3's under
    7). The 5th is the 地號 cell's section, which the city indexes when the
    案名 and the cell disagree (河堤五小段 vs 河堤段五小段)."""
    anchor = next((n for n in project["nodes"]
                   if n["recno"] == project["anchor_recno"]), project["nodes"][0])
    parcels = list(anchor.get("parcels") or [])
    cell_section = ""
    from urtpe.cleanse import cell_section as parse_cell_section
    cell_section = parse_cell_section(anchor.get("land") or "")
    return (anchor.get("section", ""), anchor.get("first_parcel", ""),
            (anchor.get("case_name") or anchor.get("name") or "")[:40],
            parcels, cell_section)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=1.2)
    args = ap.parse_args(argv)

    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    targets = []
    for p in doc["projects"]:
        recnos = {int(n["recno"]) for n in p.get("nodes") or ()}
        if recnos & UNPLACED_RECNO:
            targets.append(p)

    print("the 7 unplaced projects:", len(targets))
    for p in targets:
        section, parcel, _name, _parcels, _cell = _search_key(p)
        recnos = sorted({int(n["recno"]) for n in p["nodes"]} & UNPLACED_RECNO)
        want = [FOUND[r] for r in recnos]
        print("   %-46s section=%-14s parcel=%-10s nodes=%s want=%s"
              % (p["project_id"], section, parcel, recnos, want))
    if args.dry_run:
        print("would refresh those projects")
        return 0

    # the portal's title search, paced like every other live request
    def fetch_portal(section: str, city_id: str = "2") -> list[dict]:
        _pace(args.delay)
        return fetch_portal_title_search(section, city_id,
                                         cache_dir=CACHE_DIR)

    report = []
    with SingleWriterLock(ROOT / "data"):
        for p in targets:
            pid = p["project_id"]
            key = _search_key(p)
            try:
                r = refresh_project(CACHE_DIR, pid, search_key=key,
                                    fetch_portal=fetch_portal)
            except Exception as exc:
                print(f"  FAILED {pid}: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                report.append({"project_id": pid, "error": f"{type(exc).__name__}: {exc}"})
                continue
            added = r.get("added") or []
            unconfirmed = r.get("unconfirmed") or []
            recnos = sorted({int(n["recno"]) for n in p["nodes"]} & UNPLACED_RECNO)
            want = [FOUND[r] for r in recnos]
            now = json.loads((CACHE_DIR / pid / "result.json").read_text(
                encoding="utf-8")).get("city_case_ids") or []
            report.append({"project_id": pid, "added": added,
                           "unconfirmed": unconfirmed,
                           "error": r.get("error"),
                           "want": want, "now": now})
            print("%-46s added=%s unconfirmed=%s"
                  % (pid, [a["case_id"] for a in added], unconfirmed))
            print("%-46s   the case ids now: %s" % ("", now))

    print()
    print("ids added:", sum(len(x.get("added") or []) for x in report))
    print("ids unconfirmed:", sum(len(x.get("unconfirmed") or []) for x in report))
    for x in report:
        if x.get("error"):
            print("  ERROR", x["project_id"], x["error"])
    Path(ROOT / "data" / "unplaced_by_cell_section_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
