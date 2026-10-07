# -*- coding: utf-8 -*-
"""A publication's own ordering, as a number.

Test-writing group 4 of gazette-ingest-cadence.

Re-measured with the corrected reader on 2026-10-05:

    1150820  1422 dated records   9 departures
    1150827  1427 dated records   9 departures
    1151002  1436 dated records   1 departure

This is the figure `parked.md` recorded as **withdrawn**. It was parked on the belief
that it could not be re-derived once the contaminated reader was replaced — not because it
was wrong. The single 1151002 departure is 編號 109 (2025-08-05) above 編號 110
(2025-11-26): the same unit's 第二次 and 第三次 權利變換, i.e. a re-dated historical row,
not a sort failure. So the publisher does sort by date and then re-dates history behind
itself. Whether that is permanent needs two more publications; recording the count is what
makes that answerable without re-deriving it by hand.

Two traps produced confidently wrong numbers first, and both are pinned below:

- **1151002 repeats 編號 1 as a running page head on all 246 pages.** Counted without
  deduplicating, the file yields 1681 rows instead of 1436 and the departure count inflates
  from 1 to 246.
- **1151002 is Gregorian** (`2026/9/24`). An ROC-only parser returns *zero* dated records
  for the whole file — which reports as "0 departures", the most dangerous failure
  available to a metric whose job is to detect an ordering change, because a broken metric
  is indistinguishable from a healthy one.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.ordering import date_order_report, departures_from_descending  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


def _rows(dates):
    """One row per recno, dated as given."""
    return [tuple([str(i + 1), d, *ROC_ROWS[0][2:]]) for i, d in enumerate(dates)]


def _pdf(tmp_path, name, rows, **kw):
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), rows, **kw)
    return path


# --- the shape of the answer ------------------------------------------------

def test_a_perfectly_ordered_publication_has_no_departures(tmp_path):
    r = date_order_report(_pdf(tmp_path, "sorted", _rows(
        ["115/8/27", "115/8/20", "115/8/13", "110/1/1"])))
    assert r.violations == 0, r
    assert r.dated_records == 4, r


def test_each_inversion_counts_once(tmp_path):
    """Dated ascending rather than descending: three adjacent pairs invert."""
    r = date_order_report(_pdf(tmp_path, "asc", _rows(
        ["110/1/1", "110/1/2", "110/1/3", "110/1/4"])))
    assert r.violations == 3, r
    assert not r.is_sorted, "a list that ascends is not descending"


def test_an_undated_record_is_not_a_violation(tmp_path):
    """The publisher leaves some cells blank; those are not inversions."""
    rows = _rows(["115/8/27", "115/8/20"])
    rows.append(tuple(["3", "", *ROC_ROWS[0][2:]]))   # a distinct 編號, or it dedups away
    r = date_order_report(_pdf(tmp_path, "gap", rows))
    assert r.violations == 0, r
    assert r.dated_records == 2, "an undated row is excluded from the dated count"
    assert r.total_records == 3, "it is still a record"


# --- task 4.6: the repeated page head is not a second record -----------------

def test_a_repeated_recno_counts_once_not_once_per_page(tmp_path):
    """1151002 repeats 編號 1 as a running head on all 246 pages.

    Without deduplication the file reads as 1681 rows and its single real departure
    inflates to 246 — a metric that manufactures the anomaly it exists to detect.
    """
    rows = _rows(["115/8/27", "115/8/20"])
    first = rows[0]
    # the page head: 編號 1 reappears ahead of the next real record, 40 pages of it
    repeated = [first] * 40 + rows
    r = date_order_report(_pdf(tmp_path, "pagehead", repeated))
    assert r.dated_records == 2, (
        "a running page head is one record, not %d" % (len(repeated) - 1))
    assert r.violations == 0, r


def test_the_page_head_case_would_have_inflated_the_count_without_deduplication(tmp_path):
    """The trap, stated as the failure it prevents — and where it actually bites.

    Measured on 1151002: a raw table scan reads 1681 rows where the publication has 1436,
    because 編號 1 repeats as a page head on all 246 pages. Each head restates the newest
    date after an older row, so the scan reports 246 departures against the real 1.

    `date_order_report` counts 0 here. The inflation is a property of a *raw scan*, which
    is also how the 1681 figure was obtained, so the test demonstrates it at that layer
    rather than pretending the report is the thing at risk.
    """
    import pymupdf

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

    real = date_order_report(path)
    assert real.violations == 0, (
        "deduplication is what makes this 0 rather than %d" % inflated)
    assert real.total_records == 2


# --- task 4.2: both calendars ------------------------------------------------

def test_a_gregorian_publication_is_measured_not_skipped(tmp_path):
    """1151002 publishes `2026/9/24`. An ROC-only parser sees nothing and reports 0."""
    r = date_order_report(_pdf(tmp_path, "greg", _rows(
        ["2026/9/24", "2026/9/23", "2026/9/17"]), calendar="gregorian"))
    assert r.dated_records == 3, (
        "a Gregorian publication must not read as undateable")
    assert r.violations == 0, r


def test_one_publication_may_mix_calendars(tmp_path):
    rows = _rows(["2026/9/24", "115/8/20", "2026/9/17"])
    r = date_order_report(_pdf(tmp_path, "mixed", rows, calendar="mixed"))
    assert r.dated_records == 3, r
    assert r.violations == 1, (
        "2026-09-24 then 2026-08-20 then 2026-09-17 has exactly one inversion")


# --- task 4.3: a zero that means the parser failed is not a zero -------------

def test_a_parser_matching_no_dates_reports_an_error_not_zero_violations(tmp_path):
    rows = [tuple([str(i + 1), "not-a-date", *ROC_ROWS[0][2:]]) for i in range(5)]
    r = date_order_report(_pdf(tmp_path, "junk", rows))
    assert r.dated_records == 0, r
    assert r.violations == 0, "the count is still zero"
    assert r.unmeasurable, (
        "zero dated records must read as unmeasurable, or a broken parser looks "
        "like a perfectly ordered publication")


def test_a_low_dated_count_relative_to_records_is_flagged(tmp_path):
    rows = _rows(["115/8/27", "115/8/20", "not-a-date", "also-not", "nor-this"])
    r = date_order_report(_pdf(tmp_path, "partial", rows))
    assert r.unmeasurable, (
        "2 of 5 dated is a parser problem, not an ordering fact")
    assert r.violations == 0, "and it must not be presented as a clean result"


def test_a_fully_dated_publication_is_measurable(tmp_path):
    r = date_order_report(_pdf(tmp_path, "full", _rows(
        ["115/8/27", "115/8/20", "115/8/13"])))
    assert not r.unmeasurable, r


def test_an_empty_publication_is_unmeasurable_not_a_clean_result(tmp_path):
    from urtpe.ordering import DateOrderReport

    # A publication with no rows cannot be rendered as a table, so this asserts the
    # report's own verdict rather than going through the reader.
    r = DateOrderReport()
    assert r.unmeasurable, "no records means nothing was measured"
    assert r.violations == 0
    assert "UNMEASURABLE" in r.describe()


def test_a_single_dated_record_establishes_no_ordering():
    from urtpe.ordering import DateOrderReport

    r = DateOrderReport(violations=0, dated_records=1, total_records=1)
    assert r.is_sorted is False, (
        "one record is not evidence of an ordering, in either direction")


def test_two_dated_records_in_order_do_establish_one():
    from urtpe.ordering import DateOrderReport

    assert DateOrderReport(violations=0, dated_records=2, total_records=2).is_sorted


# --- the re-dated row, the one real departure in 1151002 --------------------

def test_a_redated_historical_row_is_an_inversion_not_a_sort_failure(tmp_path):
    """編號 109 (2025-08-05) above 編號 110 (2025-11-26): one unit, two stages."""
    r = date_order_report(_pdf(tmp_path, "redate", _rows(
        ["115/8/27", "115/8/20", "114/8/5", "114/11/26"])))
    assert r.violations == 1, r
    assert r.is_sorted is False, "one inversion still means not descending"
    assert r.max_inversion_days == 113, r


def test_the_largest_inversion_is_reported_so_a_redate_is_distinguishable(tmp_path):
    """A one-day slip and a 113-day re-date are different findings."""
    slip = date_order_report(_pdf(tmp_path, "slip", _rows(
        ["115/8/20", "115/8/21"])))
    redate = date_order_report(_pdf(tmp_path, "redate2", _rows(
        ["114/8/5", "114/11/26"])))
    assert slip.max_inversion_days == 1
    assert redate.max_inversion_days == 113
    assert redate.max_inversion_days > slip.max_inversion_days * 30


# --- pure helper, no PDF needed ---------------------------------------------

def test_departures_from_descending_is_a_pure_function():
    assert departures_from_descending([]) == (0, 0, False)
    assert departures_from_descending(["2026-08-27", "2026-08-20"])[0] == 0
    assert departures_from_descending(["2026-08-20", "2026-08-27"]) == (1, 7, False)


def test_departures_ignores_gaps_rather_than_treating_them_as_inversions():
    """An undated cell between two dated ones must not manufacture an inversion."""
    n, worst, _ = departures_from_descending(
        ["2026-08-27", None, "2026-08-20", "2026-08-13"])
    assert n == 0, (n, worst)

# --- task 4.4: the count lands in the index, beside its denominator ----------

def test_the_ordering_result_is_recorded_in_the_index(tmp_path):
    from urtpe.archive import GazetteArchive
    from urtpe.ordering import date_order_report

    archive = GazetteArchive(tmp_path / "gazettes")
    path = _pdf(tmp_path, "idx", _rows(["115/8/27", "115/8/20"]))
    report = date_order_report(path)
    archive.record_ingest(path, "2026-08-27", published_date="2026-08-27")
    archive.record_ordering("2026-08-27", report.violations, report.dated_records)

    latest = archive.entries()[-1]
    assert latest.date_order_violations == report.violations
    assert latest.dated_records == report.dated_records, (
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
