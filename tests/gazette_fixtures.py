# -*- coding: utf-8 -*-
"""Ruled-table gazette PDF fixtures.

Builds PDFs whose cells are delimited by real ruling lines, the way the Taipei
City Government's 核定案件一覽表 is produced. Configurable along the axes the
city's own exports have varied on: calendar (ROC / Gregorian), column geometry,
records per page, and table defects (merged cells, missing ruling lines,
repeated header rows).

Unlike `tests/fixtures.py` (which writes free text with no cell borders, for the
positional reader), these fixtures let `page.find_tables(strategy="lines")`
recover genuine cell structure.
"""

from __future__ import annotations

import re

import pymupdf

# Column widths in points. The real document is A4 landscape (841.68 x 595.2);
# these sum with TABLE_ORIGIN to ~792 so the last ruling line stays on the page.
COLUMN_WIDTHS = [40.0, 78.0, 46.0, 150.0, 268.0, 96.0, 92.0]
TABLE_ORIGIN = [30.0, 70.0]
ROW_HEIGHT = 40.0
HEADER_HEIGHT = 34.0
PAGE_SIZE = (841.68, 595.2)
FONT = "china-s"

COLUMN_LABELS = ["編號", "本府核定日期", "行政區", "案名", "地號", "實施者", "更新規劃單位"]


def column_edges(origin_x: float = TABLE_ORIGIN[0], widths: list[float] | None = None) -> list[float]:
    """Return the right edge of each column, plus the table's right edge."""
    widths = widths or COLUMN_WIDTHS
    edges = [origin_x]
    for w in widths:
        edges.append(edges[-1] + w)
    return edges


def _bar(page, x0: float, y0: float, x1: float, y1: float) -> None:
    """Draw a thin filled rectangle standing in for a ruling line."""
    page.draw_rect(pymupdf.Rect(x0, y0, x1, y1), color=(0, 0, 0), fill=(0, 0, 0), width=0)


def draw_table(
    page,
    top: float,
    edges: list[float],
    row_heights: list[float],
    skip_hlines: set[tuple[int, int]] | None = None,
    skip_vlines: set[tuple[int, int]] | None = None,
) -> list[float]:
    """Draw a grid of cells; return the y coordinate just below the last row.

    ``skip_hlines`` holds ``(row_index, column_index)`` pairs whose *bottom*
    ruling line is omitted, which merges that cell with the one below it.
    ``skip_vlines`` holds ``(row_index, column_index)`` pairs whose *right*
    ruling line is omitted, merging it with its right neighbour.
    """
    skip_hlines = skip_hlines or set()
    skip_vlines = skip_vlines or set()
    half = 0.4

    ys = [top]
    for h in row_heights:
        ys.append(ys[-1] + h)

    n_rows = len(row_heights)
    n_cols = len(edges) - 1

    for c in range(n_cols + 1):
        for r in range(n_rows):
            if (r, c - 1) in skip_vlines:
                continue
            _bar(page, edges[c] - half, ys[r], edges[c] + half, ys[r + 1])

    for r in range(n_rows + 1):
        for c in range(n_cols):
            if (r - 1, c) in skip_hlines or (r - 1, c) in skip_vlines:
                continue
            _bar(page, edges[c], ys[r] - half, edges[c + 1], ys[r] + half)

    return ys


def put_cell(page, edges: list[float], ys: list[float], row: int, col: int, text: str,
             fontsize: float = 7.0) -> None:
    """Write text inside a cell, wrapping it to the column width."""
    if not text:
        return
    x0 = edges[col] + 3.0
    x1 = edges[col + 1] - 2.0
    top = ys[row] + fontsize + 1.0
    rect = pymupdf.Rect(x0, ys[row] + 1.0, x1, ys[row + 1] - 1.0)
    page.insert_textbox(rect, text, fontsize=fontsize, fontname=FONT, align=0)


def put_cell_clipped(page, edges: list[float], ys: list[float], row: int, col: int,
                     text: str, fontsize: float = 7.0) -> int:
    """Draw a cell line by line, stopping at the row's bottom ruling line.

    ``insert_textbox`` refuses to draw at all when its text does not fit, which
    cannot reproduce the publisher-side truncation seen in the real gazettes: the
    city draws wrapped lines until the row band is full and then simply stops, so
    the cell holds a partial list. This draws line by line and returns the number
    of lines that fit, leaving the cell ending mid-list exactly as published.
    """
    if not text:
        return 0
    x0 = edges[col] + 3.0
    x1 = edges[col + 1] - 2.0
    width = x1 - x0
    per_line = max(8, int(width / (fontsize * 0.62)))
    lines = [text[i:i + per_line] for i in range(0, len(text), per_line)] or [""]
    leading = fontsize + 2.0
    top = ys[row] + fontsize + 1.0
    drawn = 0
    for i, line in enumerate(lines):
        y = top + i * leading
        if y + fontsize > ys[row + 1] - 1.0:
            break  # the row is full; the publisher stops here
        page.insert_text((x0, y), line, fontsize=fontsize, fontname=FONT)
        drawn += 1
    return drawn


