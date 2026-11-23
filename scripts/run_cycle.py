#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the PDF cycle: take a newly archived gazette to a checked emission, then stop.

openspec change a4-pdf-cycle-coordinator (optimization board, A4). The coordinator runs the
existing commands in one fixed order and adds no polling, ingest or refresh logic of its own:

    poll_gazette --json, poll_p168 --json, detect, ingest, refresh_awaiting_caches,
    rebuild (--from-js), post_ingest_check, pytest, viewer_smoke, publish_report.

The coordinator's own use of git is one read-only `git status`. After a FINISHED ingest it
records the hash as finished and then runs the existing `publish_release_diff.py` (design D13:
the operator amended U-D2 for the four generated pages only), which commits and pushes only
`docs/release-diff.html`, `docs/coverage-report.html`, `docs/domain-model.html` and
`docs/etl_process.html`, as one set. The emission itself (`data/`, `viewer/`, the other generated pages)
stays uncommitted for a person to review (A5). It never passes `--allow-reconcile-block` or
`--no-archive`, and stops at the first step that exits non-zero. A failed publication is its own
outcome, `publish_failed`: it never un-finishes the hash and never brings the ingest back.

The pure rules (which gazette to ingest, when to stop, what a record holds) are in
`urtpe/cycle.py`. This file is the adapters: the subprocess runner, a READ-ONLY `git status`,
the record store, the locks. Read `urtpe/cycle.py`'s docstring first.

Locks. The coordinator holds no lock over `data/` across its steps (the A8 lesson: a parent that
holds it makes the child CLI exit 5). It probes `data/` once before its first write step, and
each child then takes its own lock. A lock of its own over the ARCHIVE ROOT, a different
directory, keeps two cycles apart without ever blocking a child.

Exit codes: 0 finished, nothing to do, or already done; 1 a step failed, a hash awaits a
person's diagnosis, or the report publication failed; 2 bad usage; 5 a lock was held or another cycle was running; 6 refused
because an owned path has uncommitted changes. The record says the rest.

    python scripts/run_cycle.py [--dry-run] [--resume SHA256] [--archive-root PATH]

`--dry-run` runs only the two polls (with their own `--dry-run`), says what it would do, and
writes nothing. `--resume` restarts a stopped hash at its failed stage; polls are skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from urtpe import cycle  # noqa: E402
from urtpe.lock import LockHeld, SingleWriterLock  # noqa: E402

LOG_NAME = "cycle_log.jsonl"
STATE_NAME = "cycle_state.json"
PAYLOAD = ROOT / "viewer" / "projects.data.js"


@dataclass
class RunResult:
    """What a step returned. A timeout is exit 124 with `timed_out` set."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


@dataclass
class Options:
    dry_run: bool = False
    resume: str | None = None
    python: str = sys.executable
    archive_root: str | None = None


@dataclass
class Deps:
    """Every outward call. Tests replace them; `main()` builds the real ones."""

    runner: Callable[[list, int], RunResult]
    git_dirty: Callable[[tuple], list]
    store: "CycleStore"
    clock: Callable[[], datetime]
    list_archived: Callable[[], list]
    verify: Callable[[cycle.Archived], tuple]
    dataset_date: Callable[[], str]
    data_dir: Path
    archive_dir: Path
    status_page: Callable[[], None] | None = None


class CycleStore:
    """The operational record, in the archive root beside `poll_log.jsonl`: outside the repo,
    shared by every process that imports `urtpe`, and honoring `URTPE_ARCHIVE_ROOT`."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    @property
    def log_path(self) -> Path:
        return self.root / LOG_NAME

    @property
    def state_path(self) -> Path:
        return self.root / STATE_NAME

    def append(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_records(self) -> list[dict]:
        if not self.log_path.is_file():
            return []
        out = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue                     # a torn line must not hide the others
        return out

    def load_state(self) -> dict:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cycle.empty_state()
        if not isinstance(state, dict) or not isinstance(state.get("hashes"), dict):
            return cycle.empty_state()
        return state

    def save_state(self, state: dict) -> None:
        """Atomic: write beside the file, then replace. A failed write keeps the old state."""
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(STATE_NAME + ".tmp")
        try:
            tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.state_path)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise


def resolve_archive_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    return Path(DEFAULT_ARCHIVE_ROOT)


# --- the cycle ---------------------------------------------------------------------------------

