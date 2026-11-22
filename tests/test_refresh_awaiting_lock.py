# -*- coding: utf-8 -*-
"""A1 and A2 — the targeted refresh writes the durable cache, so it takes the lock.

Optimization board, Part I (U3, A1, A2). `scripts/refresh_awaiting_caches.py` re-fetches
the city's reply for every project whose cached case still awaits approval and rewrites
`data/.link_cache/<project>/result.json`. Its docstring asked the operator not to run it
beside an ingestion or a sweep, and nothing enforced that. Since A8 the nightly sweep holds
`SingleWriterLock` for hours, so an unlocked refresh started by hand could write the same
cache at the same time (the 2026-08-24 shape: four concurrent runs, 47 caches wiped).

A1: take `SingleWriterLock` over the tree that holds the cache; on `LockHeld`, write
nothing and return 5, the code `urtpe.cli` returns for the same refusal.

A2: select the candidates first, offline. A run with nothing to do needs no lock, so a
no-op never collides with the 02:00 sweep. "No candidates, no network" already held; what
is new is that it also takes no lock, and that the candidates are chosen again once the
lock is held, because another writer may have changed the cache while this run started.

Every test replaces the selector's inputs and `refresh_project` with doubles. Nothing
touches the network or the real `data/`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LOCK_NAME, SingleWriterLock  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "refresh_awaiting_under_test", ROOT / "scripts" / "refresh_awaiting_caches.py")
refresh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(refresh)

PID = "大安區-測試段一小段-1地號等3筆"


def _report(**extra):
    base = {"updated": [], "status_changes": [], "removed": [], "conflicts": [],
            "closed": [], "still_awaiting": [], "added": [], "superseded": [],
            "no_successor": [], "ambiguous": []}
    base.update(extra)
    return base


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A tree `tmp/data/.link_cache` whose parent is the lock root."""
    data = tmp_path / "data"
    cache = data / ".link_cache"
    cache.mkdir(parents=True)
    state = {"data": data, "cache": cache, "refreshed": [], "lock_during": [],
             "candidates": [[PID]]}

    monkeypatch.setattr(refresh, "load_search_keys",
                        lambda payload: {PID: ("測試段一小段", "1", "案")})

    def fake_select(cache_dir, payload_keys=None):
        seq = state["candidates"]
        return list(seq.pop(0) if len(seq) > 1 else seq[0])
    monkeypatch.setattr(refresh, "select_candidates", fake_select)

    def fake_refresh(cache_dir, pid, search_key=None):
        state["refreshed"].append(pid)
        state["lock_during"].append((data / LOCK_NAME).exists())
        return _report()
    monkeypatch.setattr(refresh, "refresh_project", fake_refresh)
    return state


def _run(env, *flags):
    return refresh.main(["--cache", str(env["cache"]),
                         "--payload", str(env["data"] / "none.js"), *flags])


# --- A1: the lock --------------------------------------------------------------

def test_a_held_lock_stops_the_run_before_any_refresh(env):
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env)
    finally:
        holder.release()
    assert rc == 5                       # the CLI's LockHeld code
    assert env["refreshed"] == []        # no city request, no cache write


def test_the_refresh_runs_while_the_lock_is_held(env):
    assert _run(env) == 0
    assert env["refreshed"] == [PID]
    assert env["lock_during"] == [True]


def test_the_lock_is_free_after_a_normal_run(env):
    assert _run(env) == 0
    SingleWriterLock(env["data"]).acquire().release()      # would raise LockHeld


def test_the_lock_is_released_when_a_refresh_raises(env, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("city exploded")
    monkeypatch.setattr(refresh, "refresh_project", boom)
    with pytest.raises(RuntimeError):
        _run(env)
    SingleWriterLock(env["data"]).acquire().release()


def test_a_dry_run_writes_nothing_so_it_takes_no_lock(env):
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env, "--dry-run")
    finally:
        holder.release()
    assert rc == 0
    assert env["refreshed"] == []


def test_a_failed_refresh_still_returns_one_under_the_lock(env, monkeypatch):
    monkeypatch.setattr(refresh, "refresh_project",
                        lambda *a, **k: {**_report(), "error": "reply unreadable"})
    assert _run(env) == 1


# --- A2: select first, offline; no work means no lock ---------------------------

def test_no_candidate_means_no_refresh_and_no_lock_attempt(env):
    env["candidates"] = [[]]
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env)
    finally:
        holder.release()
    assert rc == 0                       # a held lock does not matter: nothing to do
    assert env["refreshed"] == []


def test_no_candidate_leaves_no_lock_file_behind(env):
    env["candidates"] = [[]]
    assert _run(env) == 0
    assert not (env["data"] / LOCK_NAME).exists()


def test_candidates_are_chosen_again_once_the_lock_is_held(env):
    """Another writer closed the case between the first look and the lock."""
    env["candidates"] = [[PID], []]
    assert _run(env) == 0
    assert env["refreshed"] == []


def test_the_selection_report_prints_once(env, capsys):
    assert _run(env) == 0
    out = capsys.readouterr().out
    assert out.count("candidates (a case awaits approval)") == 1
