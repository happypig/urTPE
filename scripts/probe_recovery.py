"""Is clipped cell text recoverable from the page text layer?

For each land cell that ends in a dangling separator or a dangling sub-parcel
hyphen, re-read the page's words over the row's column x-span and see whether the
missing tail is actually present in the document.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")

PDFS = [
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]
BAD = re.compile(r"[、，,]\s*$|\d+-\s*$")

for gid, path in PDFS:
    doc = pymupdf.open(path)
    print("=" * 92)
    print(gid)
    print("=" * 92)
    found = 0
    for pno, page in enumerate(doc, 1):
        for t in page.find_tables(strategy="lines"):
            data = t.extract()
            if not data or len(data[0]) < 5:
                continue
            for ri, row in enumerate(data):
                if len(row) < 5:
                    continue
                cell = (row[4] or "").replace("\n", "")
                if not BAD.search(re.sub(r"\s+", " ", cell).strip()):
                    continue
                found += 1
                # the cell rectangle find_tables gave us, for column 4
                try:
                    rect = t.rows[ri].cells[4]
                except Exception:
                    rect = None
                print("\n page %d row %d" % (pno, ri))
                print("   clipped tail : %r" % re.sub(r"\s+", " ", cell)[-45:])
                if rect is None:
                    print("   no cell rect")
                    continue
                x0, y0, x1, y1 = rect
                print("   cell rect    : x %.1f-%.1f  y %.1f-%.1f" % (x0, x1, y0, y1))
                # re-read words over a generous band: same x-span, but taller than
                # the reported row band
                for pad in (0, 6, 14):
                    clip = pymupdf.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + pad)
                    got = page.get_text("text", clip=clip).replace("\n", "")
                    got = re.sub(r"\s+", " ", got).strip()
                    print("   pad %-2d -> len %-4d tail %r" % (pad, len(got), got[-45:]))
                # what does the row below start with?
                if ri + 1 < len(data):
                    nxt = re.sub(r"\s+", " ", (data[ri + 1][4] or "").replace("\n", "")).strip()
                    print("   next row land: %r" % nxt[:45])
                if found >= 4:
                    break
            if found >= 4:
                break
        if found >= 4:
            break
    doc.close()
    print("\n (stopped after %d clipped cells)\n" % found)