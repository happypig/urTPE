# -*- coding: utf-8 -*-
"""scripts/admit_unit_cases.py (unit-count-rule 1.6)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import admit_unit_cases as ac  # noqa: E402
from urtpe.lock import SingleWriterLock  # noqa: E402

PID = "文山區-華興段一小段-8地號等4筆"
CORE = "文山區華興段一小段8地號等4筆"
N13 = "擬訂臺北市文山區華興段一小段18-1地號等13筆土地都市更新事業計畫案"
N9 = "擬訂臺北市文山區華興段一小段18-1地號等9筆土地都市更新事業計畫案"
PROJECT = {"project_id": PID}


def _cache(root: Path, pid=PID, **fields) -> Path:
    d = root / pid
    d.mkdir(parents=True)
    base = {"project_id": pid, "land_core": CORE,
            "own_parcels": ["8", "9", "18-1"], "own_counts": [4, 13],
            "city_case_ids": ["09902263"],
            "search_rejected": {"09708111": N13, "09708112": N9}}
    base.update(fields)
    (d / "result.json").write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    return d


class Ad:
    def __init__(self):
        self.calls = []

    def header(self, cid):
        self.calls.append(cid)
        return {"CASE_NAME": N13, "NAME": "事業計畫階段─實施者自行撤回",
                "uro_chk_date": ""}

    def milestones(self, cid):
        return {"申請計畫日期": "2008/08/18"}


def _run(tmp_path, ad, projects=None, **kw):
    return ac.run(tmp_path / "cache", projects or {PID: PROJECT}, tmp_path / "bak",
                  fetch_header=ad.header, fetch_milestones=ad.milestones,
                  sleep=lambda s: None, **kw)


def test_a_dry_run_lists_the_ids_and_writes_nothing(tmp_path):
    d = _cache(tmp_path / "cache")
    before = (d / "result.json").read_text(encoding="utf-8")
    ad = Ad()
    rep = _run(tmp_path, ad, apply=False)
    assert rep["plan"] == {PID: ["09708111"]} and ad.calls == []
    assert (d / "result.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "bak").exists()


def test_apply_backs_up_first_and_admits_a_passing_case_with_header_and_milestones(tmp_path):
    d = _cache(tmp_path / "cache")
    ad = Ad()
    rep = _run(tmp_path, ad, apply=True)
    assert rep["admitted"] == {PID: ["09708111"]} and rep["written"] == [PID]
    assert ad.calls == ["09708111"]
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert saved["city_case_ids"] == ["09902263", "09708111"]
    assert saved["case_milestones"]["09708111"] == {"申請計畫日期": "2008/08/18"}
    assert saved["case_headers"]["09708111"]["NAME"] == "事業計畫階段─實施者自行撤回"
    assert saved["case_case_names"]["09708111"] == N13
    assert set(saved["search_rejected"]) == {"09708111", "09708112"}   # left as recorded
    bak = json.loads((tmp_path / "bak" / PID / "result.json").read_text(encoding="utf-8"))
    assert bak["city_case_ids"] == ["09902263"]


def test_a_refused_name_is_left_in_search_rejected(tmp_path):
    d = _cache(tmp_path / "cache")
    _run(tmp_path, Ad(), apply=True)
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert "09708112" in saved["search_rejected"] and "09708112" not in saved["city_case_ids"]


def test_an_id_another_project_holds_is_left_alone(tmp_path):
    _cache(tmp_path / "cache")
    _cache(tmp_path / "cache", pid="乙-1", land_core="y", own_parcels=[], own_counts=[],
           city_case_ids=["09708111"], search_rejected={})
    rep = _run(tmp_path, Ad(), projects={PID: PROJECT, "乙-1": {"project_id": "乙-1"}},
               apply=False)
    assert rep["plan"] == {}


def test_an_id_the_project_recorded_as_view_rejected_is_left_alone(tmp_path):
    _cache(tmp_path / "cache", view_rejected={"09708111": {"shape": "A"}})
    assert _run(tmp_path, Ad(), apply=False)["plan"] == {}


def test_a_second_run_changes_nothing_and_issues_no_request(tmp_path):
    _cache(tmp_path / "cache")
    _run(tmp_path, Ad(), apply=True)
    ad = Ad()
    rep = _run(tmp_path, ad, apply=True)
    assert rep["admitted"] == {} and rep["written"] == [] and ad.calls == []


def test_a_cache_with_no_payload_project_is_named_and_skipped(tmp_path):
    _cache(tmp_path / "cache", pid="丙")
    rep = _run(tmp_path, Ad(), apply=True)
    assert rep["no_project"] == ["丙"] and rep["admitted"] == {}


def test_the_lock_refuses_a_second_writer(tmp_path):
    _cache(tmp_path / "cache")
    payload = tmp_path / "projects.json"
    payload.write_text(json.dumps({"projects": [PROJECT]}), encoding="utf-8")
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    try:
        rc = ac.main(["--cache", str(tmp_path / "cache"), "--payload", str(payload),
                      "--apply"])
    finally:
        lock.release()
    assert rc == 5
