# -*- coding: utf-8 -*-
"""The comparison outlives the terminal that printed it.

Test-writing group 5 of gazette-ingest-cadence.

`reconcile()` computes the change set, prints it, and returns. Nothing is written, so the
parked portal cascade could never be un-parked: its stated trigger is "reconciliation is
trusted in production and has produced a reliable change set across at least two
consecutive ingestions", and that is not a judgement anyone can make about output that
only ever existed on one screen.

The persisted form is keyed by publication rather than by run, so a re-ingestion does not
produce a second competing record of the same comparison, and a re-read does not silently
recompute an earlier change set against whatever predecessor happens to exist now.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.reconcile import reconcile  # noqa: E402
from urtpe.changeset import (  # noqa: E402
    ChangeSetStore,
    gained_project_ids,
    write_change_set,
)


def _rec(recno, date, land="臺北市北投區振興段四小段166地號等7筆土地"):
    return {
        "recno": str(recno), "date": date, "district": "北投區",
        "name": "擬訂臺北市北投區振興段四小段166地號等7筆土地都市更新事業計畫案",
        "land": land,
    }


@pytest.fixture
def store(tmp_path):
    return ChangeSetStore(tmp_path / "changesets")


# --- tasks 5.1, 5.2: persisted, keyed by publication -------------------------

def test_a_conclusion_is_written_where_a_later_run_can_read_it(store, tmp_path):
    prev = [_rec(i, "115/8/%02d" % (10 - i)) for i in range(5)]
    cur = [_rec(i, "115/8/%02d" % (10 - i)) for i in range(5)] + [
        _rec(99, "115/8/20", "臺北市中山區長春段一小段764地號等2筆土地")]
    result = reconcile(prev, cur, previous_id="2026-08-20", current_id="2026-08-27")

    path = write_change_set(store, result)

    assert path.exists(), "the conclusion must outlive the process"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["previous_id"] == "2026-08-20"
    assert stored["current_id"] == "2026-08-27"
    assert stored["comparable"] is True


def test_the_persisted_form_is_readable_without_rerunning_the_ingestion(store):
    prev = [_rec(1, "115/8/01")]
    cur = [_rec(1, "115/8/01"), _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地")]
    result = reconcile(prev, cur, previous_id="a", current_id="b")
    write_change_set(store, result)

    loaded = store.load("b")

    assert loaded is not None
    assert loaded["new_approvals"] == 1
    assert loaded["current_total"] == 2


def test_rewriting_the_same_publication_replaces_its_record_rather_than_adding_one(store):
    """Keyed by publication, so two runs over one publication leave one conclusion."""
    prev = [_rec(1, "115/8/01")]
    cur = [_rec(1, "115/8/01"), _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地")]
    result = reconcile(prev, cur, previous_id="a", current_id="b")

    write_change_set(store, result)
    write_change_set(store, result)

    files = list(store.root.glob("*.json"))
    assert len(files) == 1, "a re-ingestion must not leave two competing records"
    assert len(store.all()) == 1


# --- task 5.3: the identities, not just the counts ---------------------------

def test_the_change_set_names_the_projects_that_gained_an_approval(store):
    """The thing a portal sweep needs, and cannot reconstruct from a count."""
    prev = [_rec(1, "115/8/01")]
    cur = [
        _rec(1, "115/8/01"),
        _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地"),
        _rec(3, "115/8/16", "臺北市萬華區華中段一小段201-2地號等26筆土地"),
    ]
    result = reconcile(prev, cur, previous_id="a", current_id="b")
    write_change_set(store, result)

    gained = gained_project_ids(store.load("b"))

    assert len(gained) == 2, gained
    assert any("逸仙段三小段34" in g for g in gained), gained
    assert any("華中段一小段201-2" in g for g in gained), gained


def test_projects_present_in_both_publications_are_not_reported_as_gained(store):
    prev = [_rec(1, "115/8/01", "臺北市北投區振興段四小段166地號等7筆土地"),
            _rec(2, "115/8/02", "臺北市中山區長春段一小段764地號等2筆土地")]
    cur = list(prev) + [_rec(3, "115/8/16", "臺北市萬華區華中段一小段201-2地號等26筆土地")]
    result = reconcile(prev, cur, previous_id="a", current_id="b")
    write_change_set(store, result)

    gained = gained_project_ids(store.load("b"))

    assert len(gained) == 1, gained
    assert "華中段一小段201-2" in gained[0], gained


def test_a_change_set_with_no_new_approvals_names_nothing(store):
    prev = [_rec(1, "115/8/01"), _rec(2, "115/8/02", "臺北市中山區長春段一小段764地號等2筆土地")]
    result = reconcile(prev, list(prev), previous_id="a", current_id="b")
    write_change_set(store, result)

    assert gained_project_ids(store.load("b")) == []


# --- task 5.4: "no comparison" is not "nothing changed" ----------------------

def test_no_comparison_is_recorded_as_no_comparison_not_as_an_empty_set(store):
    """The distinction that a bare `[]` cannot carry."""
    result = reconcile(None, [_rec(1, "115/8/01")], current_id="first")
    write_change_set(store, result)

    stored = store.load("first")

    assert stored["comparable"] is False
    assert stored.get("note"), "a non-comparison must say why"
    assert stored["gained_project_ids"] == [], (
        "an empty gain list here means 'not measured', and must not read as 'nothing "
        "gained' — the record's comparable flag is what distinguishes them")


def test_net_change_is_a_number_not_a_null(store):
    """
