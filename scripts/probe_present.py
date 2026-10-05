"""Is the truncated tail present anywhere in the document, or is it absent at source?

For a page with clipped land cells, compare the number of land-column rows against
the number of `地號等...土地` terminators present in the page's full text. If the
terminators are missing from the document, no reader can recover them and the only
correct behaviour is to abort.
"""
import re
import sys

import pymupdf

sys.path.insert(0, ".")

CASES = [
    ("2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf", [11, 13, 31, 95, 157, 170]),
    ("2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf", [161, 169, 172]),
]
TERM = re.compile(r"地號\s*(?:等)?\s*(?:共)?\s*\d+\s*筆\s*土\s*地")
BAD = re.compile(r"[、，,]\s*$|\d+-\s*$")

for gid, path, pages in CASES:
    doc = pymupdf.open(path)
    print("=" * 94)
    print(gid)
    print("=" * 94)
    for pno in pages:
        page = doc[pno - 1]
        full = re.sub(r"\s+", " ", page.get_text("text").replace("\n", " "))
        rows = 0
        clipped = []
        for t in page.find_tables(strategy="lines"):
            data = t.extract()
            if not data or len(data[0]) < 5:
                continue
            for ri, row in enumerate(data):
                if len(row) < 5:
                    continue
                if not (row[0] or "").strip().isdigit():
                    continue
                rows += 1
                cell = re.sub(r"\s+", " ", (row[4] or "").replace("\n", "")).strip()
                if BAD.search(cell):
                    clipped.append((ri, cell))
        terms = len(TERM.findall(full))
        print("\npage %-4d data rows=%-3d  地號等…土地 terminators in page text=%-3d  clipped=%d"
              % (pno, rows, terms, len(clipped)))
        for ri, cell in clipped:
            print("   row %-3d clipped at %r" % (ri, cell[-38:]))
            head = cell[:18]
            print("        head %r" % head)
        if clipped:
            ri, cell = clipped[0]
            print("   -- does the document contain a terminator for the clipped row? --")
            for m in TERM.finditer(full):
                s = max(0, m.start() - 55)
                print("      ...%s" % full[s:m.end()])
    doc.close()
    print()