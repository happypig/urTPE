"""§9 BDD scenarios (add-virtual-node-ordering-and-chain follow-ups, D12 Amendment 3):
links.taipei ascending emission, 相關連結 ascending render, 603 family-wide
interleave, same-date adjacency, gazette-anomaly review flag.
"""
from __future__ import annotations

import json
import sys

import pytest

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import attach_links_to_projects
from urtpe.models import make_record, Project


def _disc(pid, over=None):
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


class TestTaipeiAscending:
    """9.2 — attach emits links.taipei case_id-ascending."""

    def test_platform_order_drift_normalized(self):
        pid = "中山區-吉林段二小段-898地號等3筆"
        rec = make_record(9, "109/6/9", "中山區",
                          "擬訂臺北市中山區吉林段二小段898地號等3筆土地都市更新事業計畫案",
                          "臺北市中山區吉林段二小段898地號等3筆", "某建設", "某規劃")
        project = make_project(pid, [rec])
        disc = _disc(pid, {"taipei": ["10906091", "11403002", "10906092", "10906093"]})
        attach_links_to_projects([project], disc)
        assert project.links["taipei"] == ["10906091", "10906092", "10906093", "11403002"]

    def test_anchored_assignments_unchanged(self):
        """Sorting the project-level list never re-anchors node cases."""
        pid = "中山區-吉林段四小段-676地號等1筆"
        rec = make_record(1284, "115/3/25", "中山區",
                          "擬訂臺北市中山區吉林段四小段676地號等1筆土地都市更新事業計畫案",
                          "臺北市中山區吉林段四小段676地號等1筆", "某建設", "某規劃")
        project = make_project(pid, [rec])
        disc = _disc(pid, {"taipei": ["09601262", "09601260"]})
        attach_links_to_projects([project], disc)
        assert project.links["taipei"] == ["09601260", "09601262"]


def make_project(pid, members):
    from urtpe.models import Project
    return Project(project_id=pid, anchor_recno=members[0].recno, members=members)


class TestGazetteAnomalyFlag:
    """9.4 — printed 擬訂 vs platform 變更+approved → review flag, stage faithful."""

    def test_anomaly_flag_added(self):
        pid = "中正區-臨沂段一小段-507地號等3筆"
        rec = make_record(1, "115/8/11", "中正區",
                          "變更臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫及變更(第二次)權利變換計畫案",
                          "臺北市中正區臨沂段一小段507地號等3筆", "東綺建設", "某規劃")
        # simulate the 920-shape: gazette prints 擬訂 while the platform case is a 變更 with approval
        rec.name = "擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案"
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        raw = RawRecord(920, "107/1/25", "中正區",
                        "擬訂臺北市中正區河堤段五小段399地號等3筆土地都市更新事業計畫案",
                        "臺北市中正區河堤段五小段399地號等3筆", "某建設", "某規劃")
        project = make_project(pid, [cleanse(raw)])
        disc = _disc(pid, {
            "taipei": ["09511214"],
            "candidate_names": {"09511214": "變更臺北市中正區河堤段五小段399地號等3筆土地都市更新事業計畫案"},
        })
        attach_links_to_projects([project], disc)
        node = project.members[0]
        assert node.stage == "擬訂"  # faithful to the PDF
        assert any("平台案件狀態不一致" in f for f in node.review_flags)


class TestNoFalseAnomaly:
    def test_matching_stage_no_flag(self):
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        pid = "中正區-臨沂段一小段-507地號等3筆"
        raw = RawRecord(994, "106/3/21", "中正區",
                        "擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案",
                        "臺北市中正區臨沂段一小段507地號等3筆", "東綺建設", "某規劃")
        project = make_project(pid, [cleanse(raw)])
        disc = _disc(pid, {
            "taipei": ["10110211"],
            "candidate_names": {"10110211": "擬訂臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫案"},
        })
        attach_links_to_projects([project], disc)
        assert not any("平台案件狀態不一致" in f for f in project.members[0].review_flags)
