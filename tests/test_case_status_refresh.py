# -*- coding: utf-8 -*-
"""The refresh re-derives each case's status and replaces its milestones
(refresh-case-status-and-drop-withdrawn-fields, tasks 1.2 / 1.4 / 1.5).

The defects these pin, all measured live on 2026-11-02 against the 13 cases the
awaiting-approval refresh reported as "still awaiting":

- the refresh never re-read a case's status, so 8 cases the platform lists as
  申請報府核定中 / 審查中 kept a cached 已核准 — a badge the viewer omits;
- the refresh merged ``{**before, **fetched}``, so a date the city withdrew
  stayed forever (士林區-光華段四小段-282's 11408032 kept 申請核定日期 2026/08/18);
- withdrawn cases were reported as "still awaiting approval".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (refresh_project, refreshed_schedule,
                         state_of_header, header_has_no_state)  # noqa: E402


# ── 0.0  state_of_header: split 無 vs empty for the per-case badge (§7 viewer-UX) ──


def test_state_of_header_maps_wu_to_wu():
    assert state_of_header({"NAME": "無"}) == "無"


def test_state_of_header_maps_empty_to_na():
    assert state_of_header({"NAME": ""}) == "NA"


def test_state_of_header_maps_missing_row_to_empty():
    assert state_of_header(None) == ""
    assert state_of_header({}) == ""


def test_state_of_header_maps_other_states_to_empty():
    assert state_of_header({"NAME": "審查中"}) == ""
    assert state_of_header({"NAME": "已核准"}) == ""


# ── 1.2  the pure status rule (D2) ──────────────────────────────────────────

PENDING = {"申請核定日期": "2026/06/09"}
APPROVED = {"核定日期": "2022/08/02"}


def test_a_stale_approved_status_takes_the_header_in_review():
    """中正段一小段-68 10406283: cached 已核准, header 申請報府核定中 → 審查中."""
    assert refreshed_schedule("已核准", "審查中", PENDING) == "審查中"


def test_a_none_header_stores_wu_as_its_own_state():
    """§7 viewer-UX decision 2: a header reading 無 is stored as [無], not cleared.
    This overrides the old supersede-headerless-cases D1 silence."""
    assert refreshed_schedule("審查中", "", PENDING, header_state="無") == "無"
    assert refreshed_schedule("已核准", "", PENDING, header_state="無") == "無"
    assert refreshed_schedule("", "", PENDING, header_state="無") == "無"


def test_a_none_header_stores_empty_as_na():
    """§7 viewer-UX decision 2: an empty NAME reads as [NA]."""
    assert refreshed_schedule("審查中", "", PENDING, header_state="NA") == "NA"
    assert refreshed_schedule("", "", PENDING, header_state="NA") == "NA"


def test_a_none_header_clears_an_in_review_status_wu():
    """supersede-headerless-cases D1 reversed (see §7 viewer-UX decision 2):
    a header reading 無 stores [無], even for a cached 審查中 on an approved unit."""
    assert refreshed_schedule("審查中", "", PENDING, header_state="無") == "無"
    assert refreshed_schedule("已核准", "", PENDING, header_state="無") == "無"


def test_a_none_header_overrides_terminal_with_wu():
    """§7 viewer-UX decision 2: 無 shows on every case, even a cached terminal
    status — reversing supersede D1's silence so the platform's current word wins."""
    for before in ("自行撤回", "已駁回", "已失效", "施工中", "已完工", "完成成果備查"):
        assert refreshed_schedule(before, "", PENDING, header_state="無") == "無"


def test_a_none_header_clears_an_approved_status():
    """虎林段四小段-38 10806141 (re-filed as 11510017)."""
    assert refreshed_schedule("已核准", "", PENDING, no_state=True) == ""
    assert refreshed_schedule("已核定", "", APPROVED, no_state=True) == ""


def test_a_none_header_keeps_a_terminal_or_later_status():
    """A withdrawn case stays withdrawn — clearing it could hide a project's
    never-approved reason."""
    for kept in ("自行撤回", "已駁回", "已失效", "施工中", "已完工", "完成成果備查"):
        assert refreshed_schedule(kept, "", PENDING, no_state=True) == kept


def test_an_unrecognised_header_keeps_a_consistent_status():
    assert refreshed_schedule("審查中", "", PENDING) == "審查中"


def test_an_unrecognised_header_clears_a_contradicted_approved_status():
    assert refreshed_schedule("已核准", "", PENDING) == ""
    assert refreshed_schedule("已核定", "", PENDING) == ""


def test_an_unrecognised_header_keeps_an_approved_status_the_milestones_support():
    assert refreshed_schedule("已核准", "", APPROVED) == "已核准"


def test_a_later_cached_stage_is_never_downgraded():
    for later in ("施工中", "已完工", "完成成果備查", "已核定"):
        assert refreshed_schedule(later, "已核准", APPROVED) == later


def test_terminal_and_in_review_headers_win():
    assert refreshed_schedule("已核准", "自行撤回", PENDING) == "自行撤回"
    assert refreshed_schedule("審查中", "已駁回", PENDING) == "已駁回"
    assert refreshed_schedule("", "審查中", PENDING) == "審查中"
    assert refreshed_schedule("審查中", "已核准", APPROVED) == "已核准"


# ── shared cache writer ─────────────────────────────────────────────────────

def _write_cache(cache_dir: Path, pid: str, *, case_milestones: dict,
                 case_schedules: dict | None = None) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": case_milestones,
        "city_case_ids": sorted(case_milestones),
        # no national page: the refresh's view-page absorb has nothing to fetch
        "twur_url": "", "twur_view_id": "",
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {},
        "case_schedules": case_schedules or {}, "error": "",
    }
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _saved(cache_dir: Path, pid: str) -> dict:
    return json.loads((cache_dir / pid / "result.json").read_text(encoding="utf-8"))


# ── 1.4  milestone replacement (D3) ─────────────────────────────────────────

def test_a_date_the_city_withdrew_leaves_the_cache(tmp_path):
    """光華段四小段-282 11408032: the live data2 tab no longer has 申請核定日期."""
    pid = "士林區-光華段四小段-282地號等2筆"
    _write_cache(tmp_path, pid, case_milestones={"11408032": {
        "申請計畫日期": "2025/08/20", "申請核定日期": "2026/08/18",
        "審議通過日期": "2026/09/23"}})

    report = refresh_project(tmp_path, pid, fetch=lambda cid: {
        "申請計畫日期": "2025/08/20", "審議通過日期": "2026/09/23"})

    ms = _saved(tmp_path, pid)["case_milestones"]["11408032"]
    assert "申請核定日期" not in ms
    assert ms["申請計畫日期"] == "2025/08/20"
    assert {"case_id": "11408032", "label": "申請核定日期",
            "was": "2026/08/18"} in report["removed"]


def test_a_withdrawn_approval_date_is_kept_and_reported_as_a_conflict(tmp_path):
    pid = "甲"
    _write_cache(tmp_path, pid, case_milestones={"X": {
        "申請核定日期": "2022/04/29", "核定日期": "2022/08/02"}})

    report = refresh_project(tmp_path, pid, fetch=lambda cid: {
        "申請核定日期": "2022/04/29"})

    ms = _saved(tmp_path, pid)["case_milestones"]["X"]
    assert ms["核定日期"] == "2022/08/02"
    assert {"case_id": "X", "label": "核定日期", "was": "2022/08/02"} in report["conflicts"]
    assert not any(r["label"] == "核定日期" for r in report["removed"])


def test_an_empty_reply_changes_nothing(tmp_path):
    pid = "乙"
    before = {"申請計畫日期": "2025/08/20", "申請核定日期": "2026/08/18"}
    _write_cache(tmp_path, pid, case_milestones={"X": dict(before)})
    report = refresh_project(tmp_path, pid, fetch=lambda cid: {})
    assert _saved(tmp_path, pid)["case_milestones"]["X"] == before
    assert report["removed"] == [] and report["conflicts"] == []


def test_a_failed_fetch_changes_nothing(tmp_path):
    pid = "丙"
    before = {"申請核定日期": "2026/08/18"}
    _write_cache(tmp_path, pid, case_milestones={"X": dict(before)})

    def boom(cid):
        raise TimeoutError("down")

    report = refresh_project(tmp_path, pid, fetch=boom)
    assert report["error"]
    assert _saved(tmp_path, pid)["case_milestones"]["X"] == before


# ── 1.5  the production default re-derives the status (D4) ──────────────────

def test_the_default_refresh_rederives_the_status(tmp_path, monkeypatch):
    """No fetcher injected = the production call the script makes. If the
    default refreshes milestones only, the 68 case keeps 已核准 and this fails —
    the §33 'passes its own test, inert in production' class."""
    pid = "中正區-中正段一小段-68地號等12筆"
    _write_cache(tmp_path, pid,
                 case_milestones={
                     "10406282": {"核定日期": "2016/01/25"},
                     "10406283": {"權變申請核定日期": "2026/06/09"},
                     "11012301": {"申請核定日期": "2021/12/29"},
                 },
                 case_schedules={"10406282": "已核准", "10406283": "已核准",
                                 "11012301": "審查中"})
    names = {
        "10406282": "事業計畫階段─業經本府核定",
        "10406283": "權利變換計畫階段─申請報府核定中",
        "11012301": "事業計畫及權利變換計畫階段─實施者自行撤回",
    }
    milestones = {
        "10406282": {"核定日期": "2016/01/25"},
        "10406283": {"權變申請核定日期": "2026/06/09"},
        "11012301": {"申請核定日期": "2021/12/29"},
    }
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                        lambda cid: dict(milestones[cid]))
    monkeypatch.setattr("urtpe.links.fetch_taipei_case_header_api",
                        lambda cid: {"NAME": names[cid]})

    report = refresh_project(tmp_path, pid)

    scheds = _saved(tmp_path, pid)["case_schedules"]
    assert scheds["10406283"] == "審查中"
    assert scheds["10406282"] == "已核准"
    assert scheds["11012301"] == "自行撤回"
    assert {"case_id": "10406283", "was": "已核准", "now": "審查中",
            "name": "權利變換計畫階段─申請報府核定中"} in report["status_changes"]
    assert report["closed"] == ["11012301"]
    assert report["still_awaiting"] == ["10406283"]


def test_an_injected_milestone_fetcher_alone_leaves_the_status_alone(tmp_path):
    """D4: a caller injecting only ``fetch`` (every pre-existing offline test)
    gets no status fetch — no network, no status change."""
    pid = "丁"
    _write_cache(tmp_path, pid, case_milestones={"X": {"申請核定日期": "2026/07/30"}},
                 case_schedules={"X": "已核准"})
    report = refresh_project(tmp_path, pid, fetch=lambda cid: {"申請核定日期": "2026/07/30"})
    assert _saved(tmp_path, pid)["case_schedules"] == {"X": "已核准"}
    assert report["status_changes"] == []
