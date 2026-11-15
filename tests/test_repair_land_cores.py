# -*- coding: utf-8 -*-
"""scripts/repair_land_cores.py and the live pin (F5, D5 = C part A).

docs/inspection-batchF.md F5: 3 of 675 caches hold a land_core that disagrees
with their project id's parts (大同區-市府段二小段-220-2 reads 中正區; two others
lack `地號等N筆`). The §8 gate decides a case by that field, so 09609301 was
refused by a district typo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import repair_land_cores as rl  # noqa: E402

PID = "大同區-市府段二小段-220-2地號等54筆"
GOOD = "大同區市府段二小段220-2地號等54筆"
BAD = "中正區市府段二小段220-2地號等54筆"


def _cache(root: Path, pid: str, core: str, **fields) -> Path:
    d = root / pid
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(
        {"project_id": pid, "land_core": core, **fields}, ensure_ascii=False),
        encoding="utf-8")
    return d


def test_the_expected_core_is_the_project_id_s_parts():
    assert rl.expected_core(PID) == GOOD
    assert rl.expected_core("松山區-寶清段一小段-51-13地號等1筆") == "松山區寶清段一小段51-13地號等1筆"


def test_an_id_that_is_not_a_unit_id_has_no_expected_core():
    for pid in ("大同區-市府段二小段-220-2地號等54筆-2", "未解析-1354",
                "內湖區-東湖段一小段-地號等?筆", "松山區-寶清段一小段-51-13地號等?筆"):
        assert rl.expected_core(pid) == "", pid


def test_a_dry_run_names_the_mismatch_and_writes_nothing(tmp_path):
    cache = tmp_path / "cache"
    d = _cache(cache, PID, BAD)
    before = (d / "result.json").read_text(encoding="utf-8")
    rep = rl.repair(cache, {PID: {}}, tmp_path / "bak", dry_run=True)
    assert rep["written"] == {PID: [BAD, GOOD]}
    assert (d / "result.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "bak").exists()


def test_a_real_run_rewrites_the_core_and_backs_up_the_pre_image(tmp_path):
    cache = tmp_path / "cache"
    d = _cache(cache, PID, BAD, city_case_ids=["09609301"])
    rep = rl.repair(cache, {PID: {}}, tmp_path / "bak")
    assert rep["written"] == {PID: [BAD, GOOD]}
    saved = json.loads((d / "result.json").read_text(encoding="utf-8"))
    assert saved["land_core"] == GOOD and saved["city_case_ids"] == ["09609301"]
    bak = json.loads((tmp_path / "bak" / PID / "result.json").read_text(encoding="utf-8"))
    assert bak["land_core"] == BAD


def test_a_missing_count_is_repaired_too(tmp_path):
    pid = "松山區-寶清段一小段-51-13地號等1筆"
    cache = tmp_path / "cache"
    d = _cache(cache, pid, "松山區寶清段一小段51-13")
    rl.repair(cache, {pid: {}}, tmp_path / "bak")
    assert json.loads((d / "result.json").read_text(encoding="utf-8"))["land_core"] \
        == "松山區寶清段一小段51-13地號等1筆"


def test_a_correct_core_is_untouched_and_a_second_run_changes_nothing(tmp_path):
    cache = tmp_path / "cache"
    _cache(cache, PID, BAD)
    rl.repair(cache, {PID: {}}, tmp_path / "bak1")
    rep = rl.repair(cache, {PID: {}}, tmp_path / "bak2")
    assert rep["written"] == {} and rep["unchanged"] == [PID]
    assert not (tmp_path / "bak2").exists()


def test_a_cache_with_no_payload_project_or_no_unit_id_is_named_and_skipped(tmp_path):
    cache = tmp_path / "cache"
    _cache(cache, "丙-1", "x")
    _cache(cache, "未解析-1354", "y")
    rep = rl.repair(cache, {"未解析-1354": {}}, tmp_path / "bak")
    assert rep["no_project"] == ["丙-1"] and rep["no_unit_id"] == ["未解析-1354"]
    assert rep["written"] == {}


# ── the live pin ──────────────────────────────────────────────────────────────

def test_every_payload_project_cache_land_core_equals_its_project_id_parts():
    """F5 live pin: 3 caches disagreed before the repair (市府220-2 read 中正區;
    寶清51-13 and 崇仁新村711-3 lacked 地號等N筆). A mismatch names the project."""
    cache = ROOT / "data" / ".link_cache"
    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    bad = {}
    for p in doc["projects"]:
        pid = p["project_id"]
        want = rl.expected_core(pid)
        rf = cache / pid / "result.json"
        if not want or not rf.is_file():
            continue
        have = json.loads(rf.read_text(encoding="utf-8")).get("land_core")
        if have != want:
            bad[pid] = [have, want]
    assert not bad, (f"{len(bad)} caches hold a land_core that differs from the "
                     f"project id's parts: {bad}. Run scripts/repair_land_cores.py.")
