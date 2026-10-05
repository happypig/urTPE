"""Inspect every record the reader excludes, so no false positive ships silently."""
import re
import sys

sys.path.insert(0, ".")

import pymupdf  # noqa: E402

from urtpe.extract import FOOTER_TAIL_RE, TRUNCATED_TAIL_RE, extract_pdf_with_faults  # noqa: E402

PDFS = [
    ("1150822", "2026-08-11", "source.pdf"),
    ("1150820", "2026-08-20", r"D:\project\urtpe-gazettes\核定案件-2026-08-20.pdf"),
    ("1150827", "2026-08-27", r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"),
    ("1151002", "2026-09-24", r"D:\project\urtpe-gazettes\核定案件-2026-09-24.pdf"),
]


def raw_cell(gid, page_no, row_idx, col):
    """Re-read the raw grid cell so we can see the text before any cleaning."""
    doc = pymupdf.open(PATHS[gid])
    page = doc[page_no - 1]
    for t in page.find_tables(strategy="lines").tables:
        grid = t.extract()
        if len(grid) > row_idx and len(grid[row_idx]) > col:
            out = grid[row_idx][col]
            doc.close()
            return re.sub(r"\s+", " ", (out or "").replace("\n", " ")).strip()
    doc.close()
    return ""


PATHS = {g: p for g, _, p in PDFS}

print("%-9s %-6s %-5s %s" % ("gazette", "recno", "row", "raw cell tail as published"))
print("-" * 100)
for gid, pub, path in PDFS:
    recs, faults = extract_pdf_with_faults(path)
    if not faults:
        continue
    print("\n%s (%s): %d excluded, %d emitted" % (gid, pub, len(faults), len(recs)))
    for f in faults:
        cell = raw_cell(gid, f.page, f.row, 4)
        ends_digit = bool(re.search(r"\d$", cell))
        ends_sep = bool(re.search(r"[、，,]$", cell))
        # how many parcels does the 案名 claim, vs how many did we get?
        claim = re.search(r"等\s*(?:共)?\s*(\d+)\s*筆", recs[0]["name"] if False else "")
        verdict = "digit-tail" if ends_digit else ("sep-tail" if ends_sep else "OTHER?")
        print("  編號 %-6s p%-4d r%-3s %-11s %r" % (f.recno, f.page, f.row, verdict, cell[-46:]))