def _poll_status(res: RunResult) -> tuple[str, bool]:
    """(status word, ok). A timeout and an unreadable result are failures, never 'nothing new'."""
    if res.timed_out:
        return "timeout", False
    try:
        body = json.loads(res.stdout)
        status = str(body["status"])
    except (ValueError, KeyError, TypeError):
        return "malformed", False
    return status, res.exit_code == 0


def run(opts: Options, deps: Deps) -> int:
    if opts.dry_run:
        return _dry_run(opts, deps)
    try:
        cycle_lock = SingleWriterLock(deps.archive_dir).acquire()
    except LockHeld as exc:
        return _finish(deps, {}, "another_cycle", reason="another cycle is running: %s" % exc)
    try:
        return _cycle(opts, deps)
    finally:
        cycle_lock.release()


def _now(deps: Deps) -> str:
    return deps.clock().isoformat(timespec="seconds")


def _finish(deps: Deps, polls: dict, outcome: str, **kw) -> int:
    """Append the record, refresh the status page (best effort), return the exit code."""
    record = cycle.make_record(_now(deps), polls, outcome, **kw)
    deps.store.append(record)
    print("cycle: %s%s" % (outcome, (" - " + record["reason"]) if record["reason"] else ""))
    if deps.status_page is not None:
        try:
            deps.status_page()
        except Exception as exc:  # noqa: BLE001 - the page must never change the cycle's result
            print("status page not written: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
    return cycle.exit_code_for(outcome)


def _cycle(opts: Options, deps: Deps) -> int:
    polls: dict = {}
    sha = gazette_id = ""
    current = ""                             # the step in hand, for an unexpected failure
    done = False                             # the ingest finished and the hash is recorded
    last_stage = ""
    state = deps.store.load_state()
    try:
        if opts.resume:
            try:
                gazette_id, start = cycle.resume_plan(state, opts.resume)
            except ValueError as exc:
                print("cannot resume: %s" % exc, file=sys.stderr)
                return cycle.EXIT_USAGE
            sha = opts.resume
            path = next((a.path for a in deps.list_archived() if a.sha256 == sha), "")
            cycle.mark_in_progress(state, sha, gazette_id, start, _now(deps))
            deps.store.save_state(state)
        else:
            for name, key in (("poll_gazette", "gazette"), ("poll_p168", "p168")):
                current = name
                step = next(s for s in cycle.build_steps(opts.python, archive_root=opts.archive_root)
                            if s.name == name)
                res = deps.runner(list(step.argv), step.timeout)
                status, ok = _poll_status(res)
                polls[key] = status
                if not ok:
                    return _finish(deps, polls, "stopped", failed_stage=name,
                                   last_stage=last_stage, exit_code=res.exit_code or 1,
                                   reason="%s: %s" % (name, status))
                last_stage = name
            current = "detect"
            det = cycle.pick_candidate(deps.list_archived(), deps.dataset_date(), state, deps.verify)
            if det.kind == "none":
                return _finish(deps, polls, "nothing_new", last_stage="detect")
            sha, gazette_id, path = det.sha256, det.gazette_id, det.path
            if det.kind == "already_done":
                return _finish(deps, polls, "already_done", sha256=sha, gazette_id=gazette_id,
                               last_stage="detect", reason="this hash already finished a cycle")
            if det.kind == "awaiting_diagnosis":
                return _finish(deps, polls, "awaiting_diagnosis", sha256=sha, gazette_id=gazette_id,
                               last_stage="detect", failed_stage=det.stage, reason=det.reason)
            if det.kind == "unverified":
                cycle.mark_stopped(state, sha, gazette_id, "detect", cycle.EXIT_FAILED, _now(deps))
                deps.store.save_state(state)
                return _finish(deps, polls, "refused", sha256=sha, gazette_id=gazette_id,
                               last_stage="detect", failed_stage="detect", reason=det.reason)
            start = "ingest" if det.kind == "candidate" else det.stage
            last_stage = "detect"

        steps = {s.name: s for s in cycle.build_steps(opts.python, pdf=path or "<pdf>",
                                                      archive_root=opts.archive_root)}
        order = [n for n in cycle.STEP_ORDER if n not in ("poll_gazette", "poll_p168", "detect")]
        # the report publication is not tracked as progress: it follows the finished mark
        run_steps = [n for n in order[order.index(start):] if n != "publish_report"]

        # Before the first step that writes: the dirty-tree check (only when the cycle starts
        # fresh at the ingest; past it the dirt is this cycle's own), then the lock probe.
        if start == "ingest":
            dirty = deps.git_dirty(cycle.OWNED_PATHS)
            if cycle.dirty_decision(True, dirty) == "refuse":
                return _finish(deps, polls, "dirty_tree", sha256=sha, gazette_id=gazette_id,
                               last_stage=last_stage,
                               reason="uncommitted changes in owned paths: " + ", ".join(dirty))
        if steps[start].writes:
            try:
                probe = SingleWriterLock(deps.data_dir).acquire()
                probe.release()
            except LockHeld as exc:
                return _finish(deps, polls, "locked", sha256=sha, gazette_id=gazette_id,
                               last_stage=last_stage, failed_stage=start,
                               exit_code=cycle.EXIT_LOCKED,
                               reason="a writer holds the lock over data/: %s" % exc)

        cycle.mark_in_progress(state, sha, gazette_id, start, _now(deps))
        deps.store.save_state(state)

        for name in run_steps:
            current = name
            step = steps[name]
            print("cycle: %s" % name, flush=True)
            res = deps.runner(list(step.argv), step.timeout)
            kind = cycle.classify_exit(name, res.exit_code, res.timed_out)
            if kind == "ok":
                nxt = cycle.next_step_after(name)
                if nxt is not None and nxt != "publish_report":
                    cycle.mark_in_progress(state, sha, gazette_id, nxt, _now(deps))
                    deps.store.save_state(state)
                last_stage = name
                continue
            if kind == "transient":
                # Another writer took the lock after the last step. Keep the hash at THIS stage
                # so the next run resumes here (the ingest has already moved the dataset).
                cycle.mark_in_progress(state, sha, gazette_id, name, _now(deps))
                deps.store.save_state(state)
                return _finish(deps, polls, "locked", sha256=sha, gazette_id=gazette_id,
                               last_stage=last_stage, failed_stage=name, exit_code=res.exit_code,
                               reason="%s exited %s: a lock was held" % (name, res.exit_code))
            cycle.mark_stopped(state, sha, gazette_id, name, res.exit_code, _now(deps))
            deps.store.save_state(state)
            refused = name == "ingest" and res.exit_code in (2, 3, 4)
            return _finish(deps, polls, "refused" if refused else "stopped", sha256=sha,
                           gazette_id=gazette_id, last_stage=last_stage, failed_stage=name,
                           exit_code=res.exit_code,
                           reason=("%s timed out" % name) if res.timed_out
                           else "%s exited %s" % (name, res.exit_code))

        # Finished FIRST, then published: a failed push must never bring the ingest back.
        cycle.mark_finished(state, sha, gazette_id, _now(deps))
        deps.store.save_state(state)
        done = True
        current = "publish_report"
        step = steps["publish_report"]
        print("cycle: publish_report", flush=True)
        res = deps.runner(list(step.argv), step.timeout)
        if cycle.classify_exit("publish_report", res.exit_code, res.timed_out) != "ok":
            return _finish(deps, polls, "publish_failed", sha256=sha, gazette_id=gazette_id,
                           last_stage=last_stage, failed_stage="publish_report",
                           exit_code=res.exit_code,
                           reason=("publish_report timed out" if res.timed_out
                                   else "publish_report exited %s" % res.exit_code))
        return _finish(deps, polls, "ingested", sha256=sha, gazette_id=gazette_id,
                       last_stage="publish_report")
    except Exception as exc:  # noqa: BLE001 - an unexpected failure is a recorded stop, not a traceback
        if done:       # the ingest finished; only the report publication failed
            return _finish(deps, polls, "publish_failed", sha256=sha, gazette_id=gazette_id,
                           last_stage=last_stage, failed_stage="publish_report",
                           exit_code=cycle.EXIT_FAILED,
                           reason="%s: %s (during publish_report)" % (type(exc).__name__, exc))
        if sha and current in cycle.STEP_ORDER:
            try:
                cycle.mark_stopped(state, sha, gazette_id, current, cycle.EXIT_FAILED, _now(deps))
                deps.store.save_state(state)
            except Exception:  # noqa: BLE001
                pass
        return _finish(deps, polls, "stopped", sha256=sha, gazette_id=gazette_id,
                       last_stage=last_stage, failed_stage="internal", exit_code=cycle.EXIT_FAILED,
                       reason="%s: %s (during %s)" % (type(exc).__name__, exc, current or "start"))


def _dry_run(opts: Options, deps: Deps) -> int:
    """Read-only: the two polls with their own --dry-run, then say what a real run would do.
    Writes no record, no archive file and nothing under the emitted tree."""
    polls = {}
    failed = False
    for name, key in (("poll_gazette", "gazette"), ("poll_p168", "p168")):
        step = next(s for s in cycle.build_steps(opts.python, dry_run=True,
                                                 archive_root=opts.archive_root) if s.name == name)
        res = deps.runner(list(step.argv), step.timeout)
        status, ok = _poll_status(res)
        polls[key] = status
        print("dry run: %s -> %s" % (name, status))
        failed = failed or not ok
    state = deps.store.load_state()
    det = cycle.pick_candidate(deps.list_archived(), deps.dataset_date(), state, deps.verify)
    if det.kind == "none":
        print("dry run: nothing to ingest: no archived gazette is newer than the dataset")
    elif det.kind in ("candidate", "resume"):
        start = "ingest" if det.kind == "candidate" else det.stage
        order = [n for n in cycle.STEP_ORDER if n not in ("poll_gazette", "poll_p168", "detect")]
        print("dry run: would %s gazette %s (%s), starting at %s" %
              ("ingest" if det.kind == "candidate" else "resume", det.gazette_id, det.sha256[:12], start))
        print("dry run: steps: " + ", ".join(order[order.index(start):])
              + "; the last step publishes the four generated pages, and the emission stays "
              "uncommitted for you to review")
        if start == "ingest":
            dirty = deps.git_dirty(cycle.OWNED_PATHS)
            if cycle.dirty_decision(True, dirty) == "refuse":
                print("dry run: it would be REFUSED: uncommitted changes in " + ", ".join(dirty))
    else:
        print("dry run: %s for %s %s" % (det.kind, det.gazette_id, det.reason))
    return cycle.EXIT_FAILED if failed else cycle.EXIT_OK


# --- the real adapters --------------------------------------------------------------------------

def _real_runner(argv: list, timeout: int) -> RunResult:
    try:
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        return RunResult(124, stdout=out, timed_out=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    return RunResult(proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _real_git_dirty(paths: tuple) -> list:
    """READ-ONLY: `git status --porcelain` over the owned paths. This is the only git command."""
    proc = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError("git status failed: %s" % proc.stderr.strip())
    return [line[3:].strip().strip('"') for line in proc.stdout.splitlines() if line.strip()]


def _dataset_date() -> str:
    head = PAYLOAD.read_text(encoding="utf-8")[:8192]
    return cycle.parse_published_date(head)


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true",
                       help="run only the two polls (read-only), say what would happen, write nothing")
    group.add_argument("--resume", metavar="SHA256", default=None,
                       help="restart a stopped gazette at its failed stage")
    ap.add_argument("--archive-root", default=None,
                    help="archive directory (default: the configured archive root)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    root = resolve_archive_root(args.archive_root)
    from urtpe.archive import GazetteArchive
    archive = GazetteArchive(root)

    def list_archived():
        out = []
        for gid in archive.archived_ids():
            path = archive.path_of(gid)
            shas = [e.sha256 for e in archive.entries() if e.gazette_id == gid and e.sha256]
            out.append(cycle.Archived(gid, shas[-1] if shas else "", str(path) if path else ""))
        return out

    def verify(a):
        try:
            archive.assert_matches_entry(a.path, a.gazette_id)
            return True, ""
        except (FileNotFoundError, KeyError, ValueError) as exc:
            return False, str(exc)

    status_page = None
    try:
        import cycle_status                                   # optional: the status page can be cut
        status_page = lambda: cycle_status.write_page(root)   # noqa: E731
    except ImportError:
        pass

    deps = Deps(runner=_real_runner, git_dirty=_real_git_dirty, store=CycleStore(root),
                clock=lambda: datetime.now().astimezone(), list_archived=list_archived,
                verify=verify, dataset_date=_dataset_date, data_dir=ROOT / "data",
                archive_dir=root, status_page=status_page)
    return run(Options(dry_run=args.dry_run, resume=args.resume, python=sys.executable,
                       archive_root=args.archive_root), deps)


if __name__ == "__main__":
    raise SystemExit(main())
