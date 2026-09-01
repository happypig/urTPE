"""Tests for official link discovery: join/attach logic, parsing, and graph emission."""

from __future__ import annotations

import re

import pytest

from urtpe.links import (
    extract_view_id_from_search,
    extract_case_ids_from_view,
    extract_tuidui_history_from_view,
    extract_taipei_stage_process,
    build_land_core_key,
    attach_links_to_projects,
    discover_project_links,
    search_taipei_cases_api,
    select_best_payload,
    implementation_milestones,
    LinksDiscovery,
    STAGE_FIELD_MAP,
)
from urtpe.graph import build_graph_document
from tests.fixtures_links import (
    VIEW_771_HTML,
    VIEW_292_HTML,
    VIEW_NO_CITY_HTML,
    VIEW_VISIBLE_TUIDUI_HTML,
    TAIPEI_CASE_10110211_HTML,
    SEARCH_UNIQUE_HIT_HTML,
    SEARCH_NO_HIT_HTML,
    SEARCH_MULTI_HIT_HTML,
    THIRD_CASE_COMPLETED_JSON,
    THIRD_CASE_EMPTY_JSON,
    FOURTH_CASE_JSON,
    FOURTH_CASE_EMPTY_JSON,
    TEST_CORES,
)


class TestSearchParsing:
    """Test parsing of national portal search results."""

    def test_stage_field_map_jud_ok_labels(self):
        """Regression (facts v2 §6.2): jud_ok_date was mislabeled 概要審議會通過日期;
        the Taipei UI calls it 審議通過日期, and jud_ok_date2 was unmapped.
        (概要審議會通過日期 is now the legitimate label of jud_ok_date0 — round 2.)"""
        labels = dict(STAGE_FIELD_MAP)
        assert labels["jud_ok_date"] == "審議通過日期"
        assert labels["jud_ok_date2"] == "權變審議通過日期"
        assert labels["jud_ok_date"] != "概要審議會通過日期"

    def test_stage_field_map_round2_labels(self):
        """Regression (facts v2 §6.2 round 2, DOM-verified): comm_hold family was
        mislabeled as 審議通過 variants; the UI calls them 召開審議會 variants.
        outline_ok_date / jud_ok_date0 / comm_hold_date0 were unmapped."""
        labels = dict(STAGE_FIELD_MAP)
        assert labels["comm_hold_date"] == "召開審議會日期"
        assert labels["comm_hold_date2"] == "權變召開審議會日期"
        assert labels["outline_ok_date"] == "概要核准日期"
        assert labels["jud_ok_date0"] == "概要審議會通過日期"
        assert labels["comm_hold_date0"] == "概要召開審議會日期"
        assert "審議會審議通過日期" not in labels.values()
        assert "權變審議會審議通過日期" not in labels.values()

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


def _taipei_entry(case_id: str, case_name: str, schedule: str = "已核准") -> dict:
    """One Get_updcase_list.ashx row shaped like the live API."""
    return {
        "details": f"https://gis.uro.taipei/r_progress_detail.aspx?case_id={case_id}",
        "case_name": case_name,
        "schedule": schedule,
    }


