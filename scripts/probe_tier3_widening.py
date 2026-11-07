"""What a widened tier-3 rule would change. Read-only, offline.

The 7 unplaced projects of docs/coverage-report.html hold 11 nodes. The live
search finds a case id for every one. The pipeline's own resolver binds only
3, because the tier-3 name rule (stage + kind + land-core similarity >= 0.85)
cannot read a unit whose 案名 and 地號 cell name it differently.

Two proposed widenings, measured here against the WHOLE corpus:

  A. the node's core may be built from the 地號 cell's section as well as
     the 案名's, and the city core is compared against both;
  B. the comparison accepts a city core whose first parcel is ANY parcel of
     the node's own parcel set, not only its first parcel.

The risk of a widened rule is over-binding: a case of ANOTHER unit slipping
in. This measures the risk by replaying the rule over every cached
candidate name, so the change in the binding set is counted, not assumed.

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
CACHE = ROOT / "data" / ".link_cache"

_CELL_SECTION_RE = re.compile(r"^\s*臺北市[^\s]*?區\s*([^\s\d]+)")


def cell_section(land: str) -> str:
    m = _CELL_SECTION_RE.match(land or "")
    return m.group(1) if m else ""


def parse_core(lc: str) -> tuple[str, str, str, str]:
    """(district, section, first_parcel, count) from a core string.

    The section is cut at the LAST 段, so 河堤段五小段 reads as one section
    name and not as section 河堤段 with parcel 五小段399.
    """
    district = section = parcel = count = ""
    m = re.match(r"(.+?區)", lc)
    if m:
        district = m.group(1)
        rest = lc[len(district):]
    else:
        rest = lc
    m = re.match(r"(.+?)地號", rest)
    if m:
        head = m.group(1)
        rest = rest[len(m.group(1)) + 2:]
        i = head.rfind("段")
        if i >= 0:
            section, parcel = head[:i + 1], head[i + 1:]
        else:
            parcel = head
    m = re.search(r"等(\d+)筆", lc)
    if m:
        count = m.group(1)
    return district, section, parcel, count


def core_of(district: str, section: str, parcel: str, count: str) -> str:
    return "%s%s%s地號等%s筆" % (district, section, parcel, count)


def similar(node_core: str, city_core: str, node_parcels=()) -> bool:
    """The widened tier-3 land-core comparison.

    The district, the section and the count must agree; the city's first
    parcel must equal the node's first parcel OR be one of the node's own
    parcels. The section comparison is exact — the widenings are in WHICH
    core is used, not in how two sections are compared.
    """
    nd, ns, np_, nc = parse_core(node_core)
    cd, cs, cp, cc = parse_core(city_core)
    if not (nd and cd and nd == cd):
        return False
    if not (ns and cs and ns == cs):
        return False
    if nc and cc and nc != cc:
        return False
    if not np_ or not cp:
        return False
    if np_ == cp:
        return True
    # widening B: the city's declared parcel is one of the node's parcels
    return bool(node_parcels) and cp in node_parcels


def main() -> int:
    rows = {int(r["recno"]): r for r in
            csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t")}

    # ---- the 11 nodes, under the widened rule ----
    print("=" * 78)
    print("the 11 unplaced nodes under the widened rule")
    print("=" * 78)
    print()
    FOUND = {
        122: ("10305021", "中正區", "臨沂段三小段", "412", "12"),
        204: ("11005053", "中正區", "河堤五小段", "399", "3"),
        551: ("10611051", "信義區", "吳興一小段", "330", "43"),
        706: ("10405235", "信義區", "吳興段二小段", "247", "2"),
        993: ("10011301", "萬華區", "萬華段一小段", "519-2", "35"),
        483: ("10903061", "萬華區", "萬華段一小段", "519-2", "35"),
        1081: ("10111171", "大安區", "復興段一小段", "3", "5"),
        669: ("10111173", "大安區", "復興段一小段", "3", "2"),
        1170: ("10002141", "大安區", "懷生段一小段", "928", "1"),
        1433: ("09102220", "信義區", "吳興段二小段", "247", "2"),
        1333: ("09102221", "信義區", "吳興段二小段", "247", "2"),
    }
    CITY = {
        "10305021": ("中正區", "臨沂段三小段", "412", "12"),
        "11005053": ("中正區", "河堤段五小段", "399", "3"),
        "10611051": ("信義區", "吳興段一小段", "330", "43"),
        "10405235": ("信義區", "吳興段二小段", "247", "2"),
        "10011301": ("萬華區", "萬大段一小段", "519-2", "35"),
        "10903061": ("萬華區", "萬大段一小段", "519-2", "35"),
        "10111171": ("大安區", "復興段一小段", "3", "5"),
        "10111173": ("大安區", "復興段一小段", "3", "2"),
        "10002141": ("大安區", "懷生段一小段", "928", "1"),
        "09102220": ("信義區", "吳興段二小段", "247", "2"),
        "09102221": ("信義區", "吳興段二小段", "247", "2"),
    }
    ok = 0
    for recno, (cid, dist, sec, parcel, count) in sorted(FOUND.items()):
        row = rows[recno]
        parcels = tuple(row["parcels"].split("|")) if row["parcels"] else ()
        cell = cell_section(row["land"])
        name_core = core_of(dist, sec, parcel, count)
        cell_core = core_of(dist, cell, parcel, count) if cell else ""
        cd, cs, cp, cc = CITY[cid]
        city_core = core_of(cd, cs, cp, cc)
        hit_name = similar(name_core, city_core, parcels)
        hit_cell = similar(cell_core, city_core, parcels) if cell_core else False
        verdict = "MATCH" if (hit_name or hit_cell) else "NO MATCH"
        if hit_name or hit_cell:
            ok += 1
        print("  recno %-5s %-10s %-8s  via %-9s %s"
              % (recno, cid, verdict,
                 "案名 core" if hit_name else ("地號 cell core" if hit_cell else "-"),
                 "(the cell says %s)" % cell if cell and cell != sec else ""))
    print()
    print("  the widened rule matches %d of %d" % (ok, len(FOUND)))
    print()

    # ---- the over-binding risk: replay over every cached candidate name ----
    print("=" * 78)
    print("the over-binding risk, measured over every cached candidate name")
    print("=" * 78)
    print()
    from urtpe.links import _tier3_names_match, extract_landcore_from_case_name

    # the project's OWN nodes — the pairs the resolver actually compares.
    # A candidate name is compared against the nodes of its own project
    # only; pairing it against every record in the district measures
    # something the resolver never does.
    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    project_rows: dict[str, list[dict]] = defaultdict(list)
    for p in doc["projects"]:
        for n in p.get("nodes") or ():
            r = rows.get(int(n["recno"]))
            if r:
                project_rows[p["project_id"]].append(r)

    old_hits = new_hits = 0
    changed = []
    pairs_seen = 0
    for d in sorted(CACHE.iterdir()):
        rf = d / "result.json"
        if not rf.is_file() or d.name.startswith("."):
            continue
        try:
            res = json.loads(rf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        names = res.get("candidate_names") or {}
        if not names:
            continue
        members = project_rows.get(d.name) or []
        if not members:
            continue
        for cid, cname in names.items():
            for r in members:
                pairs_seen += 1
                node_core = extract_landcore_from_case_name(r["name"])
                if not node_core:
                    continue
                parcels = tuple(r["parcels"].split("|")) if r["parcels"] else ()
                old = _tier3_names_match(r["name"], cname)
                city_core = extract_landcore_from_case_name(cname)
                new = similar(node_core, city_core, parcels) if city_core else False
                old_hits += old
                new_hits += new
                if old != new:
                    changed.append((d.name, r["recno"], cid, old, new))
    print("  node x candidate pairs examined: %d" % pairs_seen)
    print("  the current rule matches:  %d" % old_hits)
    print("  the widened rule matches:  %d" % new_hits)
    print("  pairs whose verdict CHANGES: %d" % len(changed))
    new_only = [c for c in changed if not c[3] and c[4]]
    lost = [c for c in changed if c[3] and not c[4]]
    print("  newly matched: %d | no longer matched: %d" % (len(new_only), len(lost)))
    for row in new_only[:15]:
        print("      NEW %s recno %s %s" % (row[0], row[1], row[2]))
    for row in lost[:15]:
        print("      LOST %s recno %s %s" % (row[0], row[1], row[2]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
