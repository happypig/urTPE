# -*- coding: utf-8 -*-
"""Cache freshness: report a cache that predates the gazette, and refresh only the
caches whose cases were awaiting approval (refresh-awaiting-approval-caches 1.1).

The defect these pin: discover_project_links returns a cache hit without
re-fetching, so a case's milestones freeze at first cache. A case approved after
that moment never reaches the payload, _match_case_by_date finds no match, and the
attach falls to the positional fallback — the wrong badge, and (via the case-key
tie-break) the wrong row order. Measured on 通化段四小段-336: cache 2026-08-30,
case 11501034 approved 2026-10-15 per the city's API.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    cache_is_stale_for,
    cached_cases_awaiting_approval,
    refresh_project,
)


def _write_cache(cache_dir: Path, pid: str, *, published: str,
                 case_milestones: dict, **extra) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": case_milestones,
        "city_case_ids": sorted(case_milestones),
        "twur_url": "https://example/view/1",
        "twur_view_id": "1",
        "national_milestones": {"事業計畫核定日期": "111.08.02"},
        "taipei_milestones": {}, "milestones_source": {}, "implementation": {},
        "rewards": {}, "search_rejected": {}, "candidate_names": {},
        "case_schedules": {}, "error": "",
    }
    payload.update(extra)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _backdate(path: Path, days: int) -> None:
    """Make the cache file look written N days ago — the signal is the mtime."""
    import os
    import time
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def test_a_cache_written_before_the_gazette_is_stale(tmp_path):
    d = _write_cache(tmp_path, "甲", published="2026-08-30", case_milestones={})
    _backdate(d / "result.json", 90)          # written ~3 months before the gazette
    assert cache_is_stale_for(tmp_path, "甲", "2026-10-15") is True


def test_a_cache_written_on_or_after_the_gazette_is_not_stale(tmp_path):
    _write_cache(tmp_path, "甲", published="2026-10-15", case_milestones={})
    # written now, gazette dated in the past -> not stale
    assert cache_is_stale_for(tmp_path, "甲", "2026-10-15") is False


def test_a_missing_cache_is_not_stale(tmp_path):
    assert cache_is_stale_for(tmp_path, "缺席", "2026-10-15") is False


def test_staleness_uses_the_file_mtime_not_a_stored_field(tmp_path):
    """The guard against the inert version: no real cache stores a publication
    date (measured on all 726), so the signal MUST be the file's mtime. A cache
    written now is NOT stale for an old gazette even though its payload has no
    date field at all."""
    import os
    import time
    d = _write_cache(tmp_path, "甲", published="", case_milestones={})
    # remove any date-ish field to prove the check does not depend on one
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert "published_date" not in saved or not saved["published_date"]
    # freshly written -> not stale for a gazette dated a year ago
    assert cache_is_stale_for(tmp_path, "甲", "2025-01-01") is False
    # backdate the file -> stale for a gazette after that
    old = time.time() - 90 * 86400
    os.utime(d / "result.json", (old, old))
    assert cache_is_stale_for(tmp_path, "甲", "2026-10-15") is True


def test_the_selector_picks_a_case_awaiting_approval():
    ms = {"11501034": {"申請計畫日期": "2025/09/10", "申請核定日期": "2026/07/30"}}
    assert cached_cases_awaiting_approval(ms) is True


def test_the_selector_picks_a_plan_change_application_awaiting_approval():
    """The 303 shape (fix-row-order-tiebreak-and-view-badges 1.2): the case was
    filed as a plan change — only 申請計畫日期/申請權變日期 in the cache — and the
    API now reports 核定日期 2026/09/30 for 11505020. The archived selector
    (approval applications only) skipped this cache and left node 5 (2026-09-30)
    on the positional fallback."""
    ms = {"11505020": {"申請計畫日期": "2026/05/15", "申請權變日期": "2026/05/15"}}
    assert cached_cases_awaiting_approval(ms) is True


def test_the_selector_picks_a_concept_application_awaiting_approval():
    ms = {"11507024": {"申請概要核准日期": "2026/06/01"}}
    assert cached_cases_awaiting_approval(ms) is True


def test_the_selector_still_skips_resolved_cases():
    """A case with ANY approval date is resolved, whatever application fields
    it also carries — the selector must not re-fetch settled caches."""
    ms = {"10011271": {"核定日期": "2022/08/02", "申請核定日期": "2022/04/29"}}
    assert cached_cases_awaiting_approval(ms) is False
    ms2 = {"10803151": {"申請計畫日期": "2019/04/16", "權變核定日期": "2020/07/28"}}
    assert cached_cases_awaiting_approval(ms2) is False


def test_the_selector_skips_resolved_cases():
    ms = {"10011271": {"核定日期": "2022/08/02", "申請核定日期": "2022/04/29"}}
    assert cached_cases_awaiting_approval(ms) is False


def test_the_selector_skips_an_empty_case_set():
    assert cached_cases_awaiting_approval({}) is False
    assert cached_cases_awaiting_approval(None) is False


def test_the_selector_accepts_the_quanbian_application_field():
    ms = {"X": {"權變申請核定日期": "2026/07/30"}}
    assert cached_cases_awaiting_approval(ms) is True


def test_the_selector_skips_a_project_whose_awaiting_cases_were_closed():
    """refresh-case-status-and-drop-withdrawn-fields D5: a withdrawn or rejected
    case never gains an approval date, yet every refresh re-selected it (85 of
    176 selected projects, 2026-11-02). Shapes: 南海段一小段-687 11012301 and
    信義段二小段-142 11105301 (自行撤回), 三玉段一小段-672 09812232 (已駁回)."""
    ms = {"11012301": {"申請核定日期": "2021/12/29", "權變申請核定日期": "2021/12/29"}}
    assert cached_cases_awaiting_approval(ms, {"11012301": "自行撤回"}) is False
    ms = {"09812232": {"申請核定日期": "2012/01/03"}}
    assert cached_cases_awaiting_approval(ms, {"09812232": "已駁回"}) is False
    ms = {"X": {"申請計畫日期": "2020/01/01"}}
    assert cached_cases_awaiting_approval(ms, {"X": "已失效"}) is False


def test_one_open_awaiting_case_keeps_the_project_selected():
    ms = {"A": {"申請核定日期": "2021/12/29"}, "B": {"申請核定日期": "2026/06/09"}}
    assert cached_cases_awaiting_approval(ms, {"A": "自行撤回", "B": "審查中"}) is True
    # an unknown status is not terminal
    assert cached_cases_awaiting_approval(ms, {"A": "自行撤回"}) is True


def test_refresh_merges_the_new_approval_and_preserves_other_fields(tmp_path):
    pid = "大安區-通化段四小段-336地號等26筆"
    _write_cache(tmp_path, pid, published="2026-08-30", case_milestones={
        "11501034": {"申請計畫日期": "2025/09/10", "申請核定日期": "2026/07/30"},
    })

    def fake_fetch(case_id: str) -> dict:
        assert case_id == "11501034"
        return {"申請計畫日期": "2025/09/10", "申請核定日期": "2026/07/30",
                "核定日期": "2026/10/15"}

    report = refresh_project(tmp_path, pid, fetch=fake_fetch)

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert saved["case_milestones"]["11501034"]["核定日期"] == "2026/10/15"
    # every other field preserved
    assert saved["twur_url"] == "https://example/view/1"
    assert saved["national_milestones"] == {"事業計畫核定日期": "111.08.02"}
    assert saved["status"] == "resolved"
    # the report names the before/after
    assert report["project_id"] == pid
    assert report["updated"], report
    assert report["updated"][0]["case_id"] == "11501034"
    assert report["updated"][0]["核定日期"] == "2026/10/15"


def test_refresh_reports_a_case_still_awaiting(tmp_path):
    pid = "甲"
    _write_cache(tmp_path, pid, published="2026-08-30", case_milestones={
        "X": {"申請核定日期": "2026/07/30"},
    })
    report = refresh_project(tmp_path, pid, fetch=lambda cid: {"申請核定日期": "2026/07/30"})
    assert report["updated"] == []
    assert report["still_awaiting"] == ["X"]
    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert "核定日期" not in saved["case_milestones"]["X"]
