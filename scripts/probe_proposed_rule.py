"""The widened land-core rule, measured against the corpus. Read-only, offline.

The 7 unplaced projects of docs/coverage-report.html hold 11 nodes. The live
search finds a case id for every one. The pipeline's own resolver binds 3 of
the 11 today, and the name rule refuses 5 more: it cannot read a unit whose
gazette text and the city's index name it differently.

Three separate name defects keep the rule from matching. Each is measured
here, and each is a separate widening:

  A. the 案名's section is wrong, and the 地號 cell's section is right —
     the city indexes the CELL's section (河堤五小段 vs 河堤段五小段,
     萬華段一小段 vs 萬大段一小段);
  B. the gazette omits the 段 from the section — the 案名 AND the cell both
     say 吳興一小段 where the city says 吳興段一小段;
  C. the city declares a parcel that is one of the node's own parcels but
     not its FIRST (吳興's first parcel is 163-2, the city declares 247).

The widening keeps the stage and the kind test, keeps the district and the
count test, and widens only the section and the parcel:

  the section matches when its 小段 suffix agrees and its 段 name agrees
  after dropping a trailing 段 from either side, and a core is read at both
  its first 段 and its last;
  the city's parcel matches when it equals the node's first parcel OR is
  one of the node's own parcels;
  the node's core may be built from the 地號 cell's section as well as the
  案名's.

This probe calls the pipeline's OWN functions — `compute_landcore_similarity`,
`_tier3_names_match`, `_cell_landcore`, `_node_parcels` — so the measurement
cannot drift from the implementation. The baseline is the rule as it stood:
the same tier-3 rule with no alternative core and no parcel set, which is
what the pipeline did before the change.

The risk of a widened rule is over-binding: a case of ANOTHER unit slipping
in. This measures the risk by replaying both rules over every node x
candidate pair the pipeline actually compares, so the change in the binding
set is counted, not assumed.

Read-only, offline.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import pathlib
import re
import sys
from collections import defaultdict
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    _cell_landcore,
    _node_parcels,
    _record_landcore,
    _tier3_names_match,
    extract_landcore_from_case_name,
)

CLEAN = ROOT / "data" / "clean.tsv"
PROJECTS = ROOT / "data" / "projects.json"
CACHE = ROOT / "data" / ".link_cache"

_CELL_SECTION_RE = re.compile(r"^\s*臺北市[^\s]*?區\s*([^\s\d]+)")


def cell_section(land: str) -> str:
    """The 地號 cell's own section."""
    m = _CELL_SECTION_RE.match(land or "")
    return m.group(1) if m else ""


def member_of(row: dict):
    """The record, shaped like the node the resolver reads."""
    m = SimpleNamespace()
    m.recno = int(row["recno"])
    m.date = row["date"]
    m.name = row["name"]
    m.section = row["section"]
    m.section_land = cell_section(row["land"])
    m.first_parcel = row["first_parcel"]
    m.parcels = list(row["parcels"].split("|")) if row["parcels"] else []
    m.district = row["district"]
    m.district_land = row["district_land"]
    m.land_count = (int(row["land_count"]) if row["land_count"] else None)
    m.orig_count = (int(row["orig_count"]) if row["orig_count"] else None)
    return m


def present_rule(row: dict, city_name: str) -> bool:
    """The rule as it stood, before the change.

    It is the tier-3 test over the pipeline's OWN core parse: the section cut
    at its first 段, the sections compared for EXACT equality, the parcel
    compared for exact equality, and the count term costing .10 on a
    mismatch. The change widened the comparison, so the baseline cannot be
    measured with the widened function — it must replay the old one.
    """
    from urtpe.links import (_kind_matches, node_stage_kind, _parse_landcore)
    cs, ck = node_stage_kind(city_name)
    ns, nk = node_stage_kind(row["name"])
    if not (cs and cs == ns and _kind_matches(nk, ck)):
        return False
    node_core = (extract_landcore_from_case_name(row["name"])
                 or _record_landcore(member_of(row)))
    city_core = extract_landcore_from_case_name(city_name)
    if not node_core or not city_core:
        return False
    a_district, a_section, a_parcel, a_count = _parse_landcore(node_core)
    b_district, b_section, b_parcel, b_count = _parse_landcore(city_core)
    if a_district != b_district or a_section != b_section:
        return False
    fp = 0.0
    if a_parcel and b_parcel:
        if a_parcel == b_parcel:
            fp = 1.0
        elif (b_parcel in a_parcel) or (a_parcel in b_parcel):
            fp = 0.95
        elif a_parcel in b_parcel or b_parcel in a_parcel:
            fp = 0.7
    cnt = 1.0 if (a_count and b_count and a_count == b_count) else 0.0
    jac = 1.0 if a_parcel == b_parcel else 0.0
    return (0.35 + 0.2 * fp + 0.3 * jac + 0.1 * cnt) >= 0.85


