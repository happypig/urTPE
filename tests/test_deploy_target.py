# -*- coding: utf-8 -*-
"""The published site is the build this repository holds, and its address is written down.

Test-writing group 1 of deployment-verification.

`https://happypig.github.io/urtPE/viewer/index.html` served a stale build and nobody
noticed for several commits. The URL that was open is also the wrong capitalisation --
the repository is `urTPE` and Pages paths are case-sensitive, so `/urtPE/` answers with
GitHub's "Page not found" document while the browser keeps rendering a cached copy. A
Taipei case that had been in the committed payload the whole time looked missing.

Two things were unverified, and only the second is interesting: the deployed address was
recorded nowhere, and a deployed build was never compared to the committed build. The
comparison is exact rather than heuristic -- the served bytes are byte-identical to the
HEAD blob -- so staleness is a decidable question.

Everything here is offline. `AGENTS.md` records that the suite must stay that way, and it
matters concretely: the capitalisation check is exactly the test that would have caught
this, and a check that needs the network would not have run before the mistake.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TARGET = ROOT / "viewer" / "deploy.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _load_target() -> dict:
    return json.loads(TARGET.read_text(encoding="utf-8"))


def _remote_repo() -> tuple[str, str]:
    """owner and repository name, exactly as git spells them.

    Handles both remote spellings: https://github.com/owner/repo.git and
    git@github.com:owner/repo.git.
    """
    url = _git("remote", "get-url", "origin")
    slug = url.split("://")[-1].replace(":", "/").rstrip("/")
    if slug.endswith(".git"):
        slug = slug[:-4]
    parts = slug.split("/")
    return parts[-2], parts[-1]


def _skip_if_absent():
    if not TARGET.exists():
        pytest.skip("deploy target not recorded yet")


# --- 1.1: the target is recorded once --------------------------------------

def test_the_deploy_target_is_recorded_in_one_place():
    _skip_if_absent()
    data = _load_target()

    assert _git("ls-files", "--error-unmatch", "viewer/deploy.json") == "viewer/deploy.json", (
        "an unrecorded address is knowledge that lives only in a browser tab")
    for field in ("owner", "repo", "pages_base", "artifacts"):
        assert data.get(field), "%s is required" % field
    assert data["artifacts"], "an empty artifact list checks nothing"


# --- 1.2: capitalisation, the whole point ---------------------------------

def test_the_recorded_pages_path_matches_the_remote_repository_name_case():
    _skip_if_absent()
    _owner, name = _remote_repo()
    base = _load_target()["pages_base"].rstrip("/")
    recorded = base.rsplit("/", 1)[-1]

    assert recorded == name, (
        "GitHub Pages paths are case-sensitive: the repository is %r but the recorded path "
        "ends %r, so /%s/ is a different site that serves GitHub's 'Page not found' "
        "document while the browser keeps showing a cached render. /%s/ is the real one."
        % (name, recorded, recorded, name))


def test_a_wrong_capitalisation_is_reported_as_such(capsys):
    """The message has to name the cause, not just fail.

    A bare 404 from Pages is indistinguishable from an unbuilt site, and that ambiguity is
    what sent the original investigation toward the data instead of the URL.
    """
    from scripts.check_deploy import case_mismatch_note
    _owner, name = _remote_repo()

    note = case_mismatch_note("https://happypig.github.io/urtPE/")

    assert name.lower() in note.lower(), note
    assert "case" in note.lower() or "capital" in note.lower(), note
    assert "https://happypig.github.io/%s/" % name in note, (
        "the note must hand back the corrected address, not only complain")


# --- 1.3: the base is well formed ------------------------------------------

def test_the_recorded_base_is_a_pages_url_for_that_repository():
    _skip_if_absent()
    data = _load_target()
    owner, name = _remote_repo()
    m = re.match(r"^https://([\w.-]+)\.github\.io/([^/]+)/?$", data["pages_base"])

    assert m, "pages_base must be https://<owner>.github.io/<repo>[: /path]"
    assert m.group(1).lower() == owner.lower(), "host owner %r != remote %r" % (m.group(1), owner)
    assert m.group(2) == name, "the path segment must match the repository name exactly"
    assert data["owner"] == owner and data["repo"] == name, (
        "the record must agree with the remote, or it is describing some other site")


# --- 1.4: every listed artifact is really in the repo ----------------------

def test_every_listed_artifact_is_tracked_by_git():
    _skip_if_absent()
    tracked = set(_git("ls-files").splitlines())
    missing = [a for a in _load_target()["artifacts"] if a not in tracked]

    assert missing == [], (
        "%r are listed as deploy artifacts but are not tracked, so the check would compare "
        "them against nothing" % (missing,))


# --- 1.5: the verdict distinguishes the three states ------------------------

def test_the_verdict_distinguishes_fresh_stale_and_missing():
    from scripts.check_deploy import verdict

    committed = b'window.PROJECTS = {"projects": []};\n'

    assert verdict(committed, committed) == "fresh", "identical bytes are current"
    assert verdict(b'window.PROJECTS = {"projects": [1]};\n', committed) == "stale", (
        "served but different is a superseded build, which must not read as healthy")
    assert verdict(b'same length, other bytes'[:len(committed)], committed) == "stale"
    assert verdict(None, committed) == "missing", "absent is not stale"
    assert verdict(committed, None) == "untracked", "nothing committed to compare against"


# --- 1.6: a 404 carries the hint -------------------------------------------

def test_a_404_is_reported_with_the_case_sensitivity_hint():
    from scripts.check_deploy import describe_fetch

    note = describe_fetch(404, "https://happypig.github.io/urtPE/viewer/index.html")

    assert "case" in note.lower() or "capital" in note.lower(), note
    assert "404" in note


def test_a_200_is_not_given_the_case_hint():
    from scripts.check_deploy import describe_fetch

    assert "case" not in describe_fetch(200, "https://x/").lower()


# --- 1.7: docs cannot drift from the record -------------------------------

def test_agents_records_the_canonical_url():
    _skip_if_absent()
    base = _load_target()["pages_base"].rstrip("/")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert base in agents, (
        "AGENTS.md must cite the recorded base; a second copy of the address is exactly the "
        "thing that goes stale")


# --- 1.8: stated counts are checkable -------------------------------------

def test_the_recorded_record_count_matches_the_emitted_payload():
    text = (ROOT / "viewer" / "projects.data.js").read_text(encoding="utf-8")
    payload = json.loads(text[text.find("{"):text.rfind("}") + 1])
    config = (ROOT / "openspec" / "config.yaml").read_text(encoding="utf-8")
    stated = re.search(r"([\d,]+)\s+approvals", config)

    assert stated, "config.yaml must state the approval count for this to check anything"
    n = int(stated.group(1).replace(",", ""))

    assert n == payload["counts"]["records"], (
        "config.yaml says %d approvals, the emitted payload carries %d. That figure is the "
        "project context an analyst or an assistant reads before proposing a change."
        % (n, payload["counts"]["records"]))