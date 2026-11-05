# -*- coding: utf-8 -*-
"""The refresh re-derives, re-fetches and labels (D7 + D8 + D13).

Three defects, one function:

- D7 — the refresh rewrote each case's milestones but never re-merged them, so
  the merged projection went stale (85 of 719 caches diverged; 14 projects
  emitted no construction date a case actually holds).
- D8 — the refresh never re-fetched the implementation layer, so a project
  whose payload was empty stayed empty forever.
- D13 — a case the city emptied kept its stale 已核准 state, and its stale
  payload kept winning the project payload.

The tests here are offline: the fetchers are injected.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    pick_implementation_payload,
    refresh_project,
    select_best_payload,
)


def _write_cache(cache_dir: Path, pid: str, *, case_milestones: dict,
                 city_case_ids: list[str], taipei_milestones: dict | None = None,
                 milestones_source: dict | None = None, **extra) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": case_milestones,
        "city_case_ids": city_case_ids,
        "twur_url": "", "twur_view_id": "",
        "national_milestones": {},
        "taipei_milestones": taipei_milestones or {},
        "milestones_source": milestones_source or {},
        "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {}, "case_schedules": {},
        "case_headers": {}, "case_case_names": {},
        "superseded_by": {}, "view_rejected": {}, "view_verified_case_ids": [],
        "error": "",
    }
    payload.update(extra)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _saved(cache_dir: Path, pid: str) -> dict:
    return json.loads((cache_dir / pid / "result.json").read_text(encoding="utf-8"))


def _refresh(cache_dir: Path, pid: str, **kw) -> dict:
    """A refresh with every adapter injected, so it never reaches the network.

    The implementation fetchers default only on the production path (the
    milestone fetcher is injected here), so a test that wants the D8 fetch
    passes them explicitly.
    """
    kw.setdefault("fetch", lambda cid: {})
    kw.setdefault("fetch_status", lambda cid: None)
    kw.setdefault("fetch_implementation", lambda cid: {})
    kw.setdefault("fetch_rewards", lambda cid: {})
    return refresh_project(cache_dir, pid, **kw)


# ── D7: the merged projection is re-derived ──────────────────────────────

def test_a_case_appended_after_the_merge_reaches_the_projection(tmp_path):
    """吉林508 shape: the case 11508023 was appended after the merge and
    carries a newer 召開幹事會日期."""
    pid = "中山區-吉林段四小段-508地號等17筆"
    _write_cache(tmp_path, pid, case_milestones={
        "11011241": {"召開幹事會日期": "2022/11/15"},
        "11011242": {"召開幹事會日期": "2022/11/15"},
        "11508023": {"召開幹事會日期": "2026/10/02"},
    }, city_case_ids=["11011241", "11011242", "11508023"],
        taipei_milestones={"召開幹事會日期": "2022/11/15"},
        milestones_source={"召開幹事會日期": "11011242"})

    _refresh(tmp_path, pid)

    saved = _saved(tmp_path, pid)
    assert saved["taipei_milestones"]["召開幹事會日期"] == "2026/10/02", (
        "the re-derived projection must carry the newer case's value")
    assert saved["milestones_source"]["召開幹事會日期"] == "11508023"


def test_a_withdrawn_label_leaves_the_projection(tmp_path):
    """市府220-2 shape: the stored dict holds 公告公展日期 and no case does."""
    pid = "大同區-市府段二小段-220-2地號等54筆"
    _write_cache(tmp_path, pid, case_milestones={
        "09609300": {"核定日期": "2013/02/26"},
        "09609302": {"核定日期": "2013/02/26"},
    }, city_case_ids=["09609300", "09609302"],
        taipei_milestones={"核定日期": "2013/02/26", "公告公展日期": "2011/01/10"},
        milestones_source={"核定日期": "09609300", "公告公展日期": "09609300"})

    _refresh(tmp_path, pid)

    saved = _saved(tmp_path, pid)
    assert "公告公展日期" not in saved["taipei_milestones"], (
        "a label no case carries any more must leave the projection")
    assert saved["taipei_milestones"]["核定日期"] == "2013/02/26"


def test_a_redated_label_carries_the_new_value(tmp_path):
    """光華282 shape: the city re-dated 審議通過日期."""
    pid = "士林區-光華段四小段-282地號等2筆"
    _write_cache(tmp_path, pid, case_milestones={
        "11408032": {"審議通過日期": "2026/09/23"},
    }, city_case_ids=["11408032"],
        taipei_milestones={"審議通過日期": "2026/03/18"},
        milestones_source={"審議通過日期": "11408032"})

    _refresh(tmp_path, pid)

    saved = _saved(tmp_path, pid)
    assert saved["taipei_milestones"]["審議通過日期"] == "2026/09/23"


def test_a_project_whose_cases_did_not_move_keeps_its_projection(tmp_path):
    pid = "甲"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"],
        taipei_milestones={"核定日期": "2019/02/14"},
        milestones_source={"核定日期": "10105152"})

    _refresh(tmp_path, pid)

    saved = _saved(tmp_path, pid)
    assert saved["taipei_milestones"] == {"核定日期": "2019/02/14"}
    assert saved["milestones_source"] == {"核定日期": "10105152"}


# ── D8: the implementation layer is re-fetched per case ──────────────────

def test_a_live_approved_case_with_no_entry_gains_one(tmp_path):
    pid = "文山區-實踐段二小段-641地號等1筆"
    _write_cache(tmp_path, pid, case_milestones={
        "09009032": {"核定日期": "2010/01/01"},
    }, city_case_ids=["09009032"],
        case_schedules={"09009032": "已核准"})

    seen_impl, seen_rew = [], []

    def impl(cid):
        seen_impl.append(cid)
        return {"Eng_Start_Date": "2004/09/24", "Ulic_Date": "2007/10/31"}

    def rew(cid):
        seen_rew.append(cid)
        return {"F0": "100"}

    _refresh(tmp_path, pid, fetch_implementation=impl, fetch_rewards=rew,
             fetch=lambda cid: {"核定日期": "2010/01/01"},
             fetch_status=lambda cid: {"NAME": "事業計畫階段─業經本府核定"})

    saved = _saved(tmp_path, pid)
    assert seen_impl == ["09009032"], "the case must be fetched"
    assert saved["implementation"]["09009032"]["Eng_Start_Date"] == "2004/09/24"
    assert saved["rewards"]["09009032"]["F0"] == "100"


def test_a_case_that_already_has_an_entry_is_not_refetched(tmp_path):
    pid = "乙"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"], implementation={"10105152": {"F0": "1"}})

    seen: list[str] = []

    _refresh(tmp_path, pid,
             fetch_implementation=lambda cid: seen.append(cid) or {"Eng_Start_Date": "2004/09/24"},
             fetch_rewards=lambda cid: {})

    assert seen == [], "a case with an entry must not be re-fetched"


def test_an_empty_implementation_reply_stores_nothing(tmp_path):
    pid = "丙"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"])

    _refresh(tmp_path, pid,
             fetch_implementation=lambda cid: {},
             fetch_rewards=lambda cid: {})

    saved = _saved(tmp_path, pid)
    assert "10105152" not in saved["implementation"], (
        "an empty reply must not be stored as an empty entry")


# ── D13: a case the city emptied is labelled 無 ──────────────────────────

def test_an_emptied_case_is_labelled_wu_and_keeps_its_id(tmp_path):
    """青年130 shape: 11501041 was emptied by the city."""
    pid = "萬華區-青年段一小段-130地號等3筆"
    _write_cache(tmp_path, pid, case_milestones={
        "11501041": {"核定日期": "2026/01/20"},
        "11510008": {"核定日期": "2026/01/20"},
    }, city_case_ids=["11501041", "11510008"],
        case_schedules={"11501041": "已核准", "11510008": "已核定"})

    report = _refresh(tmp_path, pid, fetch=lambda cid: {},
                      fetch_status=lambda cid: None)

    saved = _saved(tmp_path, pid)
    assert saved["case_schedules"]["11501041"] == "無", (
        "the emptied case must be labelled 無, not keep 已核准")
    assert "11501041" in saved["city_case_ids"], "the id stays"
    assert saved["case_milestones"]["11501041"], "the cached data stays"
    assert "11501041" in report.get("labelled_wu", []), (
        "the report must name every case it labelled 無")


def test_a_revoked_case_is_not_labelled_wu(tmp_path):
    """美仁800 near-miss: 09707196 reads 業經本府撤銷核准 — not this shape."""
    pid = "大安區-美仁段一小段-800地號等9筆"
    _write_cache(tmp_path, pid, case_milestones={
        "09707196": {"核定日期": "2019/02/14"},
    }, city_case_ids=["09707196"],
        case_schedules={"09707196": ""})

    _refresh(tmp_path, pid,
             fetch=lambda cid: {"核定日期": "2019/02/14"},
             fetch_status=lambda cid: {"NAME": "業經本府撤銷核准",
                                       "CASE_NAME": "案"})

    saved = _saved(tmp_path, pid)
    assert saved["case_schedules"].get("09707196") != "無", (
        "a revoked case is not an emptied case")


def test_one_empty_source_is_not_enough(tmp_path):
    """The header is empty but the milestones are not — no 無 label."""
    pid = "丁"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"],
        case_schedules={"10105152": "已核准"})

    _refresh(tmp_path, pid,
             fetch=lambda cid: {"核定日期": "2019/02/14"},
             fetch_status=lambda cid: None)

    saved = _saved(tmp_path, pid)
    assert saved["case_schedules"].get("10105152") != "無"


def test_hulin38_case_is_labelled_wu(tmp_path):
    """虎林38 shape: 11410001's header and its data2 are both empty."""
    pid = "信義區-虎林段四小段-38地號等138筆"
    _write_cache(tmp_path, pid, case_milestones={
        "11410001": {"核定日期": "2024/01/01"},
        "11502012": {"核定日期": "2025/01/01"},
    }, city_case_ids=["11410001", "11502012"],
        case_schedules={"11410001": "已核准", "11502012": "已核定"})

    report = _refresh(tmp_path, pid,
                      fetch=lambda cid: {} if cid == "11410001"
                      else {"核定日期": "2025/01/01"},
                      fetch_status=lambda cid: None)

    saved = _saved(tmp_path, pid)
    assert saved["case_schedules"]["11410001"] == "無"
    assert "11410001" in report.get("labelled_wu", [])


