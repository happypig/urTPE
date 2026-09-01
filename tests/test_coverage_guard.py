"""BDD scenarios for the coverage regression guard (§12 #1, §18 rule 3)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from urtpe.coverage import CoverageRegression, coverage_guard, diff, snapshot

PIDS = ["甲區-某段-1地號等1筆", "乙區-某段-2地號等1筆", "丙區-某段-3地號等1筆"]


def _make_cache(root: Path, pid: str, *, status="resolved", twur=True, ulic=False):
    safe = re.sub(r"[^\w\-]", "_", pid)
    d = root / safe
    d.mkdir(parents=True, exist_ok=True)
    nm = {"使用核發日期": "113.01.01"} if ulic else {}
    (d / "result.json").write_text(json.dumps({
        "project_id": pid,
        "status": status,
        "twur_url": f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/{pid}" if twur else "",
        "national_milestones": nm,
    }, ensure_ascii=False), encoding="utf-8")


def _seed(root):
    _make_cache(root, PIDS[0], twur=True, ulic=True)   # fully resolved
    _make_cache(root, PIDS[1], twur=True)              # resolved, no occupancy
    _make_cache(root, PIDS[2], status="unresolved", twur=False)  # bare


class TestSnapshot:
    def test_counts_flags_per_project(self, tmp_path):
        _seed(tmp_path)
        snap = snapshot(tmp_path, PIDS)
        assert snap[PIDS[0]] == {"resolved": True, "twur": True, "national": True, "ulic": True}
        assert snap[PIDS[1]] == {"resolved": True, "twur": True, "national": False, "ulic": False}
        assert snap[PIDS[2]] == {"resolved": False, "twur": False, "national": False, "ulic": False}


class TestDiff:
    def test_monotonic_job_has_no_regressions(self, tmp_path):
        _seed(tmp_path)
        before = snapshot(tmp_path, PIDS)
        _make_cache(tmp_path, PIDS[2], status="resolved", twur=True, ulic=True)  # job improves
        after = snapshot(tmp_path, PIDS)
        d = diff(before, after)
        assert d["regressions"] == {}
        assert d["gained"] == []

    def test_wipe_detected_on_shared_pid(self, tmp_path):
        _seed(tmp_path)
        before = snapshot(tmp_path, PIDS)
        _make_cache(tmp_path, PIDS[0], twur=False)  # the wipe
        d = diff(before, snapshot(tmp_path, PIDS))
        assert d["regressions"] == {PIDS[0]: ["twur", "national", "ulic"]}

    def test_family_merge_lost_pid_not_a_regression(self, tmp_path):
        """崇仁新村-shape: 未解析-1354 folds into the family; flags on the
        surviving pid unchanged — lost pid is reported, not raised."""
        merge_pids = ["未解析-1354", "萬華區-崇仁新村青年段一小段-711-3地號等2筆"]
        _make_cache(tmp_path, "未解析-1354", twur=True, ulic=True)
        _make_cache(tmp_path, "萬華區-崇仁新村青年段一小段-711-3地號等2筆", twur=True, ulic=True)
        before = snapshot(tmp_path, merge_pids)
        after = snapshot(tmp_path, merge_pids[1:])  # merge removes the folded id
        d = diff(before, after)
        assert d["regressions"] == {}
        assert d["lost"] == ["未解析-1354"]


class TestGuard:
    def test_monotonic_job_passes(self, tmp_path):
        _seed(tmp_path)
        with coverage_guard(tmp_path, PIDS) as result:
            _make_cache(tmp_path, PIDS[2], status="resolved", twur=True)  # job
        assert result["diff"]["regressions"] == {}

    def test_wipe_raises_with_pid_and_flag(self, tmp_path):
        _seed(tmp_path)
        with pytest.raises(CoverageRegression) as ei:
            with coverage_guard(tmp_path, PIDS):
                _make_cache(tmp_path, PIDS[0], twur=False)  # job wipes
        assert PIDS[0] in str(ei.value) and "twur" in str(ei.value)

    def test_strict_false_collects_without_raising(self, tmp_path):
        _seed(tmp_path)
        with coverage_guard(tmp_path, PIDS, strict=False) as result:
            _make_cache(tmp_path, PIDS[0], twur=False)
        assert result["diff"]["regressions"] == {PIDS[0]: ["twur", "national", "ulic"]}

    def test_alert_trail_written_only_on_regression(self, tmp_path):
        _seed(tmp_path)
        alert = tmp_path / "coverage_alerts.jsonl"
        with coverage_guard(tmp_path, PIDS, alert_path=alert):
            pass  # clean job
        assert not alert.exists()
        with pytest.raises(CoverageRegression):
            with coverage_guard(tmp_path, PIDS, alert_path=alert):
                _make_cache(tmp_path, PIDS[1], twur=False)
        lines = alert.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1 and PIDS[1] in lines[0]
