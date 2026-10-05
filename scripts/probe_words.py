"""Definitive recover-vs-abort check: do the missing glyphs exist as words at all?

Lists every word whose x-span sits inside the land column and whose y lies below
the clipped row's band, so we can see whether the continuation was drawn at all.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")

CASES = [
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf", 11, 1),
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf", 157, 6),
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf", 161, 4),
]
BAD = re.compile(r"[、，,]\s*$|\d+-\s*$")

for gid, path, pno, target_row in CASES:
    doc = pymupdf.open(path)
    page = doc[pno - 1]
    print("=" * 94)
    print("%s page %d row %d" % (gid, pno, target_row))
    print("=" * 94)

    tab = None
    for t in page.find_tables(strategy="lines"):
        data = t.extract()
        if not data or len(data[0]) < 5:
            continue
        if len(data) > target_row and (data[target_row][4] or "").strip():
            tab = (t, data)
            break
    if not tab:
        print("  row not found")
        continue
    t, data = tab
    rect = t.rows[target_row].cells[4]
    x0, y0, x1, y1 = rect
    cell = re.sub(r"\s+", " ", (data[target_row][4] or "").replace("\n", "")).strip()
    print("  cell rect y %.1f -> %.1f  (height %.1f)" % (y0, y1, y1 - y0))
    print("  clipped tail: %r" % cell[-40:])

    # every word in the land column x-span, ordered by y
    words = [w for w in page.get_text("words")
             if w[0] >= x0 - 6 and w[2] <= x1 + 6]
    words.sort(key=lambda w: (round(w[1], 1), w[0]))
    print("\n  all %d words in the land column x-span (%.0f..%.0f), by y:"
          % (len(words), x0, x1))
    band = [w for w in words if y0 - 2 <= w[1] <= y1 + 2]
    below = [w for w in words if w[1] > y1 + 2]
    print("    inside the row band : %d words" % len(band))
    print("    below the row band  : %d words" % len(below))
    if below:
        print("\n    first 40 words below the band:")
        for w in below[:40]:
            print("      y=%7.1f x=%6.1f  %r" % (w[1], w[0], w[4]))
    # the decisive test: is there any word after the last in-band word that is not
    # the start of the next row's cell?
    print("\n    last 12 words inside the band:")
    for w in band[-12:]:
        print("      y=%7.1f x=%6.1f  %r" % (w[1], w[0], w[4]))
    doc.close()
    print()