"""A section string that drifts splits one unit into two families. Read-only.

The 7 unplaced projects of docs/coverage-report.html hold 11 nodes. The live
search finds a case id for every one. Five of the eleven are bound by a
NAME comparison the resolver's tier-3 rule refuses, and the reason is one
shape: the 案名 and the 地號 cell carry DIFFERENT section strings for the
same unit.

  the 案名 says     the 地號 cell says   the city indexes
  河堤五小段       河堤段五小段         河堤段五小段
  萬華段一小段     萬大段一小段         萬大段一小段
  吳興一小段       —                   吳興段一小段

Two readers cut a section at a different place, so the same unit reads as
two:

  the merge (urtpe/merge.py _candidates) groups candidate pairs by
  (district, section) EXACTLY, so the two forms never meet;
  the land-core parser (urtpe/links.py _parse_landcore) cuts a section at
  its FIRST 段, so 河堤段五小段 parses as section 河堤段 with the parcel
  五小段399 — and the tier-3 name rule needs the two sections to match.

This measures how many records the shape touches, and how many units it
splits into more than one family.

Read-only, offline.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLEAN = ROOT / "data" / "clean.tsv"
PROJECTS = ROOT / "data" / "projects.json"

# the 地號 cell's own section, read from the cell's text
_CELL_SECTION_RE = re.compile(r"^\s*臺北市[^\s]*?區\s*([^\s\d]+)")


def cell_section(land: str) -> str:
    """The section the 地號 cell names, if it names one."""
    m = _CELL_SECTION_RE.match(land or "")
    return m.group(1) if m else ""


def main() -> int:
    rows = list(csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t"))
    doc = json.loads(PROJECTS.read_text(encoding="utf-8"))
    recno_project = {}
    for p in doc["projects"]:
        for n in p.get("nodes") or ():
            recno_project[int(n["recno"])] = p["project_id"]

    print("=" * 78)
    print("the records whose 案名 section and 地號 cell section differ")
    print("=" * 78)
    print()
    differing = []
    for r in rows:
        name_sec = r["section"]
        cell_sec = cell_section(r["land"])
        if cell_sec and cell_sec != name_sec:
            differing.append((r, name_sec, cell_sec))
    print("  records: %d" % len(rows))
    print("  the two sections differ on %d" % len(differing))
    print()

    # The unit's identity, per the domain rules: the district, the first
    # parcel and the land count. The section is NOT part of it — a section
    # string that drifts between the 案名 and the 地號 cell must not split
    # one unit in two.
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[(r["district"], r["first_parcel"], r["land_count"])].append(r)

    print("=" * 78)
    print("the units the shape splits into more than one family")
    print("=" * 78)
    print()
    split = 0
    split_units = []
    for key, rs in sorted(by_unit.items()):
        pids = {recno_project.get(int(r["recno"])) for r in rs}
        if len(pids) > 1:
            split += 1
            secs = sorted({r["section"] for r in rs})
            split_units.append((key, rs, pids, secs))
            print("  %s %s 地號等%s筆  sections %s"
                  % (key[0], key[1], key[2], secs))
            for pid in sorted(pids):
                rs2 = [r for r in rs if recno_project.get(int(r["recno"])) == pid]
                print("      %-46s recnos %s"
                      % (pid, sorted(r["recno"] for r in rs2)))
            # is this split the section drift's doing?
            drifts = any(cell_section(r["land"]) and cell_section(r["land"]) != r["section"]
                         for r in rs)
            print("      the section drift is present: %s" % ("yes" if drifts else "NO"))
            print()
    print("  units split into more than one family: %d of %d" % (split, len(by_unit)))
    print()

    # which of the 7 unplaced projects sit in a split unit
    print("=" * 78)
    print("the 7 unplaced projects, and the unit each belongs to")
    print("=" * 78)
    print()
    unplaced = ["中正區-河堤五小段-399地號等3筆",
                "中正區-臨沂段三小段-412地號等12筆",
                "信義區-吳興一小段-330地號等43筆",
                "信義區-吳興段二小段-163-2地號等2筆",
                "大安區-復興段一小段-3地號等2筆",
                "大安區-懷生段一小段-928地號等1筆",
                "萬華區-萬華段一小段-519-2地號等35筆"]
    for pid in unplaced:
        recnos = [n["recno"] for p in doc["projects"] if p["project_id"] == pid
                  for n in p.get("nodes") or ()]
        r0 = next((r for r in rows if int(r["recno"]) == recnos[0]), None)
        if r0 is None:
            continue
        key = (r0["district"], r0["first_parcel"], r0["land_count"])
        others = [r for r in by_unit[key] if r["recno"] != r0["recno"]]
        other_pids = sorted({recno_project.get(int(r["recno"])) for r in others})
        print("  %s" % pid)
        print("      recnos %s | 案名 section %-12s | 地號 cell section %s"
              % (recnos, r0["section"], cell_section(r0["land"]) or "-"))
        print("      the same unit elsewhere in the corpus: %s"
              % (other_pids or "none"))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
