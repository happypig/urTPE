"""Two remaining checks.

1) 寶清57-13: the permit index has FOUR permits on mono '57'. The city reports
   Ulic_Date 2025/06/25 (114使字第0094號, 開工 2020-05-06) — the LAST one.
   Why? The project's parcel is 57-13, so mono '57'. All four permits sit on
   mono 57. Does the 開工 date pick the same one? If yes, then the 開工 date is
   a usable disambiguator, not the 使照 date.

2) D7 interaction: does the permit matcher read links.milestones_taipei? The
   permit_review_flags call reads mt = project.links['milestones_taipei'] —
   the very dict D7 corrupts. Confirm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from urtpe.permit_sources import load_permit_index, match_project_permits

ARCHIVE = Path(r"D:\project\urtpe-gazettes")
index = load_permit_index(ARCHIVE)

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)


def keys_of(proj):
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
    return keys


print("=" * 92)
print("1) 寶清57-13 — four permits on mono '57'")
print("=" * 92)
proj = next(p for p in data["projects"]
            if p["project_id"] == "松山區-寶清段一小段-57-13地號等1筆")
keys = keys_of(proj)
print(f"  keys: {keys}")
for r in index.get(("松山區", "寶清段一小段", "57"), ()):
    mark = ""
    print(f"    {r.permit_no:>20}  使照={r.date:>12}  開工={r.construction_start:>12}  "
          f"orig={r.orig_permit:>18}  jianzi={r.is_jianzi}{mark}")
mt = proj["links"]["milestones_taipei"]
impl = proj.get("implementation", {})
print(f"  city 開工日期 = {mt.get('開工日期')}   impl.Eng_Start_Date = {impl.get('Eng_Start_Date')}")
print(f"  city 使照核發日期 = {mt.get('使照核發日期')}  impl.Ulic_Date = {impl.get('Ulic_Date')}")
print()
print("  -> does 開工 pick the same permit as 使照?")
eng = impl.get("Eng_Start_Date", "").replace("/", "-")
for r in index.get(("松山區", "寶清段一小段", "57"), ()):
    if r.construction_start == eng:
        print(f"     YES: {r.permit_no} 開工={r.construction_start} 使照={r.date}")

print()
print("=" * 92)
print("2) How many projects have a 開工 date that disambiguates the permit?")
print("=" * 92)
ambiguous_eng = 0
resolvable_by_eng = 0
by_eng = 0
for proj in data.get("projects", []):
    permits = match_project_permits(index, keys_of(proj))
    if len(permits) < 2:
        continue
    by_eng += 1
    mt = proj.get("links", {}).get("milestones_taipei", {})
    impl = proj.get("implementation", {})
    eng = (impl.get("Eng_Start_Date") or mt.get("開工日期") or "").replace("/", "-")
    if not eng:
        ambiguous_eng += 1
        continue
    hit = [p for p in permits if p.construction_start == eng]
    if len(hit) == 1:
        resolvable_by_eng += 1
print(f"  projects with >1 matched permit: {by_eng}")
print(f"  開工 date picks exactly ONE of them: {resolvable_by_eng}")
print(f"  no 開工 date to disambiguate: {ambiguous_eng}")

print()
print("=" * 92)
print("3) D7 interaction — permit_review_flags reads the dict D7 corrupts")
print("=" * 92)
import inspect
from urtpe.links import permit_review_flags
src = inspect.getsource(permit_review_flags)
print("  permit_review_flags(city, national, permits) — city/national are passed in.")
print("  the CALLER reads project.links['milestones_taipei'] — see links.py:3378-3381:")
for i, line in enumerate(
        Path("urtpe/links.py").read_text(encoding="utf-8").splitlines()[3374:3384], 3375):
    print(f"    {i}: {line}")
