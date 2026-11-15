# -*- coding: utf-8 -*-
"""scripts/walk_unit_siblings.py (unit-sibling-id-walk 1.5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import walk_unit_siblings as ws  # noqa: E402
from urtpe.lock import SingleWriterLock  # noqa: E402

PID = "大安區-懷生段二小段-16地號等8筆"
CORE = "大安區懷生段二小段16地號等8筆"
SIB = "擬訂臺北市大安區懷生段二小段16地號等8筆土地都市更新事業計畫案-A區"
PROJECT = {"project_id": PID, "anchor_recno": 1,
           "nodes": [{"recno": 1, "first_parcel": "16", "parcels": ["16", "17", "18"]}]}


def _cache(root: Path, ids=("09503200", "09503204")) -> Path:
    d = root / PID
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(
        {"project_id": PID, "land_core": CORE, "own_parcels": ["16", "17", "18"],
         "city_case_ids": list(ids)}, ensure_ascii=False), encoding="utf-8")
    return d


class Adapters:
    def __init__(self):
        self.calls = []

    def header(self, cid):
        self.calls.append(cid)
        if cid == "09503202":
            return {"CASE_NAME": SIB, "NAME": "事業計畫階段─業經本府核定",
                    "uro_chk_date": "2006/03/20"}
        return {}

    def milestones(self, cid):
        return {"核定日期": "2006/03/20"}


def _run(tmp_path, ad, **kw):
    return ws.run(tmp_path / "cache", {PID: PROJECT}, tmp_path / "bak",
                  fetch_header=ad.header, fetch_milestones=ad.milestones,
                  sleep=lambda s: None, **kw)


def test_a_dry_run_issues_no_request_and_writes_nothing(tmp_path):
    d = _cache(tmp_path / "cache")
    before = (d / "result.json").read_text(encoding="utf-8")
    ad = Adapters()
    rep = _run(tmp_path, ad, apply=False)
    assert ad.calls == []
    assert rep["plan"] == {PID: ["09503201", "09503202", "09503203"]}
    assert (d / "result.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "bak").exists()


def test_apply_backs_up_first_writes_and_a_second_apply_changes_nothing(tmp_path):
    d = _cache(tmp_path / "cache")
    rep = _run(tmp_path, Adapters(), apply=True)
    assert rep["written"] == [PID] and rep["added"] == {PID: ["09503202"]}
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert "09503202" in saved["city_case_ids"]
    assert set(saved["sibling_probed"]) == {"09503201", "09503203"}
    bak = json.loads((tmp_path / "bak" / PID / "result.json").read_text(encoding="utf-8"))
    assert "sibling_probed" not in bak and "09503202" not in bak["city_case_ids"]
    ad = Adapters()
    again = _run(tmp_path, ad, apply=True)
    assert ad.calls == [] and again["written"] == []


def test_a_cache_with_no_project_in_the_payload_is_named_and_skipped(tmp_path):
    root = tmp_path / "cache"
    other = root / "丙"
    other.mkdir(parents=True)
    (other / "result.json").write_text(json.dumps(
        {"project_id": "丙", "land_core": "x", "city_case_ids": ["09100000", "09100004"]}),
        encoding="utf-8")
    ad = Adapters()
    rep = _run(tmp_path, ad, apply=True)
    assert rep["no_project"] == ["丙"] and ad.calls == []


def test_an_id_another_project_holds_is_not_probed(tmp_path):
    _cache(tmp_path / "cache")
    other = tmp_path / "cache" / "乙-1"
    other.mkdir()
    (other / "result.json").write_text(json.dumps(
        {"project_id": "乙-1", "land_core": "y", "city_case_ids": ["09503202"]}),
        encoding="utf-8")
    ad = Adapters()
    rep = ws.run(tmp_path / "cache", {PID: PROJECT, "乙-1": {**PROJECT, "project_id": "乙-1"}},
                 tmp_path / "bak", fetch_header=ad.header, fetch_milestones=ad.milestones,
                 sleep=lambda s: None, apply=False)
    assert "09503202" not in rep["plan"][PID]


def test_the_lock_refuses_a_second_writer(tmp_path):
    _cache(tmp_path / "cache")
    payload = tmp_path / "projects.json"
    payload.write_text(json.dumps({"projects": [PROJECT]}), encoding="utf-8")
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    try:
        rc = ws.main(["--cache", str(tmp_path / "cache"), "--payload", str(payload),
                      "--apply"])
    finally:
        lock.release()
    assert rc == 5
