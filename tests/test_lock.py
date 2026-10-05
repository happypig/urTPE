"""Single-writer lock tests.

Task 11.5 of robust-gazette-ingestion. The 2026-08-24 incident wiped 47 project
caches because four runs wrote concurrently; the rule is enforced structurally here.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from urtpe import cli
from urtpe.lock import LockHeld, LockInfo, SingleWriterLock
from tests.gazette_fixtures import ROC_ROWS, write_gazette


def test_lock_is_acquirable_and_released(tmp_path):
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    assert lock.path.exists()
    lock.release()
    assert not lock.path.exists()


def test_second_acquisition_is_refused(tmp_path):
    first = SingleWriterLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(LockHeld):
            SingleWriterLock(tmp_path).acquire()
    finally:
        first.release()


def test_context_manager_releases_on_error(tmp_path):
    with pytest.raises(RuntimeError):
        with SingleWriterLock(tmp_path):
            raise RuntimeError("boom")
    assert not SingleWriterLock(tmp_path).path.exists()


def test_lock_from_a_dead_process_is_reclaimed(tmp_path):
    """A crashed run must not block the next one forever."""
    from urtpe.lock import _hostname, _process_alive

    lock = SingleWriterLock(tmp_path)
    lock.root.mkdir(parents=True, exist_ok=True)
    lock.path.write_text(json.dumps({"pid": 999_999_999, "started_at": time.time(),
                                     "host": _hostname()}), encoding="utf-8")
    lock.acquire()
    assert lock._held


def test_process_probe_does_not_kill_the_probee(tmp_path):
    """A liveness probe must never signal the process it inspects.

    `os.kill(pid, 0)` is the POSIX idiom but on Windows CPython implements it as
    TerminateProcess(handle, 0), which would kill the holder — including pytest
    itself when the holder is this process.
    """
    import subprocess
    import sys

    from urtpe.lock import _process_alive

    code = "import time,sys; sys.stdout.write('up'); sys.stdout.flush(); time.sleep(30)"
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE)
    try:
        assert proc.stdout is not None
        assert proc.stdout.read(2) == b"up"
        assert _process_alive(proc.pid) is True
        assert proc.poll() is None, "the probe must not have terminated the process"
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_process_probe_reports_a_dead_pid():
    from urtpe.lock import _process_alive

    assert _process_alive(999_999_999) is False
    assert _process_alive(0) is False
    assert _process_alive(-1) is False


def test_lock_older_than_stale_after_is_reclaimed(tmp_path):
    lock = SingleWriterLock(tmp_path, stale_after=1.0)
    lock.root.mkdir(parents=True, exist_ok=True)
    lock.path.write_text(json.dumps({"pid": os.getpid(), "started_at": time.time() - 10,
                                     "host": ""}), encoding="utf-8")
    lock.acquire()
    assert lock._held


def test_corrupt_lock_file_is_reclaimed(tmp_path):
    lock = SingleWriterLock(tmp_path)
    lock.root.mkdir(parents=True, exist_ok=True)
    lock.path.write_text("{garbage", encoding="utf-8")
    lock.acquire()
    assert lock._held


def test_foreign_host_lock_is_respected_until_stale(tmp_path):
    lock = SingleWriterLock(tmp_path, stale_after=3600.0)
    lock.root.mkdir(parents=True, exist_ok=True)
    lock.path.write_text(json.dumps({"pid": 4242, "started_at": time.time(),
                                     "host": "some-other-machine"}), encoding="utf-8")
    with pytest.raises(LockHeld):
        lock.acquire()


def test_cli_refuses_a_concurrent_run_and_writes_nothing(tmp_path):
    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()

    held = SingleWriterLock(out)
    held.acquire()
    try:
        assert cli.main([str(pdf), "-o", str(out)]) == 5
        assert not (out / "raw.tsv").exists()
        assert not (out / "projects.json").exists()
    finally:
        held.release()

    # With the lock released the same run succeeds.
    assert cli.main([str(pdf), "-o", str(out)]) == 0
    assert (out / "projects.json").exists()


def test_lock_records_the_writing_process(tmp_path):
    lock = SingleWriterLock(tmp_path)
    lock.acquire()
    info = json.loads(lock.path.read_text(encoding="utf-8"))
    assert info["pid"] == os.getpid()
    assert info["started_at"] > 0
    lock.release()


def test_lock_info_age_is_monotonic(tmp_path):
    info = LockInfo(pid=1, started_at=time.time() - 60)
    assert info.age() >= 60