def widened_rule(row: dict, city_name: str) -> bool:
    """The rule as it stands after the change."""
    member = member_of(row)
    node_core = (extract_landcore_from_case_name(row["name"])
                 or _record_landcore(member))
    alt = tuple(c for c in (_cell_landcore(member),) if c)
    return _tier3_names_match(row["name"], city_name, node_core,
                              node_parcels=_node_parcels(member),
                              alt_landcores=alt)


# the city's own names for the 11 candidates, as the city answered on
# 2026-11-07
CITY_NAMES = {
    "10305021": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
    "11005053": "變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案",
    "10611051": "擬訂臺北市信義區吳興段一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案",
    "10405235": "變更(第二次)臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及變更權利變換計畫案",
    "10011301": "擬訂臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
    "10903061": "變更臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
    "10111171": "擬訂臺北市大安區復興段一小段3地號等5筆土地都市更新事業計畫案",
    "10111173": "變更臺北市大安區復興段一小段3地號等2筆(原5筆)土地都市更新事業計畫案",
    "10002141": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
    "09102220": "擬訂臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫案",
    "09102221": "變更臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及擬訂權利變換計畫案",
}

# the 11 unplaced nodes, and the case the live search found for each
FOUND = {
    122: "10305021", 204: "11005053", 551: "10611051", 706: "10405235",
    993: "10011301", 483: "10903061", 1081: "10111171", 669: "10111173",
    1170: "10002141", 1433: "09102220", 1333: "09102221",
}


def main() -> int:
    rows = {int(r["recno"]): r for r in
            csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t")}
    doc = json.loads(PROJECTS.read_text(encoding="utf-8"))
    project_rows: dict[str, list[dict]] = defaultdict(list)
    for p in doc["projects"]:
        for n in p.get("nodes") or ():
            r = rows.get(int(n["recno"]))
            if r:
                project_rows[p["project_id"]].append(r)

    # ---- part 1: the 11 unplaced nodes ----
    print("=" * 78)
    print("the 11 unplaced nodes under the widened rule")
    print("=" * 78)
    print()
    ok = 0
    for recno, cid in sorted(FOUND.items()):
        row = rows[recno]
        hit = widened_rule(row, CITY_NAMES[cid])
        ok += hit
        member = member_of(row)
        print("  recno %-5s %-10s %-9s  案名 core %-26s cell core %s"
              % (recno, cid, "MATCH" if hit else "NO MATCH",
                 extract_landcore_from_case_name(row["name"]) or "(none)",
                 _cell_landcore(member) or "(none)"))
    print()
    print("  the widened rule matches %d of %d" % (ok, len(FOUND)))
    print()

    # ---- part 2: the over-binding risk over the real pairs ----
    print("=" * 78)
    print("the over-binding risk, over every node x candidate pair")
    print("=" * 78)
    print()
    old_hits = new_hits = 0
    changed = []
    pairs = 0
    for rf in sorted(glob.glob(str(CACHE / "*" / "result.json"))):
        pid = os.path.basename(os.path.dirname(rf))
        try:
            res = json.loads(pathlib.Path(rf).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        names = res.get("candidate_names") or {}
        members = project_rows.get(pid) or []
        if not names or not members:
            continue
        for cid, cname in names.items():
            for r in members:
                pairs += 1
                old = present_rule(r, cname)
                new = widened_rule(r, cname)
                old_hits += old
                new_hits += new
                if old != new:
                    changed.append((pid, r["recno"], cid, old, new))
    print("  pairs examined:            %d" % pairs)
    print("  the present rule matches:  %d" % old_hits)
    print("  the widened rule matches:  %d" % new_hits)
    print("  verdict changes:           %d" % len(changed))
    newly = [c for c in changed if not c[3] and c[4]]
    lost = [c for c in changed if c[3] and not c[4]]
    print("  newly matched:             %d" % len(newly))
    print("  no longer matched:         %d" % len(lost))
    for c in newly[:20]:
        print("      NEW  %s recno %s %s" % (c[0], c[1], c[2]))
    for c in lost[:20]:
        print("      LOST %s recno %s %s" % (c[0], c[1], c[2]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
