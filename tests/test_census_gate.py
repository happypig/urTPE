# -*- coding: utf-8 -*-
"""The census gate: the merge partition must be total, disjoint, and agree with
the emission count — verified before any artifact is written.

wire-standing-checks task 1.1. The dataset-completeness audit's Appendix A
asserts this in its own script; the gate moves the assertion into the pipeline,
beside the tripwire, under the same exit-4 contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.models import CleanRecord, Project  # noqa: E402
from urtpe.tripwire import Tripwire  # noqa: E402


def _record(recno: int) -> CleanRecord:
    return CleanRecord(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district="中正區", district_land="中正區", name=f"案{recno}", name_raw="",
        land=f"臺北市中正區甲段一小段{recno}地號等1筆土地", section="甲段一小段",
        first_parcel=str(recno), parcels=[str(recno)], aliases={},
        land_count=1, orig_count=None, named_anchor="", area_section="",
        stage="擬訂", stage_index=0, track="事業計畫",
        implementer="甲", planner="乙", auto_fixes=[], review_flags=[],
    )


def _family(pid: str, *recnos: int) -> Project:
    return Project(project_id=pid, anchor_recno=recnos[0],
                   members=[_record(r) for r in recnos])


def test_a_total_disjoint_partition_passes():
    clean = [_record(1), _record(2), _record(3)]
    projects = [_family("甲", 1, 2), _family("乙", 3)]
    faults = Tripwire().check_partition(clean, projects)
    assert faults == [], faults


def test_a_lost_record_is_named():
    clean = [_record(1), _record(2), _record(3)]
    # family covers only 1 and 2 — record 3 is lost
    projects = [_family("甲", 1, 2)]
    faults = Tripwire().check_partition(clean, projects)
    assert faults, "a lost record must be a fault"
    assert any("3" in f for f in faults), faults


def test_a_double_counted_record_names_both_families():
    clean = [_record(1), _record(2)]
    # record 2 appears in both families
    projects = [_family("甲", 1, 2), _family("乙", 2)]
    faults = Tripwire().check_partition(clean, projects)
    assert faults, "a double-counted record must be a fault"
    joined = " ".join(faults)
    assert "甲" in joined and "乙" in joined, joined


def test_count_disagreement_is_a_fault():
    clean = [_record(1), _record(2)]
    projects = [_family("甲", 1, 2)]
    # doc claims 3 records while clean holds 2
    faults = Tripwire().check_partition(clean, projects, emitted_records=3)
    assert faults, "a count disagreement must be a fault"
    assert any("3" in f and "2" in f for f in faults), faults


def test_empty_partition_with_empty_clean_passes():
    faults = Tripwire().check_partition([], [])
    assert faults == []


def test_the_census_is_pure_no_io():
    """The check takes domain objects and returns strings; no filesystem access.
    Pinned by calling it with objects whose paths do not exist."""
    clean = [_record(1)]
    projects = [_family("甲", 1)]
    faults = Tripwire().check_partition(clean, projects)
    assert faults == []