et_change is a property, so it is absent from asdict; a null reads as a gap."""
    prev = [_rec(1, "115/8/01")]
    cur = [_rec(1, "115/8/01"), _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地")]
    write_change_set(store, reconcile(prev, cur, previous_id="a", current_id="b"))

    stored = store.load("b")

    assert stored["net_change"] == 1, stored["net_change"]
    assert stored["authoritative"]["net_change"] == 1


def test_an_incomparable_record_is_marked_unmeasurable(store):
    result = reconcile(None, [_rec(1, "115/8/01")], current_id="first")
    write_change_set(store, result)

    assert store.load("first")["comparable"] is False
    assert store.load("first")["new_approvals"] == 0, (
        "counts default to zero, which is why comparable must be read alongside them")


# --- task 5.5: a re-read does not recompute against a newer predecessor ------

def test_a_reread_writes_under_its_own_event_not_over_the_original(store):
    prev = [_rec(1, "115/8/01")]
    cur = [_rec(1, "115/8/01"), _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地")]
    write_change_set(store, reconcile(prev, cur, previous_id="a", current_id="b"),
                     event="first_ingest")

    # a later publication arrives and the original is re-read against *it*
    newer = cur + [_rec(3, "115/9/01", "臺北市大安區懷生段四小段地號等19筆土地")]
    write_change_set(store, reconcile(newer, cur, previous_id="c", current_id="b"),
                     event="reread")

    assert store.load("b")["previous_id"] == "a", (
        "the original comparison named publication a; a re-read against c must not "
        "silently rewrite what the b ingestion concluded")
    assert store.load("b")["previous_id"] != "c"
    rereads = [e for e in store.load("b").get("events", [])
               if e.get("event") == "reread"]
    assert rereads and rereads[0]["previous_id"] == "c", (
        "the re-read is recorded, as its own event, against the predecessor it used")


def test_the_authoritative_signals_are_separated_from_unresolvable_movement(store):
    prev = [_rec(1, "115/8/01")]
    cur = [_rec(1, "115/8/01"), _rec(2, "115/8/15", "臺北市信義區逸仙段三小段34地號等6筆土地")]
    write_change_set(store, reconcile(prev, cur, previous_id="a", current_id="b"))

    stored = store.load("b")

    assert "authoritative" in stored, (
        "new approvals and net change are assertions; re-dating and editing are the "
        "same observation as a deletion in this data, and must not be filed beside them")
    assert set(stored["authoritative"]) == {"new_approvals", "net_change",
                                            "current_total", "previous_total"}
    assert set(stored["unresolvable"]) >= {"redated", "edited", "vanished"}