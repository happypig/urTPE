"""Ruled-table PDF extraction adapter.

Reads the Taipei City Government urban-renewal 核定案件一覽表 PDF by recovering the
published table structure: cell boundaries come from the document's own ruling lines
via ``page.find_tables(strategy="lines")``, never from stored coordinates. The city
has changed the date column's calendar and moved every column horizontally between
publications, and repeated a data row in the page header; none of that is visible to
a reader that takes its geometry from the document.

Two properties matter more than convenience here:

* **Refuse rather than approximate.** A structure this module cannot read exactly
  (a merged cell, a page with no table, a ragged row) raises ``TableStructureError``
  naming page, row, and column. There is no positional or whitespace-aligned
  fallback: ``strategy="text"`` was measured collapsing a 4-column grid to 2 and
  merging two cells into one field, which would corrupt 編號.
* **Say what was read.** ``published_date`` comes from the document's own 統計至
  line; nothing is hardcoded.

This module is an I/O adapter: it knows about the PDF layout but no domain
normalization rules live here.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

import pymupdf

# The 7 published columns, in order.
COLUMNS = ["recno", "date", "district", "name", "land", "implementer", "planner"]

# Page furniture that can sit outside the ruled table and must never be read as
# data. Cell boundaries make per-word filtering unnecessary, but the 統計至 line
# has to be lifted out as metadata.
TITLE_TEXT = "臺北市都市更新核定案件一覽表"

# 統計至115年9月24日 / 統計至 115年8月11日止共1,419筆
PUBLISHED_DATE_RE = re.compile(r"統計至\s*(\d{1,4})\s*[年/]\s*(\d{1,2})\s*[月/]\s*(\d{1,2})\s*日?")

# A 核定日期 cell in either calendar. ROC years are 1-3 digits and always below
# 1912, so a year under 1911 is unambiguously ROC.
DATE_CELL_RE = re.compile(r"^(\d{1,4})/(\d{1,2})/(\d{1,2})$")

RECNO_RE = re.compile(r"^\d{1,4}$")

# Cell text may be wrapped across lines inside its own cell boundary. Joining
# with nothing restores the original: a wrap either consumed a space that the
# layout supplied, or split a token (217-\n3 -> 217-3). Whitespace that the
# source genuinely contained survives, because only the newline is removed.
WRAP_RE = re.compile(r"\n")

# Geometry tolerance when checking ruling lines against the detected grid, in
# points. Observed bar half-thickness in the fixtures is 0.4pt.
LINE_TOL = 1.5


class TableStructureError(RuntimeError):
    """The document's table structure could not be read exactly.

    Carries one located :class:`Fault` per structural problem found, so a run can
    report every fault in one pass rather than aborting on the first.
    """

    def __init__(self, faults: list["Fault"]):
        self.faults = list(faults)
        super().__init__(self.render())

    def render(self) -> str:
        lines = [f"{len(self.faults)} structural fault(s); refusing to emit:"]
        lines += [f"  {f}" for f in self.faults]
        return "\n".join(lines)


@dataclass(frozen=True)
class Fault:
    """One located structural problem."""

    page: int
    row: int | None
    column: str | None
    kind: str
    detail: str = ""

    def __str__(self) -> str:
        where = f"page {self.page}"
        if self.row is not None:
            where += f", row {self.row}"
        if self.column:
            where += f", column {self.column}"
        return f"{where}: {self.kind}" + (f" ({self.detail})" if self.detail else "")


def _fault(page: int, row: int | None, column: str | None, kind: str, detail: str = "") -> Fault:
    return Fault(page=page, row=row, column=column, kind=kind, detail=detail)


@dataclass(frozen=True)
class CellFault:
    """One located fault in a cell's text that the reader did not cause.

    A structural :class:`Fault` means the document could not be read as published
    and the run must stop. A ``CellFault`` means the publisher's own output is
    defective in a way no reading can repair, so the affected record is excluded
    and reported rather than emitted with unknown contents.
    """

    page: int
    row: int | None
    column: str | None
    kind: str
    recno: str = ""
    detail: str = ""

    def __str__(self) -> str:
        where = f"page {self.page}"
        if self.row is not None:
            where += f", row {self.row}"
        if self.column:
            where += f", column {self.column}"
        if self.recno:
            where += f", 編號 {self.recno}"
        return f"{where}: {self.kind}" + (f" ({self.detail})" if self.detail else "")


# ---------------------------------------------------------------------------
# Cell content: page furniture and publisher truncation
# ---------------------------------------------------------------------------

# A 地號 cell ends with a CJK character in every published wording observed
# (…地號等N筆土地, …筆土地), optionally followed by a closing paren. Ending on an
# ASCII digit or a list separator means the parcel list stops mid-enumeration.
TRUNCATED_TAIL_RE = re.compile(r"[、，,]$|\d$")

# The city prints the page number inside the last row's 地號 cell on some pages.
# The trailing digits always equal that page: 11 of 11 occurrences measured across
# 1150822, 1150820 and 1150827.
FOOTER_TAIL_RE = re.compile(
    r"^(?P<head>.*?地\s*號\s*(?:等)?\s*\d+\s*筆\s*土\s*地)\s*(?P<page>\d+)$"
)

# A truncated cell whose parcel count equals the count its own 案名 declares has
# lost only the closing phrase, not any parcel. The count comes from the same
# published row, so this is a self-check and imports nothing from another record.
DECLARED_COUNT_RE = re.compile(r"地\s*號\s*(?:等)?\s*(?:共)?\s*(\d+)\s*筆")
SECTION_PREFIX_RE = re.compile(r"^臺北市[^區]{1,4}區.*?小段")
PARCEL_TOKEN_RE = re.compile(r"\d+(?:-\d+)?")
LAND_TERMINATOR_RE = re.compile(r"地\s*號\s*(?:等)?\s*(?:共)?\s*\d*\s*筆\s*土\s*地\s*\)?\s*$")


def declared_parcel_count(name: str) -> int | None:
    """The parcel count the row's 案名 states, or None when it states none."""
    m = DECLARED_COUNT_RE.search(name or "")
    return int(m.group(1)) if m else None


