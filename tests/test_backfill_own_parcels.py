# -*- coding: utf-8 -*-
"""scripts/backfill_own_parcels.py (section8-gate-anchor-parcel-drift 3.1/3.2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import backfill_own_parcels as bf  # noqa: E402

PID = "萬華區-華中段一小段-247地號等26筆"
PROJECT = {"project_id": PID, "anchor_recno": 14,
           "nodes": [{"recno": 14, "first_parcel": "247",
                      "parcels": ["247", "248", "201-2", "352"]}]}


def _cache(root: Path, pid: str, **fields) -> Path:
    d = root / pid
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(
        {"project_id": pid, "land_core": "x", **fields}, ensure_ascii=False),
        encoding="utf-8")
    return d


def test_the_anchor_s_parcels_come_first_parcel_first():
    assert bf.anchor_parcels(PROJECT) == ["247", "248", "201-2", "352"]


def test_a_dry_run_writes_nothing(tmp_path):
    cache = tmp_path / "cache"
    d = _cache(cache, PID, view_rejected={"09305081": {"shape": "A"}})
    before = (d / "result.json").read_text(encoding="utf-8")
    rep = bf.backfill(cache, {PID: PROJECT}, tmp_path / "bak", dry_run=True)
    assert rep["written"] == [PID]
    assert (d / "result.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "bak").exists()


def test_a_real_run_writes_the_field_and_the_backup(tmp_path):
    cache = tmp_path / "cache"
    d = _cache(cache, PID, view_verified_case_ids=["09305081"])
    rep = bf.backfill(cache, {PID: PROJECT}, tmp_path / "bak")
    assert rep["written"] == [PID]
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert saved["own_parcels"] == ["247", "248", "201-2", "352"]
    bak = json.loads((tmp_path / "bak" / PID / "result.json").read_text(encoding="utf-8"))
    assert "own_parcels" not in bak          # the backup is the pre-image


def test_a_second_run_changes_nothing(tmp_path):
    cache = tmp_path / "cache"
    _cache(cache, PID, view_rejected={"09305081": {"shape": "A"}})
    bf.backfill(cache, {PID: PROJECT}, tmp_path / "bak1")
    rep = bf.backfill(cache, {PID: PROJECT}, tmp_path / "bak2")
    assert rep["written"] == [] and rep["unchanged"] == [PID]
    assert not (tmp_path / "bak2").exists()


def test_only_caches_that_hold_view_ids_are_touched(tmp_path):
    cache = tmp_path / "cache"
    other = _cache(cache, "乙", city_case_ids=["09100001"])
    before = (other / "result.json").read_text(encoding="utf-8")
    rep = bf.backfill(cache, {"乙": PROJECT}, tmp_path / "bak")
    assert rep["candidates"] == 0
    assert (other / "result.json").read_text(encoding="utf-8") == before


def test_a_cache_with_no_project_in_the_payload_is_named_and_skipped(tmp_path):
    cache = tmp_path / "cache"
    _cache(cache, "丙", view_rejected={"09100001": {"shape": "A"}})
    rep = bf.backfill(cache, {PID: PROJECT}, tmp_path / "bak")
    assert rep["no_project"] == ["丙"] and rep["written"] == []