def test_qingnian130_the_live_sibling_binds_and_gets_its_implementation(tmp_path):
    """The board's end-to-end case: the city emptied 11501041 and moved the
    case to 11510008. After the refresh the node binds 11510008, and 11510008
    carries the implementation payload."""
    from urtpe.links import filter_live_cases

    pid = "萬華區-青年段一小段-130地號等3筆"
    name = "擬訂臺北市萬華區青年段一小段130地號等3筆土地都市更新事業計畫案"
    _write_cache(tmp_path, pid, case_milestones={
        "11501041": {"核定日期": "2026/01/20", "申請計畫日期": "2025/01/01"},
        "11510008": {"核定日期": "2026/01/20", "申請計畫日期": "2025/01/01"},
    }, city_case_ids=["11501041", "11510008"],
        case_schedules={"11501041": "已核准", "11510008": "已核定"},
        candidate_names={"11501041": name, "11510008": name})

    def milestones(cid):
        if cid == "11501041":
            return {}          # the city emptied the old id
        return {"核定日期": "2026/01/20", "申請計畫日期": "2025/01/01"}

    def header(cid):
        if cid == "11501041":
            return {}
        return {"NAME": "事業計畫階段─業經本府核定", "CASE_NAME": name}

    report = _refresh(tmp_path, pid, fetch=milestones, fetch_status=header,
                      fetch_implementation=lambda cid: (
                          {"Settle_Old_Doors": "140.0"} if cid == "11510008" else {}),
                      fetch_rewards=lambda cid: (
                          {"F0": "100"} if cid == "11510008" else {}))

    saved = _saved(tmp_path, pid)
    assert saved["case_schedules"]["11501041"] == "無", (
        "the emptied case must be labelled 無")
    assert "11501041" in report.get("labelled_wu", [])
    # the live sibling carries the payload
    assert saved["implementation"]["11510008"]["Settle_Old_Doors"] == "140.0"
    # and the node binds the live sibling alone
    class D:
        pass
    d = D()
    d.case_schedules = saved["case_schedules"]
    d.case_milestones = saved["case_milestones"]
    live = filter_live_cases(["11501041", "11510008"], d)
    assert live == ["11510008"], (
        f"the 無 case must yield to the live sibling, got {live}")