def write_gazette(
    path: str,
    rows: list[tuple],
    *,
    published: str = "統計至115年8月11日",
    calendar: str = "roc",
    shift: float = 0.0,
    rows_per_page: int = 8,
    repeat_header_row: bool = False,
    borderless_pages: tuple[int, ...] = (),
    merged_cells: tuple[tuple[int, int], ...] = (),
    paginate: bool = True,
    longest_land_row: int | None = None,
    footer_inside_last_cell: bool = False,
    land_without_terminator: int | None = None,
) -> str:
    """Write a ruled-table gazette PDF.

    ``calendar`` selects the date rendering applied to each row's date string:
    ``"roc"`` passes it through, ``"gregorian"`` converts ``YY/M/D`` to
    ``YYYY/M/D``, ``"mixed"`` converts every other row.
    ``shift`` moves every column left by that many points (the real 8pt shift).
    ``repeat_header_row`` repeats the first data row inside the table header of
    every page after the first (the 1151002 defect).
    ``borderless_pages`` draws data rows without ruling lines on those pages.
    ``merged_cells`` holds ``(row, col)`` pairs whose bottom ruling line is
    omitted, merging each cell downwards.
    ``longest_land_row`` replaces that row's 地號 cell with a parcel list far
    longer than the row band can hold, so ``insert_textbox`` draws only the part
    that fits and the cell ends mid-list. This is the publisher-side truncation
    seen in the real gazettes; without it no fixture can reach that path.
    ``footer_inside_last_cell`` draws the page number inside the last row's 地號
    cell rectangle, as the city's layout does on some pages, so a reader that
    trusts the cell rectangle absorbs it as cell text.
    ``land_without_terminator`` gives that row a 地號 cell carrying every parcel
    its 案名 declares but omitting the closing ``地號等N筆土地``, which is how the
    real gazettes lose only the closing phrase (1150827 編號 868 and 909).
    """
    doc = pymupdf.open()
    edges = column_edges(TABLE_ORIGIN[0] - shift)
    n_rows = len(rows)
    paginate = paginate and n_rows > 0
    per_page = rows_per_page if paginate else n_rows
    pages = [rows[i:i + per_page] for i in range(0, n_rows, per_page)] or [[]]

    first = True
    for page_index, page_rows in enumerate(pages):
        page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
        page.insert_font(fontname=FONT)
        page.insert_text((TABLE_ORIGIN[0], 34.0), "臺北市都市更新核定案件一覽表",
                         fontsize=9.0, fontname=FONT)
        if first:
            page.insert_text((560.0, 34.0), published, fontsize=7.0, fontname=FONT)

        merged = {(r, c) for (r, c) in merged_cells if r < len(page_rows)}
        borderless = page_index in borderless_pages

        skip_h: set[tuple[int, int]] = {(r + 1, c) for (r, c) in merged}
        header_cells = list(COLUMN_LABELS)
        if repeat_header_row and not first:
            # The defective export: the header band carries row 0's content.
            header_cells = list(_render_row(page_rows[0], calendar, 0)[:7])

        heights = [HEADER_HEIGHT] + [ROW_HEIGHT] * len(page_rows)
        if borderless:
            ys = [TABLE_ORIGIN[1]]
            for h in heights:
                ys.append(ys[-1] + h)
        else:
            ys = draw_table(page, TABLE_ORIGIN[1], edges, heights, skip_hlines=skip_h)

        for c, label in enumerate(header_cells):
            put_cell(page, edges, ys, 0, c, label)

        for r, row in enumerate(page_rows):
            rendered = _render_row(row, calendar, r + (1 if repeat_header_row else 0))
            if longest_land_row is not None and r == longest_land_row:
                rendered[4] = _long_parcel_list()
            elif land_without_terminator is not None and r == land_without_terminator:
                rendered[4] = _land_without_terminator(rendered[4])
            for c in range(7):
                if (r, c) in merged:
                    continue  # cell is owned by the span above it
                cell_text = rendered[c] if c < len(rendered) else ""
                if longest_land_row is not None and r == longest_land_row and c == 4:
                    put_cell_clipped(page, edges, ys, r + 1, c, cell_text)
                else:
                    put_cell(page, edges, ys, r + 1, c, cell_text)

        if footer_inside_last_cell and page_rows:
            # The page number printed at the foot of the last row's 地號 cell,
            # which is where the city's layout puts it on the pages that exhibit
            # the bleed. Placing it below the cell's own text reproduces the real
            # signature: a bare integer welded onto the cell's tail.
            page.insert_text((edges[4] + 3.0, ys[len(page_rows) + 1] - 2.0),
                             str(page_index + 1), fontsize=7.0, fontname=FONT)
        else:
            page.insert_text((600.0, 580.0), str(page_index + 1), fontsize=7.0, fontname=FONT)
        first = False

    doc.save(path)
    doc.close()
    return path


