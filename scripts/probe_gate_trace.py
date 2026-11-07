"""Which gate refuses each of the 11 nodes. Read-only, live.

The exploration found a case id for every one of the 11 nodes of the 7
unplaced projects. The pipeline's own resolver binds only 3 of them. This
traces the resolver's gates, in order, for each node, and names the gate
that refuses.

The resolver's step 4 (the parcel search) is a chain:

  1. the search must RETURN the candidate — the search asks for the node's
     own section, and the city indexes the case under a different string;
  2. the name must match — tier 1 (loose equality) or tier 3 (stage + kind
     + land-core similarity >= 0.85);
  3. the approval date must match EXACTLY — the header's 核定日期 or
     權變核定日期 against the node's date.

A node that fails gate 1 needs a section the city indexes. A node that
fails gate 2 needs a name the comparison can read. A node that fails gate 3
needs the drift rule, which step 4 does not have.

Reads the city and the corpus. Writes nothing.

    python scripts/probe_gate_trace.py [recno]

Live: the city's search and header endpoints. >= 1.2 s between requests.
The request carries a generic browser User-Agent and no contact address.
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
    _iso_date,
    _probe_name_ok,
    fetch_taipei_case_header_api,
    node_name_loose,
    search_taipei_cases_for_node,
)

CLEAN = ROOT / "data" / "clean.tsv"

# recno -> (the case id the exploration found, the parcel it hides under)
FOUND = {
    122: ("10305021", "414"), 204: ("11005053", "399"),
    551: ("10611051", "330"), 706: ("10405235", "163-2"),
    993: ("10011301", "519-2"), 483: ("10903061", "519-2"),
    1081: ("10111171", "7"), 669: ("10111173", "7"),
    1170: ("10002141", "928"), 1433: ("09102220", "163-2"),
    1333: ("09102221", "163-2"),
}

# the section strings the city is known to index for these units, and the
# node's own section (the 案名's)
SECTION_FORMS = {
    204: ["河堤五小段", "河堤段五小段"],
    551: ["吳興一小段", "吳興段一小段"],
    993: ["萬華段一小段", "萬大段一小段"],
    483: ["萬華段一小段", "萬大段一小段"],
}

_cache: dict[tuple[str, str], list[dict]] = {}
_requests = 0


def _pace() -> None:
    global _requests
    _requests += 1
    time.sleep(1.2)


def search(section: str, parcel: str) -> list[dict]:
    key = (section, parcel)
    if key not in _cache:
        _pace()
        _cache[key] = search_taipei_cases_for_node(section, parcel) or []
    return _cache[key]


def header(cid: str) -> dict:
    _pace()
    try:
        return fetch_taipei_case_header_api(cid) or {}
    except Exception:
        return {}


def trace(recno: int, row: dict) -> str:
    cid, parcel = FOUND[recno]
    node_name = row["name"]
    node_section = row["section"]
    forms = SECTION_FORMS.get(recno, [node_section])

    print()
    print("=" * 78)
    print("recno %-5s %s" % (recno, row["date"]))
    print("  案名 %s" % node_name[:68])
    print("  the node's section %s | the candidate %s under parcel %s"
          % (node_section, cid, parcel))
    print("=" * 78)

    # ---- gate 1: does the search return the candidate at all? ----
    hit_form = None
    for form in forms:
        hits = search(form, parcel)
        names = [h.get("case_name", "") for h in hits]
        got = [h for h in hits if h.get("case_id") == cid]
        print("  gate 1  search(%s, %s) -> %d hit(s)%s"
              % (form, parcel, len(hits),
                 "  <- the candidate is here" if got else ""))
        for h in hits[:6]:
            mark = "  <== the candidate" if h.get("case_id") == cid else ""
            print("            %-10s %s%s"
                  % (h.get("case_id", ""), h.get("case_name", "")[:52], mark))
        if got and hit_form is None:
            hit_form = form
    if hit_form is None:
        print("  GATE 1 FAILS: the parcel search never returns %s under %s"
              % (cid, " / ".join(forms)))
        print("             (the case is not indexed by the parcel search)")
        return "portal"

    # ---- gate 2: does the name match? ----
    hits = search(hit_form, parcel)
    case_name = next(h["case_name"] for h in hits if h.get("case_id") == cid)
    loose = node_name_loose(case_name) == node_name_loose(node_name)
    tier3 = _probe_name_ok(case_name, node_name)
    print()
    print("  gate 2  the city's name %s" % case_name[:68])
    print("            tier 1 (loose equality): %s" % ("yes" if loose else "NO"))
    print("            tier 3 (stage+kind+core): %s" % ("yes" if tier3 else "NO"))
    if not (loose or tier3):
        print("  GATE 2 FAILS: the name comparison refuses the pair")
        return "name"

    # ---- gate 3: does the date match exactly? ----
    top = header(cid)
    dates = [str(top.get(f, "") or "") for f in ("uro_chk_date", "uro_chk_date2")]
    dates = [d for d in dates if d]
    target = _iso_date(row["date"]) or row["date"]
    exact = any(_iso_date(d) == target for d in dates)
    print()
    print("  gate 3  the node's date %s" % target)
    print("            the case's approval %s" % (dates or "(none)"))
    print("            an exact match: %s" % ("yes" if exact else "NO"))
    if not exact:
        print("  GATE 3 FAILS: the approval date is not the node's date")
        return "date"
    print()
    print("  -> the resolver BINDS %s" % cid)
    return "bound"


def main() -> int:
    rows = {int(r["recno"]): r for r in
            csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t")}
    want = [int(a) for a in sys.argv[1:]] or sorted(FOUND)
    verdicts = {}
    for recno in want:
        verdicts[recno] = trace(recno, rows[recno])

    print()
    print("=" * 78)
    print("the gate that refuses each node")
    print("=" * 78)
    counts = {}
    for recno, v in verdicts.items():
        counts[v] = counts.get(v, 0) + 1
        print("  recno %-5s %s" % (recno, v))
    print()
    for v, n in sorted(counts.items()):
        print("  %-8s %d" % (v, n))
    print("  requests made: %d" % _requests)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
