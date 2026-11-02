# -*- coding: utf-8 -*-
"""The emitted payload carries links.view_verified_case_ids
(fix-row-order-tiebreak-and-view-badges task 1.5).

The pairing is portal-asserted: view/621 (北投區-關渡段二小段-303's national
page) names cases 10803151 and 10105152 in its 相關連結 block. The field exists
on DiscoveryResult and in the cache, but the attach/emit step never copied it
into project.links — so the viewer cannot tell a portal-asserted case from a
parcel-search-only one, and the 國 badge cannot follow the pairing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import attach_links_to_projects  # noqa: E402
from urtpe.models import make_record  # noqa: E402


def _disc(pid: str, over: dict | None = None) -> dict:
    base = {
        "twur": "",
        "taipei": [],
        "milestones_national": {},
        "milestones_taipei": {},
        "case_milestones": {},
        "milestones_source": {},
        "implementation": {},
        "rewards": {},
        "search_rejected": {},
        "candidate_names": {},
        "case_schedules": {},
    }
    if over:
        base.update(over)
    return {pid: base}


def _project(pid: str, recno: int = 9, date: str = "109/6/9",
             name: str = "擬訂臺北市中山區吉林段二小段898地號等3筆土地都市更新事業計畫案",
             land: str = "臺北市中山區吉林段二小段898地號等3筆"):
    from urtpe.models import Project
    rec = make_record(recno, date, "中山區", name, land, "某建設", "某規劃")
    return Project(project_id=pid, anchor_recno=recno, members=[rec])


def test_view_verified_ids_reach_the_payload():
    pid = "北投區-關渡段二小段-303地號等5筆"
    project = _project(pid)
    disc = _disc(pid, {
        "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/621",
        "taipei": ["10105152", "10803151"],
        "view_verified_case_ids": ["10803151", "10105152"],
    })
    attach_links_to_projects([project], disc)
    assert project.links["view_verified_case_ids"] == ["10803151", "10105152"]


def test_a_result_without_the_field_emits_without_the_key():
    """Legacy caches carry no such field — the payload must tolerate that and
    emit without the key rather than an empty-list lie."""
    pid = "甲"
    project = _project(pid)
    disc = _disc(pid, {"taipei": ["09601260"]})
    attach_links_to_projects([project], disc)
    assert "view_verified_case_ids" not in project.links


def test_an_empty_list_is_a_discovery_fact_and_is_emitted():
    """The field present but empty (view page had no 相關連結 block, or the
    extractor found no ids) is distinct from the field being absent — emit it
    as the empty list it is."""
    pid = "乙"
    project = _project(pid)
    disc = _disc(pid, {"taipei": ["09601260"], "view_verified_case_ids": []})
    attach_links_to_projects([project], disc)
    assert project.links["view_verified_case_ids"] == []
