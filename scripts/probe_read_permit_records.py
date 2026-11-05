"""Read the permit records for the two projects' parcels and show every one.

The emitted links.permit takes permits[0] — the winner of the parcel-overlap
count. But `permits` lists all winners, and the flag check walks them in order.
This shows what each permit actually says, so the mismatch is visible.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from urtpe.permit_sources import load_permit_index, match_project_permits

ARCHIVE = Path(r"D:\project\urtpe-gazettes")

TARGETS = {
    "松山區-寶清段一小段-57-13地號等1筆": [
        ("松山區", "寶清段一小段", "57"),
        ("松山區", "寶清段一小段", "5713"),
    ],
    "大安區-金華段一小段-719地號等1筆": [
        ("大安區", "金華段一小段", "719"),
    ],
}

index = load_permit_index(ARCHIVE)
if index is None:
    raise SystemExit("permit index unavailable (download failed)")

print(f"index keys: {len(index)}")
print()

for project_id, keys in TARGETS.items():
    print("=" * 92)
    print(f"### {project_id}")
    for key in keys:
        print(f"\n  key {key}:")
        for r in index.get(key, ()):
            print(f"    permit_no={r.permit_no:>20}  date={r.date:>12}  "
                  f"orig={r.orig_permit:>20}  is_jianzi={r.is_jianzi}  "
                  f"開工={r.construction_start}")
    print("\n  match_project_permits ->")
    for r in match_project_permits(index, keys):
        print(f"    permit_no={r.permit_no:>20}  date={r.date:>12}  "
              f"orig={r.orig_permit:>20}  is_jianzi={r.is_jianzi}  "
              f"開工={r.construction_start}")
    print()