def parcel_token_count(land: str) -> int:
    """Distinct parcel numbers visible in a 地號 cell, ignoring its section prefix.

    Counts what the cell actually shows, so a cell the publisher cut short yields a
    count below the number the 案名 declares.
    """
    body = land.replace(" ", "").replace("\u3000", "")
    body = SECTION_PREFIX_RE.sub("", body)
    body = LAND_TERMINATOR_RE.sub("", body)
    return len(set(PARCEL_TOKEN_RE.findall(body)))


def land_cell_is_complete(land: str, name: str) -> bool:
    """Whether a truncated-looking 地號 cell still carries every parcel.

    A dangling tail normally means the publisher stopped mid-list. But when the
    cell's parcel count already equals the count the same row's 案名 declares, the
    parcel list is provably whole and only the closing phrase was lost, so the
    record is sound and must not be discarded.
    """
    declared = declared_parcel_count(name)
    if declared is None:
        return False
    return parcel_token_count(land) == declared


@dataclass(frozen=True)
class CompletionResult:
    """Outcome of attempting to complete a publisher-truncated 地號 cell."""

    completed: bool
    reason: str = ""
    parcels: tuple[str, ...] = ()
    parcel_count: int = 0
    land: str = ""
    source_gazette: str = ""
    source_recno: str = ""

    def audit_entry(self) -> str:
        """One line naming the source, so a completion is reversible after the fact."""
        if not self.completed:
            return ""
        return (f"completed from {self.source_gazette} 編號 {self.source_recno}: "
                f"{self.parcel_count} parcels")


_SECTION_RE = re.compile(r"^臺北市[^區]{1,4}區\s*([^\d]{1,14}段[^\d]{0,4}小段)")


def _section_token(land: str) -> str:
    """The 段/小段 of a land cell, without the leading 區, for comparison."""
    m = _SECTION_RE.match((land or "").strip())
    if not m:
        return ""
    return m.group(1).replace(" ", "").lstrip("區")


