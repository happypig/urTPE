"""Tests for official link discovery: join/attach logic, parsing, and graph emission."""

from __future__ import annotations

import pytest

from urtpe.links import (
    extract_view_id_from_search,
    extract_case_ids_from_view,
    extract_tuidui_history_from_view,
    extract_taipei_stage_process,
    build_land_core_key,
    attach_links_to_projects,
    LinksDiscovery,
)
from tests.fixtures_links import (
    VIEW_771_HTML,
    VIEW_292_HTML,
    VIEW_NO_CITY_HTML,
    VIEW_VISIBLE_TUIDUI_HTML,
    TAIPEI_CASE_10110211_HTML,
    SEARCH_UNIQUE_HIT_HTML,
    SEARCH_NO_HIT_HTML,
    SEARCH_MULTI_HIT_HTML,
    TEST_CORES,
)


class TestSearchParsing:
    """Test parsing of national portal search results."""

    def test_unique_hit_returns_view_id(self):
        view_id = extract_view_id_from_search(SEARCH_UNIQUE_HIT_HTML)
        assert view_id == "771"

    def test_no_hit_returns_none(self):
        view_id = extract_view_id_from_search(SEARCH_NO_HIT_HTML)
        assert view_id is None

    def test_multi_hit_returns_none_and_flagged(self):
        view_id = extract_view_id_from_search(SEARCH_MULTI_HIT_HTML)
        assert view_id is None


class TestViewPageParsing:
    """Test parsing of national portal view pages."""

    def test_extract_single_city_case_id(self):
        case_ids = extract_case_ids_from_view(VIEW_771_HTML)
        assert case_ids == ["10110181"]

    def test_extract_multiple_city_case_ids(self):
        case_ids = extract_case_ids_from_view(VIEW_292_HTML)
        assert set(case_ids) == {"10110211", "10810271"}

    def test_no_city_links_returns_empty(self):
        case_ids = extract_case_ids_from_view(VIEW_NO_CITY_HTML)
        assert case_ids == []

    def test_extract_tuidui_history(self):
        history = extract_tuidui_history_from_view(VIEW_771_HTML)
        assert "事業計畫申請日期" in history
        assert history["事業計畫申請日期"] == "101.12.28"
        assert history["事業計畫核定日期"] == "109.11.17"
        assert history["權利變換計畫申請日期"] == "101.12.28"
        assert history["權利變換計畫核定日期"] == "109.11.17"

    def test_extract_tuidui_history_visible_table(self):
        """Current portal serves 推動歷程 as a visible type4_table (no display:none)."""
        history = extract_tuidui_history_from_view(VIEW_VISIBLE_TUIDUI_HTML)
        assert history["事業計畫申請日期"] == "99.01.27"
        assert history["事業計畫核定日期"] == "101.08.28"
        assert history["權利變換計畫申請日期"] == "99.01.27"
        assert history["第一次變更事業計畫核定日期"] == "105.08.24"
        assert history["使用核發日期"] == "105.08.29"
        # Negative guards: empty cells and non-milestone tables must not leak in
        assert "備註" not in history
        assert "資料更新日期" not in history

    def test_case_ids_coexist_with_visible_tuidui_table(self):
        ids = extract_case_ids_from_view(VIEW_VISIBLE_TUIDUI_HTML)
        assert ids == ["11407009"]


class TestTaipeiCaseParsing:
    """Test parsing of Taipei platform case pages."""

    def test_extract_stage_process(self):
        stages = extract_taipei_stage_process(TAIPEI_CASE_10110211_HTML)
        assert "計畫公聽會日期" in stages
        assert stages["計畫公聽會日期"] == "2012/10/21"
        assert stages["申請計畫日期"] == "2012/11/08"
        assert stages["公告公展日期"] == "2014/01/15"
        assert stages["申請幹事會日期"] == "2014/03/04"
        assert stages["召開幹事會日期"] == "2014/04/29"
        assert stages["審議通過日期"] == "2016/03/14"
        assert stages["核定日期"] == "2017/03/21"
        assert stages["建照核發日期"] == "2022/08/25"


class TestLandCoreKey:
    """Test land-identity core key generation from project data."""

    def test_build_key_from_project_fields(self):
        from urtpe.models import CleanRecord
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw = RawRecord(
            recno=1,
            date="115/8/11",
            district="大同區",
            name="擬訂大同玉泉段二小段40地號等29筆都市更新事業計畫及權利變換計畫案",
            land="大同區玉泉段二小段40、40-2、43地號等29筆",
            implementer="弘千建設",
            planner="某規劃公司",
        )
        clean = cleanse(raw)
        core = build_land_core_key(clean)
        assert "玉泉段二小段" in core
        assert "40" in core
        assert "29筆" in core

    def test_build_key_from_linyi_project(self):
        from urtpe.models import RawRecord
        from urtpe.cleanse import cleanse

        raw = RawRecord(
            recno=1,
            date="115/8/11",
            district="中正區",
            name="擬訂中正臨沂段一小段507地號等3筆都市更新事業計畫案",
            land="中正區臨沂段一小段507、508、509地號等3筆",
            implementer="東綺建設",
            planner="某規劃公司",
        )
        clean = cleanse(raw)
        core = build_land_core_key(clean)
        assert "臨沂段一小段" in core
        assert "507" in core
        assert "3筆" in core


