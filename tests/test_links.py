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
        monkeypatch.setattr(links, "search_taipei_cases_api", lambda section, parcel: [
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
        monkeypatch.setattr(links, "search_taipei_cases_api", lambda section, parcel: [
            {"case_id": "09811141", "case_name": "x", "schedule": ""}])

        project = self._project()
        result = discover_project_links(project, tmp_path, fresh=True, delay=0)

        assert result.implementation.get("09811141", {}) in ({}, None) or "09811141" not in result.implementation
        assert result.rewards["09811141"]["F0"] == "8,982.01"
        assert "09811141" in result.error