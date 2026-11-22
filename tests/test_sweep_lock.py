# -*- coding: utf-8 -*-
"""A8 — the nightly national-portal sweep is an unattended writer.

Optimization board, Part I, U9 (2026-11-22). Four measured gaps:

1. The crawl writes ``data/.link_cache/`` for hours and holds no lock. Only its child
   ``urtpe.cli`` takes ``SingleWriterLock`` over ``data`` (``urtpe/cli.py:567``).
2. A parent that kept the lock through the rebuild would make the child exit 5
   (``LockHeld``), so the sweep must release the lock before the rebuild.
3. A run that updated no project still rebuilt the payload.
4. The rebuild result never reached the exit code, so a failed rebuild showed as
   ``Last Result 0``.

The sweep calls the real network and the real cache in production. Every test here
redirects the cwd and the lock root into ``tmp_path`` and replaces the network, the
cache writer and the rebuild with doubles. Nothing touches ``data/``.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LOCK_NAME, SingleWriterLock  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "sweep_lock_under_test", ROOT / "scripts" / "fetch_remaining_national_portal.py")
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)


def _cand(pid="大安區-測試段一小段-1地號等3筆"):
    return {"project_id": pid, "section": "測試段一小段", "parcel": "1",
            "count": "3", "current_date": "2026-11-01"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A sandbox: cwd, lock root, argv and every outward call are replaced."""
    monkeypatch.chdir(tmp_path)
    lock_root = tmp_path / "data"
    lock_root.mkdir()
    monkeypatch.setattr(sweep, "LOCK_ROOT", lock_root)
    monkeypatch.setattr(sys, "argv", ["sweep", "--deadline", "23:59"])
    state = {"rebuilds": 0, "lock_seen_during_rebuild": None,
             "crawled": 0, "rebuild_result": True}

    monkeypatch.setattr(sweep, "load_candidates", lambda *a, **k: [_cand()])

    def fake_find(section, parcel, count, max_probe=8):
        state["crawled"] += 1
        return ("v1", {"使照核發日期": "2026-01-01"}, [], "<html>", ["v1"],
                sweep.OUTCOME_MATCH)
    monkeypatch.setattr(sweep, "find_matching_view_with_outcome", fake_find)
    monkeypatch.setattr(sweep, "update_project_cache", lambda *a, **k: True)

    def fake_regen():
        state["rebuilds"] += 1
        state["lock_seen_during_rebuild"] = (lock_root / LOCK_NAME).exists()
        return state["rebuild_result"]
    monkeypatch.setattr(sweep, "regenerate_viewer", fake_regen)
    state["lock_root"] = lock_root
    state["tmp"] = tmp_path
    return state


def _miss(monkeypatch, state):
    def fake_find(section, parcel, count, max_probe=8):
        state["crawled"] += 1
        return ("", {}, [], "", ["v1"], sweep.OUTCOME_MISS)
    monkeypatch.setattr(sweep, "find_matching_view_with_outcome", fake_find)


def _run_lines(state):
    log = state["tmp"] / "data" / ".link_cache" / "sweep_runs.jsonl"
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x]


# --- 1. the crawl takes the lock ---------------------------------------------

def test_a_held_lock_stops_the_run_before_any_read_or_write(env, monkeypatch):
    holder = SingleWriterLock(env["lock_root"]).acquire()
    try:
        called = []
        monkeypatch.setattr(sweep, "load_candidates",
                            lambda *a, **k: called.append("load") or [_cand()])
        rc = sweep.main()
    finally:
        holder.release()
    assert rc == 5                       # the CLI's LockHeld code
    assert called == []                  # no candidate read
    assert env["crawled"] == 0           # no portal request
    assert env["rebuilds"] == 0
    assert not (env["tmp"] / "data" / ".link_cache" / "no_match_ledger.json").exists()


def test_the_crawl_runs_while_the_lock_is_held(env, monkeypatch):
    seen = []

    def fake_find(section, parcel, count, max_probe=8):
        seen.append((env["lock_root"] / LOCK_NAME).exists())
        return ("", {}, [], "", ["v1"], sweep.OUTCOME_MISS)
    monkeypatch.setattr(sweep, "find_matching_view_with_outcome", fake_find)
    assert sweep.main() == 0
    assert seen == [True]


