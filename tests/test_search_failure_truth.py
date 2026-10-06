# -*- coding: utf-8 -*-
"""A search that could not be performed is not a negative.

Test-writing group 1 of search-failure-truth.

`sweep-failure-truth` split the *probe* loop into match / miss / error. The *search* that
produces candidate view ids still returned `[]` for both a failed request and a search that
succeeded with no results, so the caller recorded a 14-day negative either way.

That distinction cannot be recovered later: both leave `view_ids_checked: []`, and 14 of the
75 existing entries are in exactly that state.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "sweep", ROOT / "scripts" / "fetch_remaining_national_portal.py")
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

NOW = datetime(2026, 10, 6, 14, 0)


def _cand(pid="proj-1"):
    return {"project_id": pid, "section": "通化段六小段", "parcel": "202",
            "count": "7", "current_date": "2026-08-19"}


# --- 1.1 / 1.2: the two empty results are different --------------------------

def test_a_search_request_that_raises_is_reported_as_an_error(monkeypatch):
    def boom(url, data=None, browser=False):
        raise OSError("connection reset")

    monkeypatch.setattr(sweep, "fetch_url", boom)

    outcome, ids = sweep.search_portal("通化段六小段")

    assert outcome == "error", (
        "a request that never completed learned nothing about the portal; reporting an "
        "empty result here is what buries the project for the re-probe TTL")
    assert ids == []


def test_a_search_that_ran_and_found_nothing_is_reported_as_a_miss(monkeypatch):
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: "<html>no results</html>")

    outcome, ids = sweep.search_portal("通化段六小段")

    assert outcome == "miss", (
        "the portal answered and held nothing for this section, which is a real negative")
    assert ids == []


def test_a_search_that_finds_candidates_reports_them_with_a_miss(monkeypatch):
    html = '<a href="/view/1037">a</a><a href="/view/892">b</a>'
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: html)

    outcome, ids = sweep.search_portal("通化段六小段")

    assert ids == ["1037", "892"], ids
    assert outcome == "miss", "candidates found is not itself an error"


# --- 1.3 / 1.4: the ledger records the difference ---------------------------

def test_a_failed_search_produces_an_error_entry_with_no_exclusion():
    ledger = {}

    sweep.record_outcome(ledger, "proj-1", [], outcome="error")

    assert ledger["proj-1"]["twur_class"] == "error"
    kept, skipped = sweep.filter_candidates([_cand()], ledger, now=NOW)
    assert len(kept) == 1 and not skipped, (
        "a search that failed must not suppress the project for the TTL")


def test_an_empty_search_produces_a_miss_entry_with_an_exclusion():
    ledger = {}

    sweep.record_outcome(ledger, "proj-1", [], outcome="miss")

    assert ledger["proj-1"]["twur_class"] == "miss"
    kept, skipped = sweep.filter_candidates([_cand()], ledger, now=NOW)
    assert not kept and len(skipped) == 1, (
        "the portal answered and held nothing, so the exclusion is correct")


def test_the_two_are_distinguishable_despite_identical_empty_check_lists():
    """Both leave `view_ids_checked: []`, which is why the class has to carry it."""
    failed, empty = {}, {}

    sweep.record_outcome(failed, "p", [], outcome="error")
    sweep.record_outcome(empty, "p", [], outcome="miss")

    assert failed["p"]["view_ids_checked"] == empty["p"]["view_ids_checked"] == []
    assert failed["p"]["twur_class"] != empty["p"]["twur_class"], (
        "the class is the only thing separating a failed search from an empty one")


# --- 1.5 / 1.6: end to end through the search helper -----------------------

def test_a_failed_search_makes_no_probe_requests(monkeypatch):
    """Nothing was obtained, so nothing can be probed; probing would be noise."""
    probes = {"n": 0}

    def fetch(url, data=None, browser=False):
        if "/view/" in url:
            probes["n"] += 1
        raise OSError("connection reset")

    monkeypatch.setattr(sweep, "fetch_url", fetch)

    vid, _m, _c, _h, checked, outcome = sweep.find_matching_view_with_outcome(
        "通化段六小段", "202", "7")

    assert vid == "", vid
    assert checked == [], checked
    assert outcome == "error", outcome
    assert probes["n"] == 0, "no candidate pages existed to probe"


def test_an_empty_search_is_a_miss_through_the_search_helper(monkeypatch):
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: "<html>nothing</html>")

    vid, _m, _c, _h, checked, outcome = sweep.find_matching_view_with_outcome(
        "通化段六小段", "202", "7")

    assert vid == "" and checked == []
    assert outcome == "miss", outcome


@pytest.mark.parametrize("label,html,raises,expected", [
    ("found", '<a href="/view/1">x</a>', False, "match"),
])
def test_a_matching_page_still_wins_over_a_failed_search(label, html, raises, expected,
                                                         monkeypatch):
    """Sanity: the new search outcome must not disturb the match path."""
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: html)
    monkeypatch.setattr(sweep, "view_page_matches", lambda *a: True)

    vid, *_rest, outcome = sweep.find_matching_view_with_outcome("s", "p", "c")

    assert outcome == expected
    assert vid == "1"