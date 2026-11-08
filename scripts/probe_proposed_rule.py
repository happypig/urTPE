"""The proposed tier-3 rule, measured. Read-only, offline.

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

The rule under test keeps the stage and the kind test, keeps the district
and the count test, and widens only the section and the parcel:

  the section matches when its 小段 suffix agrees and its 段 name agrees
  after dropping a trailing 段 from either side;
  the city's parcel matches when it equals the node's first parcel OR is
  one of the node's own parcels;
  the node's core may be built from the 地號 cell's section as well as the
  案名's.

The risk of a widened rule is over-binding: a case of ANOTHER unit slipping
in. This measures the risk by replaying the rule over every node x
candidate pair the pipeline actually compares, so the change in the binding
set is counted, not assumed.

The baseline is the resolver's OWN call, including the record-core fallback
it passes (`node_landcore = extract_landcore_from_case_name(node_name) or
_record_landcore(member)`). A baseline that omits the fallback undercounts
the pipeline's own bindings by 5 and reports 5 false additions. Measured
against the pipeline's own rule, the widened rule adds 3 bindings over the
5,185 pairs and loses none.

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

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import extract_landcore_from_case_name  # noqa: E402

CLEAN = ROOT / "data" / "clean.tsv"
PROJECTS = ROOT / "data" / "projects.json"
CACHE = ROOT / "data" / ".link_cache"

_CELL_SECTION_RE = re.compile(r"^\s*臺北市[^\s]*?區\s*([^\s\d]+)")
# a section's 小段 suffix: 一小段, 二小段, ... 六小段, 小段
_SUB_RE = re.compile(r"^(.*?)([一二三四五六七八九十]?小段)$")


def cell_section(land: str) -> str:
    m = _CELL_SECTION_RE.match(land or "")
    return m.group(1) if m else ""


def section_parts(section: str) -> tuple[str, str]:
    """(段 name, 小段 suffix) — 河堤段五小段 -> (河堤段, 五小段)."""
    m = _SUB_RE.match(section or "")
    if not m:
        return (section or "", "")
    return (m.group(1), m.group(2))


def sections_match(a: str, b: str) -> bool:
    """Two sections name the same 小段 and the same 段.

    The 段 name may differ by a trailing 段 on either side: the gazette
    writes 吳興一小段 where the city writes 吳興段一小段.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    an, asub = section_parts(a)
    bn, bsub = section_parts(b)
    if asub != bsub:
        return False
    if an == bn:
        return True
    return an == bn + "段" or bn == an + "段"


def core_of(district: str, section: str, parcel: str, count: str) -> str:
    return "%s%s%s地號等%s筆" % (district, section, parcel, count)


def record_core(row: dict) -> str:
    """The record's own land core — the pipeline's fallback when the 案名
    does not parse (`urtpe.links._record_landcore`). The count falls back to
    orig_count, as `build_land_core_key` does."""
    if not row["first_parcel"]:
        return ""
    parts = []
    if row["district_land"]:
        parts.append(row["district_land"])
    if row["section"]:
        parts.append(row["section"])
    core = "".join(parts) + row["first_parcel"]
    count = row["land_count"] or row["orig_count"]
    if count:
        core += "地號等%s筆" % count
    return core


def node_core(row: dict) -> str:
    """The node's land core as the resolver builds it: the 案名's core, or
    the record's own when the 案名 does not parse (resolve_node_cases:
    `node_landcore = extract_landcore_from_case_name(node_name) or
    _record_landcore(member)`). A baseline that omits this fallback
    undercounts the pipeline's own bindings by 5."""
    return extract_landcore_from_case_name(row["name"]) or record_core(row)


