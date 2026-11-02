# -*- coding: utf-8 -*-
"""Superseded cases and cases filed after the cache was written
(supersede-headerless-cases-and-discover-new-ids, tasks 1.2 / 1.4 / 1.5 / 1.6).

Measured live 2026-11-02. The city re-files an application under a new case id
and leaves the old one with header 目前辦理情形 = 無:

- 立農段五小段-163-2: 11211211 (無) → 11409026 (核定 2026/08/18), same 案名, the
  old data2 map a subset of the new one;
- 虎林段四小段-38: 10806141 (無) → 11510017 (申請報府核定中), identical data2 —
  and 11510017 was not in the project's cache at all (cache 2026-08-30; the
  refresh re-read only the ids it held), while the parcel search returns it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    DiscoveryResult,
    attach_links_to_projects,
    find_superseding_case,
    refresh_project,
)
from urtpe.models import make_record  # noqa: E402

NAME_LINONG = "擬訂臺北市北投區立農段五小段163-2地號等4筆土地都市更新事業計畫及權利變換計畫案"
NAME_HULIN = "擬訂臺北市信義區虎林段四小段38地號等138筆(原120筆)土地都市更新權利變換計畫案"

OLD_LINONG = {"計畫公聽會日期": "2023/11/21", "申請計畫日期": "2024/02/06",
              "審議通過日期": "2026/01/19", "申請核定日期": "2026/03/04"}
NEW_LINONG = {**OLD_LINONG, "核定日期": "2026/08/18"}
HULIN_MS = {"權變公聽會日期": "2019/06/14", "申請權變日期": "2019/08/21",
            "權變審議通過日期": "2026/06/29", "權變申請核定日期": "2026/07/31"}


# ── 1.2  the pure twin rule (D2) ────────────────────────────────────────────

def test_a_refiled_case_finds_its_successor():
    ms = {"11211211": OLD_LINONG, "11409026": NEW_LINONG}
    names = {"11211211": NAME_LINONG, "11409026": NAME_LINONG}
    assert find_superseding_case("11211211", ms, names) == ("11409026", "", [])


def test_an_identical_history_finds_its_successor():
    ms = {"10806141": HULIN_MS, "11510017": dict(HULIN_MS), "11502012": {"核定日期": "2026/03/12"}}
    names = {"10806141": NAME_HULIN, "11510017": NAME_HULIN, "11502012": "變更…事業計畫案"}
    assert find_superseding_case("10806141", ms, names) == ("11510017", "", [])


def test_a_different_case_name_is_not_a_successor():
    ms = {"11211211": OLD_LINONG, "11409026": NEW_LINONG}
    names = {"11211211": NAME_LINONG, "11409026": "變更" + NAME_LINONG}
    assert find_superseding_case("11211211", ms, names) == ("", "none", [])


def test_two_qualifying_successors_are_ambiguous():
    ms = {"11211211": OLD_LINONG, "11409026": NEW_LINONG, "11409027": NEW_LINONG}
    names = {k: NAME_LINONG for k in ms}
    assert find_superseding_case("11211211", ms, names) == ("", "ambiguous", [])


def test_a_sparse_case_is_not_matched():
    sparse = {"申請計畫日期": "2024/02/06", "申請核定日期": "2026/03/04"}
    ms = {"11211211": sparse, "11409026": NEW_LINONG}
    names = {k: NAME_LINONG for k in ms}
    assert find_superseding_case("11211211", ms, names) == ("", "none", [])


def test_an_older_id_is_not_a_successor():
    ms = {"11409026": OLD_LINONG, "11211211": NEW_LINONG}
    names = {k: NAME_LINONG for k in ms}
    assert find_superseding_case("11409026", ms, names) == ("", "none", [])


# ── match-superseding-case-on-application-dates (1.1) ──────────────────────
# The maintainer's decision (2026-11-02): a re-filed case restates its
# application dates and re-runs later steps, so only the application dates
# must agree. Both shapes are live measurements the strict rule refused.

NAME_YAXIANG = "擬訂臺北市信義區雅祥段一小段227-4地號等10筆土地都市更新事業計畫及權利變換計畫案"
OLD_YAXIANG = {"計畫公聽會日期": "2024/03/18", "申請計畫日期": "2024/05/09",
               "申請權變日期": "2024/05/09", "公告公展日期": "2025/05/07",
               "權變公告公展日期": "2025/05/07"}
NEW_YAXIANG = {**OLD_YAXIANG, "公告公展日期": "2026/10/13", "權變公告公展日期": "2026/10/13"}

NAME_JILIN = "變更臺北市中山區吉林段四小段705-3地號等14筆土地都市更新事業計畫及權利變換計畫案"
OLD_JILIN = {"計畫公聽會日期": "2023/12/03", "申請計畫日期": "2024/02/07",
             "申請權變日期": "2024/02/07", "召開幹事會日期": "2026/01/27"}
NEW_JILIN = {**OLD_JILIN, "召開幹事會日期": "2026/01/09", "召開幹事複審日期": "2026/09/29"}


def test_a_refiled_case_with_a_re_held_exhibition_matches():
    ms = {"11009142": OLD_YAXIANG, "11510001": NEW_YAXIANG}
    names = {k: NAME_YAXIANG for k in ms}
    assert find_superseding_case("11009142", ms, names) == (
        "11510001", "", ["公告公展日期", "權變公告公展日期"])


def test_a_refiled_case_with_a_corrected_committee_date_matches():
    ms = {"10410012": OLD_JILIN, "11503012": NEW_JILIN}
    names = {k: NAME_JILIN for k in ms}
    assert find_superseding_case("10410012", ms, names) == (
        "11503012", "", ["召開幹事會日期"])


def test_a_different_application_date_is_not_a_successor():
    ms = {"11009142": OLD_YAXIANG, "11510001": {**NEW_YAXIANG, "申請計畫日期": "2026/01/01"}}
    names = {k: NAME_YAXIANG for k in ms}
    assert find_superseding_case("11009142", ms, names) == ("", "none", [])


def test_a_case_without_an_application_date_is_not_matched():
    no_app = {"計畫公聽會日期": "2024/03/18", "公告公展日期": "2025/05/07",
              "公展公聽會日期": "2025/05/23"}
    ms = {"11009142": no_app, "11510001": dict(no_app)}
    names = {k: NAME_YAXIANG for k in ms}
    assert find_superseding_case("11009142", ms, names) == ("", "none", [])


# ── shared cache writer ─────────────────────────────────────────────────────

def _write_cache(cache_dir: Path, pid: str, *, case_milestones: dict,
                 city_case_ids: list[str], case_schedules: dict | None = None) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": case_milestones, "city_case_ids": city_case_ids,
        "twur_url": "", "twur_view_id": "",
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {},
        "case_schedules": case_schedules or {}, "error": "",
    }
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return d


def _saved(cache_dir: Path, pid: str) -> dict:
    return json.loads((cache_dir / pid / "result.json").read_text(encoding="utf-8"))


HULIN_PID = "信義區-虎林段四小段-38地號等138筆"
HULIN_KEY = ("虎林段四小段", "38", "變更(第二次)臺北市信義區虎林段四小段38地號等138筆(原120筆)土地都市更新事業計畫案")
HULIN_IDS = ["09403312", "10806141", "11502012"]
HULIN_CACHE_MS = {
    "09403312": {"核定日期": "2019/05/28"},
    "10806141": dict(HULIN_MS),
    "11502012": {"申請核定日期": "2026/01/16", "核定日期": "2026/03/12"},
}
HULIN_LIVE_MS = {**HULIN_CACHE_MS, "11510017": dict(HULIN_MS)}
HULIN_HEADERS = {
    "09403312": {"NAME": "事業計畫階段─業經本府核定", "CASE_NAME": "擬訂…事業計畫案"},
    "10806141": {"NAME": "無", "CASE_NAME": NAME_HULIN},
    "11502012": {"NAME": "事業計畫階段─業經本府核定", "CASE_NAME": "變更(第二次)…事業計畫案"},
    "11510017": {"NAME": "事業計畫及權利變換計畫階段─申請報府核定中", "CASE_NAME": NAME_HULIN},
}
HULIN_SEARCH = [
    {"case_id": "09403312", "case_name": "擬訂…事業計畫案", "schedule": "已核定"},
    {"case_id": "11510017", "case_name": NAME_HULIN, "schedule": "審查中"},
    {"case_id": "11502012", "case_name": "變更(第二次)…事業計畫案", "schedule": "已核定"},
]


def _hulin_cache(tmp_path):
    _write_cache(tmp_path, HULIN_PID, case_milestones=json.loads(json.dumps(HULIN_CACHE_MS)),
                 city_case_ids=list(HULIN_IDS),
                 case_schedules={"09403312": "已核准", "11502012": "已核准"})


# ── 1.4  the refresh appends new ids and records supersession (D3/D4) ───────

def test_the_refresh_appends_a_new_case_and_records_the_successor(tmp_path):
    _hulin_cache(tmp_path)
    searched = []

    def search(section, parcel, dropped_out=None, anchor_name=""):
        searched.append((section, parcel, anchor_name))
        return [dict(e) for e in HULIN_SEARCH]

    report = refresh_project(
        tmp_path, HULIN_PID,
        fetch=lambda cid: dict(HULIN_LIVE_MS[cid]),
        fetch_status=lambda cid: dict(HULIN_HEADERS[cid]),
        search=search, search_key=HULIN_KEY)

    assert searched == [HULIN_KEY]
    saved = _saved(tmp_path, HULIN_PID)
    # appended after the old ids, the old order untouched
    assert saved["city_case_ids"] == HULIN_IDS + ["11510017"]
    assert saved["case_milestones"]["11510017"] == HULIN_MS
    assert saved["case_schedules"]["11510017"] == "審查中"
    assert saved["superseded_by"] == {"10806141": "11510017"}
    assert saved["case_headers"]["10806141"] == "無"
    # §7 viewer-UX decision 2: 無 stores as its own state ([無]), so 10806141 keeps
    # it instead of being cleared (reversing supersede D1's silence).
    assert saved["case_schedules"]["10806141"] == "無"
    assert report["added"] == [{"case_id": "11510017", "schedule": "審查中",
                                "name": "事業計畫及權利變換計畫階段─申請報府核定中"}]
    assert report["superseded"] == [{"case_id": "10806141", "by": "11510017", "differs": []}]
    assert report["still_awaiting"] == ["11510017"]


def test_a_headerless_case_without_a_successor_is_named(tmp_path):
    pid = "甲"
    _write_cache(tmp_path, pid, case_milestones={"11211211": dict(OLD_LINONG)},
                 city_case_ids=["11211211"], case_schedules={"11211211": "審查中"})
    report = refresh_project(
        tmp_path, pid, fetch=lambda cid: dict(OLD_LINONG),
        fetch_status=lambda cid: {"NAME": "無", "CASE_NAME": NAME_LINONG},
        search=lambda *a, **k: [], search_key=("立農段五小段", "163-2", NAME_LINONG))
    assert report["no_successor"] == ["11211211"]
    assert report["still_awaiting"] == []
    # §7 viewer-UX decision 2: header 無 stores [無] even without a successor.
    assert _saved(tmp_path, pid)["case_schedules"] == {"11211211": "無"}


def test_a_failed_search_is_a_failure_and_writes_nothing(tmp_path):
    _hulin_cache(tmp_path)
    before = (tmp_path / HULIN_PID / "result.json").read_bytes()

    def boom(*a, **k):
        raise TimeoutError("search down")

    report = refresh_project(tmp_path, HULIN_PID, fetch=lambda cid: {},
                             fetch_status=lambda cid: {}, search=boom, search_key=HULIN_KEY)
    assert "search" in report["error"]
    assert (tmp_path / HULIN_PID / "result.json").read_bytes() == before


def test_no_search_key_is_reported_not_searched(tmp_path):
    _hulin_cache(tmp_path)
    report = refresh_project(tmp_path, HULIN_PID, fetch=lambda cid: {},
                             fetch_status=lambda cid: {}, search=lambda *a, **k: [],
                             search_key=None)
    assert report["not_searched"] is True


# ── 1.5  the production default runs the search (D4) ───────────────────────

def test_the_default_refresh_searches_and_records_the_successor(tmp_path, monkeypatch):
    _hulin_cache(tmp_path)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                        lambda cid: dict(HULIN_LIVE_MS[cid]))
    monkeypatch.setattr("urtpe.links.fetch_taipei_case_header_api",
                        lambda cid: dict(HULIN_HEADERS[cid]))
    monkeypatch.setattr("urtpe.links.search_taipei_cases_api",
                        lambda section, parcel, dropped_out=None, anchor_name="": [dict(e) for e in HULIN_SEARCH])
    refresh_project(tmp_path, HULIN_PID, search_key=HULIN_KEY)
    saved = _saved(tmp_path, HULIN_PID)
    assert saved["city_case_ids"][-1] == "11510017"
    assert saved["superseded_by"] == {"10806141": "11510017"}


# ── 1.6  the payload carries the map and survives a reload (D6) ─────────────

def _project(pid: str):
    from urtpe.models import Project
    rec = make_record(22, "2026/8/18", "北投區", NAME_LINONG,
                      "臺北市北投區立農段五小段163-2地號等4筆", "某建設", "某規劃")
    return Project(project_id=pid, anchor_recno=22, members=[rec])


def test_the_map_reaches_the_payload_and_survives_a_reload():
    pid = "北投區-立農段五小段-163-2地號等4筆"
    disc = DiscoveryResult(project_id=pid, land_core="x",
                           city_case_ids=["11211211", "11409026"],
                           superseded_by={"11211211": "11409026"})
    first = _project(pid)
    attach_links_to_projects([first], {pid: disc})
    assert first.links["superseded_by"] == {"11211211": "11409026"}

    # --from-js: the emitted links dict is the next run's discovery input
    second = _project(pid)
    attach_links_to_projects([second], {pid: json.loads(json.dumps(first.links))})
    assert second.links["superseded_by"] == {"11211211": "11409026"}


def test_a_result_without_the_map_emits_without_the_key():
    pid = "乙"
    first = _project(pid)
    attach_links_to_projects([first], {pid: DiscoveryResult(project_id=pid, land_core="x",
                                                            city_case_ids=["09601260"])})
    assert "superseded_by" not in first.links
