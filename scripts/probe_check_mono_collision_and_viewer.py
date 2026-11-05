"""Two follow-ups:

1. The 寶清 project is 57-13, but the permit index keys it under mono '57'.
   The permit adapter strips the sub-parcel (mono = parcel.partition('-')[0]),
   and the permit XML's 地段號 carries the mono too. So '57-13' and '57' land on
   the same key — a sub-parcel collision. How many permits sit on a mono key
   that carries several sub-parcels?

2. What does the VIEWER show for 使照核發日期, and does it show links.permit?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ---- 1. how many parcels share a mono key in the gazette? -------------------
with open("data/projects.json", encoding="utf-8") as f:
    data = json.load(f)

mono_collisions = {}
for proj in data.get("projects", []):
    for node in proj.get("nodes", []):
        section = node.get("section", "")
        district = node.get("district_land") or node.get("district") or ""
        for p in node.get("parcels", []) or []:
            mono = str(p).partition("-")[0]
            key = (district, section, mono)
            mono_collisions.setdefault(key, set()).add(str(p))

multi = {k: v for k, v in mono_collisions.items() if len(v) > 1}
print(f"=== mono keys carrying more than one sub-parcel: {len(multi)} ===")
for k, v in sorted(multi.items())[:15]:
    print(f"  {k} -> {sorted(v)}")
print()

# the two named cases
for proj in data.get("projects", []):
    if proj["project_id"] in ("松山區-寶清段一小段-57-13地號等1筆",
                              "大安區-金華段一小段-719地號等1筆"):
        print(f"### {proj['project_id']}")
        for node in proj.get("nodes", []):
            print(f"  node recno={node.get('recno')} section={node.get('section')} "
                  f"parcels={node.get('parcels')} "
                  f"district_land={node.get('district_land')!r} district={node.get('district')!r}")
        print()

# ---- 2. the viewer: what renders 使照核發日期 and links.permit? -------------
print("=== viewer: 使照核發日期 / permit rendering sites ===")
app = Path("viewer/app.js").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(app, 1):
    if any(t in line for t in ("使照核發日期", "permit", "Permit", "links.permit")):
        print(f"  {i:5d}: {line.strip()[:120]}")