class TestTaipeiSearchParcelGuard:
    """§6.7/§6.8 guard: search keeps only cases whose own case_name carries the
    searched parcel (notation-drift tolerant). Cross-family pollution must not
    enter city_case_ids."""

    def _search(self, monkeypatch, entries, section: str, parcel: str):
        import json as jsonlib
        import urtpe.links as links

        monkeypatch.setattr(
            links, "_post_taipei_api",
            lambda url, params, max_retries=3: jsonlib.dumps(entries),
        )
        dropped_out: dict[str, str] = {}
        kept = search_taipei_cases_api(section, parcel, dropped_out=dropped_out)
        return [e["case_id"] for e in kept], dropped_out

    def test_own_family_cases_survive_the_guard(self, monkeypatch):
        """Spec scenario: 寶清段一小段(四小段) 57-13 — all four own approvals stay."""
        names = [
            ("10212211", "擬訂臺北市中山區寶清段四小段57-13地號等1筆土地都市更新事業計畫案"),
            ("10212212", "變更臺北市中山區寶清段四小段57-13地號等1筆土地都市更新事業計畫案"),
            ("10212214", "變更(第二次)臺北市中山區寶清段四小段57-13地號等1筆土地都市更新事業計畫案"),
            ("11412018", "變更臺北市中山區寶清段四小段57-13等1筆土地都市更新權利變換計畫案"),
        ]
        kept, dropped = self._search(
            monkeypatch, [_taipei_entry(cid, n) for cid, n in names],
            "寶清段四小段", "57-13",
        )
        assert kept == [cid for cid, _ in names]
        assert dropped == {}

    def test_foreign_same_section_case_rejected(self, monkeypatch):
        """Spec scenario: 正義段四小段 115 — 11102211 (133地號1筆) is dropped."""
        entries = [
            _taipei_entry("11102210", "擬訂臺北市中山區正義段四小段115地號等4筆土地都市更新事業計畫及權利變換計畫案"),
            _taipei_entry("11102211", "擬訂臺北市中山區正義段四小段133地號1筆土地都市更新事業計畫案"),
        ]
        kept, dropped = self._search(monkeypatch, entries, "正義段四小段", "115")
        assert kept == ["11102210"]
        assert set(dropped) == {"11102211"}
        assert "133地號" in dropped["11102211"]

    def test_sibling_r13_gaiyao_cases_rejected(self, monkeypatch):
        """Spec scenario (§6.7): 南港段一小段 520-2 — the four sibling 概要 cases on
        other land are dropped; 09407070/71/73 (520-2等18筆) remain."""
        entries = [
            _taipei_entry("09407070", "擬訂臺北市南港區南港段一小段520-2等18筆土地(R13)都市更新事業概要案"),
            _taipei_entry("09407071", "擬訂臺北市南港區南港段一小段520-2等18筆土地(R13)都市更新事業計畫及權利變換計畫案"),
            _taipei_entry("09407073", "變更臺北市南港區南港段一小段520-2等18筆土地(R13)都市更新事業計畫及權利變換計畫案"),
            _taipei_entry("09407110", "擬訂臺北市南港區南港段一小段522等45筆土地(R13)都市更新事業概要案"),
            _taipei_entry("09407113", "擬訂臺北市南港區南港段一小段467等41筆土地(R13)都市更新事業概要案"),
            _taipei_entry("09509071", "擬訂臺北市南港區南港段一小段403-2等28筆土地都市更新事業概要案"),
            _taipei_entry("09607130", "擬訂臺北市南港區南港段一小段561等5筆土地都市更新事業概要案"),
        ]
        kept, dropped = self._search(monkeypatch, entries, "南港段一小段", "520-2")
        assert kept == ["09407070", "09407071", "09407073"]
        assert set(dropped) == {"09407110", "09407113", "09509071", "09607130"}

    def test_notation_drift_tolerated(self, monkeypatch):
        """Spec scenario: searched 263-19 keeps 263之19 / full-width spellings;
        look-alike parcels (209-19, 1263-19) stay rejected."""
        entries = [
            _taipei_entry("10204032", "擬訂臺北市中正區河堤段四小段263之19地號等25筆土地都市更新事業計畫案"),
            _taipei_entry("10707031", "變更臺北市中正區河堤段四小段２６３之１９地號等25筆土地都市更新權利變換計畫案"),
            _taipei_entry("10601001", "擬訂臺北市中正區河堤段四小段209-19地號等1筆土地都市更新事業計畫案"),
            _taipei_entry("10601002", "擬訂臺北市中正區河堤段四小段1263-19地號等1筆土地都市更新事業計畫案"),
            _taipei_entry("10601003", "擬訂臺北市中正區河堤段四小段263-191地號等1筆土地都市更新事業計畫案"),
        ]
        kept, dropped = self._search(monkeypatch, entries, "河堤段四小段", "263-19")
        assert kept == ["10204032", "10707031"]
        assert set(dropped) == {"10601001", "10601002", "10601003"}

    def test_mono_legacy_name_form_kept(self, monkeypatch):
        """The mono-part clause: an older approval naming the pre-subdivision
        form (<mono>地號…) survives a sub-parcel search (57-13 → 57地號…)."""
        entries = [
            _taipei_entry("10212211", "擬訂臺北市中山區寶清段四小段57-13地號等1筆土地都市更新事業計畫案"),
            _taipei_entry("09901001", "擬訂臺北市中山區寶清段四小段57地號等29筆土地都市更新事業計畫案"),
        ]
        kept, _ = self._search(monkeypatch, entries, "寶清段四小段", "57-13")
        # exact-parcel hit kept; legacy mono form of the same stem kept too
        assert kept == ["10212211", "09901001"]

    def test_missing_or_foreign_stem_names_dropped(self, monkeypatch):
        entries = [
            _taipei_entry("11100001", ""),
            _taipei_entry("11100002", "擬訂臺北市中山區寶清段四小段99地號等2筆土地都市更新事業計畫案"),
        ]
        kept, dropped = self._search(monkeypatch, entries, "寶清段四小段", "57-13")
        assert kept == []
        assert set(dropped) == {"11100001", "11100002"}


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

    def test_merge_records_winning_case_per_label(self):
        from urtpe.links import merge_stage_milestones

        all_ms, source = {}, {}
        merge_stage_milestones(all_ms, source, "10011041", {"建照核發日期": "2017/02/07"})
        merge_stage_milestones(all_ms, source, "10011042", {"核定日期": "2019/05/14"})
        merge_stage_milestones(all_ms, source, "10011042", {"建照核發日期": "2019/06/19"})
        assert all_ms["建照核發日期"] == "2019/06/19"
        assert source["建照核發日期"] == "10011042", "overwritten label must name the winner"
        assert source["核定日期"] == "10011042"

    def test_attach_passes_source_map_and_impl_dates_name_case(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw1 = RawRecord(1042, "115/8/11", "中正區", "擬訂中正河堤段四小段263-19地號等25筆事業計畫案",
                         "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        raw2 = RawRecord(772, "115/8/11", "中正區", "變更中正河堤段四小段263-19地號等25筆權利變換計畫案",
                         "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        project = Project(
            project_id="中正區-河堤段四小段-263-19地號等25筆",
            anchor_recno=1042,
            members=[cleanse(raw1), cleanse(raw2)],
        )
        discovered = {project.project_id: {
            "twur": "",
            "taipei": ["10204032", "10707031"],
            "milestones_national": {},
            "milestones_taipei": {"建照核發日期": "2017/07/14"},
            "milestones_source": {"建照核發日期": "10204032"},
            "case_milestones": {},
            "implementation": {
                "10204032": {"Exe_Way": "協議合建", "Eng_Start_Date": "2017/10/31"},
            },
            "rewards": {},
        }}
        attach_links_to_projects([project], discovered)

        src = project.links["milestones_source"]
        assert src["建照核發日期"] == "10204032", "stage label keeps its merged winner"
        assert src["開工日期"] == "10204032", "implementation-derived dates name the payload case"

    def test_attach_per_node_implementation_snapshot(self):
        """Per-record implementation snapshots (additive): a record whose
        anchored case carries a third.ashx payload rides on that record."""
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw1 = RawRecord(1042, "115/8/11", "中正區", "擬訂中正河堤段四小段263-19地號等25筆事業計畫案",
                         "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        raw2 = RawRecord(772, "115/8/11", "中正區", "變更中正河堤段四小段263-19地號等25筆權利變換計畫案",
                         "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        project = Project(
            project_id="中正區-河堤段四小段-263-19地號等25筆",
            anchor_recno=1042,
            members=[cleanse(raw1), cleanse(raw2)],
        )
        discovered = {project.project_id: {
            "twur": "",
            "taipei": ["10204032", "10707031"],
            "milestones_national": {},
            "milestones_taipei": {},
            "case_milestones": {},
            "implementation": {
                "10204032": {"Exe_Way": "協議合建", "Base_Area": "1233.0",
                             "Eng_Start_Date": "2017/10/31"},
                "10707031": {},
            },
            "rewards": {},
        }}
        attach_links_to_projects([project], discovered)

        carriers = [m for m in project.members if getattr(m, "implementation", None)]
        assert len(carriers) == 1, "exactly one record carries the payload case"
        assert carriers[0].implementation["case_id"] == "10204032"
        assert carriers[0].implementation["Exe_Way"] == "協議合建"
        for m in project.members:
            if m not in carriers:
                assert not hasattr(m, "implementation") or not m.implementation

    def test_attach_per_node_links_by_approval_date(self):
        """Regression (facts §16): positional linking attached the older case to
        the newer node. Nodes must anchor by 核定日期 instead."""
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw_old = RawRecord(1042, "115/8/11", "中正區", "擬訂中正河堤段四小段263-19地號等25筆都市更新計畫案",
                            "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        raw_new = RawRecord(772, "115/8/11", "中正區", "變更中正河堤段四小段263-19地號等25筆都市更新事業計畫案",
                            "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        project = Project(
            project_id="中正區-河堤段四小段-263-19地號等25筆",
            anchor_recno=772,
            members=[cleanse(raw_old), cleanse(raw_new)],
        )
        # Node dates come from the PDF record; override to the known approval dates
        for member in project.members:
            if member.recno == 1042:
                member.date = "2016-07-05"
            elif member.recno == 772:
                member.date = "2019-08-01"

        disc_obj = type("Disc", (object,), {})()
        disc_obj.project_id = "中正區-河堤段四小段-263-19地號等25筆"
        disc_obj.twur_url = "https://twur.nlma.gov.tw/zh/urban/rebuild/view/262"
        # NOTE: list order is (newest-first) — positional logic would mislink these
        disc_obj.city_case_ids = ["10204032", "10707031"]
        disc_obj.national_milestones = {}
        disc_obj.taipei_milestones = {}
        disc_obj.case_milestones = {
            "10204032": {"核定日期": "2016/07/05", "建照核發日期": "2017/07/14"},
            "10707031": {"核定日期": "2019/08/01"},
        }

        attach_links_to_projects([project], {"中正區-河堤段四小段-263-19地號等25筆": disc_obj})

        by_recno = {m.recno: m for m in project.members}
        assert by_recno[1042].links["taipei"] == ["10204032"]  # 核定 2016-07-05
        assert by_recno[772].links["taipei"] == ["10707031"]   # 核定 2019-08-01

    def test_date_match_falls_back_to_positional_without_case_milestones(self):
        """Old caches carry no case_milestones: legacy positional behavior kept."""
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw1 = RawRecord(1, "115/8/11", "中正區", "擬訂中正臨沂段一小段507地號等3筆事業計畫案",
                         "中正區臨沂段一小段507等3筆", "東綺建設", "某規劃")
        project = Project(
            project_id="中正區-臨沂段一小段-507地號等3筆",
            anchor_recno=1,
            members=[cleanse(raw1)],
        )

        disc_obj = type("Disc", (object,), {})()
        disc_obj.project_id = "中正區-臨沂段一小段-507地號等3筆"
        disc_obj.twur_url = ""
        disc_obj.city_case_ids = ["10110211"]
        disc_obj.national_milestones = {}
        disc_obj.taipei_milestones = {}
        disc_obj.case_milestones = {}  # old cache

        attach_links_to_projects([project], {"中正區-臨沂段一小段-507地號等3筆": disc_obj})

        assert project.members[0].links["taipei"] == ["10110211"]


class TestFragmentFamilyDetection:
    """§6.8 fragment families: a family whose discovered cases ALL surface in
    exactly one other family's platform search (kept or guard-rejected) is a
    merge candidate — review-flagged 臨界對-style on its anchor record.
    Mixed or nowhere anchoring stays unflagged; no family mutation."""

    def _project(self, project_id, recno, name, land):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        district = project_id.split("-")[0]
        raw = RawRecord(recno, "115/8/11", district, name, land, "某建設", "某規劃")
        return Project(project_id=project_id, anchor_recno=recno, members=[cleanse(raw)])

    def _disc(self, kept, rejected=None):
        return {
            "twur": "",
            "taipei": list(kept),
            "milestones_national": {},
            "milestones_taipei": {},
            "search_rejected": dict(rejected or {}),
        }

    FF_PID = "南港區-南港段一小段-101地號等41筆"
    MAIN_PID = "南港區-南港段一小段-19-1地號等34筆"
    FF_NAME = "擬訂臺北市南港區南港段一小段101地號等41筆土地更新事業計畫及權利變換計畫案"
    MAIN_NAME = "擬訂臺北市南港區南港段一小段19-1地號等34筆土地都市更新事業計畫及權利變換計畫案"

    def test_single_case_fragment_inside_main_family_is_flagged(self):
        """Spec scenario: 10809251 (101地號等41筆) surfaced (guard-rejected) only
        inside 19-1地號等34筆's search → fragment flagged naming that family."""
        ff = self._project(self.FF_PID, 411, self.FF_NAME, "臺北市南港區南港段一小段101、105、106地號等41筆")
        main = self._project(self.MAIN_PID, 767, self.MAIN_NAME, "臺北市南港區南港段一小段19-1、20-1、21地號等34筆")
        discovered = {
            self.FF_PID: self._disc(["10809251"]),
            self.MAIN_PID: self._disc(
                ["10700001"],
                {"10809251": self.FF_NAME},
            ),
        }

        attach_links_to_projects([ff, main], discovered)

        ff_anchor = next(m for m in ff.members if m.recno == 411)
        flags = [f for f in ff_anchor.review_flags if f.startswith("片段家族合併候選")]
        assert len(flags) == 1, ff_anchor.review_flags
        assert self.MAIN_PID in flags[0], flags[0]
        # the flag carries the overlapping case count (spec: family + count)
        assert "1 筆案例" in flags[0], flags[0]
        main_anchor = next(m for m in main.members if m.recno == 767)
        assert not [f for f in main_anchor.review_flags if f.startswith("片段家族合併候選")]
        # no family mutation: membership unchanged, case ids stay put
        assert len(ff.members) == 1 and len(main.members) == 1
        assert main.links["taipei"] == ["10700001"]

    def test_shared_kept_cases_flag_pair_a_fragments(self):
        """懷生段249 shape: both spellings of the unit keep the same cases —
        the mis-districted fragment is a merge candidate of the 大安區 family."""
        ff = self._project("中正區-懷生段三小段-249地號等26筆", 650,
                           "擬訂臺北市大安區懷生段三小段249地號等26筆土地都市更新事業計畫案",
                           "臺北市大安區懷生段三小段249、250地號等26筆")
        main = self._project("大安區-懷生段三小段-249地號等26筆", 489,
                             "擬訂臺北市大安區懷生段三小段249地號等26筆土地都市更新權利變換計畫案",
                             "臺北市大安區懷生段三小段249、250地號等26筆")
        discovered = {
            "中正區-懷生段三小段-249地號等26筆": self._disc(["11100001", "11500002"]),
            "大安區-懷生段三小段-249地號等26筆": self._disc(["11100001", "11500002"]),
        }

        attach_links_to_projects([ff, main], discovered)

        # Pair-A shapes are mutual merge candidates: each side names the other.
        ff_anchor = next(m for m in ff.members if m.recno == 650)
        ff_flag = next(f for f in ff_anchor.review_flags if f.startswith("片段家族合併候選"))
        assert "大安區-懷生段三小段-249地號等26筆" in ff_flag
        main_anchor = next(m for m in main.members if m.recno == 489)
        main_flag = next(f for f in main_anchor.review_flags if f.startswith("片段家族合併候選"))
        assert "中正區-懷生段三小段-249地號等26筆" in main_flag

    def test_mixed_anchoring_is_not_flagged(self):
        """Cases surfacing across two different families → ambiguous → unflagged."""
        ff = self._project("甲區-某段-10地號等2筆", 1,
                           "擬訂臺北市甲區某段10地號等2筆土地都市更新事業計畫案", "臺北市甲區某段10地號等2筆")
        g1 = self._project("甲區-某段-20地號等3筆", 2,
                           "擬訂臺北市甲區某段20地號等3筆土地都市更新事業計畫案", "臺北市甲區某段20地號等3筆")
        g2 = self._project("甲區-某段-30地號等4筆", 3,
                           "擬訂臺北市甲區某段30地號等4筆土地都市更新事業計畫案", "臺北市甲區某段30地號等4筆")
        discovered = {
            "甲區-某段-10地號等2筆": self._disc(["c1", "c2"]),
            "甲區-某段-20地號等3筆": self._disc(["d1"], {"c1": "…10地號…"}),
            "甲區-某段-30地號等4筆": self._disc(["d2"], {"c2": "…10地號…"}),
        }

        attach_links_to_projects([ff, g1, g2], discovered)

        anchor = ff.members[0]
        assert not [f for f in anchor.review_flags if f.startswith("片段家族合併候選")]

    def test_nowhere_anchoring_is_not_flagged(self):
        """A normal family whose cases surface nowhere else stays unflagged."""
        solo = self._project("乙區-某段-50地號等5筆", 9,
                             "擬訂臺北市乙區某段50地號等5筆土地都市更新事業計畫案", "臺北市乙區某段50地號等5筆")
        other = self._project("乙區-某段-60地號等6筆", 10,
                              "擬訂臺北市乙區某段60地號等6筆土地都市更新事業計畫案", "臺北市乙區某段60地號等6筆")
        discovered = {
            "乙區-某段-50地號等5筆": self._disc(["s1"]),
            "乙區-某段-60地號等6筆": self._disc(["t1"]),
        }

        attach_links_to_projects([solo, other], discovered)

        assert not [f for f in solo.members[0].review_flags if f.startswith("片段家族合併候選")]
        assert not [f for f in other.members[0].review_flags if f.startswith("片段家族合併候選")]

    def test_partly_nowhere_anchoring_is_not_flagged(self):
        """One unanimous case + one nowhere case → spec says unflagged."""
        ff = self._project("丙區-某段-70地號等7筆", 11,
                           "擬訂臺北市丙區某段70地號等7筆土地都市更新事業計畫案", "臺北市丙區某段70地號等7筆")
        g = self._project("丙區-某段-80地號等8筆", 12,
                          "擬訂臺北市丙區某段80地號等8筆土地都市更新事業計畫案", "臺北市丙區某段80地號等8筆")
        discovered = {
            "丙區-某段-70地號等7筆": self._disc(["k1", "k2"]),
            "丙區-某段-80地號等8筆": self._disc(["m1"], {"k1": "…70地號…"}),
        }

        attach_links_to_projects([ff, g], discovered)

        assert not [f for f in ff.members[0].review_flags if f.startswith("片段家族合併候選")]

    def test_flag_is_idempotent_across_attach_runs(self):
        ff = self._project(self.FF_PID, 411, self.FF_NAME, "臺北市南港區南港段一小段101、105、106地號等41筆")
        main = self._project(self.MAIN_PID, 767, self.MAIN_NAME, "臺北市南港區南港段一小段19-1、20-1、21地號等34筆")
        discovered = {
            self.FF_PID: self._disc(["10809251"]),
            self.MAIN_PID: self._disc(["10700001"], {"10809251": self.FF_NAME}),
        }
        projects = [ff, main]

        attach_links_to_projects(projects, dict(discovered))
        attach_links_to_projects(projects, dict(discovered))

        ff_anchor = next(m for m in ff.members if m.recno == 411)
        flags = [f for f in ff_anchor.review_flags if f.startswith("片段家族合併候選")]
        assert len(flags) == 1


class TestLinksDiscoveryIntegration:
    """Integration test for the full discovery flow (POC sample cases)."""

    def test_sample_case_yuquan_resolves(self):
        """POC: 玉泉段二小段40地號等29筆 should resolve to view/771 and case_id 10110181."""
        # This test validates the POC gate - will be run against actual portal in task 1.4
        pass

    def test_sample_case_linyi_resolves(self):
        """POC: 臨沂段一小段507地號等3筆 should resolve to view/292 and case_ids 10110211, 10810271."""
        pass


class TestSelectBestPayload:
    """Pure selection logic (design D5): whole-payload pick, provenance, conflict flags."""

    def test_empty_payloads_yield_no_selection(self):
        cid, payload, flags = select_best_payload({"a": {}, "b": {}})
        assert cid == ""
        assert payload == {}
        assert flags == []

    def test_single_candidate_selected_with_provenance(self):
        payloads = {"09811141": {"Eng_Start_Date": "2013/09/10", "Exe_Way": "權利變換"}}
        cid, payload, flags = select_best_payload(payloads)
        assert cid == "09811141"
        assert payload == payloads["09811141"]
        assert flags == []

    def test_best_populated_payload_wins_whole(self):
        payloads = {
            "case_a": {"Exe_Way": "權利變換"},
            "case_b": {"Exe_Way": "權利變換", "Base_Area": "1,604.00", "Old_Doors": "50"},
        }
        cid, payload, _ = select_best_payload(payloads)
        assert cid == "case_b"
        assert payload == payloads["case_b"]  # whole payload, never field-merged

    def test_conflicting_values_flagged_for_review(self):
        payloads = {
            "case_a": {"Ulic_Date": "2016/08/29"},
            "case_b": {"Ulic_Date": "2017/01/01"},
        }
        cid, _, flags = select_best_payload(payloads)
        assert cid in ("case_a", "case_b")
        assert flags and "Ulic_Date" in flags[0]

    def test_implementation_milestones_extracts_only_non_empty_dates(self):
        payload = {"Eng_Start_Date": "2013/09/10", "Ulic_Date": "2016/08/29", "Report_Date": ""}
        assert implementation_milestones(payload) == {
            "開工日期": "2013/09/10",
            "使照核發日期": "2016/08/29",
        }


class TestImplementationEmission:
    """Acceptance: implementation/rewards reach the emitted graph (user-visible)."""

    def _make_project(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw = RawRecord(991, "115/8/11", "中山區", "擬訂中山中山段一小段254地號等13筆事業計畫案",
                        "中山區中山段一小段254地號等13筆", "聖得福建設", "某規劃")
        return Project(
            project_id="中山區-中山段一小段-254地號等13筆",
            anchor_recno=991,
            members=[cleanse(raw)],
        )

    def _disc_obj(self, **overrides):
        disc = type("Disc", (object,), {})()
        disc.project_id = "中山區-中山段一小段-254地號等13筆"
        disc.twur_url = ""
        disc.city_case_ids = ["09811141"]
        disc.national_milestones = {}
        disc.taipei_milestones = {}
        disc.case_milestones = {}
        disc.implementation = {"09811141": {"Eng_Start_Date": "2013/09/10", "Ulic_Date": "2016/08/29", "Exe_Way": "權利變換"}}
        disc.rewards = {"09811141": {"F0": "8,982.01", "F": "10,829.58"}}
        for k, v in overrides.items():
            setattr(disc, k, v)
        return disc

    def test_project_with_completed_case_emits_milestones_and_objects(self):
        project = self._make_project()
        attach_links_to_projects([project], {"中山區-中山段一小段-254地號等13筆": self._disc_obj()})
        assert project.links["milestones_taipei"]["開工日期"] == "2013/09/10"
        assert project.links["milestones_taipei"]["使照核發日期"] == "2016/08/29"
        assert project.implementation["case_id"] == "09811141"
        assert project.implementation["Exe_Way"] == "權利變換"
        assert project.rewards["F0"] == "8,982.01"

    def test_emitted_document_carries_objects_and_schema_version_2(self):
        project = self._make_project()
        attach_links_to_projects([project], {"中山區-中山段一小段-254地號等13筆": self._disc_obj()})
        doc = build_graph_document([project], {"generated_at": "t", "source": "s", "published_date": ""})
        assert doc["schema_version"] == 2
        emitted = doc["projects"][0]
        assert emitted["implementation"]["case_id"] == "09811141"
        assert emitted["rewards"]["F0"] == "8,982.01"

    def test_project_without_payloads_emits_none_and_stays_v1_consumer_valid(self):
        project = self._make_project()
        disc = self._disc_obj(implementation={}, rewards={})
        attach_links_to_projects([project], {"中山區-中山段一小段-254地號等13筆": disc})
        assert "開工日期" not in project.links["milestones_taipei"]
        doc = build_graph_document([project], {"generated_at": "t", "source": "s", "published_date": ""})
        emitted = doc["projects"][0]
        assert "implementation" not in emitted
        assert "rewards" not in emitted
        # v1 consumer contract: existing fields unchanged in meaning
        assert set(emitted["links"].keys()) == {"twur", "taipei", "milestones_national", "milestones_taipei"}

    def test_conflicting_payloads_flagged_in_emitted_object(self):
        project = self._make_project()
        disc = self._disc_obj(implementation={
            "09811141": {"Ulic_Date": "2016/08/29"},
            "09811142": {"Ulic_Date": "2017/01/01"},
        })
        attach_links_to_projects([project], {"中山區-中山段一小段-254地號等13筆": disc})
        assert project.implementation.get("review_flags"), "conflicting payloads must surface review flags"

    def test_emitted_nodes_carry_per_record_implementation_snapshots(self):
        project = self._make_project()
        attach_links_to_projects([project], {"中山區-中山段一小段-254地號等13筆": self._disc_obj()})
        doc = build_graph_document([project], {"generated_at": "t", "source": "s", "published_date": ""})
        nodes = {n["recno"]: n for n in doc["projects"][0]["nodes"]}
        assert nodes[991]["implementation"]["case_id"] == "09811141"
        assert nodes[991]["implementation"]["Exe_Way"] == "權利變換"


class TestViewerCards:
    """Acceptance: viewer renders 執行階段/獎勵資料 cards when objects exist."""

    def _app_js(self):
        from pathlib import Path
        return Path(__file__).resolve().parents[1].joinpath("viewer", "app.js").read_text(encoding="utf-8")

    def test_app_js_renders_both_cards_with_labels(self):
        js = self._app_js()
        assert "執行階段" in js and "獎勵資料" in js
        assert "implementation" in js and "rewards" in js
        # portal label map present (DOM-captured) — non-date fields only; dates
        # flow through milestones_taipei labels (design D3)
        assert "實施方式" in js and "基地面積" in js

    def test_app_js_guards_on_object_presence(self):
        js = self._app_js()
        # cards must be conditional on the emitted objects, not rendered unconditionally
        assert re.search(r"implementation\s*(?:&&|\?)", js) or "hasImpl" in js
        assert re.search(r"rewards\s*(?:&&|\?)", js) or "hasRew" in js


class TestDiscoveryFetchesThirdFourth:
    """End-to-end discovery (fixture-served): second+third+fourth per case → cache → attach."""

    def _project(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw = RawRecord(991, "115/8/11", "中山區", "擬訂中山中山段一小段254地號等13筆事業計畫案",
                        "中山區中山段一小段254地號等13筆", "聖得福建設", "某規劃")
        return Project(
            project_id="中山區-中山段一小段-254地號等13筆",
            anchor_recno=991,
            members=[cleanse(raw)],
        )

    def test_discovery_round_trip_with_third_fourth(self, tmp_path, monkeypatch):
        import json as jsonlib
        import urtpe.links as links

        calls = []

        def fake_post(url, params, max_retries=3):
            calls.append((url, params["case_id"]))
            if "second" in url:
                return jsonlib.dumps([{"Uro_Chk_Date": "2012/08/27"}])
            if "third" in url:
                return THIRD_CASE_COMPLETED_JSON
            if "fourth" in url:
                return FOURTH_CASE_JSON
            return "[]"

        monkeypatch.setattr(links, "_post_taipei_api", fake_post)
        monkeypatch.setattr(links, "search_taipei_cases_api", lambda section, parcel, dropped_out=None: [
            {"case_id": "09811141", "case_name": "x", "schedule": ""}])

        project = self._project()
        result = discover_project_links(project, tmp_path, fresh=True, delay=0)

        third_calls = [c for c in calls if "third" in c[0]]
        fourth_calls = [c for c in calls if "fourth" in c[0]]
        assert third_calls and fourth_calls
        assert result.implementation["09811141"]["Eng_Start_Date"] == "2013/09/10"
        assert result.rewards["09811141"]["F0"] == "8,982.01"

        # cache round-trip
        cached = links.load_project_cache(tmp_path, project.project_id)
        assert cached.implementation["09811141"]["Ulic_Date"] == "2016/08/29"
        assert cached.rewards["09811141"]["F"] == "10,829.58"

        # attach → milestones + objects
        attach_links_to_projects([project], {project.project_id: cached})
        assert project.links["milestones_taipei"]["開工日期"] == "2013/09/10"
        assert project.implementation["case_id"] == "09811141"

    def test_third_fetch_failure_recorded_without_aborting(self, tmp_path, monkeypatch):
        import json as jsonlib
        import urtpe.links as links

        def fake_post(url, params, max_retries=3):
            if "third" in url:
                raise ConnectionResetError("boom")
            if "second" in url:
                return jsonlib.dumps([{"Uro_Chk_Date": "2012/08/27"}])
            if "fourth" in url:
                return FOURTH_CASE_JSON
            return "[]"

        monkeypatch.setattr(links, "_post_taipei_api", fake_post)
        monkeypatch.setattr(links, "search_taipei_cases_api", lambda section, parcel, dropped_out=None: [
            {"case_id": "09811141", "case_name": "x", "schedule": ""}])

        project = self._project()
        result = discover_project_links(project, tmp_path, fresh=True, delay=0)

        assert result.implementation.get("09811141", {}) in ({}, None) or "09811141" not in result.implementation
        assert result.rewards["09811141"]["F0"] == "8,982.01"
        assert "09811141" in result.error

class TestOrphanGhostAnchoring:
    """§6.8 orphan ghost nodes: city_case_ids that no node anchors become
    ghost nodes when a landcore-similar case_name exists (search_rejected)
    OR when stage attribution (milestones_source) proves the case belongs
    to this unit. Anchored siblings are never ghosted, on both the PDF path
    (fresh merge) and the --from-js path."""

    PID = "文山區-木柵段三小段-623地號等39筆"

    def _project(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw1 = RawRecord(5, "115/8/11", "文山區",
                         "變更文山區木柵段三小段623地號等39筆都市更新權利變換計畫案",
                         "臺北市文山區木柵段三小段623地號等39筆", "某建設", "某規劃")
        raw2 = RawRecord(263, "99/12/20", "文山區",
                         "擬訂文山區木柵段三小段623地號等39筆土地都市更新事業計畫案",
                         "臺北市文山區木柵段三小段623地號等39筆", "某建設", "某規劃")
        return Project(project_id=self.PID, anchor_recno=5,
                       members=[cleanse(raw1), cleanse(raw2)])

    def _disc(self, **over):
        base = {
            "twur": "",
            "taipei": ["09907222", "11501041", "09907221"],
            "milestones_national": {},
            "milestones_taipei": {
                "計畫公聽會日期": "2010/05/01",
                "核定日期": "2010/12/20",
                "事業計畫申請日期": "2011/02/01",
                "建照核發日期": "2011/06/15",
                "開工日期": "2011/08/01",
                "使照核發日期": "2014/03/10",
            },
            "case_milestones": {},
            "milestones_source": {
                "計畫公聽會日期": "09907223",
                "核定日期": "09907223",
                "事業計畫申請日期": "09907221",
                "建照核發日期": "09907221",
                "開工日期": "09907221",
                "使照核發日期": "09907221",
            },
            "implementation": {},
            "rewards": {},
            "search_rejected": {},
        }
        base.update(over)
        return {self.PID: base}

    def test_attribution_only_orphan_becomes_ghost(self):
        project = self._project()
        attach_links_to_projects([project], self._disc())

        ghosts = project.links.get("orphan_nodes")
        assert ghosts is not None and len(ghosts) == 1
        g = ghosts[0]
        assert g["case_id"] == "09907221"
        assert g["orphan"] is True
        assert g["provenance"] == "orphan-case-anchoring"
        assert set(g["milestones_taipei"]) == {
            "事業計畫申請日期", "建照核發日期", "開工日期", "使照核發日期",
        }

    def test_anchored_siblings_are_not_ghosted(self):
        project = self._project()
        attach_links_to_projects([project], self._disc())

        ghost_ids = {g["case_id"] for g in project.links.get("orphan_nodes", [])}
        assert "09907222" not in ghost_ids
        assert "11501041" not in ghost_ids

    def test_dissimilar_named_orphan_is_excluded(self):
        project = self._project()
        disc = self._disc(
            taipei=["09907222", "11501041", "09907221"],
            milestones_source={},
            search_rejected={
                "09907221": "擬訂臺北市中山區中山段二小段125地號等1筆土地都市更新事業計畫案",
            },
        )
        attach_links_to_projects([project], disc)
        assert "orphan_nodes" not in project.links

    def test_view_verified_orphan_bypasses_similarity_gate(self):
        """Cases listed on the project's own national view page 相關連結 are
        portal-verified — they become ghosts even when the case name carries
        no parcel (landcore similarity 0.0), e.g. 崇仁新村 (§6.11/§6.12)."""
        project = self._project()
        disc = self._disc(
            taipei=["09907222", "11501041", "09907221"],
            milestones_source={},
            candidate_names={
                "09907221": "變更臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案",
            },
            view_verified_case_ids=["09907221"],
        )
        attach_links_to_projects([project], disc)
        ghosts = project.links.get("orphan_nodes", [])
        assert {g["case_id"] for g in ghosts} == {"09907221"}
        assert ghosts[0]["case_name"].startswith("變更臺北市萬華區崇仁新村")

    def test_similar_named_orphan_still_becomes_ghost(self):
        project = self._project()
        name = "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"
        disc = self._disc(
            taipei=["09907222", "11501041", "09907221"],
            milestones_source={"建照核發日期": "09907221"},
            search_rejected={"09907221": name},
        )
        attach_links_to_projects([project], disc)
        ghosts = project.links.get("orphan_nodes", [])
        assert [g["case_id"] for g in ghosts] == ["09907221"]
        assert ghosts[0]["case_name"] == name

    def test_twin_bridge_anchors_shadowed_twin_without_attribution(self):
        project = self._project()
        shared = [
            ("計畫公聽會日期", "2010/05/01"),
            ("核定日期", "2019/01/31"),
            ("建照核發日期", "2022/02/17"),
            ("開工日期", "2022/08/26"),
        ]
        disc = self._disc(
            taipei=["09907222", "11501041", "09907223"],
            milestones_source={},
            case_milestones={
                "09907222": dict(shared),
                "09907223": dict(shared + [("申請計畫日期", "2010/07/22")]),
            },
        )
        attach_links_to_projects([project], disc)
        ghost_ids = {g["case_id"] for g in project.links.get("orphan_nodes", [])}
        assert "09907223" in ghost_ids

    def test_twin_bridge_excludes_disjoint_history_orphan(self):
        project = self._project()
        disc = self._disc(
            taipei=["09907222", "10809251"],
            milestones_source={},
            case_milestones={
                "09907222": {"計畫公聽會日期": "2010/05/01", "核定日期": "2019/01/31",
                             "建照核發日期": "2022/02/17"},
                "10809251": {"計畫公聽會日期": "2008/03/03", "核定日期": "2008/11/12",
                             "建照核發日期": "2009/06/01"},
            },
        )
        attach_links_to_projects([project], disc)
        ghost_ids = {g["case_id"] for g in project.links.get("orphan_nodes", [])}
        assert "10809251" not in ghost_ids


class TestLoaderRestoresNodeLinks:
    """/--from-js round-trip must restore per-record links so that attach's
    anchored-set reflects real node anchoring (graph.py emits them)."""

    def test_load_projects_restores_member_links(self, tmp_path):
        import json

        from urtpe.cli import _load_projects_from_js

        doc = {
            "schema_version": 2,
            "published_date": "",
            "projects": [
                {
                    "project_id": "大同區-玉泉段一小段-11地號等73筆",
                    "anchor_recno": 7,
                    "nodes": [
                        {
                            "recno": 7,
                            "date": "2016-05-20",
                            "track": "事業計畫、權利變換",
                            "case_name": "擬訂大同區玉泉段一小段11地號等73筆案",
                            "links": {"taipei": ["10110181"], "milestones_national": {},
                                      "milestones_taipei": {}},
                        }
                    ],
                }
            ],
        }
        js = tmp_path / "projects.data.js"
        js.write_text("window.PROJECTS=" + json.dumps(doc, ensure_ascii=False) + ";",
                      encoding="utf-8")

        projects, _meta = _load_projects_from_js(str(js))
        member = projects[0].members[0]
        assert member.links["taipei"] == ["10110181"]


class TestCandidateNameHarvest:
    """§5.1: kept-case names persist into candidate_names and supersede the
    attribution/twin-bridge proxies; ghost payloads carry stage/track/node_date
    derived from the harvested name + milestones."""

    PID = "文山區-木柵段三小段-623地號等39筆"
    NAME = "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"

    def _project(self):
        from urtpe.models import Project
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord

        raw = RawRecord(5, "115/8/11", "文山區",
                        "變更文山區木柵段三小段623地號等39筆都市更新權利變換計畫案",
                        "臺北市文山區木柵段三小段623地號等39筆", "某建設", "某規劃")
        return Project(project_id=self.PID, anchor_recno=5, members=[cleanse(raw)])

    def _disc(self, **over):
        base = {
            "twur": "",
            "taipei": ["09907221"],
            "milestones_national": {},
            "milestones_taipei": {"建照核發日期": "2022/02/17"},
            "case_milestones": {"09907221": {"核定日期": "2019/01/31",
                                             "建照核發日期": "2022/02/17"}},
            "milestones_source": {},
            "implementation": {},
            "rewards": {},
            "search_rejected": {},
            "candidate_names": {"09907221": self.NAME},
        }
        base.update(over)
        return {self.PID: base}

    def test_harvested_name_supersedes_proxies(self):
        project = self._project()
        attach_links_to_projects([project], self._disc(
            taipei=["09907222", "11501041", "09907221"],
        ))
        ghosts = project.links.get("orphan_nodes", [])
        assert [g["case_id"] for g in ghosts] == ["09907221"]
        assert ghosts[0]["case_name"] == self.NAME

    def test_payload_derives_stage_track_node_date(self):
        project = self._project()
        attach_links_to_projects([project], self._disc(
            taipei=["09907222", "11501041", "09907221"],
        ))
        g = project.links["orphan_nodes"][0]
        assert g["stage"] == "擬訂"
        assert g["track"] == "事業計畫"
        assert g["node_date"] == "2019-01-31"

    def test_dissimilar_harvested_name_blocks_proxies(self):
        project = self._project()
        disc = self._disc(
            taipei=["09907222", "11501041", "09907221"],
            milestones_source={"建照核發日期": "09907221"},
            candidate_names={
                "09907221": "擬訂臺北市中山區中山段二小段125地號等1筆土地都市更新事業計畫案",
            },
        )
        attach_links_to_projects([project], disc)
        assert "orphan_nodes" not in project.links


class TestDeriveFromCaseName:
    def test_stage_variants(self):
        from urtpe.links import derive_stage_from_case_name as f
        assert f("擬訂臺北市文山區…案") == "擬訂"
        assert f("變更臺北市文山區…案") == "變更"
        assert f("變更(第二次)臺北市文山區…案") == "變更(第二次)"
        assert f("變更（第二次）臺北市文山區…案") == "變更(第二次)"
        assert f("") == ""

    def test_track_variants(self):
        from urtpe.links import derive_track_from_case_name as f
        assert f("擬訂臺北市…事業計畫案") == "事業計畫"
        assert f("擬訂臺北市…事業計畫及權利變換計畫案") == "事業計畫、權利變換"
        assert f("變更臺北市…權利變換計畫案") == "權利變換"
        assert f("擬訂臺北市…事業概要案") == "事業概要"
        assert f("擬訂臺北市…都市更新計畫案") == "都市更新計畫"
        assert f("擬訂臺北市…案") == ""


class TestChimeraEmitFix:
    """§8 / facts §12 #2: the project-level merged milestones_taipei is
    last-write-wins (newest fetched case wins every label), so all nodes would
    render the newest case's dates. Each node must instead emit its OWN
    anchored case's per-case timeline (from case_milestones), falling back to
    the merged dict only when no per-case timeline exists."""

    PID = "中山區-中山段一小段-254地號等13筆"

    def _family(self):
        from urtpe.models import Project, RawRecord
        from urtpe.cleanse import cleanse

        rows = [
            (1219, "101/8/27", "擬訂臺北市中山區中山段一小段254地號等13筆土地都市更新事業計畫案"),
            (1037, "105/8/23", "變更臺北市中山區中山段一小段254地號等13筆土地都市更新事業計畫案"),
            (991, "106/4/13", "變更臺北市中山區中山段一小段254地號等13筆土地都市更新事業計畫案"),
        ]
        members = [cleanse(RawRecord(rn, dt, "中山區", nm,
                                     "臺北市中山區中山段一小段254地號等13筆",
                                     "某建設", "某規劃")) for rn, dt, nm in rows]
        return Project(project_id=self.PID, anchor_recno=1219, members=members)

    def _disc(self):
        return {self.PID: {
            "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/136",
            "taipei": ["09811141", "09811142", "09811144"],
            "milestones_national": {},
            # the merged chimera: 142 was fetched last and won 核定日期
            "milestones_taipei": {"核定日期": "2016/08/23"},
            "case_milestones": {
                "09811141": {"核定日期": "2012/08/27"},
                "09811142": {"核定日期": "2016/08/23"},
                "09811144": {"核定日期": "2017/04/13"},
            },
            "milestones_source": {"核定日期": "09811142"},
            "implementation": {}, "rewards": {}, "search_rejected": {},
        }}

    def test_nodes_emit_own_case_timeline_not_chimera(self):
        import copy

        project = self._family()
        disc = self._disc()
        before = copy.deepcopy(disc)
        attach_links_to_projects([project], disc)

        by_recno = {m.recno: m.links for m in project.members}
        assert by_recno[1219]["milestones_taipei"]["核定日期"] == "2012/08/27"
        assert by_recno[1037]["milestones_taipei"]["核定日期"] == "2016/08/23"
        assert by_recno[991]["milestones_taipei"]["核定日期"] == "2017/04/13"
        # project-level merged dict + provenance untouched (no mutation)
        assert disc[self.PID]["milestones_taipei"] == before[self.PID]["milestones_taipei"]
        assert disc[self.PID]["milestones_source"] == before[self.PID]["milestones_source"]

    def test_legacy_cache_falls_back_to_merged_dict(self):
        """Anchored case without a per-case timeline → node falls back to the
        project-level merged dict (current behavior preserved)."""
        from urtpe.models import Project, RawRecord
        from urtpe.cleanse import cleanse

        raw = RawRecord(772, "115/8/11", "中正區",
                        "變更中正區河堤段四小段263-19地號等25筆都市更新事業計畫案",
                        "中正區河堤段四小段263-19等25筆", "萬仕達建設", "某規劃")
        project = Project(project_id="中正區-河堤段四小段-263-19地號等25筆",
                          anchor_recno=772, members=[cleanse(raw)])
        merged = {"核定日期": "2019/08/01"}
        disc = {"中正區-河堤段四小段-263-19地號等25筆": {
            "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/262",
            "taipei": ["10707031"],
            "milestones_national": {},
            "milestones_taipei": merged,
            "case_milestones": {},  # legacy: no per-case data
            "milestones_source": {},
            "implementation": {}, "rewards": {}, "search_rejected": {},
        }}
        attach_links_to_projects([project], disc)
        node_links = project.members[0].links
        assert node_links["milestones_taipei"] == merged
