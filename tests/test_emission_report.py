"""Emission reports the portal data a run failed to attach.

Test-writing group 2 of no-silent-data-loss.

`official-link-discovery` and `taipei-implementation-data` already state that link and
implementation data SHALL be attached. Nothing checked conformance, so a rebuild without
`--links` emitted a dataset violating both capabilities and reported success. These
tests pin the check that closes that.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.emission import emission_faults, emission_partial  # noqa: E402

LINK_FIELDS = ("twur", "taipei", "milestones_national", "milestones_taipei")


def _project(pid, links=None, implementation=None):
    node = {
        "recno": "1", "date": "2020-01-01", "district": "中正區",
        "stage": "事業計畫", "track": "事業計畫", "is_current": True,
        "land": "臺北市中正區甲段一小段 1 地號等1筆土地",
    }
    if links is not None:
        node["links"] = links
    if implementation is not None:
        node["implementation"] = implementation
    p = {
        "project_id": pid, "district": "中正區", "section": "甲段一小段",
        "implementer": "甲公司", "anchor_recno": "1", "member_recnos": ["1"],
        "published_date": "2026-08-27", "edges": [], "nodes": [node],
    }
    if links is not None:
        p["links"] = links
    if implementation is not None:
        p["implementation"] = implementation
    return p


def _conforming_links():
    return {f: {"a": "b"} if f.startswith("milestones") else ["x"]
            for f in LINK_FIELDS}


# --- task 2.1 every project lacks link data ---------------------------------

def test_a_dataset_with_no_link_data_is_reported():
    projects = [_project(f"P{i}", links={}) for i in range(5)]
    faults = emission_faults(projects)
    assert faults, "a dataset with no link data must be reported, not emitted quietly"
    assert any("link" in f.lower() for f in faults)


def test_the_report_names_the_fields_and_the_count():
    projects = [_project(f"P{i}", links={}) for i in range(5)]
    faults = emission_faults(projects)
    joined = " ".join(faults)
    assert "5" in joined, "the report must state how many projects are affected"
    for field in ("twur", "milestones_taipei"):
        assert field in joined, f"the report must name the missing field {field}"


def test_the_report_names_the_step_that_did_not_attach_it():
    """Actionable from the output alone: a reader must not have to guess."""
    projects = [_project("P0", links={})]
    joined = " ".join(emission_faults(projects))
    assert "--links" in joined, (
        "the report must name the run step that attaches this data, otherwise the "
        "cause is not identifiable without re-running")


# --- task 2.2 a partial set is partial, not conforming -----------------------

def test_a_partial_link_set_is_reported_as_partial():
    """Partial coverage is the expected state and must not be a fault.

    The portals do not cover every project; the real dataset has 7 of 709 without link
    data and is healthy. Reporting that as a fault would fire on every run and be
    ignored, which is the failure mode this change exists to remove. It is reported as a
    count instead, so a regression against a previous run stays visible.
    """
    projects = [_project("P0", links=_conforming_links(), implementation={"Base_Area": "1"})]
    projects += [_project(f"Q{i}", links={}, implementation={"Base_Area": "1"})
                for i in range(4)]
    assert emission_faults(projects) == [], (
        "partial coverage is not a fault: %s" % emission_faults(projects))
    notes = emission_partial(projects)
    assert notes, "partial coverage must still be reported as a count"
    joined = " ".join(notes)
    assert "1" in joined and "5" in joined, (
        "the note must give both the covered and the uncovered counts: %s" % joined)


def test_a_minority_populated_is_reported_as_a_count():
    projects = [_project(f"P{i}", links=_conforming_links(), implementation={"Base_Area": "1"})
                for i in range(1)]
    projects += [_project(f"Q{i}", links={}, implementation={"Base_Area": "1"})
                for i in range(9)]
    assert emission_faults(projects) == [], (
        "one populated project out of ten is coverage, not a failed run")
    assert "1 of 10" in " ".join(emission_partial(projects))


def test_records_without_link_data_are_counted_separately():
    """A rebuild can leave project-level links while dropping record-level ones."""
    projects = [_project("P0", links=_conforming_links()) for _ in range(3)]
    projects[0]["nodes"][0].pop("links", None)
    joined = " ".join(emission_partial(projects))
    assert "record-level" in joined.lower(), (
        "record-level coverage must be distinguishable from project-level: %s" % joined)


# --- task 2.3 a conforming dataset is silent --------------------------------

def test_a_conforming_dataset_reports_nothing():
    projects = [_project(f"P{i}", links=_conforming_links(),
                         implementation={"Base_Area": "100"}) for i in range(5)]
    assert emission_faults(projects) == [], (
        "a conforming dataset must not raise: %s" % emission_faults(projects))
    assert emission_partial(projects) == [], (
        "a fully covered dataset must not raise a partial note either")


def test_the_current_emission_is_conforming():
    """The real dataset, not a fixture: the check must pass on what we actually ship."""
    data = ROOT / "viewer" / "projects.data.js"
    if not data.exists():
        pytest.skip("projects.data.js not emitted")
    import json
    text = data.read_text(encoding="utf-8")
    doc = json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))
    faults = emission_faults(doc["projects"])
    assert faults == [], (
        "the emitted dataset must be conforming; it is not: %s" % faults)


# --- task 2.5 implementation and reward fields -------------------------------

def test_absent_implementation_data_is_reported_with_both_counts():
    projects = [_project(f"P{i}", links=_conforming_links()) for i in range(6)]
    faults = emission_faults(projects)
    joined = " ".join(faults)
    assert "implementation" in joined.lower(), (
        "absent implementation data must be reported: %s" % joined)
    assert "6" in joined, "the report must give the affected count"


def test_partial_implementation_data_is_reported_as_a_count():
    projects = [_project("P0", links=_conforming_links(), implementation={"Base_Area": "1"})]
    projects += [_project(f"Q{i}", links=_conforming_links()) for i in range(3)]
    assert emission_faults(projects) == []
    assert "1 of 4" in " ".join(emission_partial(projects))


def test_implementation_absent_alone_does_not_mask_a_link_fault():
    projects = [_project(f"P{i}", links={}) for i in range(3)]
    joined = " ".join(emission_faults(projects)).lower()
    assert "link" in joined, "the link fault must still be reported"
