"""Single-writer lock for pipeline runs.

The 2026-08-24 incident: four concurrent runs each treated a partially-populated
cache as authoritative and 47 project caches were wiped. The rule that prevents a
recurrence is structural rather than advisory — one run at a time per output tree.

The lock is a file holding the writer's pid and start time. A lock whose holder is
gone, or whose start is older than ``stale_after``, is reclaimable, because a
crashed run must not block the next one forever. The lock covers every path a run
mutates, including the gazette archive and the correction ledger, which is why it
is taken before the first read as well as before the first write.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

LOCK_NAME = ".pipeline.lock"


class LockHeld(RuntimeError):
    """Another run holds the lock for this output tree."""


@dataclass
class LockInfo:
    pid: int
    started_at: float
    host: str = ""

    def age(self) -> float:
        return time.time() - self.started_at


class SingleWriterLock:
    """Exclusive, stale-reclaimable lock over one output tree."""

    def __init__(self, root: Path | str, *, stale_after: float = 6 * 3600.0,
                 name: str = LOCK_NAME):
        self.root = Path(root)
        self.path = self.root / name
        self.stale_after = stale_after
        self._held = False

    def _read(self) -> LockInfo | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return LockInfo(pid=int(data["pid"]), started_at=float(data["started_at"]),
                            host=str(data.get("host", "")))
        except (KeyError, TypeError, ValueError):
            return None

    def _alive(self, info: LockInfo) -> bool:
        if info.host and info.host != _hostname():
            # Another machine's lock; we cannot judge its liveness, so respect it
            # until it goes stale rather than stealing it.
            return info.age() < self.stale_after
        if info.age() >= self.stale_after:
            return False
        return _process_alive(info.pid)

    def acquire(self) -> "SingleWriterLock":
        self.root.mkdir(parents=True, exist_ok=True)
        existing = self._read()
        if existing is not None and self._alive(existing):
            raise LockHeld(
                f"another run holds {self.path} "
                f"(pid {existing.pid} on {existing.host or 'this host'}, "
                f"{existing.age() / 60:.0f} min old). "
                "The single-writer rule forbids concurrent runs over one output tree.")
        # Write atomically so a crash mid-write cannot leave a half-parsed lock.
        tmp = self.path.with_suffix(".lock.part")
        tmp.write_text(json.dumps({"pid": os.getpid(), "started_at": time.time(),
                                   "host": _hostname()}), encoding="utf-8")
        os.replace(tmp, self.path)
        self._held = True
        return self

    def release(self) -> None:
        if not self._held:
            return
        try:
            self.path.unlink()
        except OSError:
            pass
        self._held = False

    def __enter__(self) -> "SingleWriterLock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()


def _hostname() -> str:
    import socket

    try:
        return socket.gethostname()
    except OSError:
        return ""


def _process_alive(pid: int) -> bool:
    """Whether ``pid`` names a live process, without signalling it.

    ``os.kill(pid, 0)`` is the POSIX idiom but is unsafe on Windows, where CPython
    implements it as ``TerminateProcess(handle, 0)`` — a zero-signal probe would
    *kill* the holder. The Windows path therefore opens a query handle instead.
    """
    import sys

    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True