"""The segment-cut comparison, measured. Read-only, offline.

Design D1 kept BOTH readings of a core's section — the cut at its first 段
and the cut at its last — and the change widened only the section and the
parcel. This measures what each cut alone binds, over the same pairs the
pipeline compares, so the design's figures are not stale.

    python scripts/probe_cut_variants.py
"""
from __future__ import annotations

import csv
import glob
import json
import os
import pathlib
import sys
from collections import defaultdict
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    _cell_landcore,
    _kind_matches,
    _node_parcels,
    _parse_landcore,
    _parse_landcore_at_last_segment,
    _record_landcore,
    extract_landcore_from_case_name,
    landcore_sections_match,
    node_stage_kind,
)

CLEAN = ROOT / "data" / "clean.tsv"
PROJECTS = ROOT / "data" / "projects.json"
CACHE = ROOT / "data" / ".link_cache"

_CELL_SECTION_RE = __import__("re").compile(r"^\s*臺北市[^\s]*?區\s*([^\s\d]+)")


def member_of(row: dict):
    m = SimpleNamespace()
    m.recno = int(row["recno"])
    m.name = row["name"]
    m.section = row["section"]
    m.section_land = (_CELL_SECTION_RE.match(row["land"] or "") or [None, ""])[1]
    m.first_parcel = row["first_parcel"]
    m.parcels = list(row["parcels"].split("|")) if row["parcels"] else []
    m.district = row["district"]
    m.district_land = row["district_land"]
    m.land_count = (int(row["land_count"]) if row["land_count"] else None)
    m.orig_count = (int(row["orig_count"]) if row["orig_count"] else None)
    return m


def _score(node_core: str, city_core: str, parcels: tuple, cut: str) -> float:
    """The widened four-part score, over the readings the cut allows."""
    parsers = ([_parse_landcore] if cut == "first"
               else [_parse_landcore_at_last_segment] if cut == "last"
               else [_parse_landcore, _parse_landcore_at_last_segment])
    best = 0.0
    for pn in parsers:
        for pc in parsers:
            a = pn(node_core)
            b = pc(city_core)
            if not (a[0] and b[0] and a[0] == b[0]):
                continue
            if not landcore_sections_match(a[1], b[1]):
                continue
            if not a[2] or not b[2]:
                continue
            fp = 0.0
            if a[2] == b[2]:
                fp = 1.0
            elif parcels and b[2] in parcels:
                fp = 1.0
            elif (b[2] in a[2]) or (a[2] in b[2]):
                fp = 0.95
            elif a[2] in b[2] or b[2] in a[2]:
                fp = 0.7
            jac = 1.0 if fp == 1.0 else 0.0
            cnt = 1.0 if (a[3] and b[3] and a[3] == b[3]) else 0.0
            best = max(best, 0.35 + 0.2 * fp + 0.3 * jac + 0.1 * cnt)
    return best


def _rule(row: dict, city_name: str, cut: str) -> bool:
    cs, ck = node_stage_kind(city_name)
    ns, nk = node_stage_kind(row["name"])
    if not (cs and cs == ns and _kind_matches(nk, ck)):
        return False
    city_core = extract_landcore_from_case_name(city_name)
    if not city_core:
        return False
    member = member_of(row)
    node_core = (extract_landcore_from_case_name(row["name"])
                 or _record_landcore(member))
    cores = [node_core]
    alt = _cell_landcore(member)
    if alt:
        cores.append(alt)
    parcels = _node_parcels(member)
    return any(_score(c, city_core, parcels, cut) >= 0.85 for c in cores)


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

    res = {"first": {}, "last": {}, "both": {}}
    for rf in sorted(glob.glob(str(CACHE / "*" / "result.json"))):
        pid = os.path.basename(os.path.dirname(rf))
        try:
            cache = json.loads(pathlib.Path(rf).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        names = cache.get("candidate_names") or {}
        members = project_rows.get(pid) or []
        if not names or not members:
            continue
        for cid, cname in names.items():
            for r in members:
                key = (pid, r["recno"], cid)
                for cut in res:
                    res[cut][key] = _rule(r, cname, cut)

    print("pairs examined: %d" % len(res["both"]))
    for cut in ("first", "last", "both"):
        print("  the %-5s cut alone binds %5d" % (cut, sum(res[cut].values())))
    a, b = res["first"], res["last"]
    only_first = [k for k in a if a[k] and not b[k]]
    only_last = [k for k in b if b[k] and not a[k]]
    print("  the first cut binds and the last does not: %d" % len(only_first))
    for k in only_first:
        print("      ", k)
    print("  the last cut binds and the first does not:  %d" % len(only_last))
    for k in only_last:
        print("      ", k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
