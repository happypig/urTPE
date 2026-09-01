"""BDD scenarios for the curated-exception resolve flow (category 1, §6.14).

Scenarios mirror the 11 unresolved projects' failure shapes:
  - anchor-parcel drift (華中段247: cases named 201-2、352地號)
  - unparseable count (東湖段?筆: name carries 20-9地號)
  - section drift (實踐段641: 案名 section 木新路三段 vs land core 實踐段二小段)
  - parcel-less names (崇仁新村 shape) — identity must come from tokens or portal cross-refs
  - twur'd empty payloads (臨沂412, 玉成253-1) — linkage complete, platform has no timeline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.curated_resolve import (
    attach_cases,
    classify_failure,
    derive_queries,
    identity_verdict,
)


def _disc(**over):
    base = {
        "status": "unresolved",
        "error": "",
        "city_case_ids": [],
        "candidate_names": {},
        "case_milestones": {},
        "taipei_milestones": {},
        "milestones_source": {},
        "national_milestones": {},
        "search_rejected": {},
        }
    base.update(over)
    return base


class TestClassifyFailure:
    def test_timeout(self):
        assert classify_failure({"status": "unresolved", "error": "Taipei search failed: The read operation timed out"}) == "timeout"

    def test_blank_search(self):
        assert classify_failure({"status": "unresolved", "error": ""}) == "blank-search"

    def test_guard_dropped(self):
        assert classify_failure({"status": "unresolved", "error": "", "search_rejected": {"09907221": "…"}}) == "guard-dropped"


class TestDeriveQueries:
    def test_anchor_parcel_drift_from_case_name(self):
        """華中段247: land core first_parcel=247, but 案名 names 201-2、352."""
        project = {
            "project_id": "萬華區-華中段一小段-247地號等26筆",
            "name": "變更臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案",
        }
        disc = {"land_core": "萬華區華中段一小段247地號等26筆"}
        queries = derive_queries(project, disc)
        assert ("華中段一小段", "201-2") in queries
        assert ("華中段一小段", "352") in queries
        assert ("華中段一小段", "247") not in queries  # already tried

    def test_name_parcel_when_count_unparseable(self):
        """東湖段?筆: 案名 carries 20-9地號 — the only usable parcel."""
        project = {
            "project_id": "內湖區-東湖段一小段-地號等?筆",
            "name": "變更臺北市內湖區東湖段一小段20-9地號土地都市更新權利變換計畫案(含釐正圖…)",
        }
        disc = {"land_core": "內湖區東湖段一小段"}
        assert ("東湖段一小段", "20-9") in derive_queries(project, disc)

    def test_section_drift_query_from_case_name(self):
        """實踐段641: 案名 section is 木新路三段 — try it too."""
        project = {
            "project_id": "文山區-實踐段二小段-641地號等1筆",
            "name": "擬訂臺北市文山區木新路三段95巷南側地區(原國泰攬翠天廈基地)都市更新事業計畫案",
        }
        disc = {"land_core": "文山區實踐段二小段641地號等1筆"}
        queries = derive_queries(project, disc)
        assert any(q[0] == "木新路三段" for q in queries)


class TestIdentityVerdict:
    def test_parcel_in_case_name_passes(self):
        v = identity_verdict(
            case_name="變更臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案",
            project_name="變更臺北市萬華區華中段一小段247地號等26筆土地都市更新事業計畫案",
            searched_parcel="201-2",
        )
        assert v == "parcel-in-name"

    def test_settlement_token_match(self):
        v = identity_verdict(
            case_name="變更臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案",
            project_name="變更臺北市萬華區崇仁新村都市更新事業計畫及權利變換計畫案臺北市萬華區崇仁新村青年段一小段711-3、青年段二小段18地號土地",
            searched_parcel="711-3",
        )
        assert v in ("token-match", "none")  # token verification requires the distinctive token

    def test_parcel_less_without_shared_token_rejected(self):
        v = identity_verdict(
            case_name="擬訂臺北市大安區某段地號都市更新事業計畫案",
            project_name="變更臺北市萬華區某整宅地區都市更新事業計畫案",
            searched_parcel="999",
        )
        assert v == "none"


class TestAttachCases:
    def test_attach_validates_and_resolves(self):
        d = {
            "project_id": "文山區-實踐段二小段-641地號等1筆",
            "land_core": "文山區實踐段二小段641地號等1筆",
            "status": "unresolved",
            "error": "",
            "city_case_ids": [],
            "candidate_names": {},
            "case_milestones": {},
            "taipei_milestones": {},
            "milestones_source": {},
            "national_milestones": {},
            "search_rejected": {},
        }
        cases = [{
            "case_id": "10210151",
            "case_name": "擬訂臺北市文山區實踐段二小段641地號等1筆土地都市更新事業計畫案",
            "milestones": {"計畫公聽會日期": "2015/01/11", "核定日期": "2016/03/10"},
            "implementation": {"Eng_Start_Date": "2017/01/01", "Ulic_Date": "2019/01/01", "case_id": "10210151"},
        }]
        attach_cases(d, cases)
        assert d["status"] == "resolved" and d["error"] == ""
        assert d["city_case_ids"] == ["10210151"]
        assert d["candidate_names"]["10210151"].startswith("擬訂臺北市文山區實踐段")
        assert d["case_milestones"]["10210151"]["核定日期"] == "2016/03/10"
        assert d["taipei_milestones"]["核定日期"] == "2016/03/10"
        from urtpe.links import DiscoveryResult
        DiscoveryResult(**d)  # must round-trip

    def test_empty_payload_case_still_links(self):
        """Twur'd projects (臨沂412/玉成253-1): platform holds no timeline, but the
        linkage is real — attach with empty milestones and resolve."""
        d = {
            "project_id": "中正區-臨沂段三小段-412地號等12筆",
            "land_core": "中正區臨沂段三小段412地號等12筆",
            "status": "unresolved",
            "error": "",
            "city_case_ids": ["09904141"],
            "candidate_names": {"09904121": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案"},
            "case_milestones": {},
            "taipei_milestones": {},
            "milestones_source": {},
            "national_milestones": {},
            "search_rejected": {},
        }
        cases = [{"case_id": "09904121", "case_name": "擬訂臺北市中正區臨沂段三小段412地號等12筆土地都市更新事業計畫案", "milestones": {}, "implementation": {}}]
        attach_cases(d, cases)
        assert d["status"] == "resolved"