def parse_core(lc: str) -> tuple[str, str, str, str]:
    """(district, section, first_parcel, count) from a core string.

    The section is cut at the FIRST 段 — the pipeline's own rule
    (`urtpe.links._parse_landcore`), so the comparison keeps the bindings
    the pipeline already makes. A section cut at the LAST 段 is offered as
    a SECOND reading of the same core, not as a replacement: 河堤段五小段
    reads as section 河堤段 with parcel 五小段399 under the first rule, and
    as section 河堤段五小段 with parcel 399 under the second.
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
        i = head.find("段")
        if i >= 0:
            section, parcel = head[:i + 1], head[i + 1:]
        else:
            parcel = head
    m = re.search(r"等(\d+)筆", lc)
    if m:
        count = m.group(1)
    return district, section, parcel, count


def parse_core_alt(lc: str) -> tuple[str, str, str, str]:
    """The same core read with the section cut at its LAST 段."""
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
        i = head.rfind("段")
        if i >= 0:
            section, parcel = head[:i + 1], head[i + 1:]
        else:
            parcel = head
    m = re.search(r"等(\d+)筆", lc)
    if m:
        count = m.group(1)
    return district, section, parcel, count


def core_match(node_core: str, city_core: str, node_parcels=()) -> bool:
    """The widened land-core comparison.

    The pipeline scores a core pair on four weighted parts (section .35,
    first parcel .20, parcel Jaccard .30, count .10) and accepts the pair at
    >= 0.85. This keeps that SCORE and widens only the parts the pipeline
    is too strict about:

      the section: two sections match when they name the same 小段 and the
      same 段 — a trailing 段 may be present on either side (the gazette
      writes 吳興一小段 where the city writes 吳興段一小段);
      the parcel: the city's parcel scores the full weight when it equals
      the node's first parcel OR is one of the node's own parcels (吳興's
      first parcel is 163-2, the city declares 247).

    A count mismatch costs the .10 count term, exactly as it does now — so
    a pair the pipeline accepts still accepts.

    Each core is read two ways — the section cut at its first 段 and at its
    last — and either reading may match.
    """
    best = 0.0
    for na, ca in ((parse_core(node_core), parse_core(city_core)),
                   (parse_core_alt(node_core), parse_core_alt(city_core)),
                   (parse_core(node_core), parse_core_alt(city_core)),
                   (parse_core_alt(node_core), parse_core(city_core))):
        nd, ns, np_, nc = na
        cd, cs, cp, cc = ca
        if not (nd and cd and nd == cd):
            continue
        if not sections_match(ns, cs):
            continue
        if not np_ or not cp:
            continue
        fp = 0.0
        if np_ == cp:
            fp = 1.0
        elif node_parcels and cp in node_parcels:
            fp = 1.0
        elif (cp in np_) or (np_ in cp):
            fp = 0.95
        jac = 1.0 if fp == 1.0 else 0.0
        cnt = 1.0 if (nc and cc and nc == cc) else 0.0
        score = 0.35 + 0.2 * fp + 0.3 * jac + 0.1 * cnt
        best = max(best, score)
        if score >= 0.85:
            return True
    return best >= 0.85


def main() -> int:
    from urtpe.links import (
        _kind_matches,
        _tier3_names_match,
        node_stage_kind,
    )

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
    FOUND = {
        122: ("10305021", "中正區", "臨沂段三小段", "412", "12",
              "臨沂段三小段"),
        204: ("11005053", "中正區", "河堤五小段", "399", "3", "河堤段五小段"),
        551: ("10611051", "信義區", "吳興一小段", "330", "43", "吳興段一小段"),
        706: ("10405235", "信義區", "吳興段二小段", "163-2", "2", "吳興段二小段"),
        993: ("10011301", "萬華區", "萬華段一小段", "519-2", "35", "萬大段一小段"),
        483: ("10903061", "萬華區", "萬華段一小段", "519-2", "35", "萬大段一小段"),
        1081: ("10111171", "大安區", "復興段一小段", "3", "5", "復興段一小段"),
        669: ("10111173", "大安區", "復興段一小段", "3", "2", "復興段一小段"),
        1170: ("10002141", "大安區", "懷生段一小段", "928", "1", "懷生段一小段"),
        1433: ("09102220", "信義區", "吳興段二小段", "247", "2", "吳興段二小段"),
        1333: ("09102221", "信義區", "吳興段二小段", "247", "2", "吳興段二小段"),
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

    def widened(recno: int, row: dict, city_name: str) -> bool:
        cs, ck = node_stage_kind(city_name)
        ns, nk = node_stage_kind(row["name"])
        if not (cs and cs == ns and _kind_matches(nk, ck)):
            return False
        city_core = extract_landcore_from_case_name(city_name)
        if not city_core:
            return False
        parcels = tuple(row["parcels"].split("|")) if row["parcels"] else ()
        cores = []
        # the node's core as the resolver builds it: the 案名's, or the
        # record's own when the 案名 does not parse
        name_core = node_core(row)
        if name_core:
            cores.append(name_core)
        # the record's own core, built from the 地號 cell's section
        cell = cell_section(row["land"])
        if cell:
            cores.append(core_of(row["district_land"], cell,
                                 row["first_parcel"], row["land_count"]))
        return any(core_match(c, city_core, parcels) for c in cores)

    def pipeline_rule(row: dict, city_name: str) -> bool:
        """The resolver's own tier-3 call, with the record-core fallback the
        resolver passes (`resolve_node_cases`: `node_landcore =
        extract_landcore_from_case_name(node_name) or _record_landcore(member)`).
        A baseline that omits the fallback undercounts the pipeline's own
        bindings by 5 and reports 5 false additions."""
        return _tier3_names_match(row["name"], city_name, node_core(row))

    ok = 0
    for recno, (cid, dist, sec, parcel, count, city_sec) in sorted(FOUND.items()):
        row = rows[recno]
        hit = widened(recno, row, CITY_NAMES[cid])
        ok += hit
        print("  recno %-5s %-10s %-9s  案名 core %-14s cell core %-14s"
              % (recno, cid, "MATCH" if hit else "NO MATCH",
                 extract_landcore_from_case_name(row["name"]) or "(none)",
                 core_of(row["district_land"], cell_section(row["land"]),
                         row["first_parcel"], row["land_count"])))
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
                old = pipeline_rule(r, cname)
                new = widened(0, r, cname)
                old_hits += old
                new_hits += new
                if old != new:
                    changed.append((pid, r["recno"], cid, old, new))
    print("  pairs examined:            %d" % pairs)
    print("  the current rule matches:  %d" % old_hits)
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


if __name__ == "__main__":
    raise SystemExit(main())
