# -*- coding: utf-8 -*-
"""A fetch failure is not a portal negative.

Test-writing group 1 of sweep-failure-truth.

`find_matching_view` catches every exception per probe and returns an empty view id when
all of them fail. The caller reads that as "no match" and stamps `last_probed`, which is
what excludes the project for 14 days -- so one transient failure buries a project for two
weeks, in a ledger entry byte-identical to a genuine "the portal does not list this parcel".

This is already a violation rather than a gap: the requirement *No-match ledger
persistence* scopes recording to a candidate that **completes** targeted search, and a run
whose probes all raised never completed one.

Three outcomes, not two:

    match   a probe returned a page satisfying the strict matcher -> entry removed
    miss    every probe returned, none satisfied                 -> 14-day exclusion
    error   every probe raised                                   -> no exclusion
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "sweep", ROOT / "scripts" / "fetch_remaining_national_portal.py")
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

NOW = datetime(2026, 10, 6, 10, 30)


def _cand(pid):
    return {"project_id": pid, "section": "華中段二小段", "parcel": "201-2",
            "count": "26", "current_date": "2026-09-24"}


# --- 1.1 / 1.3: the ledger distinguishes the two ---------------------------

def test_an_all_failed_probe_run_is_recorded_as_an_error_not_a_no_match():
    ledger = {}

    sweep.record_outcome(ledger, "proj-1", ["v1", "v2"], outcome="error")

    entry = ledger["proj-1"]
    assert entry["twur_class"] == "error", (
        "a run where every fetch raised is not evidence the portal lacks the case")
    assert entry["view_ids_checked"] == ["v1", "v2"], "what was attempted is evidence"
    assert entry["last_probed"], "when it failed is evidence"


def test_an_error_entry_is_readable_as_an_error_without_the_run_log():
    ledger = {}
    sweep.record_no_match(ledger, "proj-miss", ["v9"])
    sweep.record_outcome(ledger, "proj-err", ["v1"], outcome="error")

    assert ledger["proj-miss"].get("twur_class") != "error"
    assert ledger["proj-err"]["twur_class"] == "error", (
        "a reader must be able to tell these apart from the ledger alone")


# --- 1.2 / 1.5 / 1.6: eligibility -----------------------------------------

def test_an_error_entry_does_not_exclude_the_project_from_the_next_run():
    """The whole point: a failure must not cost two weeks of coverage."""
    ledger = {"proj-1": {"last_probed": NOW.isoformat(), "twur_class": "error",
                         "view_ids_checked": ["v1"]}}

    kept, skipped = sweep.filter_candidates([_cand("proj-1")], ledger, now=NOW)

    assert [c["project_id"] for c in kept] == ["proj-1"], kept
    assert skipped == [], "an error entry must not suppress re-probing"


def test_an_error_entry_stays_eligible_however_recent_it_is():
    ledger = {"proj-1": {"last_probed": NOW.isoformat(), "twur_class": "error",
                         "view_ids_checked": ["v1"]}}

    kept, _ = sweep.filter_candidates([_cand("proj-1")], ledger,
                                      reprobe_days=36500, now=NOW)

    assert len(kept) == 1, (
        "the entry must not gain an exclusion as the TTL grows; it was never a negative")


def test_a_genuine_miss_still_carries_the_ttl_exclusion():
    """The fix must not weaken the rule it corrects."""
    ledger = {"proj-1": {"last_probed": NOW.isoformat(), "view_ids_checked": ["v1"]}}

    kept, skipped = sweep.filter_candidates([_cand("proj-1")], ledger, now=NOW)

    assert kept == [], "a real miss is still excluded within the TTL"
    assert [c["project_id"] for c in skipped] == ["proj-1"]


def test_a_miss_recorded_via_record_outcome_is_still_excluded():
    ledger = {}
    sweep.record_outcome(ledger, "proj-1", ["v1"], outcome="miss")

    kept, skipped = sweep.filter_candidates([_cand("proj-1")], ledger, now=NOW)

    assert kept == []
    assert len(skipped) == 1


def test_never_approved_is_still_permanently_excluded():
    ledger = {"proj-1": {"last_probed": (NOW - timedelta(days=400)).isoformat(),
                         "twur_class": "never-approved"}}

    _, skipped = sweep.filter_candidates([_cand("proj-1")], ledger, now=NOW)

    assert len(skipped) == 1, "an expired never-approved entry stays excluded"


# --- 1.4: a partial failure that still matched is a match ------------------

def test_a_search_returning_no_view_ids_is_a_miss_not_an_error(monkeypatch):
    """The empty-result path.

    A search that yielded no view ids at all is a real negative: the portal answered, with
    nothing in it. There was nothing to fetch, so nothing could have failed -- calling it an
    error would return every such project to the queue forever. It must also carry the
    outcome, which is the return path this test exists to pin: it once returned five values
    while every other path returned six, and the whole sweep died on its first project.
    """
    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: [])

    result = sweep.find_matching_view_with_outcome("華中段二小段", "201-2", "26")

    assert len(result) == 6, "every return path carries the outcome: %r" % (result,)
    assert result[5] == "miss", result[5]


def test_every_return_path_of_the_search_carries_an_outcome(monkeypatch):
    """A shape test, because the failure was a shape mismatch, not a logic error."""
    cases = []

    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: [])
    cases.append(("no view ids", sweep.find_matching_view_with_outcome("s", "p", "c")))

    def boom(url, data=None, browser=False):
        raise OSError("connection reset")

    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: ["v1"])
    monkeypatch.setattr(sweep, "fetch_url", boom)
    cases.append(("all probes raised",
                  sweep.find_matching_view_with_outcome("s", "p", "c")))

    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: "<html>x</html>")
    monkeypatch.setattr(sweep, "view_page_matches", lambda *a: False)
    cases.append(("probed, none matched",
                  sweep.find_matching_view_with_outcome("s", "p", "c")))

    monkeypatch.setattr(sweep, "view_page_matches", lambda *a: True)
    cases.append(("matched",
                  sweep.find_matching_view_with_outcome("s", "p", "c")))

    for label, result in cases:
        assert len(result) == 6, "%s returned %d values, expected 6: %r" % (label, len(result), result)
        assert result[5] in ("match", "miss", "error"), "%s: bad outcome %r" % (label, result[5])


def test_some_probes_raising_with_a_later_match_is_a_match_not_an_error(monkeypatch):
    """Discarding a real match would be wrong in the opposite direction."""
    calls = {"n": 0}

    def fake_fetch(url, data=None, browser=False):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("connection reset")
        return "<html>華中段二小段 201-2地號等26筆</html>"

    monkeypatch.setattr(sweep, "fetch_url", fake_fetch)
    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: ["v1", "v2"])
    monkeypatch.setattr(sweep, "view_page_matches", lambda h, s, p, c: True)

    vid, *_rest, outcome = sweep.find_matching_view_with_outcome(
        "華中段二小段", "201-2", "26", max_probe=4)

    assert vid == "v2", vid
    assert outcome == "match", f"a raised probe then a hit is a match, got {outcome!r}"


def test_all_probes_raising_reports_error_not_a_miss(monkeypatch):
    def fake_fetch(url, data=None, browser=False):
        raise OSError("connection reset")

    monkeypatch.setattr(sweep, "fetch_url", fake_fetch)
    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: ["v1", "v2", "v3"])

    vid, _m, _c, _h, checked, outcome = sweep.find_matching_view_with_outcome(
        "華中段二小段", "201-2", "26", max_probe=4)

    assert vid == "", vid
    assert outcome == "error", (
        "every probe raised, so the search never completed; reporting a miss here is "
        "what buries the project for 14 days")
    assert len(checked) == 3, checked


def test_probes_returning_but_none_matching_reports_a_miss(monkeypatch):
    monkeypatch.setattr(sweep, "fetch_url", lambda *a, **k: "<html>nothing</html>")
    monkeypatch.setattr(sweep, "search_portal", lambda *a, **k: ["v1", "v2"])
    monkeypatch.setattr(sweep, "view_page_matches", lambda *a: False)

    _vid, _m, _c, _h, _checked, outcome = sweep.find_matching_view_with_outcome(
        "華中段二小段", "201-2", "26", max_probe=4)

    assert outcome == "miss", (
        "a portal that answered and had nothing is a real negative")


# --- 1.7: classification applies to negatives only -------------------------

def test_an_error_outcome_is_not_classified_as_recoverable():
    ledger = {"proj-1": {"last_probed": NOW.isoformat(), "twur_class": "error"}}

    sweep.annotate_class(ledger, "proj-1", "recoverable")

    assert ledger["proj-1"]["twur_class"] == "error", (
        "nothing was retrieved, so there is no case outcome to classify; forcing "
        "recoverable would assert the portal should hold a page we never reached")


def test_annotate_class_still_works_for_a_real_negative():
    ledger = {"proj-1": {"last_probed": NOW.isoformat()}}

    sweep.annotate_class(ledger, "proj-1", "never-approved")

    assert ledger["proj-1"]["twur_class"] == "never-approved"


# --- 1.8 / 1.9 / 1.10: the stop time ---------------------------------------

def test_a_malformed_deadline_refuses_the_run_rather_than_defaulting():
    with pytest.raises(ValueError):
        sweep.parse_deadline("half past six")


def test_a_deadline_is_parsed_into_an_hour_and_minute():
    assert sweep.parse_deadline("17:00") == (17, 0)
    assert sweep.parse_deadline("06:30") == (6, 30)


def test_an_out_of_range_deadline_is_refused():
    with pytest.raises(ValueError):
        sweep.parse_deadline("25:00")


def test_the_default_stop_time_is_0630_not_the_hardcoded_0700():
    assert sweep.DEFAULT_DEADLINE == "06:30", (
        "the requirement says 06:30; the implementation said 07:00. The requirement is "
        "what the spec-level contract asserts, so it wins.")
    hour, minute = sweep.parse_deadline(sweep.DEFAULT_DEADLINE)
    assert (hour, minute) == (6, 30)


def test_a_post_deadline_launch_resolves_to_the_next_day_not_an_instant_exit():
    start = datetime(2026, 10, 6, 10, 30)          # already past 06:30
    resolved = sweep.resolve_deadline(start, *sweep.parse_deadline("06:30"))
    assert resolved.date() == (start + timedelta(days=1)).date(), resolved
    assert (resolved - start) > timedelta(hours=12), "not an instant stop"


def test_a_pre_deadline_launch_resolves_to_the_same_day():
    start = datetime(2026, 10, 6, 4, 0)
    resolved = sweep.resolve_deadline(start, *sweep.parse_deadline("06:30"))
    assert resolved.date() == start.date()
    assert (resolved - start) == timedelta(hours=2, minutes=30)


def test_a_supplied_deadline_governs_instead_of_the_default():
    resolved = sweep.resolve_deadline(datetime(2026, 10, 6, 10, 30),
                                      *sweep.parse_deadline("17:00"))
    assert resolved.date() == datetime(2026, 10, 6).date()
    assert resolved.hour == 17 and resolved.minute == 0, resolved