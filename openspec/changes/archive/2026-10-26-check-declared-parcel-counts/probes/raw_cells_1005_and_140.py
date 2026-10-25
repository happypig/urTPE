# -*- coding: utf-8 -*-
"""Task 1.1 follow-up probe — raw cell text (line breaks visible) for two shapes.

1. 編號 1005 (雙園段二小段505等77筆) — the motivating row; proposal says 75/77,
   the census measures 76/77. Dump the full cell to see which is right and where
   the text stops.
2. 編號 60 (長安段四小段140等22筆) — the most common clean-tail flip (4 rows per
   gazette). Its tail shows `163 164` with a space; check whether a wrap join
   glued two parcels somewhere (reader artifact) or the deficit is real.

Read-only; prints to stdout with non-ASCII escaped for console safety.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

from urtpe.extract import (  # noqa: E402
    RECNO_RE,
    parcel_token_count,
    strip_page_footer,
)

PDF = Path(r"D:\project\urtpe-gazettes\核定案件-2026-10-23.pdf")
TARGETS = {"1005", "60"}


def show(label: str, text: str) -> None:
    print(f"--- {label} (line breaks as <NL>) ---")
    print(ascii(text.replace("\n", "<NL>")))
    print(f"parcel_token_count on joined text: {parcel_token_count(text.replace(chr(10), ''))}")
    print()


def main() -> int:
    doc = pymupdf.open(PDF)
    try:
        for page in doc:
            page_no = page.number + 1
            for table in page.find_tables(strategy="lines").tables:
                grid = table.extract()
                if not grid or max(len(r) for r in grid) != 7:
                    continue
                for row in grid:
                    if any(c is None for c in row):
                        continue
                    recno = (row[0] or "").strip()
                    if recno not in TARGETS:
                        continue
                    land_raw = row[4] or ""
                    land, removed = strip_page_footer(
                        land_raw.replace("\n", "").strip(), page_no)
                    show(f"編號 {recno} page {page_no} raw land cell", land_raw)
                    show(f"編號 {recno} joined+footer-stripped (removed={removed})", land)
                    name_raw = row[3] or ""
                    print(f"--- 編號 {recno} raw name cell ---")
                    print(ascii(name_raw.replace("\n", "<NL>")))
                    print()
    finally:
        doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
