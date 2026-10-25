# -*- coding: utf-8 -*-
"""Probe — the seven cut units as rendered by the ROC-era gazettes.

The census shows the 永昌段159 / 46-4 / 雙園段505 / 萬隆段519 cells cut in every
Gregorian gazette (2026-09-24 onward) and absent from the ROC-era mismatch
lists. If the ROC renderings carry those lists complete, the corpus completion
path can rescue the cut rows instead of excluding them. This probe dumps every
row of those units in 核定案件-2026-08-27.pdf with both counters' verdicts.

Read-only; prints to stdout with non-ASCII escaped for console safety.
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

from urtpe.extract import (  # noqa: E402
    RECNO_RE,
    _clean_cell,
    declared_parcel_count,
    parcel_token_count,
    strip_page_footer,
)

PDF = r"D:\project\urtpe-gazettes\核定案件-2026-08-27.pdf"
UNITS = ("永昌段三小段159", "永昌段四小段46-4", "雙園段二小段505", "萬隆段二小段519")


def main() -> int:
    doc = pymupdf.open(PDF)
    try:
        seen: set[str] = set()
        for page in doc:
            page_no = page.number + 1
            for table in page.find_tables(strategy="lines").tables:
                grid = table.extract()
                if not grid or max(len(r) for r in grid) != 7:
                    continue
                for row in grid:
                    if any(c is None for c in row):
                        continue
                    recno = _clean_cell(row[0])
                    if not RECNO_RE.match(recno) or recno in seen:
                        continue
                    seen.add(recno)
                    name = _clean_cell(row[3])
                    if not any(u in name for u in UNITS):
                        continue
                    land, removed = strip_page_footer(_clean_cell(row[4]), page_no)
                    declared = declared_parcel_count(name)
                    print(f"編號 {recno}  page {page_no}  footer_removed={removed}  "
                          f"declared={declared} old-vis={parcel_token_count(land)}")
                    print(f"  head: {ascii(land[:80])}")
                    print(f"  tail: {ascii(land[-80:])}")
    finally:
        doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