def complete_truncated_cell(land: str, name: str,
                            candidates: list[dict] | None = None,
                            *, source_gazette: str = "") -> CompletionResult:
    """Complete a truncated 地號 cell from another approval of the same unit.

    Borrowing was forbidden outright by the previous change, on the evidence that it
    is unsafe for 17 of 21 truncated records. That evidence stands, so a candidate is
    accepted only when three independent checks all hold:

    1. **Same unit** — the same 行政區 and the same 段/小段. A section is never matched
       by string containment: 甲段一小段 must not match 甲段二小段.
    2. **Literal prefix** — the truncated cell's text is a prefix of the candidate's,
       so the parcels already read are byte-identical to the candidate's opening.
    3. **The count closes** — the candidate's parcel count equals the count the same
       row's 案名 declares.

    Checks 1 and 2 can be satisfied by a parcel set that merely *starts* the same way;
    check 3 is what separates "the same list, continued" from "a different list". The
    refused case is recorded in `tests/test_bounded_completion.py` as 雙連段一小段197等72筆:
    prefix match, and the count closes at 62 against a 案名 declaring 72 — so neither
    publication holds the list and the record stays excluded.
    """
    declared = declared_parcel_count(name)
    if declared is None:
        return CompletionResult(False, "the 案名 declares no parcel count")

    if land_cell_is_complete(land, name):
        tokens = _parcel_tokens(land)
        return CompletionResult(
            False,
            "the parcel list is already whole; only the closing phrase was lost, "
            "so no completion is needed",
            parcels=tuple(tokens), parcel_count=len(tokens), land=land)

    if not candidates:
        return CompletionResult(False, "no candidate from another approval is available")

    trimmed = _normalise_for_compare(land)
    here = _section_token(land)
    for cand in candidates:
        cand_land = cand.get("land") or ""
        if (cand.get("district") or "") != "" and not _same_district(land, cand):
            continue
        cand_sec = _section_token(cand_land) or str(cand.get("section") or "").lstrip("區")
        if not here or not cand_sec or cand_sec != here:
            continue
        if not _normalise_for_compare(cand_land).startswith(trimmed):
            continue
        # The prefix establishes textual continuity; containment establishes that no
        # parcel already read is missing from the candidate. Both are needed: a shared
        # opening alone does not mean the same list.
        cand_parcels = set(_parcel_tokens(cand_land))
        if not set(_parcel_tokens(land)).issubset(cand_parcels):
            continue
        count = int(cand.get("parcel_count") or len(cand_parcels))
        if count != declared:
            # keep looking: another candidate may close the count exactly
            continue
        return CompletionResult(
            True, "", parcels=tuple(_parcel_tokens(cand_land)), parcel_count=count,
            land=cand_land, source_gazette=str(cand.get("gazette_id") or ""),
            source_recno=str(cand.get("recno") or ""))

    return CompletionResult(
        False,
        f"no candidate satisfied all three checks (same 段/小段, literal prefix, and a "
        f"parcel count equal to the {declared} the 案名 declares)")


def _normalise_for_compare(text: str) -> str:
    """Collapse the publisher's inconsistent spacing before comparing two cells.

    Spacing around `、` and around sub-parcel hyphens varies between publications for
    the same list — 1150827 writes `332 、333` where 1151002 writes `332、333` — and is
    presentation rather than content. Comparing raw text fails on that alone and would
    refuse a genuine continuation. Parcel identity is checked separately.
    """
    return re.sub(r"[\s\u3000]+", "", text or "")


def _parcel_tokens(land: str) -> list[str]:
    body = (land or "").replace(" ", "").replace("\u3000", "")
    body = SECTION_PREFIX_RE.sub("", body)
    body = LAND_TERMINATOR_RE.sub("", body)
    return sorted(set(PARCEL_TOKEN_RE.findall(body)))


