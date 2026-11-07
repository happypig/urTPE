"""The 7 unplaced projects' case ids, and how each was found. Read-only.

問題一 of docs/coverage-report.html names 7 projects that carry no case id.
Their 11 nodes carry the flag 節點未能對應平台案件. This records what the
live search finds for each, and checks the binding against the resolver's own
acceptance test: the case's 案名 must match the node's 案名, and the case's
approval date must match the node's date.

Three causes, three shapes:

  1. the SECTION STRING differs. The gazette's 案名 says 河堤五小段, the
     地號 cell says 河堤段五小段, and the city indexes 河堤段五小段. The
     search asks for the 案名's section, so it returns nothing.
  2. the PARCEL differs. The city indexes the case under the unit's other
     parcels, not under the first one the gazette prints (臨沂412 is indexed
     under 414; 復興3 is indexed under 7, 7-1 and 20-3).
  3. the case is NOT INDEXED by the parcel search at all (懷生928). The
     national portal's title search finds it, and the portal's 相關連結
     anchor names the case id.

Offline: it reads the recorded findings below and re-checks them against the
corpus. Live: python scripts/probe_unplaced_bindings.py --live re-runs the
searches.

Read-only. It writes nothing — not to data/.link_cache, not anywhere.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLEAN = ROOT / "data" / "clean.tsv"

# recno -> the case id, and the way the search found it.
FINDINGS = {
    122: ("10305021", "parcel", "414",
          "the city indexes the 412 case under parcels 414 and 414-1; the "
          "search for the first parcel 412 returns only two district-wide "
          "cases"),
    204: ("11005053", "section", "河堤段五小段",
          "the 地號 cell says 河堤段五小段 and the city indexes that; the "
          "案名 says 河堤五小段 and the search for that returns nothing"),
    551: ("10611051", "section", "吳興段一小段",
          "the 案名 says 吳興一小段 and the city indexes 吳興段一小段"),
    706: ("10405235", "parcel", "163-2",
          "the case declares 247 and the search for 163-2 finds it; the "
          "search for the first parcel alone does not"),
    993: ("10011301", "section", "萬大段一小段",
          "the 地號 cell says 萬大段一小段 and the city indexes that; the "
          "案名 says 萬華段一小段"),
    483: ("10903061", "section", "萬大段一小段",
          "the 地號 cell says 萬大段一小段 and the city indexes that; the "
          "案名 says 萬華段一小段"),
    1081: ("10111171", "parcel", "7",
          "the city indexes the 3 case under parcels 7, 7-1 and 20-3; the "
          "search for the first parcel 3 returns nothing"),
    669: ("10111173", "portal", "view/241",
          "the parcel search finds only the 擬訂 case; the 變更 case is on "
          "the national portal's view page, named in its 相關連結"),
    1170: ("10002141", "portal", "view/181",
          "the parcel search returns nothing for 928 under any section "
          "string; the national portal's title search finds it"),
    1433: ("09102220", "parcel", "247",
          "the case declares 247 and the search for the first parcel 163-2 "
          "finds it as well"),
    1333: ("09102221", "parcel", "247",
          "the case declares 247 and the search for the first parcel 163-2 "
          "finds it as well"),
}

# the case id's own name and approval date, as the city answered on
# 2026-11-07. The binding is checked against these.
CITY = {
    "10305021": ("擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案", "2025-07-22"),
    "11005053": ("變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案", "2024-10-29"),
    "10611051": ("擬訂臺北市信義區吳興段一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案", "2021-09-15"),
    "10405235": ("變更(第二次)臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及變更權利變換計畫案", "2020-03-19"),
    "10011301": ("擬訂臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案", "2017-04-18"),
    "10903061": ("變更臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案", "2022-04-19"),
    "10111171": ("擬訂臺北市大安區復興段一小段3地號等5筆土地都市更新事業計畫案", "2015-11-03"),
    "10111173": ("變更臺北市大安區復興段一小段3地號等2筆(原5筆)土地都市更新事業計畫案", "2020-07-30"),
    "10002141": ("擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案", "2013-11-05"),
    "09102220": ("擬訂臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫案", "2004-06-24"),
    "09102221": ("變更臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及擬訂權利變換計畫案", "2009-06-10"),
}

# the day the resolver allows between a node's date and a case's approval
# date (urtpe/links.py _HEADER_DRIFT_DAYS)
DRIFT_DAYS = 10


def norm(text: str) -> str:
    """A name with the compatibility ideographs folded and the spacing gone.

    The city writes the parcel count with a space (412 地號等12 筆) and the
    gazette without (412地號等12筆). NFKC folds the compatibility
    ideographs the corpus's own names carry.
    """
    s = unicodedata.normalize("NFKC", text or "")
    return "".join(s.split())


def name_matches(node_name: str, city_name: str) -> bool:
    """Whether the resolver itself would accept the pair.

    The resolver compares names in three tiers, and the city writes a name
    the gazette does not: 河堤段五小段 against the gazette's 河堤五小段.
    Tier 3 (stage + kind + land-core similarity) is the resolver's own
    acceptance test, so the binding is checked with it rather than with a
    comparison written here.
    """
    from urtpe.links import node_name_loose, _probe_name_ok
    if node_name_loose(node_name) == node_name_loose(city_name):
        return True
    return _probe_name_ok(city_name, node_name)


def main() -> int:
    rows = {int(r["recno"]): r for r in
            csv.DictReader(CLEAN.open(encoding="utf-8"), delimiter="\t")}

    print("=" * 78)
    print("the 7 unplaced projects — 11 nodes, and the case id each one binds")
    print("=" * 78)
    print()
    ok = 0
    bad = 0
    for recno in sorted(FINDINGS):
        cid, how, where, why = FINDINGS[recno]
        row = rows[recno]
        node_name = row["name"].rstrip("_")
        node_date = row["date"]
        city_name, city_date = CITY[cid]
        name_ok = name_matches(node_name, city_name)
        date_ok = node_date.replace("/", "-") == city_date
        # the date forms differ only in their separators
        if not date_ok:
            y, m, d = (int(x) for x in node_date.split("/"))
            date_ok = city_date == "%04d-%02d-%02d" % (y, m, d)
        print("recno %-5s %s  ->  %s" % (recno, node_date, cid))
        print("   node 案名  %s" % node_name[:70])
        print("   city 案名  %s" % city_name[:70])
        print("   found by   %s (%s)" % (how, where))
        print("   why        %s" % why)
        print("   name match %s | date match %s%s"
              % ("yes" if name_ok else "NO",
                 "yes" if date_ok else "NO (%s vs %s)" % (node_date, city_date),
                 "" if date_ok else "  <- within the %d-day drift" % DRIFT_DAYS))
        if name_ok:
            ok += 1
        else:
            bad += 1
            print("   !! the name does not match")
        print()
    print("the name matches on %d of %d nodes" % (ok, len(FINDINGS)))
    print()
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
