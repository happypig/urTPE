"""Measure the permit-witness selection defect across the corpus.

Defect shape (from 寶清57-13 and 金華719):
- links.permit takes `permits[0]` — the FIRST winner of the parcel-overlap
  count — so the viewer callout names one arbitrary permit.
- match_project_permits keys on the MONO parcel (the sub-parcel is stripped),
  so every permit on the same mono lands on the same key.
- The 使照 the city reports (Ulic_Date) belongs to ONE permit; the others are
  earlier buildings on the same mono number.

Measure: for every project with a permit, does the city's 使照 date equal the
FIRST permit's date, or a LATER permit's date?
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from urtpe.permit_sources import load_permit_index, match_project_permits

ARCHIVE = Path(r"D:\project\urtpe-gazettes")

with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

index = load_permit_index(ARCHIVE)
if index is None:
    raise SystemExit("permit index unavailable")

# Rebuild each project's parcel keys the way attach_links_to_projects does.
def project_keys(proj) -> list[tuple[str, str, str]]:
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


def p_no_of(permits, city_date):
    for p in permits:
        if p.date == city_date:
            return p.permit_no
    return "?"


def norm(v: str) -> str:
    import re
    t = (v or "").strip()
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", t)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.fullmatch(r"(\d{2,3})\.(\d{1,2})\.(\d{1,2})", t)
    if m:
        y = int(m.group(1))
        if y <= 115:
            return f"{y+1911}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return t


stats = Counter()
mismatch_examples = []
no_permit = 0
multi_permit = 0
first_is_city = 0
later_is_city = 0
neither = 0

for proj in data.get("projects", []):
    links = proj.get("links", {})
    city = norm(links.get("milestones_taipei", {}).get("使照核發日期", ""))
    if not city:
        stats["no_city_date"] += 1
        continue
    keys = project_keys(proj)
    if not keys:
        stats["no_keys"] += 1
        continue
    permits = match_project_permits(index, keys)
    if not permits:
        no_permit += 1
        stats["no_permit"] += 1
        continue
    if len(permits) > 1:
        multi_permit += 1
    dates = [p.date for p in permits]
    if city in dates:
        idx = dates.index(city)
        if idx == 0:
            first_is_city += 1
            stats["city_is_FIRST_permit"] += 1
        else:
            later_is_city += 1
            stats["city_is_LATER_permit"] += 1
            if len(mismatch_examples) < 12:
                mismatch_examples.append((proj["project_id"], city, permits[0].permit_no,
                                          permits[0].date, p_no_of(permits, city), idx))
    else:
        neither += 1
        stats["city_matches_NO_permit"] += 1
    # what the viewer actually shows
    emitted = (links.get("permit") or {}).get("date", "")
    if emitted and norm(emitted) != city:
        stats["EMITTED_permit_date_differs_from_city"] += 1

print("=" * 92)
print("PERMIT WITNESS — corpus measurement")
print("=" * 92)
for k, v in stats.most_common():
    print(f"  {k}: {v}")
print()
print(f"projects with >1 matched permit: {multi_permit}")
print(f"  city's 使照 == FIRST permit (viewer callout is right): {first_is_city}")
print(f"  city's 使照 == a LATER permit (viewer callout is wrong): {later_is_city}")
print(f"  city's 使照 matches no permit: {neither}")
print(f"projects with a permit but no city 使照 date: {no_permit}")
print()
print("=== examples where the city's 使照 is a LATER permit ===")
for pid, city, first_no, first_date, city_no, idx in mismatch_examples:
    print(f"  {pid}")
    print(f"    city 使照 = {city}  ({city_no}, index {idx})")
    print(f"    emitted links.permit = {first_no} ({first_date})  <-- what the viewer shows")
