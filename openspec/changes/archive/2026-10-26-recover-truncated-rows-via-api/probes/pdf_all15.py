# -*- coding: utf-8 -*-
"""True cell contents for all 15 truncated rows, measured with the repo's own counters."""
import sys

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf

from urtpe.extract import declared_parcel_count, parcel_token_count, TRUNCATED_TAIL_RE

ROWS = {67: 11, 79: 13, 570: 95, 672: 112, 719: 121, 796: 134, 851: 144, 863: 146,
        902: 152, 912: 154, 919: 155, 930: 157, 944: 160, 997: 169, 1131: 192}
doc = pymupdf.open(r"C:\Users\jeffw\AppData\Local\Temp\opencode\g1021.pdf")

print(f"{'編號':>5} {'date':>10}  name complete?  declared/visible  land ends mid-list  section in land?")
for recno, pno in sorted(ROWS.items()):
    page = doc[pno - 1]
    cells = None
    for t in page.find_tables().tables:
        for r in t.extract():
            if (r[0] or "").strip() == str(recno):
                cells = r
                break
    if not cells:
        print(f"{recno:>5}  NOT FOUND")
        continue
    date, dist, name, land = (cells[1] or "").strip(), (cells[2] or "").strip(), cells[3] or "", cells[4] or ""
    name_flat = name.replace("\n", "").replace(" ", "")
    land_flat = land.replace("\n", "").replace(" ", "")
    declared = declared_parcel_count(name_flat)
    visible = parcel_token_count(land_flat)
    tail = bool(TRUNCATED_TAIL_RE.search(land_flat))
    has_sec = "小段" in land_flat or "段" in land_flat
    print(f"{recno:>5} {date:>10}  {('COMPLETE' if declared and len(name_flat.replace('⏎',''))>=10 else '?'):>14}  "
          f"{declared}/{visible}{'':>8}  {tail!s:>8}  {has_sec!s:>5}")
    print(f"      name: {name_flat[:76]}")
    print(f"      land: {land_flat[:100]}")