def _same_district(land: str, cand: dict) -> bool:
    m = re.match(r"^臺北市([^區]{1,4}區)", (land or "").strip())
    return bool(m) and m.group(1) == (cand.get("district") or "")


def strip_page_footer(text: str, page_no: int) -> tuple[str, bool]:
    """Remove a page number the city's layout printed inside a cell.

    Returns the cleaned text and whether a footer was removed. The removal is only
    made when the trailing digits equal the page the cell sits on, so a genuine
    trailing number is never discarded on a guess.
    """
    m = FOOTER_TAIL_RE.match(text)
    if not m:
        return text, False
    if int(m.group("page")) != page_no:
        return text, False
    return m.group("head"), True


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def to_iso(date_str: str) -> tuple[str | None, tuple[int, int, int] | None]:
    """Convert a 核定日期 cell to ISO-8601, accepting either calendar.

    ``115/8/27`` (ROC) and ``2026/8/27`` (Gregorian) both yield ``2026-08-27``.
    The decision is made per cell, so one publication may mix calendars.

    Returns ``(None, None)`` when the cell is not a date in either calendar.
    """
    m = DATE_CELL_RE.match((date_str or "").strip())
    if not m:
        return None, None
    year, month, day = (int(v) for v in m.groups())
    if year < 1911:
        year += 1911
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None, None
    return f"{year:04d}-{month:02d}-{day:02d}", (year, month, day)


def calendar_of(date_str: str) -> str:
    """Return ``"gregorian"``, ``"roc"``, or ``"unknown"`` for a 核定日期 cell."""
    m = DATE_CELL_RE.match((date_str or "").strip())
    if not m:
        return "unknown"
    return "roc" if int(m.group(1)) < 1911 else "gregorian"


# ---------------------------------------------------------------------------
# Published date
# ---------------------------------------------------------------------------

def find_published_date(path: str) -> str | None:
    """Read the 統計至 date from the document, as ISO.

    Returns e.g. ``"2026-09-24"``, or None when the line is absent or unreadable.
    """
    doc = pymupdf.open(path)
    try:
        for page in doc:
            text = page.get_text()
            if TITLE_TEXT in text or "統計至" in text:
                m = PUBLISHED_DATE_RE.search(text)
                if m:
                    year, month, day = (int(v) for v in m.groups())
                    if year < 1911:
                        year += 1911
                    return f"{year:04d}-{month:02d}-{day:02d}"
    finally:
        doc.close()
    return None


def gazette_id_for(path: str) -> str:
    """Stable identifier for a publication, derived from its 統計至 date."""
    published = find_published_date(path)
    if published:
        return published
    # No 統計至 line: fall back to the file stem so rows stay attributable.
    return re.sub(r"[^0-9A-Za-z_-]", "", path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].removesuffix(".pdf"))


# ---------------------------------------------------------------------------
# Ruling-line verification
# ---------------------------------------------------------------------------

def _ruling_index(page) -> tuple[list[float], dict[float, list[tuple[float, float]]],
                                 list[float], dict[float, list[tuple[float, float]]]]:
    """Index ruling segments by their position.

    Returns ``(h_positions, h_spans, v_positions, v_spans)`` with positions sorted
    for range lookup. Indexing matters: the grid check asks about every edge of every
    page, and a linear scan per edge is quadratic on a 246-page document.
    """
    horizontal: dict[float, list[tuple[float, float]]] = {}
    vertical: dict[float, list[tuple[float, float]]] = {}
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.height <= 2.0 and rect.width > 2.0:
            horizontal.setdefault(round((rect.y0 + rect.y1) / 2.0, 2), []).append((rect.x0, rect.x1))
        elif rect.width <= 2.0 and rect.height > 2.0:
            vertical.setdefault(round((rect.x0 + rect.x1) / 2.0, 2), []).append((rect.y0, rect.y1))
    return (sorted(horizontal), horizontal, sorted(vertical), vertical)