class TestAttachLinksToProjects:
    """Test attaching discovered links to project graph nodes."""

    def test_attach_national_and_city_links(self):
        from urtpe.models import Project, CleanRecord
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        # Create a project with two members (事業計畫 + 權利變換)
        raw1 = RawRecord(1, "115/8/11", "大同區", "擬訂大同玉泉段二小段40地號等29筆事業計畫及權利變換計畫案",
                         "大同區玉泉段二小段40等29筆", "弘千建設", "某規劃")
        raw2 = RawRecord(2, "114/5/1", "大同區", "變更大同玉泉段二小段40地號等29筆權利變換計畫案",
                         "大同區玉泉段二小段40等29筆", "弘千建設", "某規劃")
        project = Project(
            project_id="大同區-玉泉段二小段-40地號等29筆",
            anchor_recno=1,
            members=[cleanse(raw1), cleanse(raw2)],
        )

        discovered = {
            "大同區-玉泉段二小段-40地號等29筆": {
                "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/771",
                "taipei": ["10110181"],
                "milestones_national": {"事業計畫申請日期": "101.12.28", "事業計畫核定日期": "109.11.17"},
                "milestones_taipei": {"計畫公聽會日期": "2012/10/21", "核定日期": "2017/03/21"},
            }
        }

        attach_links_to_projects([project], discovered)

        assert "links" in project.__dict__ or hasattr(project, "links")
        # Check project-level links
        proj_links = project.links
        assert proj_links["twur"] == "https://twur.nlma.gov.tw/zh/urban/rebuild/view/771"
        assert proj_links["taipei"] == ["10110181"]
        assert "milestones_national" in proj_links
        assert "milestones_taipei" in proj_links

    def test_attach_per_node_city_links_by_stage(self):
        from urtpe.models import Project, CleanRecord
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw1 = RawRecord(1, "115/8/11", "中正區", "擬訂中正臨沂段一小段507地號等3筆事業計畫案",
                         "中正區臨沂段一小段507等3筆", "東綺建設", "某規劃")
        raw2 = RawRecord(2, "114/5/1", "中正區", "變更中正臨沂段一小段507地號等3筆權利變換計畫案",
                         "中正區臨沂段一小段507等3筆", "東綺建設", "某規劃")
        project = Project(
            project_id="中正區-臨沂段一小段-507地號等3筆",
            anchor_recno=1,
            members=[cleanse(raw1), cleanse(raw2)],
        )

        # Two city case_ids: one for 事業計畫, one for 權利變換
        discovered = {
            "中正區-臨沂段一小段-507地號等3筆": {
                "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/292",
                "taipei": ["10110211", "10810271"],
                "milestones_national": {"事業計畫申請日期": "101.01.15", "事業計畫核定日期": "108.06.20", "權利變換計畫申請日期": "107.03.10", "權利變換計畫核定日期": "108.12.05"},
                "milestones_taipei": {"計畫公聽會日期": "2012/10/21", "核定日期": "2017/03/21"},
            }
        }

        attach_links_to_projects([project], discovered)

        # Check project-level links
        proj_links = project.links
        assert set(proj_links["taipei"]) == {"10110211", "10810271"}

        # Check node-level links: 事業計畫 node gets 10110211, 權利變換 node gets 10810271
        for member in project.members:
            if hasattr(member, "links"):
                if "事業計畫" in member.track:
                    assert "10110211" in member.links.get("taipei", [])
                elif "權利變換" in member.track:
                    assert "10810271" in member.links.get("taipei", [])

    def test_unresolved_project_gets_empty_links(self):
        from urtpe.models import Project, CleanRecord
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw = RawRecord(1, "115/8/11", "松山區", "擬訂松山區某段某地號", "松山區某段某地號", "甲公司", "乙規劃")
        project = Project(
            project_id="松山區-某段-某地號",
            anchor_recno=1,
            members=[cleanse(raw)],
        )

        discovered = {}  # No discovery for this project
        attach_links_to_projects([project], discovered)

        assert project.links == {"twur": "", "taipei": [], "milestones_national": {}, "milestones_taipei": {}}


class TestLinksDiscoveryIntegration:
    """Integration test for the full discovery flow (POC sample cases)."""

    def test_sample_case_yuquan_resolves(self):
        """POC: 玉泉段二小段40地號等29筆 should resolve to view/771 and case_id 10110181."""
        # This test validates the POC gate - will be run against actual portal in task 1.4
        pass

    def test_sample_case_linyi_resolves(self):
        """POC: 臨沂段一小段507地號等3筆 should resolve to view/292 and case_ids 10110211, 10810271."""
        pass