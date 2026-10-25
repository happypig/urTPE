# -*- coding: utf-8 -*-
"""Task 1.1 census — declared-vs-visible parcel counts, every held gazette.

Read-only: sweeps every PDF in the gazette archive with the repo's own reader
primitives and classifies every data row twice:

  * under today's shipped detector (`[、，,]$|\\d$`, space-stripping counter),
    and
  * under the revised rule settled 2026-10-26 (option A of poc_findings.md):
    tail pattern extended with a trailing sub-parcel hyphen, plus a
    declared-count check that runs ONLY on cells that lost their closing
    phrase; the visible counter no longer strips spaces (a space standing
    where a separator belongs delimits two parcels) and the closing phrase is
    stripped iteratively so published variants (等N筆(原M筆)土地, 等N土地,
    chained )等M筆土地) neither leak count digits as parcels nor hide the
    phrase.

The only thing written is this change directory's report file; the archive,
the repo's data/ tree and the corpus cache are never touched.

Usage: python census_declared_counts.py [report_path]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, r"D:\project\urTPE")
import pymupdf  # noqa: E402

from urtpe.extract import (  # noqa: E402
    RECNO_RE,
    TRUNCATED_TAIL_RE,
    _clean_cell,
    declared_parcel_count,
    find_published_date,
    parcel_token_count,
    strip_page_footer,
)

ARCHIVE = Path(r"D:\project\urtpe-gazettes")
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "census_declared_counts.txt"

# Revised-rule detector (prototype of the option-A implementation).
REVISED_TAIL_RE = re.compile(r"[、，,]$|\d$|\d-$")

# One closing-phrase chunk: digits introduced by 地號[等共]? or by 等/共, an
# optional 筆, an optional parenthetical, then 土地 with an optional `)`. The
# digit run must be announced by one of those markers so a bare parcel before
# 土地 can never be swallowed.
_CLOSING_CHUNK_RE = re.compile(
    r"(?:地\s*號\s*(?:等|共)?|(?:等|共))\s*\d+\s*筆?(?:\s*\([^)]{1,16}\))?\s*土\s*地\s*\)?\s*$"
)
_BARE_COUNT_RE = re.compile(r"地\s*號\s*(?:等|共)?\s*\d+\s*筆\s*$")

SECTION_PREFIX = re.compile(r"^臺北市[^區]{1,4}區.*?小段")
# A parcel token: a digit run, optionally continued by a sub-parcel hyphen.
# The hyphen arm tolerates layout spaces INSIDE the token (`573 -6` is one
# parcel 573-6, measured in the 雙園段505 cells) — a space followed by
# `-digits` continues the preceding token, while a space followed by bare
# digits (`163 164`, measured in the 長安段140 cells) delimits two parcels.
PARCEL_TOKEN = re.compile(r"\d+(?:\s*-\s*\d+)?")


def closing_phrase_present(land: str) -> bool:
    """Whether the cell carries a published closing-phrase variant.

    Iteratively strips trailing chunks, so a chained tail like
    `地號等 18 筆土地)等 4 筆土地` is recognised as one completion.
    """
    text = (land or "").strip()
    while True:
        m = _CLOSING_CHUNK_RE.search(text)
        if m:
            text = text[: m.start()].rstrip()
            continue
        break
    return bool(_CLOSING_CHUNK_RE.search((land or "").strip())) or bool(
        _BARE_COUNT_RE.search((land or "").strip())
    )


def visible_revised(land: str) -> int:
    """Distinct parcels under the revised counter: no space stripping.

    The closing phrase is stripped chunk-wise from the right so its count
    digits never enter the token set; the section prefix is stripped as
    today. Spaces are left in place so `163 164` delimits two parcels, while
    `573 -6` stays one token via the hyphen continuation arm.
    """
    body = (land or "").strip()
    while True:
        m = _CLOSING_CHUNK_RE.search(body)
        if not m:
            break
        body = body[: m.start()].rstrip()
    body = SECTION_PREFIX.sub("", body)
    return len({t.replace(" ", "").replace("\u3000", "")
                for t in PARCEL_TOKEN.findall(body)})


def classify(declared: int | None, visible: int, tail: bool) -> tuple[str, str]:
    """(bucket, label) for one row under today's detector + the old proposal."""
    if declared is None:
        return "none", "案名 declares no count (not checkable, unchanged behaviour)"
    if visible == declared:
        return "none", "visible == declared (tail state decides, unchanged behaviour)"
    if visible < declared:
        label = ("visible < declared, tail caught   -> excluded today too (no flip)"
                 if tail else
                 "visible < declared, tail escaped  -> NEW exclusion (the 1005 class)")
    else:
        label = ("visible > declared, tail caught   -> tail path wins today (no flip)"
                 if tail else
                 "visible > declared, tail escaped  -> NEW review flag (案名 suspect)")
    return ("flip" if visible < declared else "review"), label


def revised_verdict(declared, land, rev_vis) -> tuple[str, bool]:
    """(label, truncated) under the revised (option A) rule.

    Mirrors the revised design end to end: truncated iff the tail pattern
    fires or the count check fires (no closing phrase and visible < declared),
    and then un-truncated when the count closes (only the closing phrase was
    lost) — the existing rescue, now measured with the corrected counter.
    """
    tail = bool(REVISED_TAIL_RE.search(land))
    phrase = closing_phrase_present(land)
    if declared is not None and rev_vis is not None and rev_vis == declared:
        return "rescued (count closes)", False
    if tail:
        return "tail-caught", True
    if phrase:
        return "closing phrase present", False
    if declared is not None and rev_vis is not None and rev_vis < declared:
        return "count check (no closing phrase)", True
    return "emitted", False