# ── the 無 exclusion at both selection layers ────────────────────────────

def _disc(schedules, implementation, names=None):
    class D:
        pass
    d = D()
    d.case_schedules = schedules
    d.implementation = implementation
    d.candidate_names = names or {}
    d.case_milestones = {}
    return d


def test_a_wu_case_does_not_win_the_key_count_pick():
    """雅祥227 shape: the 無 case holds 26 keys, the live sibling 1."""
    payloads = {
        "11009142": {f"k{i}": i for i in range(26)},
        "11009141": {"only": 1},
    }
    cid, payload, _flags = select_best_payload(
        payloads, excluded={"11009142"})
    assert cid == "11009141"
    assert payload == {"only": 1}


def test_a_wu_case_supplies_no_date_in_the_plan_case_collection():
    plan_name = "擬訂臺北市信義區雅祥段一小段227-4地號等10筆土地都市更新事業計畫案"
    payloads = {
        "11009142": {"Eng_Start_Date": "2019/01/01"},
        "11009141": {},
    }
    dates, source, _cid, _flags = pick_implementation_payload(
        payloads, {"11009142": plan_name, "11009141": plan_name},
        excluded={"11009142"})
    assert "開工日期" not in dates, (
        "the 無 case must not supply a date")


def test_a_project_whose_only_case_is_wu_keeps_the_empty_answer():
    cid, payload, _flags = select_best_payload(
        {"11009142": {"k": 1}}, excluded={"11009142"})
    assert cid == ""
    assert payload == {}


def test_the_conflict_flag_that_names_the_wu_case_stays():
    payloads = {
        "11009142": {"Eng_Start_Date": "2019/01/01"},
        "11009141": {"Eng_Start_Date": "2020/01/01"},
    }
    _cid, _payload, flags = select_best_payload(
        payloads, excluded={"11009142"})
    assert any("11009142" in f for f in flags), (
        "the conflict flag naming the 無 case must stay")
