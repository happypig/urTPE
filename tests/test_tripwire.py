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



def test_run_report_states_the_excluded_count():
    """A gazette missing records must never be presented as a faithful copy.

    The structural gate passes when a gap is fully explained, so 'PASS' alone would
    read as a complete extraction. The exclusion has to appear in the report next to
    the emitted count.
    """
    recs = [{"recno": str(n), "date": "115/8/27", "district": "中正區",
             "name": "n", "land": "l", "implementer": "i", "planner": "p"}
            for n in range(1, 6) if n != 3]
    tw = Tripwire()
    faults = tw.check(recs, excluded_recnos={3})
    assert faults == []          # the gap is explained, so the gate passes
    result = TripwireResult(ok=not faults, faults=faults, record_count=len(recs),
                            excluded_recnos=sorted(tw.excluded_recnos))
    text = result.report()
    assert "INCOMPLETE" in text
    assert "NOT a faithful copy" in text
    assert "1141" not in text
    assert " 3" in text


def test_run_report_is_silent_when_nothing_was_excluded():
    recs = [{"recno": str(n), "date": "115/8/27", "district": "中正區",
             "name": "n", "land": "l", "implementer": "i", "planner": "p"}
            for n in range(1, 6)]
    result = TripwireResult(ok=True, record_count=5)
    assert "INCOMPLETE" not in result.report()
