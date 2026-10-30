# -*- coding: utf-8 -*-
"""A publication's own ordering, as a number.

Re-measured with the corrected reader on 2026-10-05:

    1150820  1422 dated records   9 departures
    1150827  1427 dated records   9 departures
    1151002  1436 dated records   1 departure

The single 1151002 departure is 編號 109 (2025-08-05) above 編號 110
(2025-11-26): the same unit's 第二次 and 第三次 權利變換， i.e. a re-dated historical row,
not a sort failure. So the publisher does sort by date and then re-dates history behind
itself. Whether that is permanent needs two more publications; recording the count is what
makes that answerable without re-deriving it by hand.

Two traps produced confidently wrong numbers first, and both are pinned below:

- **1151002 repeats 編號 1 as a running page head on all 246 pages.** Counted without
  deduplicating, the file yields 1681 rows instead of 1436 and the departure count inflates
  from 1 to 246. The deduplication that prevents this lives in the reader
  (`urtpe.extract._dedupe_by_recno`), so the pipeline-side counts are safe by construction.
- **1151002 is Gregorian** (`2026/9/24`). An ROC-only parser returns *zero* dated records
  for the whole file — which reports as "0 departures", the most dangerous failure
  available to a metric whose job is to detect an ordering change, because a broken metric
  is indistinguishable from a healthy one.

2026-10-30 cleanup (docs/inspection.md F3): the PDF-level wrapper
`ordering.date_order_report` and its report class are deleted — no live spec cites
them and nothing in production called them. The tests below pin the *wired* path:
`departures_from_descending` (urtpe/cli.py) and `archive.record_ordering`. The two
trap tests are kept because they demonstrate the failure modes at the raw-scan
layer; the page-head test now exercises the reader's dedup directly instead of
through the deleted wrapper.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.ordering import DateOrderReport, departures_from_descending  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


def _rows(dates):
    """One row per recno, dated as given."""
    return [tuple([str(i + 1), d, *ROC_ROWS[0][2:]]) for i, d in enumerate(dates)]


def _pdf(tmp_path, name, rows, **kw):
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), rows, **kw)
    return path


# --- the shape of the answer (pure helper, the function the pipeline calls) ---

def test_departures_from_descending_is_a_pure_function():
    assert departures_from_descending([]) == (0, 0, False)
    assert departures_from_descending(["2026-08-27", "2026-08-20"])[0] == 0
    assert departures_from_descending(["2026-08-20", "2026-08-27"]) == (1, 7, False)


def test_departures_ignores_gaps_rather_than_treating_them_as_inversions():
    """An undated cell between two dated ones must not manufacture an inversion."""
    n, worst, _ = departures_from_descending(
        ["2026-08-27", None, "2026-08-20", "2026-08-13"])
    assert n == 0, (n, worst)


def test_each_inversion_counts_once():
    """Dated ascending rather than descending: three adjacent pairs invert."""
    dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    n, worst, is_sorted = departures_from_descending(dates)
    assert n == 3
    assert worst == 1
    assert not is_sorted, "a list that ascends is not descending"


def test_the_largest_inversion_is_reported_so_a_redate_is_distinguishable():
    """A one-day slip and a 113-day re-date are different findings."""
    slip = departures_from_descending(["2026-08-20", "2026-08-21"])
    redate = departures_from_descending(["2025-08-05", "2025-11-26"])
    assert slip[1] == 1
    assert redate[1] == 113
    assert redate[1] > slip[1] * 30


# --- task 4.6: the repeated page head is not a second record -----------------

def test_a_repeated_recno_counts_once_not_once_per_page(tmp_path):
    """1151002 repeats 編號 1 as a running head on all 246 pages.

    Without deduplication the file reads as 1681 rows and its single real departure
    inflates to 246 — a metric that manufactures the anomaly it exists to detect.
    The guarantee lives in the reader: extract_pdf dedupes by recno, so the CLI-side
    `departures_from_descending` call receives one row per 編號. Pinned end-to-end
    through the reader below.
    """
    from urtpe.extract import extract_pdf, to_iso

    rows = _rows(["115/8/27", "115/8/20"])
    first = rows[0]
    # the page head: 編號 1 reappears ahead of the next real record, 40 pages of it
    repeated = [first] * 40 + rows
    path = _pdf(tmp_path, "pagehead", repeated)

    records = extract_pdf(str(path))
    ordered = [to_iso(r["date"])[0] for r in records]
    assert len(records) == 2, (
        "the reader's dedup collapses the page heads: %d survived" % len(records))
    n, _worst, _sorted = departures_from_descending(ordered)
    assert n == 0


def test_the_page_head_case_would_have_inflated_the_count_without_deduplication(tmp_path):
    """The trap, stated as the failure it prevents — and where it actually bites.

    Measured on 1151002: a raw table scan reads 1681 rows where the publication has 1436,
    because 編號 1 repeats as a page head on all 246 pages. Each head restates the newest
    date after an older row, so the scan reports 246 departures against the real 1.

    The inflation is a property of a *raw scan*, which is also how the 1681 figure was
    obtained, so the test demonstrates it at that layer. The reader's dedup is what
    makes the pipeline-side count 0 rather than 246.
    """
    import pymupdf
    from urtpe.extract import extract_pdf, to_iso

    rows = _rows(["115/8/27", "115/8/20"])
    repeated = [r for row in rows for r in (rows[0], row)] * 20
    path = _pdf(tmp_path, "raw", repeated)

    raw = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            for table in page.find_tables(strategy="lines").tables:
                for row in table.extract():
                    if len(row) >= 7 and str(row[0]).strip().isdigit():
                        from urtpe.extract import to_iso
                        iso, _ = to_iso(re.sub(r"\s+", "", str(row[1] or "")))
                        raw.append(iso)

    inflated = sum(1 for a, b in zip(raw, raw[1:]) if a and b and b > a)
    assert len(raw) == len(repeated), "the scan sees every repeated head: %d rows" % len(raw)
    assert inflated > 1, "a raw scan over page heads manufactures inversions (%d)" % inflated

    records = extract_pdf(str(path))
    ordered = [to_iso(r["date"])[0] for r in records]
    n, _worst, _sorted = departures_from_descending(ordered)
    assert n == 0, (
        "the reader's dedup is what makes this 0 rather than %d" % inflated)
    assert len(records) == 2


# --- task 4.3: a zero that means the parser failed is not a zero -------------
# The unmeasurable guard lives on DateOrderReport (ordering.py), which survives the
# cleanup: `record_ordering` stores violations and dated_records together, and a
# future reader of the index needs the same denominator check the report carried.

def test_a_parser_matching_no_dates_reports_an_error_not_zero_violations():
    r = DateOrderReport(violations=0, dated_records=0, total_records=5)
    assert r.unmeasurable, (
        "zero dated records must read as unmeasurable, or a broken parser looks "
        "like a perfectly ordered publication")


def test_a_low_dated_count_relative_to_records_is_flagged():
    r = DateOrderReport(violations=0, dated_records=2, total_records=5)
    assert r.unmeasurable, (
        "2 of 5 dated is a parser problem, not an ordering fact")


def test_a_fully_dated_publication_is_measurable():
    r = DateOrderReport(violations=0, dated_records=3, total_records=3)
    assert not r.unmeasurable


def test_an_empty_publication_is_unmeasurable_not_a_clean_result():
    r = DateOrderReport()
    assert r.unmeasurable, "no records means nothing was measured"
    assert r.violations == 0
    assert "UNMEASURABLE" in r.describe()


def test_a_single_dated_record_establishes_no_ordering():
    r = DateOrderReport(violations=0, dated_records=1, total_records=1)
    assert r.is_sorted is False, (
        "one record is not evidence of an ordering, in either direction")


def test_two_dated_records_in_order_do_establish_one():
    assert DateOrderReport(violations=0, dated_records=2, total_records=2).is_sorted


# --- task 4.4: the count lands in the index, beside its denominator ----------

def test_the_ordering_result_is_recorded_in_the_index(tmp_path):
    from urtpe.archive import GazetteArchive

    archive = GazetteArchive(tmp_path / "gazettes")
    path = _pdf(tmp_path, "idx", _rows(["115/8/27", "115/8/20"]))
    archive.record_ingest(path, "2026-08-27", published_date="2026-08-27")
    archive.record_ordering("2026-08-27", 0, 2)

    latest = archive.entries()[-1]
    assert latest.date_order_violations == 0
    assert latest.dated_records == 2, (
        "the denominator must be stored too, or a zero reads as a measurement")


def test_an_entry_without_an_ordering_measurement_is_distinguishable_from_zero(tmp_path):
    from urtpe.archive import GazetteArchive

    archive = GazetteArchive(tmp_path / "g2")
    archive.record_ingest(_pdf(tmp_path, "unmeasured", _rows(["115/8/27"])),
                          "2026-08-27", published_date="2026-08-27")

    assert archive.entries()[-1].date_order_violations == -1, (
        "never measured must not read as measured-and-zero")


def test_recording_ordering_appends_rather_than_rewriting(tmp_path):
    from urtpe.archive import GazetteArchive

    archive = GazetteArchive(tmp_path / "g3")
    archive.record_ingest(_pdf(tmp_path, "appended", _rows(["115/8/27"])),
                          "2026-08-27", published_date="2026-08-27")
    before = len(archive.entries())

    archive.record_ordering("2026-08-27", 9, 1417)

    assert len(archive.entries()) == before + 1, (
        "the index is append-only; a corrected measurement is a new record")
    assert archive.entries()[0].date_order_violations == -1, (
        "the original entry is left as it was written")


# --- an ingestion measures it, or the count is only ever a test fixture --------

def test_an_ingestion_records_the_publication_ordering_indicator(tmp_path):
    """`record_ordering` existed with no caller outside this file.

    The archival spec requires every archived publication to carry the count of
    positions where its stated order departs from descending approval date, and
    `archive.record_ordering` is how an entry gets it — but nothing in the pipeline
    called it, so every real ingestion wrote -1, "never measured", and the trend the
    count exists to track could only be re-derived by hand from the PDFs.

    Found 2026-10-07 while ingesting 1151006, whose entry also read -1.
    """
    from urtpe import cli
    from urtpe.archive import GazetteArchive

    pdf = _pdf(tmp_path, "wired", _rows(["115/8/27", "115/8/20"]))
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out)]) == 0

    latest = GazetteArchive().entries()[-1]
    assert latest.date_order_violations != -1, (
        "the ingestion archived a publication and left its ordering unmeasured")
    assert latest.dated_records > 0, (
        "the count is meaningless without its denominator, so the denominator is stored")
