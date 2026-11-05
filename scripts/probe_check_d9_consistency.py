"""Consistency check for D9: resolve exactly how each case relates to the gazette.

Answers three questions the board depends on:
  1. Is a case_id present in a NODE's links.taipei, a PROJECT's links.taipei, or neither?
  2. For the 3 撤銷核准 cases: is there a gazette row at the platform's 核定公告 date?
     Does any gazette record carry the platform's parcel at all?
  3. Which of the 466 are in neither (the true unmatched set)?
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

P168_ALL = Path("data/p168_all.json")
PROJECTS = Path("data/projects.json")


def main():
    with P168_ALL.open(encoding="utf-8") as f:
        p168_all = json.load(f)
    with PROJECTS.open(encoding="utf-8") as f:
        data = json.load(f)

    node_ids: set[str] = set()
    project_ids: set[str] = set()
    all_parcels: dict[str, set[str]] = defaultdict(set)   # section -> parcels seen
    section_of: dict[str, set[str]] = defaultdict(set)    # parcel -> sections seen
    # (section, date) -> recnos, for the MEMO-date check
    by_section_date: dict[tuple[str, str], list[int]] = defaultdict(list)

    for proj in data.get("projects", []):
        for cid in proj.get("links", {}).get("taipei", []) or []:
            project_ids.add(cid)
        for node in proj.get("nodes", []):
            for cid in node.get("links", {}).get("taipei", []) or []:
                node_ids.add(cid)
            sec = node.get("section", "")
            for p in node.get("parcels", []) or []:
                all_parcels[sec].add(p)
                section_of[p].add(sec)
            by_section_date[(sec, node.get("date", ""))].append(node.get("recno"))

    in_node = [c for c in p168_all if c["case_id"] in node_ids]
    in_project_only = [c for c in p168_all
                       if c["case_id"] in project_ids and c["case_id"] not in node_ids]
    in_neither = [c for c in p168_all if c["case_id"] not in node_ids and c["case_id"] not in project_ids]

    print(f"Total platform cases: {len(p168_all)}")
    print(f"  in a NODE's links.taipei:   {len(in_node)}")
    print(f"  in PROJECT links only:      {len(in_project_only)}")
    print(f"  in NEITHER:                 {len(in_neither)}")
    print()

    print("=== 1. The 3 撤銷核准 cases: does the gazette hold their approval? ===")
    for cid, sec, parcel, memo_date in [
        ("10112154", "大安段三小段", "260", "2019-07-23"),
        ("10702271", "豐年段四小段", "479-2", "2021-12-21"),
        ("10904071", "玉成段一小段", "36", "2021-08-31"),
    ]:
        recs = by_section_date.get((sec, memo_date), [])
        print(f"  case {cid}: section={sec} parcel={parcel} MEMO date={memo_date}")
        print(f"    gazette rows in {sec} dated {memo_date}: {recs if recs else 'NONE'}")
        secs = section_of.get(parcel, set())
        print(f"    parcel {parcel} appears in gazette sections: {sorted(secs) if secs else 'NOWHERE'}")
        print(f"    parcel {parcel} in {sec}'s parcels? {parcel in all_parcels.get(sec, set())}")
        print()

    print("=== 2. The 90 cases the gazette does not hold — stage breakdown ===")
    stages = defaultdict(int)
    for c in in_neither:
        stages[c.get("stage", "")] += 1
    for stage, cnt in sorted(stages.items(), key=lambda kv: -kv[1]):
        print(f"    {stage!r}: {cnt}")
    print()

    print("=== 3. In-processing cases: where do they live? ===")
    in_proc = [c for c in p168_all if c.get("stage") not in ("核定階段", "-")]
    n_node = sum(1 for c in in_proc if c["case_id"] in node_ids)
    n_proj = sum(1 for c in in_proc if c["case_id"] in project_ids)
    n_none = sum(1 for c in in_proc if c["case_id"] not in node_ids and c["case_id"] not in project_ids)
    print(f"    total in-processing: {len(in_proc)}")
    print(f"    in a NODE's links.taipei:  {n_node}")
    print(f"    in PROJECT links only:     {n_proj}")
    print(f"    in NEITHER:                {n_none}")
    missing = [c["case_id"] for c in in_proc
               if c["case_id"] not in node_ids and c["case_id"] not in project_ids]
    if missing:
        print(f"    missing from links.taipei: {missing}")

    print()
    print("=== 4. The 3 matched-by-parcel cases whose links.taipei lacks the case_id ===")
    for cid, pid in [
        ("10708311", "南港區-南港段四小段-566地號等1筆"),
        ("11410026", "中正區-臨沂段三小段-412地號等12筆"),
        ("11412011", "南港區-玉成段二小段-166地號等12筆"),
    ]:
        in_n = cid in node_ids
        in_p = cid in project_ids
        print(f"    {cid} ({pid}): in node links={in_n}, in project links={in_p}")


if __name__ == "__main__":
    main()