def _spans_at(positions: list[float], index: dict[float, list[tuple[float, float]]],
              position: float) -> list[tuple[float, float]]:
    """All spans lying on ``position`` within tolerance.

    The table detector's edge coordinates and the drawn ruling lines differ by a
    fraction of a point (measured: 69.2 vs 69.4), so an exact key lookup misses
    every edge; tolerance has to be a range query, not a rounding.
    """
    lo = bisect.bisect_left(positions, position - LINE_TOL)
    hi = bisect.bisect_right(positions, position + LINE_TOL)
    out: list[tuple[float, float]] = []
    for key in positions[lo:hi]:
        out.extend(index[key])
    return out


def _covered(positions, index, position: float, start: float, end: float) -> bool:
    """True if ruling segments at ``position`` jointly span ``start``..``end``.

    A grid edge is drawn as one segment per cell, so coverage is a union over
    intervals rather than a single span; a merged cell leaves a real gap.
    """
    if end - start <= LINE_TOL:
        return True
    reach = start
    for lo, hi in sorted(_spans_at(positions, index, position)):
        if lo > reach + LINE_TOL:
            break
        reach = max(reach, hi)
    return reach >= end - LINE_TOL


def _missing_ruling_faults(page, table) -> list[Fault]:
    """Verify every grid edge has a ruling line; a gap means two cells are merged.

    ``find_tables`` normalizes a merged cell back into a full rectangle, so it can
    never report one: ``extract()`` yields no ``None`` and cell boxes are clipped to
    their row band. The gap is only visible against the page's own ruling lines.
    """
    h_pos, h_idx, v_pos, v_idx = _ruling_index(page)
    faults: list[Fault] = []
    page_no = page.number + 1
    rows = table.rows
    cells = [c for r in rows for c in r.cells if c]
    if not cells:
        return faults

    xs = sorted({round(c[0], 1) for c in cells} | {round(c[2], 1) for c in cells})
    ys = sorted({round(c[1], 1) for c in cells} | {round(c[3], 1) for c in cells})
    if len(xs) < 2 or len(ys) < 2:
        return faults

    # Horizontal edges: every boundary between consecutive rows, across every column.
    for i in range(len(ys) - 1):
        for j in range(len(xs) - 1):
            if not _covered(h_pos, h_idx, ys[i], xs[j], xs[j + 1]):
                faults.append(_fault(
                    page_no, i, None, "merged cell",
                    f"no ruling line at y={ys[i]:g} across column {j + 1} "
                    f"({COLUMNS[j] if j < len(COLUMNS) else j + 1}); cells are merged"))

    # Vertical edges: each column boundary must run the full table height.
    for j, x in enumerate(xs):
        if not _covered(v_pos, v_idx, x, ys[0], ys[-1]):
            faults.append(_fault(
                page_no, None, None, "merged cell",
                f"no continuous ruling line at x={x:g} (column {j + 1}); cells are merged"))
    return faults


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _clean_cell(text: str | None) -> str:
    """Rejoin a wrapped cell without inventing or dropping whitespace."""
    if text is None:
        return ""
    return WRAP_RE.sub("", text).strip()


