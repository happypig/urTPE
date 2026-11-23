# -*- coding: utf-8 -*-
"""The whole-corpus refresh takes the single-writer lock, once per slice.

openspec change refresh-whole-corpus (archived 2026-11-04), design D1: "Slices under the
lock, a checkpoint between slices. Each slice: take the lock, refresh its projects, write
the checkpoint with the cache writes, release the lock." The script's docstring said the
same, and its test module's docstring said "under the single-writer lock". The code never
called the lock (measured 2026-11-23: `grep -i lock` finds only the docstring), so the
design decision was never implemented, and the widest cache writer in the repository, about
676 projects over many minutes, could run beside the nightly sweep or a CLI rebuild.

This file pins the design, not a new rule:

* each slice runs under `SingleWriterLock` over the tree that holds the cache;
* the checkpoint is written inside the lock, and the lock is released between slices, so
  the sweep or a rebuild can run in the gaps;
* on `LockHeld` the run stops with exit 5. The slice in hand writes nothing, and the
  checkpoint keeps the slices that finished, so a re-run resumes where this one stopped;
* `--dry-run` and a run with no slice left take no lock.

Every test replaces the slice refresh with a double. Nothing touches the network or `data/`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LOCK_NAME, LockHeld, SingleWriterLock  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "refresh_whole_corpus_lock_under_test", ROOT / "scripts" / "refresh_whole_corpus.py")
rwc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rwc)

PIDS = ["P1", "P2", "P3", "P4", "P5"]          # --slices-size 2 -> [P1 P2] [P3 P4] [P5]


@pytest.fixture
def env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    cache = data / ".link_cache"
    cache.mkdir(parents=True)
    payload = tmp_path / "projects.data.js"
    payload.write_text("window.PROJECTS = " + json.dumps(
        {"projects": [{"project_id": p} for p in PIDS]}) + ";", encoding="utf-8")

    state = {"data": data, "cache": cache, "payload": payload, "events": [],
             "slices": [], "lock_file_during": []}

    # main() imports load_search_keys from a sibling script at call time
    fake_awaiting = types.ModuleType("refresh_awaiting_caches")
    fake_awaiting.load_search_keys = lambda payload: {}
    monkeypatch.setitem(sys.modules, "refresh_awaiting_caches", fake_awaiting)

    def fake_slice(cache_dir, pids, search_keys, refresh_fn=None, page_fetch=None,
                   report=None, finished=None):
        state["events"].append("slice")
        state["slices"].append(list(pids))
        state["lock_file_during"].append((data / LOCK_NAME).exists())
        if finished is not None:
            finished.extend(pids)
        return report
    monkeypatch.setattr(rwc, "refresh_slice", fake_slice)

    real_checkpoint = rwc.write_checkpoint

    def recording_checkpoint(path, last_pid, finished):
        state["events"].append("checkpoint")
        real_checkpoint(path, last_pid, finished)
    monkeypatch.setattr(rwc, "write_checkpoint", recording_checkpoint)

    class RecordingLock(SingleWriterLock):
        """The real lock, plus the order in which it is taken and given back."""
        acquires = 0
        fail_on_acquire = None          # raise LockHeld on this (1-based) acquire

        def acquire(self):
            RecordingLock.acquires += 1
            if RecordingLock.fail_on_acquire == RecordingLock.acquires:
                raise LockHeld("held by another run (test)")
            super().acquire()
            state["events"].append("acquire")
            return self

        def release(self):
            super().release()
            state["events"].append("release")
    RecordingLock.acquires = 0
    RecordingLock.fail_on_acquire = None
    # raising=False: on the old script this name does not exist, and the tests must then
    # fail on what the script does, not on a missing attribute.
    monkeypatch.setattr(rwc, "SingleWriterLock", RecordingLock, raising=False)
    state["lock_cls"] = RecordingLock
    return state


def _run(env, *flags):
    return rwc.main(["--cache", str(env["cache"]), "--payload", str(env["payload"]),
                     "--slices-size", "2", *flags])


def _checkpoint(env):
    return rwc.read_checkpoint(env["cache"] / rwc.CHECKPOINT)


# --- every slice runs under the lock ---------------------------------------------

def test_a_held_lock_stops_the_run_before_any_slice(env):
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env)
    finally:
        holder.release()
    assert rc == 5                                   # the CLI's LockHeld code
    assert env["slices"] == []                       # no project refreshed
    assert not (env["cache"] / rwc.CHECKPOINT).exists()


def test_every_slice_runs_while_the_lock_is_held(env):
    assert _run(env) == 0
    assert env["slices"] == [["P1", "P2"], ["P3", "P4"], ["P5"]]
    assert env["lock_file_during"] == [True, True, True]


def test_the_lock_is_taken_and_given_back_once_per_slice(env):
    """Design D1: take, refresh, checkpoint, release. The gaps let other writers in."""
    assert _run(env) == 0
    assert env["events"] == ["acquire", "slice", "checkpoint", "release"] * 3


def test_the_lock_is_free_after_a_normal_run(env):
    assert _run(env) == 0
    SingleWriterLock(env["data"]).acquire().release()        # would raise LockHeld


def test_the_lock_is_released_when_a_slice_raises(env, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("city exploded")
    monkeypatch.setattr(rwc, "refresh_slice", boom)
    with pytest.raises(RuntimeError):
        _run(env)
    SingleWriterLock(env["data"]).acquire().release()


# --- a lock lost mid-run: stop, keep what finished, resume later -------------------------

def test_a_lock_lost_mid_run_stops_the_run_with_exit_5(env):
    env["lock_cls"].fail_on_acquire = 2              # the second slice finds a writer
    rc = _run(env)
    assert rc == 5
    assert env["slices"] == [["P1", "P2"]]           # the third slice never started


def test_the_checkpoint_keeps_only_the_slices_that_finished(env):
    env["lock_cls"].fail_on_acquire = 2
    _run(env)
    assert _checkpoint(env)["finished"] == ["P1", "P2"]


def test_a_rerun_resumes_after_the_slice_that_was_refused(env):
    env["lock_cls"].fail_on_acquire = 2
    assert _run(env) == 5
    env["lock_cls"].fail_on_acquire = None
    env["slices"].clear()
    assert _run(env) == 0
    assert env["slices"] == [["P3", "P4"], ["P5"]]   # P1 and P2 are not refreshed again


# --- no work, no lock -----------------------------------------------------------------

def test_a_dry_run_takes_no_lock(env):
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env, "--dry-run")
    finally:
        holder.release()
    assert rc == 0
    assert env["slices"] == []


def test_a_run_with_every_project_finished_takes_no_lock(env):
    rwc.write_checkpoint(env["cache"] / rwc.CHECKPOINT, "P5", list(PIDS))
    env["events"].clear()
    holder = SingleWriterLock(env["data"]).acquire()
    try:
        rc = _run(env)
    finally:
        holder.release()
    assert rc == 0                                   # nothing to do, so a held lock is no matter
    assert env["slices"] == []


def test_one_chosen_slice_takes_the_lock_once(env):
    assert _run(env, "--slice", "1") == 0
    assert env["slices"] == [["P3", "P4"]]
    assert env["events"] == ["acquire", "slice", "checkpoint", "release"]
