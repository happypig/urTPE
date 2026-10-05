"""Tripwire tests: refuse to emit an incomplete extraction.

Task group 2 of robust-gazette-ingestion.
"""

from __future__ import annotations

from urtpe.tripwire import Tripwire, TripwireFailure, TripwireResult


def _recs(n: int, *, start: int = 1, date: str = "115/8/27") -> list[dict]:
    return [{"recno": str(i), "date": date, "district": "中正區", "name": "n",
             "land": f"l{i}", "implementer": "i", "planner": "p"}
            for i in range(start, start + n)]


def test_contiguous_recnos_pass():
    faults = Tripwire().check(_recs(10))
    assert faults == []


def test_gap_in_recnos_is_named():
    recs = _recs(10)
    del recs[4]  # 編號 5 missing
    faults = Tripwire().check(recs)
    assert any("not contiguous" in f for f in faults)
    assert any("(expected 1..10): 5" in f for f in faults)


def test_unparsed_date_is_reported():
    recs = _recs(3)
    recs[1]["date"] = "nonsense"
    faults = Tripwire().check(recs)
    assert any("核定日期" in f for f in faults)


def test_duplicate_recnos_within_tolerance_pass():
    assert Tripwire(max_duplicate_recnos=400).check(_recs(5), duplicate_recnos=245) == []


def test_duplicate_recnos_beyond_tolerance_abort():
    faults = Tripwire(max_duplicate_recnos=10).check(_recs(5), duplicate_recnos=245)
    assert any("exceeds tolerance" in f for f in faults)


def test_page_without_table_is_reported():
    faults = Tripwire().check(_recs(5), pages=202, tables_found=201)
    assert any("pages yielding a table" in f for f in faults)


def test_empty_extraction_is_a_fault():
    assert Tripwire().check([]) == ["no records extracted"]


def test_result_report_lists_every_fault():
    recs = _recs(5)
    del recs[0]
    recs[0]["date"] = "bad"
    result = TripwireResult(ok=False, faults=Tripwire().check(recs), record_count=4)
    text = result.report()
    assert "tripwire: FAIL" in text
    assert "not contiguous" in text
    assert "核定日期" in text


def test_failure_carries_the_result():
    result = TripwireResult(ok=False, faults=["x"], record_count=0)
    err = TripwireFailure(result)
    assert err.result is result
    assert "tripwire: FAIL" in str(err)