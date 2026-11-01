# -*- coding: utf-8 -*-
"""The lock acquire is atomic: O_CREAT|O_EXCL on the final path, no
tmp-and-replace race (P2.1). Two concurrent acquirers: exactly one wins, the
other gets LockHeld (exit 5), never a PermissionError crash."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.lock import LockHeld, SingleWriterLock  # noqa: E402


def test_two_concurrent_acquirers_yield_exactly_one_holder(tmp_path):
    results = []
    errors = []

    def worker():
        lock = SingleWriterLock(tmp_path)
        try:
            lock.acquire()
            results.append("held")
        except LockHeld:
            results.append("refused")
        except PermissionError as e:
            errors.append(f"crashed: {e}")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"no thread may crash with PermissionError: {errors}"
    assert results.count("held") == 1, (
        f"exactly one holder, got {results}")
    assert results.count("refused") == 7, results


def test_acquire_is_idempotent_for_the_holder(tmp_path):
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    try:
        lock.acquire()  # re-acquire by the holder must not raise
    finally:
        lock.release()
    assert not (lock.path.exists()), "release removes the file"


def test_a_dead_holder_is_reclaimable(tmp_path):
    import os
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    # simulate a dead holder: rewrite the file with a pid nothing owns
    import json
    lock.path.write_text(json.dumps({"pid": 999999999, "started_at": 0.0,
                                     "host": ""}), encoding="utf-8")
    second = SingleWriterLock(tmp_path)
    second.acquire()  # must not raise
    second.release()
