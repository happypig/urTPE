"""Would the pipeline's own resolver bind the 7 projects' case ids?

The exploration found a case id for every one of the 11 nodes. That is not
the same as a solution: the resolver has its own acceptance test (the name
comparison in tiers 1-3, then the approval date), and it may refuse a
binding the exploration accepts.

This runs the REAL resolver — `urtpe.links.resolve_node_cases` — with live
adapters, on a fresh in-memory DiscoveryResult. The resolver mutates that
object in place; nothing is written to disk, and data/.link_cache is not
touched.

The result says which of the 11 the pipeline binds as it stands, and which
it refuses. A refusal names the gate that refused.

    python scripts/probe_resolver_acceptance.py [recno]

Live: the city's search, header and stage endpoints. >= 1.2 s between
requests. The request carries a generic browser User-Agent and no contact
address.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    DiscoveryResult,
    fetch_taipei_case_header_api,
    fetch_taipei_milestones_api,
    resolve_node_cases,
    search_taipei_cases_for_node,
)

CLEAN = ROOT / "data" / "clean.tsv"

# the case id the exploration found, per recno
FOUND = {
    122: "10305021", 204: "11005053", 551: "10611051", 706: "10405235",
    993: "10011301", 483: "10903061", 1081: "10111171", 669: "10111173",
    1170: "10002141", 1433: "09102220", 1333: "09102221",
}

# the parcel the search finds the case under
UNDER = {
    122: "414", 204: "399", 551: "330", 706: "163-2", 993: "519-2",
    483: "519-2", 1081: "7", 669: "7", 1170: "928", 1433: "163-2",
    1333: "163-2",
}

_requests = 0


def _pace() -> None:
    global _requests
    _requests += 1
    time.sleep(1.2)


def fetch_header(cid: str) -> dict:
    _pace()
    return fetch_taipei_case_header_api(cid)


def fetch_milestones(cid: str) -> dict:
    _pace()
    return fetch_taipei_milestones_api(cid)


def search(section: str, parcel: str, dropped_out=None, anchor_name: str = ""):
    _pace()
    return search_taipei_cases_for_node(section, parcel)


def member_of(row: dict):
    m = type("M", (object,), {})()
    m.recno = int(row["recno"])
    m.date = row["date"]
    m.name = row["name"]
    m.stage = row["stage"]
    m.track = row["track"]
    m.section = row["section"]
    m.first_parcel = row["first_parcel"]
    m.parcels = list(row["parcels"].split("|")) if row["parcels"] else []
    m.district = row["district"]
    m.district_land = row["district_land"]
    m.land_count = row["land_count"]
    m.named_anchor = row["named_anchor"]
    m.review_flags = []
    return m


def main() -> int:
    rows = {int(r["recno"]): r for r in
            csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t")}
    want = [int(a) for a in sys.argv[1:]] or sorted(FOUND)

    bound_ok = 0
    bound_other = 0
    unbound = 0
    for recno in want:
        row = rows[recno]
        member = member_of(row)
        disc = DiscoveryResult(project_id="probe-%d" % recno, land_core="")
        got = resolve_node_cases(member, disc, fetch_header=fetch_header,
                                 fetch_milestones=fetch_milestones,
                                 search=search)
        want_id = FOUND[recno]
        print()
        print("=" * 78)
        print("recno %-5s %s" % (recno, row["date"]))
        print("  案名 %s" % row["name"][:68])
        print("  section %-12s parcels %s" % (row["section"], member.parcels))
        print("  the exploration found %s (under parcel %s)"
              % (want_id, UNDER[recno]))
        print("  the resolver bound: %s" % (got or "NOTHING"))
        if want_id in got:
            print("  -> the resolver binds the SAME id")
            bound_ok += 1
        elif got:
            print("  -> the resolver binds a DIFFERENT id")
            bound_other += 1
        else:
            print("  -> the resolver binds NOTHING")
            unbound += 1
        if disc.search_rejected:
            print("  search_rejected: %s" % list(disc.search_rejected))
        if disc.case_headers:
            for cid, hdr in disc.case_headers.items():
                print("  header %-10s %s | %s | %s"
                      % (cid, hdr.get("NAME", "")[:44],
                         hdr.get("uro_chk_date", ""), hdr.get("uro_chk_date2", "")))

    print()
    print("=" * 78)
    print("the resolver binds the same id on %d of %d nodes"
          % (bound_ok, len(want)))
    print("  a different id:   %d" % bound_other)
    print("  nothing:          %d" % unbound)
    print("  requests made:    %d" % _requests)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