def today_truncated(declared, land, old_vis) -> bool:
    """Today's shipped truncation decision, without a completion corpus."""
    if not TRUNCATED_TAIL_RE.search(land):
        return False
    return not (declared is not None and old_vis == declared)


def rows_of(path: str):
    """(page, row, recno, date, name, land) for every data row, read as the reader does.

    Mirrors extract._page_records: ruled-table cells, wrap-joined, footer digits
    stripped, header bands skipped by the 編號 content test, first occurrence of a
    repeated 編號 kept (the repeat_header_row defect).
    """
    doc = pymupdf.open(path)
    try:
        seen: set[str] = set()
        for page in doc:
            page_no = page.number + 1
            for table in page.find_tables(strategy="lines").tables:
                grid = table.extract()
                if not grid or max(len(r) for r in grid) != 7:
                    continue
                for i, row in enumerate(grid):
                    if any(c is None for c in row):
                        continue
                    recno = _clean_cell(row[0])
                    if not RECNO_RE.match(recno) or recno in seen:
                        continue
                    seen.add(recno)
                    land, _removed = strip_page_footer(_clean_cell(row[4]), page_no)
                    yield page_no, i, recno, _clean_cell(row[1]), _clean_cell(row[3]), land
    finally:
        doc.close()


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT
    lines: list[str] = []
    pdfs = sorted(ARCHIVE.glob("*.pdf"))
    lines.append(f"# declared-vs-visible parcel census — {len(pdfs)} gazette(s) in {ARCHIVE}")
    lines.append("# pass 1 = today's shipped detector ([、，,]$|\\d$, space-stripping counter)")
    lines.append("# pass 2 = revised option-A rule (hyphen tail + count check on")
    lines.append("#          closing-phrase-lost cells, space-delimiting counter)")
    lines.append("")

    totals = {"flip": 0, "review": 0, "new_excl": 0}
    for pdf in pdfs:
        published = find_published_date(str(pdf))
        gazette_id = published or pdf.stem
        lines.append("=" * 100)
        lines.append(f" gazette {gazette_id}   file {pdf.name}")
        lines.append("=" * 100)
        per_gazette = {"flip": 0, "review": 0, "new_excl": 0}
        n_rows = 0
        for page_no, row_i, recno, date, name, land in rows_of(str(pdf)):
            n_rows += 1
            declared = declared_parcel_count(name)
            visible = parcel_token_count(land)
            tail = bool(TRUNCATED_TAIL_RE.search(land))
            rev_vis = visible_revised(land) if declared is not None else None
            rev_label, rev_trunc = revised_verdict(declared, land, rev_vis)
            today_trunc = today_truncated(declared, land, visible)
            bucket, label = classify(declared, visible, tail)
            if declared is not None and visible != declared:
                per_gazette[bucket] += 1
                tail_txt = "tail" if tail else "clean"
                lines.append(
                    f"  [{bucket.upper()}] 編號 {recno}  {date}  {tail_txt}  "
                    f"declared={declared} visible={visible} revised-vis={rev_vis}  "
                    f"page {page_no} row {row_i}")
                lines.append(f"      案名: {name[:90]}")
                lines.append(f"      地號尾: …{land[-60:]}")
            if rev_trunc and not today_trunc:
                per_gazette["new_excl"] += 1
                lines.append(
                    f"  [OUTCOME-CHANGE] 編號 {recno}  {date}  emitted-today -> EXCLUDED"
                    f" ({rev_label})  declared={declared} old-vis={visible} revised-vis={rev_vis}")
                lines.append(f"      地號尾: …{land[-60:]}")
            elif today_trunc and not rev_trunc:
                lines.append(
                    f"  [OUTCOME-CHANGE] 編號 {recno}  {date}  excluded-today -> EMITTED"
                    f" ({rev_label})  declared={declared} old-vis={visible} revised-vis={rev_vis}")
                lines.append(f"      地號尾: …{land[-60:]}")
        lines.append(
            f"  -- rows(read)={n_rows}  old-mismatches={per_gazette['flip'] + per_gazette['review']}"
            f"  (flip={per_gazette['flip']}, review={per_gazette['review']})"
            f"  NEW-EXCLUSIONS under revised rule={per_gazette['new_excl']}")
        lines.append("")
        for k in totals:
            totals[k] += per_gazette[k]

    lines.append("#" * 100)
    lines.append(f"TOTAL old-rule flip-class rows: {totals['flip']}")
    lines.append(f"TOTAL old-rule review-class rows: {totals['review']}")
    lines.append(f"TOTAL NEW exclusions under revised rule (before corpus completion): {totals['new_excl']}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Console stays ASCII: CJK to the Windows console is an encoding hazard the
    # repo already avoids by writing reports to files.
    print(f"report: {out_path}")
    print(f"gazettes swept: {len(pdfs)}")
    print(f"old-rule flip-class rows: {totals['flip']}")
    print(f"old-rule review-class rows: {totals['review']}")
    print(f"NEW exclusions under revised rule (before corpus completion): {totals['new_excl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
