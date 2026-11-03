# -*- coding: utf-8 -*-
"""The refresh re-absorbs the national view page (fix-row-order-tiebreak-and-view-badges
task 1.4).

The defect: a cache written before ``DiscoveryResult.view_verified_case_ids``
existed (measured: 70 of the first 80 caches carry no such field) can never gain
it from a milestone-only refresh — yet the 國-badge rule needs the list, and the
maintainer's report pins it: view/621 (北投區-關渡段二小段-303's national page)
names cases 10803151 and 10105152 in its 相關連結 block, so the pairing is
portal-asserted and must reach the payload.

The refresh already re-fetches per-case milestones; it must also re-run the
view-page absorb (the same code path discovery uses) so a backfilled cache gains
``view_verified_case_ids`` and any case ids the page names that the parcel search
missed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import refresh_project  # noqa: E402


def _write_cache(cache_dir: Path, pid: str, *, case_milestones: dict,
                 city_case_ids: list[str], twur_view_id: str = "621",
                 **extra) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "resolved",
        "case_milestones": case_milestones,
        "city_case_ids": city_case_ids,
        "twur_url": f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{twur_view_id}",
        "twur_view_id": twur_view_id,
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {}, "case_schedules": {},
        "error": "",
    }
    payload.update(extra)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


# view/621's shape: the 相關連結 block names the two older cases.
VIEW_621 = """
<html><body>
<div class='data_table_box'>
<h3 class='t_title orange_tag'>相關連結</h3>
<table class='type1_table'><tr><td>
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10803151" title="t">權變</a>
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=10105152" title="t">計畫</a>
</td></tr></table></div>
</body></html>
"""


def test_refresh_backfills_view_verified_case_ids(tmp_path, monkeypatch):
    """A cache predating the field gains the list from the project's own view
    page — the portal's assertion, not the parcel search's inference."""
    pid = "北投區-關渡段二小段-303地號等5筆"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
        "10803151": {"權變核定日期": "2020/07/28"},
    }, city_case_ids=["10105152", "10803151"])

    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})

    report = refresh_project(tmp_path, pid, fetch=lambda cid: {})

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert saved["view_verified_case_ids"] == ["10803151", "10105152"]
    assert report["error"] == ""


def test_refresh_adds_a_view_named_case_the_search_missed(tmp_path, monkeypatch):
    """A case the page names but the parcel search never returned joins
    city_case_ids with its milestones fetched — the absorb path's whole point."""
    pid = "甲"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"])

    seen_fetches: list[str] = []

    def fake_milestones(cid: str) -> dict:
        seen_fetches.append(cid)
        if cid == "10803151":
            return {"權變核定日期": "2020/07/28"}
        return {"核定日期": "2019/02/14"}

    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", fake_milestones)

    refresh_project(tmp_path, pid, fetch=fake_milestones)

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert "10803151" in saved["city_case_ids"]
    assert saved["case_milestones"]["10803151"]["權變核定日期"] == "2020/07/28"
    assert saved["view_verified_case_ids"] == ["10803151", "10105152"]


def test_refresh_on_a_complete_cache_keeps_the_list_untouched(tmp_path, monkeypatch):
    """An already-absorbed cache is not rewritten with a stale or duplicated
    list — the absorb merges, it never shrinks."""
    pid = "乙"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"],
        view_verified_case_ids=["10105152", "10803151"])

    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})

    refresh_project(tmp_path, pid, fetch=lambda cid: {})

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert saved["view_verified_case_ids"] == ["10105152", "10803151"]


def test_refresh_absorb_skips_rejected_ids_and_drops_their_milestones(tmp_path, monkeypatch):
    """S3a (Batch C residual): the absorb re-fetches every id the page names,
    including ids a previous refresh REJECTED (§8) — so each refresh re-fetches
    them and leaves their milestones in case_milestones (measured 2026-11-04:
    10202065, 09608220, 09511211, 09807161 in the payload; no node, orphan,
    edge or badge reads them). The absorb skips view_rejected ids, and the §8
    gate drops a rejected id's case_milestones entry."""
    pid = "丙"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"],
        view_verified_case_ids=["10105152", "10803151"],
        view_rejected={"10803151": {"reason": "foreign land core",
                                    "shape": "A", "label_ok": False,
                                    "city_ok": False}})

    seen: list[str] = []

    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                        lambda cid: seen.append(cid) or {"核定日期": "2019/02/14"})

    refresh_project(tmp_path, pid, fetch=lambda cid: {})

    # the rejected id was not re-fetched by the absorb...
    assert "10803151" not in seen
    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    # ...and it holds no milestones anywhere in the cache
    assert "10803151" not in saved["case_milestones"]
    # the rejection record survives (named, never dropped silently)
    assert saved["view_rejected"]["10803151"]["reason"] == "foreign land core"
    assert "10803151" not in saved["view_verified_case_ids"]
    assert "10803151" not in saved["city_case_ids"]


def test_refresh_gate_drops_a_newly_rejected_ids_milestones(tmp_path, monkeypatch):
    """An id the current gate rejects (foreign land core) loses its milestones
    in the same run — not only on the next refresh."""
    pid = "丁"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
        "10803151": {"權變核定日期": "2020/07/28"},
    }, city_case_ids=["10105152", "10803151"],
        view_verified_case_ids=["10105152", "10803151"],
        case_case_names={"10105152": "擬訂臺北市甲區甲段1地號等1筆土地都市更新事業計畫案",
                         "10803151": "擬訂臺北市乙區乙段9地號等9筆土地都市更新事業計畫案"})

    # the project's own view page names both ids...
    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})
    # ...and the fetch_status default is off (fetch injected), so case_case_names
    # stays as written; the gate then rejects 10803151 by its foreign name.
    refresh_project(tmp_path, pid, fetch=lambda cid: {})

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert "10803151" in saved["view_rejected"]
    assert "10803151" not in saved["case_milestones"]
    assert "10803151" not in saved["city_case_ids"]


def test_absorb_stores_the_national_page_title_as_twur_name(tmp_path, monkeypatch):
    """S9/C10: the pipeline stores the national page's own 案名 (the <title>)
    as twur_name — the portal names the project by its first 擬訂 case, and 452
    of 632 projects showed the wrong 國 label under the current-node rule."""
    pid = "戊"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"])

    title_page = VIEW_621.replace("<html><body>", "<html><head><title>擬訂臺北市北投區關渡段二小段303地號等5筆土地都市更新事業計畫案-都更查詢-內政部國土管理署都市更新入口網</title></head><body>")
    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: title_page)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})

    refresh_project(tmp_path, pid, fetch=lambda cid: {})

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert saved.get("twur_name") == "擬訂臺北市北投區關渡段二小段303地號等5筆土地都市更新事業計畫案"


def test_absorb_without_a_title_leaves_twur_name_empty(tmp_path, monkeypatch):
    """A cached page without a <title> 案名 stores no name; the payload then
    emits without the key."""
    pid = "己"
    _write_cache(tmp_path, pid, case_milestones={
        "10105152": {"核定日期": "2019/02/14"},
    }, city_case_ids=["10105152"])

    monkeypatch.setattr("urtpe.links.fetch_view_page", lambda vid, cache_dir=None, fresh=False: VIEW_621)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})

    refresh_project(tmp_path, pid, fetch=lambda cid: {})

    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert not saved.get("twur_name")
