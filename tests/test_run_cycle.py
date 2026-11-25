# -*- coding: utf-8 -*-
"""A4 — the PDF-cycle coordinator's adapters and orchestration (`scripts/run_cycle.py`).

openspec change a4-pdf-cycle-coordinator, capability `pdf-cycle-coordinator`. The pure rules
are in `test_cycle.py`. Here the script runs with doubles for the subprocess runner, git, the
clock and the archive, and with the REAL `SingleWriterLock` and the real record store over
temp directories, because the lock behaviour is the point (the A8 lesson: a parent that holds
the lock makes the child exit 5).

Nothing here reaches the network, runs a real step, or touches the real `data/`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cycle  # noqa: E402
from urtpe.lock import LOCK_NAME, SingleWriterLock  # noqa: E402

SCRIPT = ROOT / "scripts" / "run_cycle.py"
NEW = cycle.Archived("2026-11-19", "b" * 64, "/archive/new.pdf")
TZ = timezone(timedelta(hours=8))


@pytest.fixture(scope="module")
def rc():
    spec = importlib.util.spec_from_file_location("run_cycle_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod            # dataclasses looks its own module up here
    spec.loader.exec_module(mod)
    return mod


def _name_of(argv):
    joined = " ".join(str(a) for a in argv)
    if "poll_gazette.py" in joined:
        return "poll_gazette"
    if "poll_p168.py" in joined:
        return "poll_p168"
    if "refresh_awaiting_caches.py" in joined:
        return "refresh"
    if "post_ingest_check.py" in joined:
        return "post_ingest_check"
    if "publish_emission.py" in joined:
        return "publish_emission"
    if "publish_release_diff.py" in joined:
        return "publish_report"
    if "viewer_smoke.js" in joined:
        return "viewer_smoke"
    if "pytest" in joined:
        return "tests"
    if "urtpe.cli" in joined and "--from-js" in joined:
        return "rebuild"
    if "urtpe.cli" in joined:
        return "ingest"
    raise AssertionError("unknown command: %s" % joined)


class Harness:
    """The coordinator over temp directories, with every outward call replaced."""

    def __init__(self, tmp_path, rc):
        self.rc = rc
        self.data = tmp_path / "data"
        self.archive = tmp_path / "gazettes"
        self.data.mkdir()
        self.archive.mkdir()
        self.calls = []                    # (step name, argv)
        self.results = {}                  # step name -> RunResult | callable(argv) -> RunResult
        self.dirty = []
        self.git_calls = []
        self.archived = [NEW]
        self.dataset = "2026-11-12"
        self.verify = (True, "")
        self.store = rc.CycleStore(self.archive)
        self.status_calls = 0
        self.status_error = None
        self.during = []                   # filled by a test's runner hook

    def runner(self, argv, timeout):
        name = _name_of(argv)
        self.calls.append((name, list(argv)))
        res = self.results.get(name)
        if callable(res):
            res = res(argv)
        if res is None:
            body = {"status": "unchanged"} if name.startswith("poll_") else None
            res = self.rc.RunResult(0, stdout=json.dumps(body) if body else "")
        return res

    def git_dirty(self, paths):
        self.git_calls.append(tuple(paths))
        return list(self.dirty)

    def status_page(self):
        self.status_calls += 1
        if self.status_error:
            raise self.status_error

    def deps(self):
        return self.rc.Deps(
            runner=self.runner, git_dirty=self.git_dirty, store=self.store,
            clock=lambda: datetime(2026, 11, 23, 6, 0, tzinfo=TZ),
            list_archived=lambda: list(self.archived),
            verify=lambda a: self.verify,
            dataset_date=lambda: self.dataset,
            data_dir=self.data, archive_dir=self.archive,
            status_page=self.status_page)

    def run(self, **opts):
        return self.rc.run(self.rc.Options(python="py", **opts), self.deps())

    def names(self):
        return [n for n, _ in self.calls]

    def records(self):
        return self.store.read_records()

    def state(self):
        return self.store.load_state()


@pytest.fixture
def h(tmp_path, rc):
    return Harness(tmp_path, rc)


# --- 1.13 the order, and git ---------------------------------------------------------------

def test_a_new_gazette_runs_every_step_once_in_order(h):
    assert h.run() == 0
    assert h.names() == ["poll_gazette", "poll_p168", "ingest", "refresh", "rebuild",
                         "post_ingest_check", "tests", "viewer_smoke", "publish_emission",
                         "publish_report"]
    ingest_argv = dict(h.calls)["ingest"]
    assert NEW.path in ingest_argv                       # the archived dated file, never the live link


def test_a_finished_cycle_is_recorded_and_the_hash_is_finished(h):
    assert h.run() == 0
    (rec,) = h.records()
    assert rec["outcome"] == "ingested" and rec["exit_code"] == 0
    assert rec["last_stage"] == "publish_report" and rec["failed_stage"] == ""
    assert rec["sha256"] == NEW.sha256
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


def test_the_only_git_interaction_is_one_read_only_status_over_the_owned_paths(h):
    """Still true of the COORDINATOR after a5-cycle-emission-publication: the commits and the
    pushes belong to the two child publishers, run through the runner, never to this process."""
    assert h.run() == 0
    assert h.git_calls == [tuple(cycle.OWNED_PATHS)]
    committers = [n for n, _ in h.calls if n in ("publish_emission", "publish_report")]
    assert committers == ["publish_emission", "publish_report"]


def test_the_script_names_no_git_write_command():
    text = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"""["'](push|commit|checkout|stash|reset|clean|restore)["']""", text)
    assert "git" in text                                   # it does read status


def test_an_unchanged_page_with_nothing_newer_runs_only_the_two_polls(h):
    h.dataset = NEW.gazette_id
    assert h.run() == 0
    assert h.names() == ["poll_gazette", "poll_p168"]
    (rec,) = h.records()
    assert rec["outcome"] == "nothing_new"
    assert list(h.data.iterdir()) == []                    # nothing written to the emitted tree


def test_a_dirty_owned_path_on_a_quiet_day_does_not_stop_the_run(h):
    h.dataset = NEW.gazette_id
    h.dirty = ["viewer/projects.data.js"]
    assert h.run() == 0
    assert h.records()[0]["outcome"] == "nothing_new"


def test_a_chosen_archive_root_reaches_both_polls(h):
    assert h.run(archive_root=str(h.archive)) == 0
    for name in ("poll_gazette", "poll_p168"):
        argv = dict(h.calls)[name]
        assert argv[argv.index("--archive-root") + 1] == str(h.archive)


# --- dirty tree (U6 proof 9) ---------------------------------------------------------------------

def test_a_dirty_owned_path_with_a_gazette_ready_stops_with_exit_6(h):
    h.dirty = ["viewer/projects.data.js", "docs/etl_process.html"]
    assert h.run() == 6
    assert h.names() == ["poll_gazette", "poll_p168"]      # nothing wrote
    (rec,) = h.records()
    assert rec["outcome"] == "dirty_tree"
    assert "viewer/projects.data.js" in rec["reason"] and "docs/etl_process.html" in rec["reason"]
    assert h.state()["hashes"] == {}                       # transient: the hash is untouched


def test_the_next_run_after_a_dirty_tree_tries_the_same_gazette_again(h):
    h.dirty = ["viewer/projects.data.js"]
    assert h.run() == 6
    h.dirty = []
    h.calls.clear()
    assert h.run() == 0
    assert "ingest" in h.names()


def test_resuming_past_the_ingest_skips_the_dirty_check_because_the_dirt_is_this_cycles(h):
    state = h.state()
    cycle.mark_in_progress(state, NEW.sha256, NEW.gazette_id, "refresh", "2026-11-23T05:00:00+08:00")
    h.store.save_state(state)
    h.dataset = NEW.gazette_id                              # the ingest already updated the dataset
    h.dirty = ["viewer/projects.data.js"]
    assert h.run() == 0
    assert h.names()[0] == "poll_gazette" and "ingest" not in h.names()
    assert "refresh" in h.names() and h.names()[-1] == "publish_report"


# --- the stop rule (U6 proofs 5, 6, 12) -------------------------------------------------------------

def test_an_ingest_refusal_stops_everything_after_it(h, rc):
    h.results["ingest"] = rc.RunResult(4)
    assert h.run() == 1
    assert h.names() == ["poll_gazette", "poll_p168", "ingest"]
    (rec,) = h.records()
    assert (rec["outcome"], rec["failed_stage"], rec["exit_code"]) == ("refused", "ingest", 4)
    entry = h.state()["hashes"][NEW.sha256]
    assert (entry["status"], entry["stage"], entry["exit_code"]) == ("stopped", "ingest", 4)


def test_a_failed_refresh_is_not_followed_by_a_rebuild(h, rc):
    h.results["refresh"] = rc.RunResult(1)
    assert h.run() == 1
    assert "rebuild" not in h.names()
    (rec,) = h.records()
    assert rec["failed_stage"] == "refresh" and rec["outcome"] == "stopped"
    assert h.state()["hashes"][NEW.sha256]["status"] == "stopped"


def test_a_step_that_times_out_is_a_failed_step(h, rc):
    h.results["tests"] = rc.RunResult(124, timed_out=True)
    assert h.run() == 1
    assert h.records()[0]["failed_stage"] == "tests"
    assert h.state()["hashes"][NEW.sha256]["status"] == "stopped"


def test_a_stopped_hash_waits_for_a_person_on_later_runs(h, rc):
    h.results["ingest"] = rc.RunResult(4)
    assert h.run() == 1
    h.results["ingest"] = None
    h.calls.clear()
    assert h.run() == 1
    assert h.names() == ["poll_gazette", "poll_p168"]       # no ingest, no later step
    assert h.records()[-1]["outcome"] == "awaiting_diagnosis"
    assert h.state()["hashes"][NEW.sha256]["status"] == "stopped"


def test_resume_restarts_at_the_failed_stage_and_skips_the_polls(h, rc):
    h.results["rebuild"] = rc.RunResult(1)
    assert h.run() == 1
    h.results["rebuild"] = None
    h.calls.clear()
    assert h.run(resume=NEW.sha256) == 0
    assert h.names() == ["rebuild", "post_ingest_check", "tests", "viewer_smoke", "publish_report"]
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


def test_resuming_a_hash_that_finished_is_a_usage_error(h):
    assert h.run() == 0
    assert h.run(resume=NEW.sha256) == cycle.EXIT_USAGE


def test_an_unverified_gazette_is_refused_at_detection(h):
    h.verify = (False, "content of new.pdf does not match any recorded digest")
    assert h.run() == 1
    assert h.names() == ["poll_gazette", "poll_p168"]
    (rec,) = h.records()
    assert rec["outcome"] == "refused" and rec["failed_stage"] == "detect"
    assert "does not match" in rec["reason"]


def test_a_completed_hash_is_not_ingested_again(h):
    assert h.run() == 0
    h.calls.clear()
    h.dataset = "2026-11-12"                                 # even if the files were reverted
    assert h.run() == 0
    assert h.names() == ["poll_gazette", "poll_p168"]
    assert h.records()[-1]["outcome"] == "already_done"


def test_a_gazette_archived_by_an_earlier_poll_is_still_ingested(h, rc):
    """The poll says `unchanged`: the status word was consumed by a hand-started poll."""
    h.results["poll_gazette"] = rc.RunResult(0, stdout=json.dumps({"status": "unchanged"}))
    assert h.run() == 0
    assert "ingest" in h.names()


# --- 1.14 locks (U6 proof 4) --------------------------------------------------------------------------

def test_a_lock_held_at_the_start_stops_before_any_write_step(h):
    with SingleWriterLock(h.data):
        assert h.run() == 5
    assert h.names() == ["poll_gazette", "poll_p168"]
    (rec,) = h.records()
    assert rec["outcome"] == "locked" and rec["exit_code"] == 5
    assert h.state()["hashes"] == {}


def test_a_child_that_exits_5_mid_cycle_stops_with_the_stage_recorded_and_resumes_there(h, rc):
    h.results["refresh"] = rc.RunResult(5)
    assert h.run() == 5
    (rec,) = h.records()
    assert rec["outcome"] == "locked" and rec["failed_stage"] == "refresh"
    entry = h.state()["hashes"][NEW.sha256]
    assert entry["status"] == "in_progress" and entry["next_stage"] == "refresh"
    # the ingest already updated the dataset, so only the progress entry can resume the cycle
    h.results["refresh"] = None
    h.calls.clear()
    h.dataset = NEW.gazette_id
    assert h.run() == 0
    assert "ingest" not in h.names() and "refresh" in h.names()
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


def test_the_coordinator_leaves_the_data_lock_free_between_steps(h, rc):
    seen = []

    def child(argv):
        # a real child takes the data lock itself; it must find it free
        with SingleWriterLock(h.data):
            seen.append((_name_of(argv), (h.archive / LOCK_NAME).exists()))
        return rc.RunResult(0)
    for name in ("ingest", "refresh", "rebuild"):
        h.results[name] = child
    assert h.run() == 0
    assert [n for n, _ in seen] == ["ingest", "refresh", "rebuild"]
    # while a child ran, the coordinator held its OWN lock, over the archive root
    assert all(cycle_lock_held for _, cycle_lock_held in seen)
    assert not (h.data / LOCK_NAME).exists()
    assert not (h.archive / LOCK_NAME).exists()              # and gave it back


def test_a_second_cycle_stops_and_records_that_one_was_running(h):
    with SingleWriterLock(h.archive):
        assert h.run() == 5
    assert h.names() == []                                    # not even a poll
    (rec,) = h.records()
    assert rec["outcome"] == "another_cycle"


def test_both_locks_are_free_after_a_run_that_raises(h, rc):
    def boom(argv):
        raise RuntimeError("the runner fell over")
    h.results["ingest"] = boom
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "stopped" and rec["failed_stage"] == "internal"
    SingleWriterLock(h.data).acquire().release()
    SingleWriterLock(h.archive).acquire().release()


# --- 1.15 a dry run writes nothing --------------------------------------------------------------------

def test_a_dry_run_runs_only_the_two_polls_with_dry_run(h, capsys):
    assert h.run(dry_run=True) == 0
    assert h.names() == ["poll_gazette", "poll_p168"]
    for _, argv in h.calls:
        assert "--dry-run" in argv
    out = capsys.readouterr().out
    assert "ingest" in out                                    # it says what it would do


def test_a_dry_run_writes_no_record_no_archive_file_and_nothing_under_data(h):
    before = sorted(p.name for p in h.archive.iterdir())
    assert h.run(dry_run=True) == 0
    assert sorted(p.name for p in h.archive.iterdir()) == before
    assert list(h.data.iterdir()) == []
    assert h.records() == []
    assert h.status_calls == 0


def test_a_dry_run_with_nothing_newer_says_so(h, capsys):
    h.dataset = NEW.gazette_id
    assert h.run(dry_run=True) == 0
    assert "nothing" in capsys.readouterr().out.lower()


# --- 1.16 the record store -----------------------------------------------------------------------------

def test_the_record_is_append_only(h):
    h.store.append({"n": 1})
    first = (h.archive / "cycle_log.jsonl").read_bytes()
    h.store.append({"n": 2})
    assert (h.archive / "cycle_log.jsonl").read_bytes().startswith(first)
    assert [r["n"] for r in h.store.read_records()] == [1, 2]


def test_the_state_round_trips_and_defaults_to_empty(h):
    assert h.store.load_state() == cycle.empty_state()
    state = cycle.empty_state()
    cycle.mark_finished(state, "a" * 64, "2026-11-12", "2026-11-23T06:00:00+08:00")
    h.store.save_state(state)
    assert h.store.load_state() == state


def test_a_failed_state_write_leaves_the_old_state(h, monkeypatch):
    old = cycle.empty_state()
    cycle.mark_finished(old, "a" * 64, "2026-11-12", "2026-11-23T06:00:00+08:00")
    h.store.save_state(old)
    new = cycle.empty_state()
    cycle.mark_finished(new, "b" * 64, "2026-11-19", "2026-11-23T06:00:00+08:00")

    def deny(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", deny)
    with pytest.raises(OSError):
        h.store.save_state(new)
    monkeypatch.undo()
    assert h.store.load_state() == old                         # the old state survived


def test_the_archive_root_honors_the_override(rc, tmp_path):
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    assert rc.resolve_archive_root(str(tmp_path)) == tmp_path
    assert rc.resolve_archive_root(None) == Path(DEFAULT_ARCHIVE_ROOT)


def test_the_record_lives_in_the_archive_root_beside_the_poll_logs(h):
    h.run()
    assert (h.archive / "cycle_log.jsonl").is_file()
    assert (h.archive / "cycle_state.json").is_file()


# --- 1.17 a failed or malformed poll is a failed step, never "nothing new" -------------------------------

def test_a_failed_gazette_poll_stops_the_cycle(h, rc):
    h.results["poll_gazette"] = rc.RunResult(1, stdout=json.dumps({"status": "failed", "error": "down"}))
    assert h.run() == 1
    assert h.names() == ["poll_gazette"]
    (rec,) = h.records()
    assert rec["outcome"] == "stopped" and rec["failed_stage"] == "poll_gazette"
    assert rec["polls"]["gazette"] == "failed"
    assert h.state()["hashes"] == {}                          # no hash was involved


def test_a_malformed_poll_result_is_a_failed_step(h, rc):
    h.results["poll_gazette"] = rc.RunResult(0, stdout="this is not json")
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "stopped" and rec["failed_stage"] == "poll_gazette"
    assert rec["outcome"] != "nothing_new"


def test_a_poll_that_times_out_is_a_failed_step(h, rc):
    h.results["poll_p168"] = rc.RunResult(124, timed_out=True)
    assert h.run() == 1
    assert h.names() == ["poll_gazette", "poll_p168"]
    assert h.records()[0]["failed_stage"] == "poll_p168"


# --- the status page is best effort ----------------------------------------------------------------------

def test_the_status_page_is_generated_at_the_end_of_every_real_run(h):
    h.run()
    assert h.status_calls == 1


def test_a_failing_status_page_never_changes_the_exit_code(h):
    h.status_error = RuntimeError("cannot write the page")
    assert h.run() == 0
    h.status_error = OSError("disk full")
    h.dataset = NEW.gazette_id
    assert h.run() == 0


# --- the command line --------------------------------------------------------------------------------------

def test_the_command_line_flags(rc):
    assert rc.parse_args([]).dry_run is False
    assert rc.parse_args(["--dry-run"]).dry_run is True
    assert rc.parse_args(["--resume", "abc"]).resume == "abc"
    assert rc.parse_args(["--archive-root", "X"]).archive_root == "X"


def test_dry_run_and_resume_together_is_a_usage_error(rc):
    with pytest.raises(SystemExit) as exc:
        rc.parse_args(["--dry-run", "--resume", "abc"])
    assert exc.value.code == cycle.EXIT_USAGE


# --- 6.4 to 6.8 the report publication (design D13) ------------------------------------------------

def _scenario(h, rc, name):
    """Run a scenario that must NOT end in a published report; return what the last run returned."""
    if name == "nothing_new":
        h.dataset = NEW.gazette_id
        return h.run()
    if name == "already_done":
        h.run()
        h.calls.clear()
        return h.run()
    if name == "refused":
        h.results["ingest"] = rc.RunResult(4)
        return h.run()
    if name == "stopped":
        h.results["refresh"] = rc.RunResult(1)
        return h.run()
    if name == "locked_at_start":
        with SingleWriterLock(h.data):
            return h.run()
    if name == "locked_mid_cycle":
        h.results["refresh"] = rc.RunResult(5)
        return h.run()
    if name == "dirty_tree":
        h.dirty = ["viewer/projects.data.js"]
        return h.run()
    if name == "awaiting_diagnosis":
        h.results["ingest"] = rc.RunResult(4)
        h.run()
        h.calls.clear()
        h.results["ingest"] = None
        return h.run()
    if name == "resume_stopped_again":
        h.results["rebuild"] = rc.RunResult(1)
        h.run()
        h.calls.clear()
        return h.run(resume=NEW.sha256)
    raise AssertionError(name)


@pytest.mark.parametrize("name", ["nothing_new", "already_done", "refused", "stopped",
                                  "locked_at_start", "locked_mid_cycle", "dirty_tree",
                                  "awaiting_diagnosis", "resume_stopped_again"])
def test_the_report_is_never_published_unless_an_ingest_finished(h, rc, name):
    _scenario(h, rc, name)
    assert "publish_report" not in h.names()


@pytest.mark.parametrize("name", ["nothing_new", "already_done", "refused", "stopped",
                                  "locked_at_start", "locked_mid_cycle", "dirty_tree",
                                  "awaiting_diagnosis", "resume_stopped_again"])
def test_the_emission_is_never_published_unless_an_ingest_finished(h, rc, name):
    _scenario(h, rc, name)
    assert "publish_emission" not in h.names()


def test_the_publications_run_last_after_the_smoke_step_emission_first(h):
    assert h.run() == 0
    assert h.names()[-3:] == ["viewer_smoke", "publish_emission", "publish_report"]


@pytest.mark.parametrize("step", ["publish_emission", "publish_report"])
def test_the_hash_is_finished_before_a_publication_starts(h, rc, step):
    seen = []

    def publisher(argv):
        seen.append(h.state()["hashes"][NEW.sha256]["status"])
        return rc.RunResult(0)
    h.results[step] = publisher
    assert h.run() == 0
    assert seen == ["finished"]


@pytest.mark.parametrize("code", [1, 2])
def test_a_failed_emission_publication_is_recorded_and_never_undoes_the_ingest(h, rc, code):
    """The hash is finished, so this is `publish_failed`, never `stopped`: a stopped hash would
    wait for diagnosis and a later run would skip it. The report publisher does not run after
    it, because the pages describe an emission that did not land."""
    h.results["publish_emission"] = rc.RunResult(code)
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "publish_failed" and rec["exit_code"] == code
    assert rec["failed_stage"] == "publish_emission" and rec["last_stage"] == "viewer_smoke"
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"
    assert "publish_report" not in h.names()
    # the next run neither ingests nor publishes again; a person retries by hand
    h.calls.clear()
    h.results["publish_emission"] = None
    assert h.run() == 0
    assert h.names() == ["poll_gazette", "poll_p168"]
    assert h.records()[-1]["outcome"] == "already_done"


def test_an_emission_publication_that_times_out_is_a_failed_publication(h, rc):
    h.results["publish_emission"] = rc.RunResult(124, timed_out=True)
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "publish_failed" and rec["failed_stage"] == "publish_emission"
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


def test_an_emission_publisher_exit_5_is_a_failed_publication_not_a_locked_stop(h, rc):
    h.results["publish_emission"] = rc.RunResult(5)
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "publish_failed" and rec["outcome"] != "locked"
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


@pytest.mark.parametrize("code", [1, 2])
def test_a_failed_publication_is_recorded_and_never_undoes_the_ingest(h, rc, code):
    h.results["publish_report"] = rc.RunResult(code)
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "publish_failed" and rec["exit_code"] == code
    assert rec["failed_stage"] == "publish_report" and rec["last_stage"] == "publish_emission"
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"
    # the next run neither ingests nor publishes again; a person retries by hand
    h.calls.clear()
    h.results["publish_report"] = None
    assert h.run() == 0
    assert h.names() == ["poll_gazette", "poll_p168"]
    assert h.records()[-1]["outcome"] == "already_done"


def test_a_publication_that_times_out_is_a_failed_publication(h, rc):
    h.results["publish_report"] = rc.RunResult(124, timed_out=True)
    assert h.run() == 1
    (rec,) = h.records()
    assert rec["outcome"] == "publish_failed" and rec["exit_code"] == 124
    assert h.state()["hashes"][NEW.sha256]["status"] == "finished"


def test_a_resume_that_finishes_publishes_the_report_last(h, rc):
    h.results["rebuild"] = rc.RunResult(1)
    assert h.run() == 1
    h.results["rebuild"] = None
    h.calls.clear()
    assert h.run(resume=NEW.sha256) == 0
    assert h.names()[-2:] == ["publish_emission", "publish_report"]


def test_the_dry_run_plan_ends_with_the_two_publications_emission_first(h, capsys):
    assert h.run(dry_run=True) == 0
    assert h.names() == ["poll_gazette", "poll_p168"]          # it still runs only the two polls
    out = capsys.readouterr().out
    plan = [line for line in out.splitlines() if "steps:" in line][0]
    steps = plan.split("steps:")[1].split(";")[0].strip()
    assert steps.endswith("publish_emission, publish_report")
    # a5-cycle-emission-publication: the emission no longer waits for a person's review
    assert "uncommitted" not in out and "review" not in out.lower().split("steps:")[1]


def test_a_chosen_archive_root_makes_both_publications_a_dry_run(h):
    assert h.run(archive_root=str(h.archive)) == 0
    assert "--dry-run" in dict(h.calls)["publish_report"]
    assert "--dry-run" in dict(h.calls)["publish_emission"]


def test_the_default_run_publishes_for_real(h):
    assert h.run() == 0
    assert "--dry-run" not in dict(h.calls)["publish_report"]
    assert "--dry-run" not in dict(h.calls)["publish_emission"]


# --- the dirty check also watches the code, and ignores untracked files -------------------------
# openspec a4-pdf-cycle-coordinator, task 6.24 (operator's word 2026-11-24).

def _real_dirty(tmp_path, monkeypatch):
    import subprocess

    path = ROOT / "scripts" / "run_cycle.py"
    spec = importlib.util.spec_from_file_location("run_cycle_real_dirty", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    def git(*a):
        return subprocess.run(["git", *a], cwd=str(tmp_path), capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    for rel in ("urtpe/a.py", "scripts/b.py", "docs/page.html"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "base")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    return mod, tmp_path


_WATCHED = ("urtpe/", "scripts/", "docs/page.html")


def test_an_edited_code_file_is_dirty(tmp_path, monkeypatch):
    mod, repo = _real_dirty(tmp_path, monkeypatch)
    (repo / "urtpe" / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert mod._real_git_dirty(_WATCHED) == ["urtpe/a.py"]


def test_an_untracked_file_is_not_dirty(tmp_path, monkeypatch):
    """A new probe script is not something the cycle runs. Only a tracked file that changed
    counts, so the cycle is not stopped by every scratch file another session leaves."""
    mod, repo = _real_dirty(tmp_path, monkeypatch)
    (repo / "scripts" / "probe_new.py").write_text("print(1)\n", encoding="utf-8")
    (repo / "urtpe" / "scratch.py").write_text("y = 1\n", encoding="utf-8")
    assert mod._real_git_dirty(_WATCHED) == []


def test_a_clean_tree_is_not_dirty(tmp_path, monkeypatch):
    mod, repo = _real_dirty(tmp_path, monkeypatch)
    assert mod._real_git_dirty(_WATCHED) == []
