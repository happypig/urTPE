# -*- coding: utf-8 -*-
"""A4 — the pure logic of the PDF-cycle coordinator (`urtpe/cycle.py`).

openspec change a4-pdf-cycle-coordinator, capability `pdf-cycle-coordinator`. This module
holds no I/O: the ordered step list, how a gazette to ingest is chosen, when a cycle stops,
how the record changes, which exit code a run returns. The adapters (subprocess, git, files,
locks) are tested in `test_run_cycle.py` with doubles.

The board's U6 proofs that live here: 1, 2, 5, 6, 9, 11, 12 (and the pure half of 4).
Proofs 7 and 8 are properties of the existing rebuild and check, observed in task group 5.

The candidate rule is the one the design found by reading the poll log: `new_gazette` is a
status word that any earlier poll consumes, including a hand-started one (both real catches
so far were). So a gazette is chosen from the archive: newest, newer than the dataset,
verified, and not already finished or stopped.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cycle  # noqa: E402

A = cycle.Archived
OLD = A("2026-10-28", "a" * 64, "/archive/old.pdf")
NEW = A("2026-11-19", "b" * 64, "/archive/new.pdf")
ALL_OK = lambda archived: (True, "")           # noqa: E731
NOW = "2026-11-23T06:00:00+08:00"


def _state(**hashes):
    state = cycle.empty_state()
    state["hashes"].update(hashes)
    return state


# --- 1.1 the step list is data, in a fixed order, and ends before git -----------------

def test_the_steps_run_in_the_fixed_order():
    names = [s.name for s in cycle.build_steps(python="py")]
    assert names == ["poll_gazette", "poll_p168", "detect", "ingest", "refresh",
                     "rebuild", "post_ingest_check", "tests", "viewer_smoke", "publish_report"]
    assert tuple(names) == cycle.STEP_ORDER


def test_the_last_step_publishes_the_report_and_no_step_touches_git():
    steps = cycle.build_steps(python="py")
    assert steps[-1].name == "publish_report"
    assert steps[-1].argv[1] == "scripts/publish_release_diff.py"
    for step in steps:
        assert "git" not in (step.argv or ())
        assert not any(a in ("commit", "push", "add", "checkout", "stash", "reset")
                       for a in (step.argv or ()))


def test_the_detect_step_is_internal_and_the_other_steps_have_an_argv():
    steps = {s.name: s for s in cycle.build_steps(python="py")}
    assert steps["detect"].argv is None
    assert all(s.argv for n, s in steps.items() if n != "detect")


def test_the_ingest_step_takes_the_archived_dated_file():
    steps = {s.name: s for s in cycle.build_steps(python="py", pdf="/archive/new.pdf")}
    argv = steps["ingest"].argv
    assert "/archive/new.pdf" in argv
    assert "--links" in argv and "--recover-truncated" in argv


def test_a_dry_run_marks_only_the_two_polls_read_only():
    steps = {s.name: s for s in cycle.build_steps(python="py", dry_run=True)}
    assert "--dry-run" in steps["poll_gazette"].argv
    assert "--dry-run" in steps["poll_p168"].argv
    assert "--dry-run" not in steps["ingest"].argv


def test_the_polls_carry_a_chosen_archive_root():
    """`run_cycle.py --archive-root X` reads the archive at X; the polls must write to X too."""
    steps = {s.name: s for s in cycle.build_steps(python="py", archive_root="/tmp/a")}
    for name in ("poll_gazette", "poll_p168"):
        argv = steps[name].argv
        assert argv[argv.index("--archive-root") + 1] == "/tmp/a"


def test_the_polls_carry_no_archive_root_by_default():
    for step in cycle.build_steps(python="py"):
        assert "--archive-root" not in (step.argv or ())


# --- 1.2 no bypass flag, ever (U6 proof 5) ----------------------------------------------

@pytest.mark.parametrize("dry_run", [False, True])
def test_no_argv_ever_holds_a_bypass_flag(dry_run):
    for step in cycle.build_steps(python="py", pdf="/x.pdf", dry_run=dry_run):
        for flag in cycle.FORBIDDEN_FLAGS:
            assert flag not in (step.argv or ()), (step.name, flag)
    assert set(cycle.FORBIDDEN_FLAGS) == {"--allow-reconcile-block", "--no-archive"}


# --- 1.3 / 1.4 choosing the gazette to ingest (U6 proofs 1, 2) -------------------------

def test_a_newer_verified_unrecorded_gazette_is_chosen():
    d = cycle.pick_candidate([OLD, NEW], "2026-11-12", cycle.empty_state(), ALL_OK)
    assert d.kind == "candidate"
    assert (d.gazette_id, d.sha256, d.path) == (NEW.gazette_id, NEW.sha256, NEW.path)


def test_a_gazette_not_newer_than_the_dataset_is_never_chosen_even_with_an_empty_record():
    d = cycle.pick_candidate([OLD, NEW], "2026-11-19", cycle.empty_state(), ALL_OK)
    assert d.kind == "none"
    d = cycle.pick_candidate([OLD, NEW], "2026-12-31", cycle.empty_state(), ALL_OK)
    assert d.kind == "none"


def test_older_archived_gazettes_are_never_chosen_on_an_empty_record():
    archive = [A("2026-08-11", "1" * 64, "/a"), A("2026-09-24", "2" * 64, "/b"),
               A("2026-10-28", "3" * 64, "/c")]
    assert cycle.pick_candidate(archive, "2026-10-28", cycle.empty_state(), ALL_OK).kind == "none"


def test_only_the_newest_gazette_is_chosen_when_several_are_newer():
    middle = A("2026-11-12", "c" * 64, "/archive/middle.pdf")
    d = cycle.pick_candidate([OLD, middle, NEW], "2026-10-28", cycle.empty_state(), ALL_OK)
    assert d.kind == "candidate" and d.gazette_id == NEW.gazette_id


def test_a_gazette_archived_by_an_earlier_poll_is_still_chosen():
    """The page is `unchanged` now: the status word was spent. The archive remembers."""
    d = cycle.pick_candidate([NEW], "2026-11-12", cycle.empty_state(), ALL_OK)
    assert d.kind == "candidate"


def test_a_reupload_of_a_gazette_the_dataset_reflects_chooses_nothing():
    d = cycle.pick_candidate([OLD], "2026-10-28", cycle.empty_state(), ALL_OK)
    assert d.kind == "none"


def test_an_empty_archive_chooses_nothing():
    assert cycle.pick_candidate([], "2026-11-12", cycle.empty_state(), ALL_OK).kind == "none"


# --- 1.5 a gazette that does not verify is refused at detection --------------------------

def test_a_newer_gazette_that_does_not_verify_is_refused_with_the_reason():
    verify = lambda a: (False, "content of new.pdf does not match any recorded digest")  # noqa: E731
    d = cycle.pick_candidate([NEW], "2026-11-12", cycle.empty_state(), verify)
    assert d.kind == "unverified"
    assert "does not match" in d.reason
    assert d.sha256 == NEW.sha256


# --- 1.6 a finished hash is not chosen again (U6 proof 11) ------------------------------

def test_a_finished_hash_is_not_chosen_again():
    state = cycle.empty_state()
    cycle.mark_finished(state, NEW.sha256, NEW.gazette_id, NOW)
    for _ in range(3):                                  # however many runs start
        d = cycle.pick_candidate([NEW], "2026-11-12", state, ALL_OK)
        assert d.kind == "already_done"


# --- 1.7 the stop rule (U6 proofs 5, 6) ---------------------------------------------------

@pytest.mark.parametrize("code", [2, 3, 4])
def test_an_ingest_refusal_is_a_refusal_stop(code):
    assert cycle.classify_exit("ingest", code) == "refusal"


def test_exit_5_is_transient_and_any_other_non_zero_is_a_refusal():
    assert cycle.classify_exit("ingest", 5) == "transient"
    assert cycle.classify_exit("refresh", 5) == "transient"
    assert cycle.classify_exit("refresh", 1) == "refusal"
    assert cycle.classify_exit("tests", 1) == "refusal"
    assert cycle.classify_exit("ingest", 0) == "ok"


def test_a_timeout_is_a_failed_step_not_a_success():
    assert cycle.classify_exit("ingest", 0, timed_out=True) == "refusal"


def test_a_stopped_cycle_names_the_failed_stage_and_is_not_finished():
    state = cycle.empty_state()
    cycle.mark_stopped(state, NEW.sha256, NEW.gazette_id, "ingest", 4, NOW)
    entry = state["hashes"][NEW.sha256]
    assert entry["status"] == "stopped"
    assert (entry["stage"], entry["exit_code"]) == ("ingest", 4)
    assert entry["status"] != "finished"


def test_the_stage_after_each_step():
    assert cycle.next_step_after("ingest") == "refresh"
    assert cycle.next_step_after("refresh") == "rebuild"       # never skipped on a failed refresh
    assert cycle.next_step_after("viewer_smoke") == "publish_report"
    assert cycle.next_step_after("publish_report") is None


# --- 1.8 a stopped hash waits for a person; resume restarts at the failed stage -----------

def test_a_stopped_hash_awaits_diagnosis_and_is_not_chosen_for_a_run():
    state = cycle.empty_state()
    cycle.mark_stopped(state, NEW.sha256, NEW.gazette_id, "ingest", 4, NOW)
    d = cycle.pick_candidate([NEW], "2026-11-12", state, ALL_OK)
    assert d.kind == "awaiting_diagnosis"
    assert d.stage == "ingest"


def test_resume_restarts_at_the_failed_stage_and_not_at_the_first_step():
    state = cycle.empty_state()
    cycle.mark_stopped(state, NEW.sha256, NEW.gazette_id, "rebuild", 1, NOW)
    gazette_id, stage = cycle.resume_plan(state, NEW.sha256)
    assert (gazette_id, stage) == (NEW.gazette_id, "rebuild")


def test_resume_of_an_unknown_or_finished_hash_is_refused():
    state = cycle.empty_state()
    with pytest.raises(ValueError):
        cycle.resume_plan(state, "f" * 64)
    cycle.mark_finished(state, NEW.sha256, NEW.gazette_id, NOW)
    with pytest.raises(ValueError):
        cycle.resume_plan(state, NEW.sha256)


def test_a_newer_gazette_does_not_make_an_earlier_failure_read_as_successful():
    """U6 proof 12: the earlier hash keeps its failed stage, whatever arrives later."""
    state = cycle.empty_state()
    cycle.mark_stopped(state, OLD.sha256, OLD.gazette_id, "ingest", 4, NOW)
    d = cycle.pick_candidate([OLD, NEW], "2026-10-01", state, ALL_OK)
    assert d.kind == "candidate" and d.sha256 == NEW.sha256       # the newer one is chosen
    assert state["hashes"][OLD.sha256]["status"] == "stopped"      # the old one is still stopped
    assert state["hashes"][OLD.sha256]["stage"] == "ingest"
    assert OLD.sha256 not in {h for h, e in state["hashes"].items() if e["status"] == "finished"}


# --- 1.9 transient stops leave the hash to be chosen again --------------------------------

def test_progress_is_kept_after_each_step_so_a_transient_stop_resumes_mid_cycle():
    """The ingest finished, so the dataset now reflects the gazette. Without a progress
    entry the next run would find nothing newer and the refresh would never run."""
    state = cycle.empty_state()
    cycle.mark_in_progress(state, NEW.sha256, NEW.gazette_id, "refresh", NOW)
    d = cycle.pick_candidate([NEW], "2026-11-19", state, ALL_OK)      # dataset already newest
    assert d.kind == "resume"
    assert d.stage == "refresh"
    assert d.sha256 == NEW.sha256


def test_a_hash_with_no_entry_after_a_transient_stop_is_chosen_again():
    state = cycle.empty_state()                                       # a held lock wrote nothing
    d = cycle.pick_candidate([NEW], "2026-11-12", state, ALL_OK)
    assert d.kind == "candidate"


def test_finishing_clears_the_progress_entry():
    state = cycle.empty_state()
    cycle.mark_in_progress(state, NEW.sha256, NEW.gazette_id, "tests", NOW)
    cycle.mark_finished(state, NEW.sha256, NEW.gazette_id, NOW)
    assert state["hashes"][NEW.sha256]["status"] == "finished"
    assert cycle.pick_candidate([NEW], "2026-11-12", state, ALL_OK).kind == "already_done"


# --- 1.10 the exit-code map -----------------------------------------------------------------

@pytest.mark.parametrize("outcome,code", [
    ("nothing_new", 0), ("ingested", 0), ("already_done", 0),
    ("refused", 1), ("stopped", 1), ("awaiting_diagnosis", 1),
    ("locked", 5), ("another_cycle", 5),
    ("dirty_tree", 6), ("publish_failed", 1),
])
def test_the_exit_code_of_each_outcome(outcome, code):
    assert cycle.exit_code_for(outcome) == code
    assert outcome in cycle.OUTCOMES


def test_bad_usage_is_exit_2_and_every_outcome_has_a_code():
    assert cycle.EXIT_USAGE == 2
    for outcome in cycle.OUTCOMES:
        assert isinstance(cycle.exit_code_for(outcome), int)


# --- 1.11 the record --------------------------------------------------------------------------

def test_a_record_holds_every_field_the_spec_names():
    rec = cycle.make_record(NOW, {"gazette": "unchanged", "p168": "changed"}, "refused",
                            sha256=NEW.sha256, gazette_id=NEW.gazette_id,
                            last_stage="detect", failed_stage="ingest", exit_code=4,
                            reason="tripwire")
    for key in ("time", "polls", "sha256", "gazette_id", "last_stage", "failed_stage",
                "exit_code", "outcome", "reason"):
        assert key in rec, key
    assert rec["polls"] == {"gazette": "unchanged", "p168": "changed"}
    assert rec["outcome"] == "refused" and rec["exit_code"] == 4


def test_a_run_that_found_nothing_is_recorded_as_such():
    rec = cycle.make_record(NOW, {"gazette": "unchanged", "p168": "unchanged"}, "nothing_new")
    assert rec["outcome"] == "nothing_new"
    assert rec["exit_code"] == 0 and rec["failed_stage"] == "" and rec["sha256"] == ""


def test_an_unknown_outcome_is_refused():
    with pytest.raises(ValueError):
        cycle.make_record(NOW, {}, "it went fine")


def test_no_record_field_keys_on_a_coordinate_or_a_project_id():
    rec = cycle.make_record(NOW, {}, "nothing_new")
    keys = " ".join(rec).lower()
    for banned in ("recno", "project_id", "編號"):
        assert banned not in keys
    assert not any("recno" in str(k) or "project_id" in str(k) for k in rec["polls"])


def test_a_gap_is_detectable_from_the_records_alone():
    records = [cycle.make_record("2026-11-20T06:00:00+08:00", {}, "nothing_new"),
               cycle.make_record("2026-11-21T06:00:00+08:00", {}, "nothing_new")]
    assert cycle.newest_record_age_hours(records, "2026-11-21T07:00:00+08:00") == pytest.approx(1.0)
    assert cycle.newest_record_age_hours(records, "2026-11-23T06:00:00+08:00") == pytest.approx(48.0)
    assert cycle.newest_record_age_hours([], NOW) is None


# --- 1.12 the owned paths and the dirty-tree decision (U6 proof 9) ------------------------------

def test_every_owned_path_exists_in_the_repository():
    """So the list cannot drift silently when a file moves."""
    for rel in cycle.OWNED_PATHS:
        assert (ROOT / rel).exists(), rel


def test_the_owned_paths_cover_what_an_ingest_and_the_check_rewrite():
    owned = set(cycle.OWNED_PATHS)
    for rel in ("data/projects.json", "viewer/projects.data.js", "viewer/index.html",
                "docs/etl_process.html", "docs/domain-model.html", "docs/release-diff.html",
                "docs/coverage-report.html", "openspec/config.yaml"):
        assert rel in owned, rel


def test_an_owned_path_dirty_with_a_gazette_ready_refuses():
    assert cycle.dirty_decision(True, ["viewer/projects.data.js"]) == "refuse"


def test_an_unrelated_dirty_path_does_not_refuse():
    assert cycle.dirty_decision(True, []) == "run"


def test_a_dirty_owned_path_on_a_quiet_day_does_not_stop_the_run():
    assert cycle.dirty_decision(False, ["viewer/projects.data.js"]) == "run"


# --- the dataset's date is read from the head of the payload --------------------------------------

def test_the_dataset_date_is_read_from_the_payload_head():
    head = 'window.PROJECTS = {"schema_version": 2, "generated_at": "x", "published_date": "2026-11-12", "counts": {}}'
    assert cycle.parse_published_date(head) == "2026-11-12"


def test_a_payload_head_without_a_date_is_an_error_not_a_default():
    with pytest.raises(ValueError):
        cycle.parse_published_date('window.PROJECTS = {"schema_version": 2}')


# --- 6.2 the report publication ---------------------------------------------------------------
# openspec change a4-pdf-cycle-coordinator, group 6 (design D13). The operator amended U-D2 for
# the release-diff report only: after a FINISHED ingest the cycle runs the existing
# publish_release_diff.py. Its failure is its own outcome and never undoes the ingest.

@pytest.mark.parametrize("code", [1, 2, 5, 137])
def test_a_publication_that_exits_non_zero_is_a_failed_publication(code):
    """Exit 1 is a push that failed, 2 a tree that is not fit to publish from. Neither is a
    refusal of the data and neither is transient: the ingest has finished."""
    assert cycle.classify_exit("publish_report", code) == "publish_failed"


def test_a_publication_that_exits_zero_is_ok_and_a_timeout_is_a_failure():
    assert cycle.classify_exit("publish_report", 0) == "ok"
    assert cycle.classify_exit("publish_report", 0, timed_out=True) == "publish_failed"


def test_a_cycle_on_a_chosen_archive_root_never_publishes_for_real():
    """A smoke run on a temporary archive must not push the real report."""
    chosen = {s.name: s for s in cycle.build_steps(python="py", archive_root="/tmp/a")}
    assert "--dry-run" in chosen["publish_report"].argv
    default = {s.name: s for s in cycle.build_steps(python="py")}
    assert "--dry-run" not in default["publish_report"].argv