def _page_records(page, faults: list[Fault],
                  cell_faults: list[CellFault] | None = None,
                  corpus: list[dict] | None = None,
                  completions: list[CompletionResult] | None = None,
                  ) -> list[dict[str, str]]:
    """Read one page's table into record dicts, appending any located faults.

    ``cell_faults`` collects publisher defects in cell text. A record carrying one
    is dropped rather than returned, because its contents cannot be trusted — unless
    ``corpus`` supplies another approval of the same unit that satisfies all three
    completion checks, in which case the record is emitted with the completed list and
    an audit entry naming the source.
    """
    page_no = page.number + 1
    if cell_faults is None:
        cell_faults = []
    tables = page.find_tables(strategy="lines").tables
    if not tables:
        faults.append(_fault(page_no, None, None, "no table on page",
                             "ruling lines absent or undetectable; refusing to fall back"))
        return []
    if len(tables) > 1:
        faults.append(_fault(page_no, None, None, "multiple tables on page",
                             f"{len(tables)} tables found"))

    records: list[dict[str, str]] = []
    for table in tables:
        faults.extend(_missing_ruling_faults(page, table))
        grid = table.extract()
        if not grid:
            continue
        width = max(len(r) for r in grid)
        if width != len(COLUMNS):
            faults.append(_fault(page_no, None, None, "ragged grid",
                                 f"{width} cells, expected {len(COLUMNS)}"))
            continue
        for i, row in enumerate(grid):
            if len(row) != len(COLUMNS):
                faults.append(_fault(page_no, i, None, "ragged row",
                                     f"{len(row)} cells, expected {len(COLUMNS)}"))
                continue
            if any(c is None for c in row):
                faults.append(_fault(page_no, i, None, "merged cell",
                                     "cell content owned by a spanning cell"))
                continue
            # The header band is NOT located by position. Measured 2026-10-07 on
            # 1151006: the city stopped drawing the column-label band after page 1,
            # so grid row 0 became the page's first real record, and skipping row 0
            # deleted one approval from each of the 245 pages after the first — 230
            # of 1,439 records, invisible until the contiguity gate fired. The two
            # observed shapes are opposites: a band carrying a *copy* of a record
            # that also appears as data (1151002), and a band carrying a record that
            # appears nowhere else (1151006). Only the content below tells them
            # apart, so the test below it does the deciding: 編號 fails RECNO_RE,
            # a data row does not.
            recno_text = _clean_cell(row[0])
            if not RECNO_RE.match(recno_text):
                # Trailing all-empty rows and other non-data bands.
                continue
            land = _clean_cell(row[4])
            land, footer_removed = strip_page_footer(land, page_no)
            name = _clean_cell(row[3])
            truncated = bool(TRUNCATED_TAIL_RE.search(land))
            if truncated and land_cell_is_complete(land, name):
                # Every parcel the row declares is present; the publisher only cut
                # the closing phrase. Keep the record rather than discard good data.
                truncated = False
            if truncated:
                # The publisher stopped drawing the parcel list at the printed row
                # height. Another approval of the same unit may complete it, but only
                # when all three checks agree; otherwise the parcel set is unknown and
                # the record is excluded and named.
                done = (complete_truncated_cell(land, name, corpus)
                        if corpus else CompletionResult(False, "no corpus available"))
                if done.completed:
                    land = done.land
                    truncated = False
                    if completions is not None:
                        completions.append(done)
            if truncated:
                # The publisher stopped drawing the parcel list at the printed row
                # height; the remainder is not in the document, so the parcel set
                # cannot be known. Drop the record and report it.
                cell_faults.append(CellFault(
                    page=page_no, row=i, column="地號",
                    kind="source_truncated_land_cell", recno=recno_text,
                    detail="cell ends mid-enumeration; the publisher truncated it "
                           "at the row height and the remainder is not in the PDF",
                ))
                continue
            if footer_removed and TRUNCATED_TAIL_RE.search(land):
                # Unreachable today, but if a footer strip ever leaves a dangling
                # tail the run must stop rather than guess.
                faults.append(_fault(page_no, i, "地號", "cell ends mid-enumeration",
                                     "after removing page furniture"))
                continue
            records.append({
                "recno": recno_text,
                "date": _clean_cell(row[1]),
                "district": _clean_cell(row[2]),
                "name": name,
                "land": land,
                "implementer": _clean_cell(row[5]),
                "planner": _clean_cell(row[6]),
            })
    return records


