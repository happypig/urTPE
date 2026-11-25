# -*- coding: utf-8 -*-
"""A5 — the emission publisher (`scripts/publish_emission.py`).

openspec change a5-cycle-emission-publication, capability `pdf-cycle-coordinator`. The
publisher commits the emission paths in one path-limited commit and pushes `main`, verified
against the remote. It is modelled on `publish_release_diff.py`, and these tests follow that
script's: a REAL temporary git repository with a bare remote, with the module's `ROOT` pointed
at it. Nothing here touches the real repository or the network.
"""
from __future__ import annotations

import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import publish_emission as pub  # noqa: E402

EMISSION = pub.OWNED_PATHS


def _payload(records, projects=677):
    return ('window.PROJECTS = {"schema_version": 2, "generated_at": "x", '
            '"published_date": "2026-11-19", "counts": {"projects": %d, "records": %d}, '
            '"projects": []};' % (projects, records))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A temporary repository the publisher is pointed at, with a bare remote."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args, cwd=None):
        return subprocess.run(["git", *args], cwd=str(cwd or repo), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    box = types.SimpleNamespace(repo=repo, git=git, remote=tmp_path / "remote.git")

    def write(rel, text):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    box.write = write
    # the base commit: every emission path, a payload of 1,448 records, and one code file
    for rel in EMISSION:
        write(rel, "base %s" % rel)
    write("viewer/projects.data.js", _payload(1448))
    write("urtpe/code.py", "x = 1\n")
    write("scripts/tool.py", "y = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    git("branch", "-M", "main")
    git("init", "-q", "--bare", str(box.remote))
    git("remote", "add", "origin", str(box.remote))
    git("push", "-q", "origin", "main")
    monkeypatch.setattr(pub, "ROOT", repo)
    return box


def _remote_head(box):
    return box.git("ls-remote", "origin", "refs/heads/main").stdout.split()[0]


def _emit(box, records=1450):
    """Rewrite every emission path, as an ingest does."""
    for rel in EMISSION:
        box.write(rel, "new %s" % rel)
    box.write("viewer/projects.data.js", _payload(records))


# --- 1.1 the path-limited commit and the verified push -----------------------

def test_the_owned_paths_are_the_emission_the_dashboard_and_the_config_sentence():
    """Nine paths. openspec/config.yaml carries the emission's own record count and date, which
    post_ingest_check rewrites; committed with the emission it stays self-consistent, and no
    cycle leaves it dirty for the next gazette to refuse on."""
    assert set(EMISSION) == {
        "data/projects.json", "data/raw.tsv", "data/clean.tsv", "data/merged.tsv",
        "data/review_report.txt", "viewer/projects.data.js", "viewer/index.html",
        "viewer/dashboard.html", "openspec/config.yaml"}


def test_the_emission_is_committed_in_one_commit_and_pushed(sandbox):
    _emit(sandbox)
    assert pub.main([]) == 0
    files = set(sandbox.git("show", "--name-only", "--format=", "HEAD").stdout.split())
    assert files == set(EMISSION)
    assert _remote_head(sandbox) == sandbox.git("rev-parse", "HEAD").stdout.strip()


def test_another_sessions_staged_file_is_neither_committed_nor_discarded(sandbox):
    _emit(sandbox)
    sandbox.write("docs/other_session.md", "their work")
    sandbox.git("add", "docs/other_session.md")
    assert pub.main([]) == 0
    files = set(sandbox.git("show", "--name-only", "--format=", "HEAD").stdout.split())
    assert "docs/other_session.md" not in files
    still_staged = sandbox.git("diff", "--cached", "--name-only").stdout.split()
    assert still_staged == ["docs/other_session.md"], "their file was committed or unstaged"
    assert (sandbox.repo / "docs" / "other_session.md").read_text(encoding="utf-8") == "their work"


def test_a_push_that_did_not_land_exits_1_and_names_it(sandbox, capsys):
    _emit(sandbox)
    sandbox.git("remote", "set-url", "origin", str(sandbox.repo.parent / "no-such-remote.git"))
    assert pub.main([]) == 1
    assert "push" in capsys.readouterr().err.lower()
    # the commit stays local, so a later run can push it
    assert sandbox.git("log", "-1", "--format=%s").stdout.strip().startswith("chore: emit the")


def test_a_retry_after_a_failed_push_pushes_the_commit_that_is_ahead(sandbox):
    _emit(sandbox)
    sandbox.git("remote", "set-url", "origin", str(sandbox.repo.parent / "no-such-remote.git"))
    assert pub.main([]) == 1
    sandbox.git("remote", "set-url", "origin", str(sandbox.remote))
    assert pub.main([]) == 0
    assert _remote_head(sandbox) == sandbox.git("rev-parse", "HEAD").stdout.strip()


def test_nothing_to_publish_commits_nothing_and_exits_0(sandbox):
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert pub.main([]) == 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


def test_a_detached_head_push_that_leaves_the_remote_behind_is_a_failure(sandbox):
    """`git push origin main` on a detached HEAD says 'up-to-date' and exits 0 while the
    commit lives only on HEAD (measured 2026-11-09 for the pages publisher)."""
    _emit(sandbox)
    sandbox.git("checkout", "-q", "--detach")
    assert pub.main([]) == 1


# --- 1.2 the no-drop guard ----------------------------------------------------

def test_a_lower_record_count_commits_and_pushes_nothing(sandbox, capsys):
    _emit(sandbox, records=1400)             # the committed payload holds 1,448
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert pub.main([]) != 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before, "a commit was made"
    assert "count" in capsys.readouterr().err.lower()
    assert _remote_head(sandbox) == before


@pytest.mark.parametrize("records", [1448, 1449, 1500])
def test_an_equal_or_higher_record_count_proceeds(sandbox, records):
    _emit(sandbox, records=records)
    # an equal count with different content still publishes: only a DROP stops
    assert pub.main([]) == 0
    assert _remote_head(sandbox) == sandbox.git("rev-parse", "HEAD").stdout.strip()


def test_an_unreadable_count_exits_2_and_commits_nothing(sandbox):
    _emit(sandbox)
    sandbox.write("viewer/projects.data.js", "window.PROJECTS = {};")
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert pub.main([]) == 2
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


# --- 1.3 the code-clean check -------------------------------------------------

@pytest.mark.parametrize("path", ["urtpe/code.py", "scripts/tool.py"])
def test_uncommitted_code_exits_2_and_commits_nothing(sandbox, path):
    _emit(sandbox)
    sandbox.write(path, "edited = True\n")
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert pub.main([]) == 2
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


def test_an_untracked_file_in_the_code_directories_does_not_stop_it(sandbox):
    _emit(sandbox)
    sandbox.write("scripts/probe_scratch.py", "print(1)\n")      # untracked
    assert pub.main([]) == 0


# --- 1.4 the no-prompt environment, the time limit, the dry run ---------------

def test_every_git_command_carries_the_no_prompt_environment(sandbox, monkeypatch):
    seen = []
    real = subprocess.run

    def spy(cmd, *a, **kw):
        if cmd and cmd[0] == "git":
            seen.append(kw.get("env") or {})
        return real(cmd, *a, **kw)

    monkeypatch.setattr(subprocess, "run", spy)
    _emit(sandbox)
    assert pub.main([]) == 0
    assert seen, "no git command was observed"
    for env in seen:
        assert env.get("GIT_TERMINAL_PROMPT") == "0"
        assert env.get("GCM_INTERACTIVE") == "never"


def test_a_push_over_its_time_limit_is_a_failure_that_names_the_credential(sandbox, monkeypatch, capsys):
    real = pub.run

    def slow(*args, cwd=None):
        if len(args) > 1 and args[0] == "git" and args[1] == "push":
            raise subprocess.TimeoutExpired(args, 120)
        return real(*args, cwd=cwd)

    monkeypatch.setattr(pub, "run", slow)
    _emit(sandbox)
    assert pub.main([]) == 1
    assert "credential" in capsys.readouterr().err.lower()


def test_a_remote_check_over_its_time_limit_is_a_failure(sandbox, monkeypatch):
    real = pub.run

    def slow(*args, cwd=None):
        if len(args) > 1 and args[0] == "git" and args[1] == "ls-remote":
            raise subprocess.TimeoutExpired(args, 120)
        return real(*args, cwd=cwd)

    monkeypatch.setattr(pub, "run", slow)
    _emit(sandbox)
    assert pub.main([]) == 1


def test_a_dry_run_commits_and_pushes_nothing(sandbox):
    _emit(sandbox)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert pub.main(["--dry-run"]) == 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before
    assert _remote_head(sandbox) == before


def test_a_dry_run_still_applies_the_guards(sandbox):
    _emit(sandbox, records=1400)
    assert pub.main(["--dry-run"]) != 0
