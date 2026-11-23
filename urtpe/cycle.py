"""The PDF-cycle coordinator's pure logic: no I/O.

openspec change a4-pdf-cycle-coordinator (optimization board, A4). The coordinator runs the
existing commands in one fixed order, stops at the first refusal, and records where it
stopped. This module holds the parts that need no disk, no clock and no process: the step
list as data, how a gazette to ingest is chosen, when a cycle stops, how the record changes,
which exit code a run returns. `scripts/run_cycle.py` supplies the adapters.

Three decisions are worth reading before changing anything here.

**The archive decides, not a status word.** `poll_gazette.py` reports `new_gazette` once:
the poll that archives a gazette updates the poller's state, so every later poll says
`unchanged`. Any poll can be that first one, including one started by hand (both real catches
so far were). A coordinator that waited for the word would archive a gazette and never ingest
it. So the gazette to ingest is chosen from the archive: the newest one that is newer than the
emitted dataset, whose file matches its archive entry, and that the record shows neither
finished nor stopped.

**A refusal waits for a person; a busy moment does not.** A non-zero exit is a refusal, not a
flake (AGENTS.md), so a hash that stopped at one is never retried by a later scheduled run. A
held lock (exit 5), a dirty tree and another running cycle are transient: the data was not
refused, only the moment.

**The report is published last, after the hash is finished** (design D13). The operator
amended U-D2 for the release-diff report only: the coordinator's own git use is read-only, but
after a finished ingest it runs the existing `publish_release_diff.py`. A failed push is its own
outcome and never brings the ingest back.

**Progress is kept after every step.** The ingest updates the dataset, so once it has run the
gazette no longer looks newer. If a later step then stops on a held lock, only a progress
entry can tell the next run to resume at that step rather than conclude there is nothing to do.

The record never keys on 編號, `recno` or `project_id`.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Callable, NamedTuple

STEP_ORDER = ("poll_gazette", "poll_p168", "detect", "ingest", "refresh", "rebuild",
              "post_ingest_check", "tests", "viewer_smoke", "publish_report")

#: The two flags that pass a refusal. No step may carry either (AGENTS.md: a non-zero exit is
#: a refusal, and `--allow-reconcile-block` and `--no-archive` are marked dangerous for a reason).
FORBIDDEN_FLAGS = ("--allow-reconcile-block", "--no-archive")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_LOCKED = 5      # the code urtpe.cli returns for LockHeld
EXIT_DIRTY = 6

OUTCOMES = ("nothing_new", "ingested", "already_done", "refused", "stopped",
            "awaiting_diagnosis", "locked", "another_cycle", "dirty_tree", "publish_failed")

_EXIT_FOR_OUTCOME = {
    "nothing_new": EXIT_OK, "ingested": EXIT_OK, "already_done": EXIT_OK,
    "refused": EXIT_FAILED, "stopped": EXIT_FAILED, "awaiting_diagnosis": EXIT_FAILED,
    "locked": EXIT_LOCKED, "another_cycle": EXIT_LOCKED,
    "dirty_tree": EXIT_DIRTY,
    "publish_failed": EXIT_FAILED,
}

#: The tracked paths a cycle rewrites, and so the paths whose uncommitted changes another
#: session could mix with the cycle's output: what an ingest emits, what the check regenerates,
#: and the current-dataset sentence that `sync_etl_process.py` keeps in `openspec/config.yaml`.
#: A test asserts each exists, so the list cannot drift silently when a file moves.
OWNED_PATHS = (
    "data/projects.json",
    "data/raw.tsv",
    "data/clean.tsv",
    "data/merged.tsv",
    "data/review_report.txt",
    "viewer/projects.data.js",
    "viewer/index.html",
    "docs/etl_process.html",
    "docs/domain-model.html",
    "docs/release-diff.html",
    "docs/coverage-report.html",
    "openspec/config.yaml",
)


@dataclass(frozen=True)
class Step:
    """One command of the cycle. `argv` is None for the one internal step, detection."""

    name: str
    argv: tuple[str, ...] | None
    timeout: int           # seconds; a timeout counts as a failed step
    writes: bool           # writes the emitted files or the cache


def build_steps(python: str = "python", pdf: str = "<pdf>", dry_run: bool = False,
                archive_root: str | None = None) -> list[Step]:
    """The cycle as data, in the fixed order. No step is git, and none carries a bypass flag.

    `archive_root`, when the operator chose one, goes to both polls: the coordinator reads the
    archive there, so the polls must write there too. It also makes the report publication a
    `--dry-run`: a hand or smoke cycle on an alternate archive must never push the real report."""
    poll_flags = ("--json", "--dry-run") if dry_run else ("--json",)
    if archive_root:
        poll_flags = (*poll_flags, "--archive-root", str(archive_root))
    steps = [
        Step("poll_gazette", (python, "scripts/poll_gazette.py", *poll_flags), 300, False),
        Step("poll_p168", (python, "scripts/poll_p168.py", *poll_flags), 300, False),
        Step("detect", None, 0, False),
        Step("ingest", (python, "-m", "urtpe.cli", pdf, "-o", "data", "--viewer", "viewer",
                        "--links", "--recover-truncated"), 900, True),
        Step("refresh", (python, "scripts/refresh_awaiting_caches.py"), 1800, True),
        Step("rebuild", (python, "-m", "urtpe.cli", "--from-js", "viewer/projects.data.js",
                         "-o", "data", "--viewer", "viewer", "--links"), 900, True),
        Step("post_ingest_check", (python, "scripts/post_ingest_check.py"), 1800, True),
        Step("tests", (python, "-m", "pytest", "-q"), 1800, False),
        Step("viewer_smoke", ("node", "scripts/viewer_smoke.js"), 300, False),
        # Design D13: the existing publisher, unchanged, only after a finished ingest. It
        # stages and commits only docs/release-diff.html; the coordinator itself runs no git.
        Step("publish_report", (python, "scripts/publish_release_diff.py",
                                *(("--dry-run",) if archive_root else ())), 600, False),
    ]
    assert tuple(s.name for s in steps) == STEP_ORDER
    return steps


def next_step_after(stage: str) -> str | None:
    """The step that follows `stage`, or None after the last one."""
    i = STEP_ORDER.index(stage)
    return STEP_ORDER[i + 1] if i + 1 < len(STEP_ORDER) else None


# --- choosing the gazette to ingest ---------------------------------------------------------

class Archived(NamedTuple):
    """An archived gazette: its id (an ISO date), the SHA-256 of its file, and the file."""

    gazette_id: str
    sha256: str
    path: str


@dataclass(frozen=True)
class Detection:
    """What detection found. `kind` is one of: none, candidate, resume, already_done,
    awaiting_diagnosis, unverified."""

    kind: str
    gazette_id: str = ""
    sha256: str = ""
    path: str = ""
    stage: str = ""        # for `resume` the step to restart at; for `awaiting_diagnosis` the failed one
    reason: str = ""


def pick_candidate(archived: list[Archived], dataset_date: str, state: dict,
                   verify: Callable[[Archived], tuple[bool, str]]) -> Detection:
    """Decide from the archive and the record, never from a poller's status word.

    A hash with a progress entry resumes first: its ingest already moved the dataset, so the
    date rule alone would say there is nothing to do. Otherwise only the NEWEST archived
    gazette newer than the dataset is considered. Each gazette is a complete list, so ingesting
    the newest one is enough, and an older unfinished one is simply superseded.
    """
    hashes = state.get("hashes", {})
    progress = [(e.get("at", ""), sha, e) for sha, e in hashes.items()
                if e.get("status") == "in_progress"]
    if progress:
        _, sha, entry = max(progress)
        path = next((a.path for a in archived if a.sha256 == sha), "")
        return Detection("resume", entry.get("gazette_id", ""), sha, path,
                         stage=entry.get("next_stage", ""))

    newer = [a for a in archived if a.gazette_id > dataset_date]
    if not newer:
        return Detection("none")
    newest = max(newer, key=lambda a: a.gazette_id)
    entry = hashes.get(newest.sha256)
    if entry and entry.get("status") == "finished":
        return Detection("already_done", newest.gazette_id, newest.sha256, newest.path)
    if entry and entry.get("status") == "stopped":
        return Detection("awaiting_diagnosis", newest.gazette_id, newest.sha256, newest.path,
                         stage=entry.get("stage", ""),
                         reason="stopped at %s with exit %s" % (entry.get("stage"), entry.get("exit_code")))
    ok, reason = verify(newest)
    if not ok:
        return Detection("unverified", newest.gazette_id, newest.sha256, newest.path, reason=reason)
    return Detection("candidate", newest.gazette_id, newest.sha256, newest.path)


# --- the stop rule ------------------------------------------------------------------------------

def classify_exit(step: str, exit_code: int, timed_out: bool = False) -> str:
    """`ok`, `transient` (exit 5: a lock was held) or `refusal` (anything else, a timeout too).

    The report publication is different: by then the ingest has finished, so a failure of it
    (exit 1, the push failed; exit 2, the generator's source is uncommitted; a timeout) is
    `publish_failed`, never a refusal and never transient, and it must not undo the ingest."""
    if step == "publish_report":
        return "ok" if exit_code == 0 and not timed_out else "publish_failed"
    if timed_out:
        return "refusal"
    if exit_code == 0:
        return "ok"
    if exit_code == EXIT_LOCKED:
        return "transient"
    return "refusal"


def exit_code_for(outcome: str) -> int:
    return _EXIT_FOR_OUTCOME[outcome]


# --- the record of hashes -------------------------------------------------------------------------

def empty_state() -> dict:
    return {"hashes": {}}


def mark_in_progress(state: dict, sha256: str, gazette_id: str, next_stage: str, at: str) -> dict:
    state["hashes"][sha256] = {"status": "in_progress", "gazette_id": gazette_id,
                               "next_stage": next_stage, "at": at}
    return state


def mark_finished(state: dict, sha256: str, gazette_id: str, at: str) -> dict:
    state["hashes"][sha256] = {"status": "finished", "gazette_id": gazette_id, "at": at}
    return state


def mark_stopped(state: dict, sha256: str, gazette_id: str, stage: str, exit_code: int,
                 at: str) -> dict:
    state["hashes"][sha256] = {"status": "stopped", "gazette_id": gazette_id, "stage": stage,
                               "exit_code": exit_code, "at": at}
    return state


def resume_plan(state: dict, sha256: str) -> tuple[str, str]:
    """(gazette id, stage to restart at) for a stopped or in-progress hash; ValueError else."""
    entry = state.get("hashes", {}).get(sha256)
    if not entry or entry.get("status") not in ("stopped", "in_progress"):
        raise ValueError("no stopped or in-progress cycle for %s" % sha256)
    stage = entry["stage"] if entry["status"] == "stopped" else entry["next_stage"]
    return entry.get("gazette_id", ""), stage


# --- the record of runs -----------------------------------------------------------------------------

def make_record(now_iso: str, polls: dict, outcome: str, *, sha256: str = "",
                gazette_id: str = "", last_stage: str = "", failed_stage: str = "",
                exit_code: int | None = None, reason: str = "") -> dict:
    """One line of `cycle_log.jsonl`. Every run writes one, including the quiet ones."""
    if outcome not in OUTCOMES:
        raise ValueError("unknown outcome: %r" % outcome)
    return {
        "time": now_iso,
        "polls": dict(polls),
        "sha256": sha256,
        "gazette_id": gazette_id,
        "last_stage": last_stage,
        "failed_stage": failed_stage,
        "exit_code": exit_code_for(outcome) if exit_code is None else exit_code,
        "outcome": outcome,
        "reason": reason,
    }


def newest_record_age_hours(records: list[dict], now_iso: str) -> float | None:
    """Hours since the newest record, or None when there is none: a gap is visible from the
    records alone, without asking the publisher."""
    if not records:
        return None
    newest = max(dt.datetime.fromisoformat(r["time"]) for r in records)
    return (dt.datetime.fromisoformat(now_iso) - newest).total_seconds() / 3600.0


# --- the dirty-tree decision and the dataset's date --------------------------------------------------

def dirty_decision(candidate_ready: bool, dirty_paths: list[str]) -> str:
    """`refuse` only when a gazette is ready and an owned path has uncommitted changes. A quiet
    day is never stopped by a dirty tree: it writes nothing."""
    return "refuse" if candidate_ready and dirty_paths else "run"


_PUBLISHED_RE = re.compile(r'"published_date"\s*:\s*"(\d{4}-\d{2}-\d{2})"')


def parse_published_date(head_text: str) -> str:
    """The emitted dataset's publication date, from the head of `viewer/projects.data.js`."""
    m = _PUBLISHED_RE.search(head_text)
    if not m:
        raise ValueError("no published_date in the payload head")
    return m.group(1)