def _land_without_terminator(land: str) -> str:
    """Strip the closing ``地號等N筆土地``, keeping every parcel.

    The parcel list stays whole, so the row's own 案名 count still matches and the
    record is sound; only the closing phrase is gone.
    """
    return re.sub(r"地\s*號\s*(?:等)?\s*(?:共)?\s*\d+\s*筆\s*土\s*地\s*\)?\s*$", "", land.strip())


def _long_parcel_list(n: int = 160) -> str:
    """A parcel list far longer than one row band can hold.

    At 7pt across the 268pt 地號 column a 40pt row holds roughly four lines, so
    this list is cut off partway through and the cell ends mid-list — the shape
    the real gazettes show when the publisher stops drawing at the row height.
    """
    parcels = ["%d-%d" % (300 + i // 4, i % 4 + 1) for i in range(n)]
    return "臺北市測試區測試段一小段 " + "、".join(parcels) + "地號等%d筆土地" % n


def _render_row(row: tuple, calendar: str, index: int) -> list[str]:
    out = [str(v) for v in row]
    if len(out) < 7:
        out += [""] * (7 - len(out))
    if calendar == "gregorian" or (calendar == "mixed" and index % 2 == 1):
        out[1] = roc_to_gregorian(out[1])
    return out[:7]


def roc_to_gregorian(date: str) -> str:
    """Render ``115/8/27`` as ``2026/8/27``."""
    parts = date.split("/")
    if len(parts) != 3 or not parts[0].isdigit():
        return date
    year = int(parts[0])
    if year > 1911:
        return date
    return f"{year + 1911}/{parts[1]}/{parts[2]}"


# --------------------------------------------------------------------------
# Sample data
# --------------------------------------------------------------------------

ROC_ROWS = [
    (1, "115/8/27", "北投區", "擬訂臺北市北投區振興段四小段166地號等7筆土地都市更新事業計畫及權利變換計畫案",
     "臺北市北投區振興段四小段166、168、168-2、169、170、171、252地號等7筆土地",
     "捷峰開發股份有限公司", "振皓工程顧問股份有限公司"),
    (2, "115/8/26", "士林區", "擬訂臺北市士林區光華段二小段956地號等26筆（原22筆）土地都市更新事業計畫及權利變換計畫案",
     "臺北市士林區光華段二小段956、957、958、959、960地號等26筆土地",
     "禾碩建設股份有限公司", "弘傑開發事業股份有限公司"),
    (3, "115/8/20", "萬華區", "擬訂臺北市萬華區福星段四小段393-1地號等18筆土地都市更新事業計畫及權利變換計畫案",
     "臺北市萬華區福星段四小段393-1、394、394-1地號等18筆土地",
     "立詠建設股份有限公司", "舜磐創新股份有限公司"),
    (4, "115/8/19", "北投區", "擬訂臺北市北投區立農段五小段163-2地號等4筆土地都市更新事業計畫及權利變換計畫案",
     "臺北市北投區立農段五小段163-2、171-2、172、173地號等4筆土地",
     "維正建設股份有限公司", "當代都更事業股份有限公司"),
    (5, "115/8/11", "中正區", "變更臺北市中正區永昌段三小段159地號等113筆土地都市更新權利變換計畫案",
     "臺北市中正區永昌段三小段159、161、162地號等113筆土地",
     "○○建設股份有限公司", "○○都市規劃股份有限公司"),
]

# Carries the data errors the cleansing step is expected to normalise later.
VERBATIM_ROWS = [
    (1, "115/8/27", "松化區", "擬訂臺北市松化區東星段一小段120地號等1筆土地都市更新事業計畫案_核定公告",
     "臺北市松化區東星段一小段120地號等1筆土地",
     "甲建設股份有限公司", "乙規劃股份有限公司"),
    (2, "115/8/26", "松山區", "變更臺北市松山區民生段155地號等3筆土地都市更新權利變換計劃案",
     "臺北市松山區民生段155、156、157地號等3筆土地",
     "丙建設股份有限公司", "丁都市規劃股份有限公司"),
]