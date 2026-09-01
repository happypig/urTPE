"""E1/E2/E3 regression tests — 概要-track support, schedule capture, ledger
classification (openspec §7 of viewer-enhancements-and-orphan-case-anchoring)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import (
    _match_case_by_date,
    extract_landcore_from_case_name,
)


class TestSingleDuanExtraction:
    """7.1.1 — single-段 sections (民生段) must extract, not just 段小段."""

    def test_single_duan_name_extracts_landcore(self):
        name = "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案"
        assert extract_landcore_from_case_name(name) == "松山區民生段140-9地號等3筆"

    def test_double_duan_name_still_extracts(self):
        name = "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"
        assert extract_landcore_from_case_name(name) == "文山區木柵段三小段623地號等39筆"

    def test_similarity_gate_now_passes_for_ming_sheng(self):
        """民生段140-9 shape: the two 駁回/撤回 概要 orphans were dropped
        because extraction returned '' (operations log §6.14)."""
        from urtpe.links import compute_landcore_similarity

        anchor = "松山區民生段140-9地號等3筆"
        lc = extract_landcore_from_case_name(
            "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案"
        )
        assert compute_landcore_similarity(anchor, lc) >= 0.7


class TestGaiYaoAnchoring:
    """7.1.2 — _match_case_by_date must know 概要核准日期 (延吉段727 shape)."""

    def _disc(self):
        disc = type("D", (object,), {})()
        disc.case_milestones = {
            "11311291": {
                "概要公聽會日期": "2024/11/29",
                "申請概要日期": "2024/12/13",
                "概要核准日期": "2026/03/31",
            },
        }
        return disc

    def test_gaiyao_approval_date_anchors(self):
        assert _match_case_by_date("2026-03-31", self._disc()) == "11311291"

    def test_roc_gazette_date_anchors(self):
        """7.1.2 (PDF pipeline): raw ROC node date must normalize."""
        assert _match_case_by_date("115/3/31", self._disc()) == "11311291"

    def test_non_gaiyao_date_does_not_match(self):
        assert _match_case_by_date("2025-01-01", self._disc()) == ""


class TestGhostNodeDateFallback:
    """7.1.3 — ghost node_date falls back 核定日期 → 權變核定日期 → 概要核准日期."""

    def test_fallback_to_gaiyao_approval(self):
        from urtpe.links import _ghost_node_date

        ms = {"概要核准日期": "2026/03/31"}
        assert _ghost_node_date(ms) == "2026-03-31"

    def test_hec_ding_wins_over_gaiyao(self):
        from urtpe.links import _ghost_node_date

        ms = {"核定日期": "2008/01/02", "概要核准日期": "2003/03/05"}
        assert _ghost_node_date(ms) == "2008-01-02"

    def test_empty_milestones_give_empty_date(self):
        from urtpe.links import _ghost_node_date

        assert _ghost_node_date({}) == ""


class TestScheduleCapture:
    """7.2.1 — search_taipei_cases_api retains per-case schedule."""

    def test_schedule_stored_in_result(self, monkeypatch):
        import urtpe.links as links

        rows = [
            {"case_id": "11207021", "case_name": "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案",
             "schedule": "已駁回", "details": "r_progress_detail.aspx?case_id=11207021"},
            {"case_id": "11302031", "case_name": "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案",
             "schedule": "自行撤回", "details": "r_progress_detail.aspx?case_id=11302031"},
        ]
        monkeypatch.setattr(links, "_post_taipei_api", lambda url, params: json.dumps(rows))

        class Rec:
            class fake:
                pass
        from urtpe.models import make_record
        rec = make_record(65, "115/12/9", "松山區",
                          "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案",
                          "臺北市松山區民生段140-9地號等3筆", "某建設", "某規劃")
        from urtpe.models import Project
        proj = Project(project_id="松山區-民生段-140-9地號等3筆", anchor_recno=65, members=[rec])
        result = links.search_taipei_cases_api("民生段", "140-9")
        assert result and result[0].get("schedule") == "已駁回"


class TestScheduleFromTop:
    """7.2.2 — top.ashx phase/NAME maps to the search schedule vocabulary."""

    def test_mapping(self):
        from urtpe.links import schedule_from_top

        assert schedule_from_top({"NAME": "事業計畫階段─本府駁回"}) == "已駁回"
        assert schedule_from_top({"NAME": "權利變換計畫階段─實施者自行撤回"}) == "自行撤回"
        assert schedule_from_top({"NAME": "事業概要階段─事業概要業已失效"}) == "已失效"
        assert schedule_from_top({"NAME": "事業計畫階段─業經本府核定"}) == "已核准"
        assert schedule_from_top({"NAME": "權利變換計畫階段─業已提出申請審查"}) == "審查中"
        assert schedule_from_top({"NAME": "執行階段_更新案施工中"}) == "施工中"
        assert schedule_from_top({}) == ""


class TestAttachEmitsSchedules:
    """7.2.2 — case_schedules round-trips through the dict shim and emits."""

    def test_shim_and_emission(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        from urtpe.links import attach_links_to_projects

        raw = RawRecord(5, "115/12/9", "松山區",
                        "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案",
                        "臺北市松山區民生段140-9地號等3筆", "某建設", "某規劃")
        project = Project(project_id="松山區-民生段-140-9地號等3筆",
                          anchor_recno=5, members=[cleanse(raw)])
        disc = {"松山區-民生段-140-9地號等3筆": {
            "twur": "",
            "taipei": ["11207021"],
            "milestones_national": {},
            "milestones_taipei": {},
            "case_milestones": {},
            "milestones_source": {},
            "implementation": {},
            "rewards": {},
            "search_rejected": {},
            "candidate_names": {"11207021": "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案"},
            "case_schedules": {"11207021": "已駁回"},
        }}
        attach_links_to_projects([project], disc)
        assert project.links["case_schedules"] == {"11207021": "已駁回"}

    def test_ghost_payload_carries_schedule(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        from urtpe.links import attach_links_to_projects

        raw = RawRecord(5, "115/12/9", "松山區",
                        "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案",
                        "臺北市松山區民生段140-9地號等3筆", "某建設", "某規劃")
        project = Project(project_id="松山區-民生段-140-9地號等3筆",
                          anchor_recno=5, members=[cleanse(raw)])
        disc = {"松山區-民生段-140-9地號等3筆": {
            "twur": "",
            "taipei": ["11207021", "11302031"],
            "milestones_national": {},
            "milestones_taipei": {},
            "case_milestones": {},
            "milestones_source": {},
            "implementation": {},
            "rewards": {},
            "search_rejected": {},
            "candidate_names": {"11207021": "擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案"},
            "case_schedules": {"11207021": "已駁回", "11302031": "自行撤回"},
            "view_verified_case_ids": ["11207021", "11302031"],
        }}
        attach_links_to_projects([project], disc)
        ghosts = project.links.get("orphan_nodes", [])
        sched = {g["case_id"]: g.get("schedule") for g in ghosts}
        assert sched == {"11207021": "已駁回", "11302031": "自行撤回"}