def _dedupe_by_recno(records: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Drop repeated-header duplicates; first occurrence of a 編號 wins.

    A defective export repeats one data row in the page header of every page after
    the first. Those repeats are exact duplicates of an earlier record, so keeping
    the first occurrence discards them without losing a genuine record.
    """
    seen: set[str] = set()
    kept: list[dict[str, str]] = []
    duplicates = 0
    for rec in records:
        if rec["recno"] in seen:
            duplicates += 1
            continue
        seen.add(rec["recno"])
        kept.append(rec)
    return kept, duplicates


def extract_pdf(path: str, *, strict: bool = True) -> list[dict[str, str]]:
    """Extract all records from a gazette PDF, newest-first as published.

    Records the publisher truncated are excluded; see :func:`extract_pdf_with_faults`
    for the report of what was dropped.

    Raises :class:`TableStructureError` when the document cannot be read exactly.
    """
    records, _duplicates, _cell_faults, _done = _extract(path, strict=strict)
    return records


def extract_pdf_with_faults(
    path: str, *, strict: bool = True, corpus: list[dict] | None = None
) -> tuple[list[dict[str, str]], list[CellFault]]:
    """Extract records together with the publisher defects found in cell text.

    The returned records exclude every record named by a returned
    :class:`CellFault`, so a caller can report the shortfall rather than present a
    short gazette as a faithful copy.
    """
    records, _duplicates, cell_faults, _done = _extract(path, strict=strict, corpus=corpus)
    return records, cell_faults


def _extract(path: str, *, strict: bool, corpus: list[dict] | None = None
            ) -> tuple[list[dict[str, str]], int, list[CellFault], list[CompletionResult]]:
    gazette_id = gazette_id_for(path)
    doc = pymupdf.open(path)
    faults: list[Fault] = []
    cell_faults: list[CellFault] = []
    completions: list[CompletionResult] = []
    records: list[dict[str, str]] = []
    try:
        for page in doc:
            records.extend(_page_records(page, faults, cell_faults, corpus, completions))
    finally:
        doc.close()

    if strict and faults:
        raise TableStructureError(faults)

    records, duplicates = _dedupe_by_recno(records)
    for rec in records:
        rec["gazette_id"] = gazette_id
    return records, duplicates, cell_faults, completions


def extract_pdf_with_meta(path: str, *, strict: bool = True,
                         corpus: list[dict] | None = None,
                         ) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Extract records plus metadata: publication date, gazette_id, calendar mix."""
    records, duplicates, cell_faults, completions = _extract(path, strict=strict, corpus=corpus)
    published = find_published_date(path)
    calendars = {calendar_of(r["date"]) for r in records}
    meta: dict[str, str] = {
        "gazette_id": gazette_id_for(path),
        "duplicate_recnos": str(duplicates),
        "record_count": str(len(records)),
    }
    if completions:
        meta["completed_count"] = str(len(completions))
        meta["completed_from"] = ",".join(
            f"{c.source_gazette}#{c.source_recno}" for c in completions)
    if cell_faults:
        # A gazette missing records must never be presented as a faithful copy.
        meta["excluded_count"] = str(len(cell_faults))
        meta["excluded_recnos"] = ",".join(f.recno for f in cell_faults if f.recno)
        meta["excluded_reason"] = cell_faults[0].kind
    if published:
        meta["published_date"] = published
    if calendars == {"roc"}:
        meta["calendar"] = "roc"
    elif calendars == {"gregorian"}:
        meta["calendar"] = "gregorian"
    elif calendars:
        meta["calendar"] = "mixed:" + ",".join(sorted(c for c in calendars if c != "unknown"))
    return records, meta


def to_raw_records(recs: list[dict[str, str]]) -> list:
    """Convert extracted dicts into RawRecord, marking non-conforming rows."""
    from urtpe.models import RawRecord

    out = []
    for rec in recs:
        errors = []
        if not rec.get("name"):
            errors.append("案名缺漏")
        if not rec.get("land"):
            errors.append("地號缺漏")
        if not rec.get("implementer"):
            errors.append("實施者缺漏")
        if to_iso(rec.get("date", ""))[0] is None:
            errors.append("核定日期缺漏")
        out.append(
            RawRecord(
                recno=int(rec.get("recno") or 0),
                date=rec.get("date", ""),
                district=rec.get("district", ""),
                name=rec.get("name", ""),
                land=rec.get("land", ""),
                implementer=rec.get("implementer", ""),
                planner=rec.get("planner", ""),
                parse_error="；".join(errors),
                gazette_id=rec.get("gazette_id", ""),
            )
        )
    return out