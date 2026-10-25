# -*- coding: utf-8 -*-
"""Probe — real post-change outcome for the 7 newly-truncated rows.

For every newly-truncated row in the current gazette (2026-10-15), runs the
repo's own `complete_truncated_cell` (the three checks: same 段/小段, literal
prefix, count closes) against a corpus built from every OTHER held gazette,
and reports completed vs excluded. This is the flip list task 1.2 records;
task 5.2's pipeline run should reproduce it exactly.

Read-only; prints to stdout with non-ASCII escaped for console safety.
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

from urtpe.extract import (  # noqa: E402
    RECNO_RE,
    _clean_cell,
    _section_token,
    complete_truncated_cell,
    declared_parcel_count,
    parcel_token_count,
    strip_page_footer,
)
from re import compile as _re

ARCHIVE = sys.modules["pathlib"].Path(r"D:\project\urtpe-gazettes") if False else None
from pathlib import Path  # noqa: E402

ARCHIVE = Path(r"D:\project\urtpe-gazettes")
NEW_TAIL = _re(r"[、，,]$|\d$|\d-$")
_CLOSING_CHUNK = _re(
    r"(?:地\s*號\s*(?:等|共)?|(?:等|共))\s*\d+\s*筆?(?:\s*\([^)]{1,16}\))?\s*土\s*地\s*\)?\s*$")
PARCEL = _re(r"\d+(?:\s*-\s*\d+)?")


def closing_phrase_present(land: str) -> bool:
    text = (land or "").strip()
    while True:
        m = _CLOSING_CHUNK.search(text)
        if not m:
            break
        text = text[: m.start()].rstrip()
    return text != (land or "").strip()


def visible_revised(land: str) -> int:
    body = (land or "").strip()
    while True:
        m = _CLOSING_CHUNK.search(body)
        if not m:
            break
        body = body[: m.start()].rstrip()
    body = _re(r"^臺北市[^區]{1,4}區.*?小段").sub("", body)
    return len({t.replace(" ", "") for t in PARCEL.findall(body)})


def rows_of(path: str):
    doc = pymupdf.open(path)
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
                    land, _ = strip_page_footer(_clean_cell(row[4]), page_no)
                    yield recno, _clean_cell(row[1]), _clean_cell(row[2]), \
                        _clean_cell(row[3]), land
    finally:
        doc.close()


def main() -> int:
    pdfs = sorted(ARCHIVE.glob("*.pdf"))
    corpora: dict[str, list[dict]] = {}
    rows_by_pdf: dict[str, list[tuple]] = {}
    for pdf in pdfs:
        rows = list(rows_of(str(pdf)))
        rows_by_pdf[pdf.name] = rows
        corpora[pdf.name] = [
            {"recno": recno, "district": dist, "name": name, "land": land,
             "section": _section_token(land),
             "parcel_count": parcel_token_count(land),
             "gazette_id": pdf.stem}
            for recno, _date, dist, name, land in rows
        ]

    current = "核定案件-2026-10-23.pdf"
    print("newly-truncated rows in the current gazette, completion attempted "
          "against every other held gazette:")
    for recno, date, dist, name, land in rows_by_pdf[current]:
        declared = declared_parcel_count(name)
        rev_vis = visible_revised(land) if declared is not None else None
        tail = bool(NEW_TAIL.search(land))
        phrase = closing_phrase_present(land)
        truncated = (declared is not None and rev_vis is not None
                     and rev_vis == declared) is False and (
            tail or (not phrase and declared is not None
                     and rev_vis is not None and rev_vis < declared))
        if not truncated:
            continue
        others = [c for pdf in pdfs if pdf.name != current
                  for c in corpora[pdf.name]]
        result = complete_truncated_cell(land, name, others,
                                         source_gazette="2026-10-15")
        outcome = "COMPLETED" if result.completed else "EXCLUDED"
        print(f"  編號 {recno}  {date}  declared={declared} visible={rev_vis}  "
              f"-> {outcome}")
        if result.completed:
            print(f"      from {result.source_gazette} 編號 {result.source_recno}"
                  f"  ({result.parcel_count} parcels)")
        else:
            print(f"      reason: {ascii(result.reason)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