# --- 2. the lock is released before the rebuild ------------------------------

def test_the_lock_is_released_before_the_rebuild(env):
    assert sweep.main() == 0
    assert env["rebuilds"] == 1
    assert env["lock_seen_during_rebuild"] is False


def test_the_lock_is_free_after_a_normal_run(env):
    assert sweep.main() == 0
    SingleWriterLock(env["lock_root"]).acquire().release()   # would raise LockHeld


def test_the_lock_is_released_when_the_crawl_raises(env, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("portal exploded")
    monkeypatch.setattr(sweep, "find_matching_view_with_outcome", boom)
    with pytest.raises(RuntimeError):
        sweep.main()
    SingleWriterLock(env["lock_root"]).acquire().release()
    assert env["rebuilds"] == 0


# --- 3. no update, no rebuild --------------------------------------------------

def test_no_candidate_means_no_rebuild(env, monkeypatch):
    monkeypatch.setattr(sweep, "load_candidates", lambda *a, **k: [])
    assert sweep.main() == 0
    assert env["rebuilds"] == 0 and env["crawled"] == 0


def test_a_run_that_only_records_misses_does_not_rebuild(env, monkeypatch):
    _miss(monkeypatch, env)
    assert sweep.main() == 0
    assert env["crawled"] == 1
    assert env["rebuilds"] == 0
    # the miss still lands in the ledger: the 14-day exclusion depends on it
    ledger = json.loads((env["tmp"] / "data" / ".link_cache"
                         / "no_match_ledger.json").read_text(encoding="utf-8"))
    assert list(ledger) == [_cand()["project_id"]]


def test_a_failed_cache_write_does_not_rebuild(env, monkeypatch):
    monkeypatch.setattr(sweep, "update_project_cache", lambda *a, **k: False)
    assert sweep.main() == 0
    assert env["rebuilds"] == 0


def test_an_updated_project_rebuilds_exactly_once(env):
    assert sweep.main() == 0
    assert env["rebuilds"] == 1


# --- 4. a failed rebuild is a failed run -------------------------------------

def test_a_failed_rebuild_returns_a_nonzero_exit(env):
    env["rebuild_result"] = False
    assert sweep.main() != 0


def test_a_successful_rebuild_returns_zero(env):
    assert sweep.main() == 0


# --- 5. every run leaves one line of evidence ---------------------------------

def test_a_normal_run_logs_one_line(env):
    sweep.main()
    lines = _run_lines(env)
    assert len(lines) == 1
    assert lines[0]["status"] == "ok"
    assert lines[0]["updated"] == 1
    assert lines[0]["rebuild"] == "ok"
    assert "started_at" in lines[0]


def test_a_failed_rebuild_is_logged_as_failed(env):
    env["rebuild_result"] = False
    sweep.main()
    assert _run_lines(env)[-1]["rebuild"] == "failed"
    assert _run_lines(env)[-1]["status"] == "rebuild_failed"


def test_a_skipped_rebuild_is_logged_as_skipped(env, monkeypatch):
    _miss(monkeypatch, env)
    sweep.main()
    assert _run_lines(env)[-1]["rebuild"] == "skipped"
    assert _run_lines(env)[-1]["updated"] == 0


def test_a_held_lock_is_logged(env):
    holder = SingleWriterLock(env["lock_root"]).acquire()
    try:
        sweep.main()
    finally:
        holder.release()
    lines = _run_lines(env)
    assert len(lines) == 1 and lines[0]["status"] == "lock_held"


def test_a_no_candidate_run_is_logged(env, monkeypatch):
    monkeypatch.setattr(sweep, "load_candidates", lambda *a, **k: [])
    sweep.main()
    assert _run_lines(env)[-1]["status"] == "no_candidates"


def test_a_log_write_failure_never_changes_the_exit_code(env, monkeypatch):
    def deny(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(sweep, "_append_run_log", deny, raising=False)
    # whatever the helper does, a failing log write must not mask the real result
    assert sweep.main() == 0
