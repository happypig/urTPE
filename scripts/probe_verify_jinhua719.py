"""Verify the 金華719 case end to end, and check the D7 interaction.

金華719's node recno=81 (the ANCHOR, 變更(第三次), 2026-01-07) has parcels
['719'] only — the whole 9-parcel list lives on the earlier nodes. So the
permit index sees mono '719' from every node, but the emitted project-level
links.permit came from a DIFFERENT parcel key.

Question: which permit does the matcher pick, and why is it 096使字第0079號
(2007-03-01) when the city reports 115使字第0018號 (2026-01-28)?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from urtpe.permit_sources import load_permit_index, match_project_permits, records_of

ARCHIVE = Path(r"D:\project\urtpe-gazettes")
index = load_permit_index(ARCHIVE)

PROJECT = "大安區-金華段一小段-719地號等1筆"

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

proj = next(p for p in data["projects"] if p["project_id"] == PROJECT)

print("=== the project's nodes and their parcels ===")
for node in proj.get("nodes", []):
    print(f"  recno={node.get('recno')} date={node.get('date')} stage={node.get('stage')}")
    print(f"    parcels={node.get('parcels')}")

# The keys the attach path builds: union over ALL nodes
keys, seen = [], set()
for node in proj.get("nodes", []):
    section = node.get("section", "") or ""
    district = node.get("district_land") or node.get("district") or ""
    for parcel in node.get("parcels", None) or []:
        mono = str(parcel).partition("-")[0]
        d = (district.replace(section[:len(district)], "", 1)
             if district and section.startswith(district) and district else district)
        key = (d, section, mono)
        if key not in seen:
            seen.add(key)
            keys.append(key)

print()
print(f"=== keys the attach path builds ({len(keys)}) ===")
for k in keys:
    recs = index.get(k, ())
    print(f"  {k}: {len(recs)} permit(s)")
    for r in recs:
        print(f"      {r.permit_no:>20}  date={r.date:>12}  orig={r.orig_permit:>18}  "
              f"jianzi={r.is_jianzi}  開工={r.construction_start}")

print()
print("=== match_project_permits (overlap-count winner) ===")
permits = match_project_permits(index, keys)
for r in permits:
    print(f"  {r.permit_no:>20}  date={r.date:>12}  jianzi={r.is_jianzi}")

print()
print("=== the overlap counts, by hand ===")
counts: dict[str, int] = {}
for k in keys:
    for r in index.get(k, ()):
        if not r.is_jianzi:
            continue
        counts[r.permit_no] = counts.get(r.permit_no, 0) + 1
for no, c in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"  {no:>20}: {c} parcel(s)")

print()
print("=== the emitted witness ===")
print(f"  links.permit = {json.dumps(proj['links'].get('permit'), ensure_ascii=False)}")
print(f"  city 使照核發日期 = {proj['links'].get('milestones_taipei', {}).get('使照核發日期')}")

print()
print("=== ALL permits on 金華段一小段 mono 719 (not just 建字) ===")
for r in index.get(("大安區", "金華段一小段", "719"), ()):
    print(f"  {r.permit_no:>20}  date={r.date:>12}  orig={r.orig_permit:>18}  jianzi={r.is_jianzi}")

print()
print("=== the 开工 dates: does the city 開工 date pick the permit too? ===")
for r in index.get(("大安區", "金華段一小段", "719"), ()):
    print(f"  {r.permit_no:>20}  開工={r.construction_start}")
print(f"  city 開工日期 = {proj['links'].get('milestones_taipei', {}).get('開工日期')}")
print(f"  impl Eng_Start_Date = {proj.get('implementation', {}).get('Eng_Start_Date')}")
