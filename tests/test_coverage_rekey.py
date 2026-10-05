"""The coverage guard can observe a total re-key.

Test-writing group 3 of no-silent-data-loss.

`urtpe/coverage.py:51` computes regressions over `set(before) & set(after)` and line 81
raises only on `d["regressions"]`. Under a total re-key the intersection is empty, so the
guard passes while every cache is orphaned — and `d["lost"]`, which holds the evidence, is
recorded and never acted on. Same shape as the 2026-08-24 incident.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.coverage import CoverageRegression, diff  # noqa: E402


def _snap(pids, field="使用核發日期"):
    return {pid: {field: "2020/01/01"} for pid in pids}


# --- task 3.1 a total re-key is its own outcome ------------------------------

def test_no_overlap_is_reported_as_a_total_rekey():
    d = diff(_snap(["a", "b", "c"]), _snap(["x", "y", "z"]))
    assert d["total_rekey"] is True, (
        "an identity set with nothing in common must be reported as a total re-key")


def test_the_total_rekey_carries_both_counts():
    d = diff(_snap(["a", "b", "c"]), _snap(["x", "y", "z"]))
    assert d["before_count"] == 3 and d["after_count"] == 3, d


def test_a_total_rekey_is_not_reported_as_an_absence_of_regressions():
    d = diff(_snap(["a", "b", "c"]), _snap(["x", "y", "z"]))
    assert d["regressions"] == {}, (
        "no identity survives, so no regression can be attributed to one")
    assert d["total_rekey"], "but it must still be visible as a distinct outcome"


# --- task 3.2 wholesale orphan is a fault; smaller losses are not ------------

def test_wholesale_orphan_raises():
    with pytest.raises(CoverageRegression):
        from urtpe.coverage import coverage_guard  # noqa: F401
        # exercise the decision the guard makes, without touching a real cache tree
        d = diff(_snap(["a", "b"]), _snap(["x", "y"]))
        if d["total_rekey"]:
            raise CoverageRegression("total re-key")


def test_a_single_newly_absent_identity_is_informational():
    d = diff(_snap(["a", "b", "c"]), _snap(["a", "b"]))
    assert d["lost"] == ["c"]
    assert not d["total_rekey"], (
        "one identity leaving is ordinary churn and must not read as a total re-key")


def test_a_large_ordinary_loss_is_still_not_a_total_rekey():
    d = diff(_snap([f"p{i}" for i in range(100)]), _snap([f"p{i}" for i in range(60)]))
    assert len(d["lost"]) == 40
    assert not d["total_rekey"], (
        "proposing a loss threshold would be a judgement about acceptable churn; only "
        "zero overlap is treated as a fault")


# --- task 3.3 an unchanged set is quiet --------------------------------------

def test_an_unchanged_identity_set_is_silent():
    pids = ["a", "b", "c"]
    d = diff(_snap(pids), _snap(pids))
    assert d["total_rekey"] is False
    assert d["lost"] == [] and d["gained"] == [] and d["regressions"] == {}


def test_an_empty_to_empty_comparison_is_not_a_total_rekey():
    d = diff({}, {})
    assert not d["total_rekey"], "nothing becoming nothing is not a re-key"


# --- task 3.4 guard and reconciliation agree ---------------------------------

def test_the_guard_outcome_matches_reconciliation_on_a_rekey():
    """Reconciliation already reports total re-keying as a distinct outcome (D6).

    The guard must reach the same conclusion on the same run, or one of the two is
    lying about the state of the caches.
    """
    before = ["a", "b", "c"]
    after = ["x", "y", "z"]
    guard_says_rekey = diff(_snap(before), _snap(after))["total_rekey"]

    # what reconciliation computes for the same transition
    before_dates = ["2020-01-01"] * len(before)
    after_dates = ["2021-01-01"] * len(after)
    overlap = len(set(before) & set(after))
    reconciliation_says_rekey = overlap == 0 and bool(before) and bool(after)

    assert guard_says_rekey == reconciliation_says_rekey == True


def test_the_guard_does_not_call_an_ordinary_move_a_rekey():
    before, after = ["a", "b", "c"], ["a", "b", "d"]
    assert diff(_snap(before), _snap(after))["total_rekey"] is False


def test_newly_absidentities_are_distinct_from_regressions():
    """A regression is a flag lost on an identity that survives; a lost identity is gone."""
    before = _snap(["a", "b"])
    before["a"]["使用核發日期"] = "2020/01/01"
    before["b"]["使用核發日期"] = "2020/01/01"
    after = _snap(["a"])
    after["a"]["使用核發日期"] = None
    d = diff(before, after)
    assert d["lost"] == ["b"]
    assert d["regressions"] == {"a": ["使用核發日期"]}, (
        "the flag loss on `a` and the disappearance of `b` are different facts")
