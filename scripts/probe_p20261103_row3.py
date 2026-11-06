"""The 2026-11-03 gazette, record 3: is its 核定日期 cell empty in the PDF?

The tripwire refused the ingest: "1 record(s) with an unparsed 核定日期: 3".
The reader returned an empty date cell for 編號 3. The question is whether the
publisher printed no date or the reader missed one.

This probe prints the first page's rows around 編號 3, with the ruled-table
cells, so the answer is read off the document.

    python scripts/probe_p20261103_row3.py [pdf]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PDF = Path(sys.argv[1] if len(sys.argv) > 1
           else r"D:\project\urtpe-gazettes\核定案件-2026-11-03.pdf")


def main() -> None:
    import pymupdf

    doc = pymupdf.open(str(PDF))
    for pno in range(min(3, doc.page_count)):
        page = doc[pno]
        print("=== page %d ===" % (pno + 1))
        tables = page.find_tables(strategy="lines")
        for tno, table in enumerate(tables):
            rows = table.extract()
            for rno, row in enumerate(rows[:8]):
                cells = [(c or "").replace("\n", " ")[:34] for c in row[:4]]
                print("  table %d row %d: %s" % (tno, rno, cells))
        # the raw text of the page's first lines, for the date cell's reading
        print("  --- the page's text (first 700 chars) ---")
        print("  " + page.get_text()[:700].replace("\n", "\n  "))
        print()


if __name__ == "__main__":
    main()
