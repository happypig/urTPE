"""The release-diff report's published contracts.

The report is a published page, so three things must hold of the committed
file:

- the viewer's header links to it, and it links back (a relative path each
  way, so the pair works from `file://` as well as from the published site);
- it is self-contained, so it renders with no network;
- the deploy record lists it, so `scripts/check_deploy.py` compares its served
  bytes against the committed build instead of leaving it unchecked.

These read the committed files rather than the generator, because the contract
is about what is published, not about how it is produced.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "release-diff.html"
VIEWER_INDEX = ROOT / "viewer" / "index.html"
DEPLOY = ROOT / "viewer" / "deploy.json"


def _report() -> str:
    if not REPORT.exists():
        pytest.skip("the report has not been generated")
    return REPORT.read_text(encoding="utf-8")


import pytest  # noqa: E402  (after the skip helper, so the import order reads plainly)


# --- the two links ----------------------------------------------------------

def test_the_report_links_back_to_the_viewer():
    """A relative link, so the pair works from a file:// page as well as from
    the published site."""
    html = _report()
    m = re.search(r'<a class="backlink" href="([^"]+)">([^<]*)</a>', html)
    assert m, "the report carries no back link"
    href = m.group(1)
    assert href == "../viewer/index.html", (
        "the back link must be relative and point at the viewer; got %r" % href)
    # The target must resolve: the report lives in docs/, the viewer in viewer/.
    assert (REPORT.parent / href).resolve() == VIEWER_INDEX.resolve()


def test_the_viewer_header_links_to_the_report():
    """In the markup, not added by script: a reader who lands on a payload
    that fails to load can still reach the report.

    The header carries more than one navlink now — the policy dashboard
    joined it — so the report is found by its target, not by being first.
    """
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    assert links, "the viewer's header carries no links"
    report_links = [(h, t) for h, t in links if h == "../docs/release-diff.html"]
    assert report_links, (
        "the viewer's header carries no link to the release-diff report; "
        "it carries %r" % (links,))
    href = report_links[0][0]
    assert (VIEWER_INDEX.parent / href).resolve() == REPORT.resolve()


def test_the_viewer_link_label_is_the_one_a_reader_would_look_for():
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    labels = [t for h, t in links if h == "../docs/release-diff.html"]
    assert labels, "the report link carries no label; the header has %r" % (links,)
    assert labels[0] == "歷次公報差異"


# --- the report is self-contained --------------------------------------------

def test_the_report_makes_no_external_request():
    """No script, stylesheet, font or image from another origin. The page is
    published as a file, and it must render with no network."""
    html = _report()
    external = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    # A link to the publisher's PDF is a link, not a request: the browser
    # fetches it only when the reader clicks. Anything in src= is a request.
    in_src = re.findall(r'src="(https?://[^"]+)"', html)
    assert in_src == [], "the report loads %s from another origin" % in_src
    assert not re.search(r'<link[^>]+href="https?://', html), (
        "the report pulls a stylesheet from another origin")
    assert not re.search(r'@import\s+url\(https?://', html)


def test_the_report_carries_no_script_that_reaches_the_network():
    html = _report()
    for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S):
        assert "XMLHttpRequest" not in script
        assert "fetch(" not in script
        assert "new Image" not in script


# --- the deploy record ------------------------------------------------------

def test_the_report_is_listed_as_a_deploy_artifact():
    """Otherwise its served bytes are never compared against the committed
    build, and it can serve superseded content while every check passes."""
    data = json.loads(DEPLOY.read_text(encoding="utf-8"))
    assert "docs/release-diff.html" in data["artifacts"], (
        "the release-diff report is not listed among the deploy artifacts; "
        "the deployment check does not cover it")


def test_every_deploy_artifact_is_tracked():
    """The deploy check compares against the HEAD blob; a listed artifact git
    does not know about compares against nothing."""
    import subprocess

    tracked = set(subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True,
        check=True).stdout.splitlines())
    data = json.loads(DEPLOY.read_text(encoding="utf-8"))
    missing = [a for a in data["artifacts"] if a not in tracked]
    assert missing == [], (
        "%r are listed as deploy artifacts but are not tracked by git" % (missing,))


# --- the per-release links --------------------------------------------------

def test_each_release_row_carries_a_link_or_says_it_has_none():
    """A release either links to its document or says the URL is unknown. It
    must never carry a link to a document that is not its own."""
    html = _report()
    section = html[html.find('<section id="releases">'):]
    section = section[:section.find("</section>")]
    rows = re.findall(r"<tr><td><b>.*?</tr>", section, re.S)
    assert rows, "the releases table is empty"
    for row in rows:
        date = re.search(r"<b>([^<]*)</b>", row).group(1)
        has_link = 'class="pdf-link"' in row
        has_none = "muted-cell" in row
        assert has_link != has_none, (
            "the row for %s carries neither a link nor a statement that the "
            "URL is unknown" % date)


def test_a_release_without_a_link_does_not_point_at_the_publisher():
    """The publisher's live URL serves the newest document. An older release
    carrying it would send a reader to the wrong gazette while the link
    looked correct."""
    html = _report()
    section = html[html.find('<section id="releases">'):]
    section = section[:section.find("</section>")]
    rows = re.findall(r"<tr><td><b>.*?</tr>", section, re.S)
    linked_dates = []
    for row in rows:
        date = re.search(r"<b>([^<]*)</b>", row).group(1)
        m = re.search(r'class="pdf-link" href="([^"]+)"', row)
        if m:
            linked_dates.append((date, m.group(1)))
    assert linked_dates, "no release carries a link at all"
    # Two releases may not share one URL: a URL serves one document.
    urls = [u for _, u in linked_dates]
    assert len(urls) == len(set(urls)), (
        "two releases carry the same URL: %r" % (linked_dates,))


def test_the_two_kinds_of_link_are_labelled_differently():
    html = _report()
    labels = set(re.findall(r'class="pdf-link"[^>]*>([^<]*)</a>', html))
    if len(labels) > 1:
        # More than one kind of link is present; they must not share a label.
        assert len(labels) == len(set(labels))


# --- the publication step ---------------------------------------------------

def test_the_step_stages_only_the_paths_it_owns():
    """The working tree routinely carries another session's changes. A
    scheduled step that swept them into a commit would publish work nobody
    had finished."""
    from scripts.publish_release_diff import OWNED_PATHS

    assert OWNED_PATHS == ["docs/release-diff.html"], (
        "the step owns one path; anything else in OWNED_PATHS would be swept "
        "into an unattended commit")
    for path in OWNED_PATHS:
        assert not path.startswith("viewer/"), (
            "the step must not stage anything under viewer/; the emitted "
            "dataset is only written by an explicit ingestion")
        assert not path.startswith("data/"), (
            "the step must not stage anything under data/")


def test_the_step_sees_a_dirty_generator_as_a_reason_to_stop():
    """A working-tree change to the generator would change what "regenerate"
    means, and the published report would be one no commit explains."""
    from scripts.publish_release_diff import GENERATOR_PATHS, PublishError, check_tree

    assert "scripts/release_diff_report.py" in GENERATOR_PATHS
    assert "scripts/release_diff.py" in GENERATOR_PATHS
    # The tree right now must be publishable: the generator is committed.
    try:
        check_tree()
    except PublishError as exc:
        pytest.fail("the tree is not publishable: %s" % exc)


def test_the_commit_takes_only_the_paths_it_owns(tmp_path, monkeypatch):
    """Another session's staged work must not ride along in the step's commit.

    The step's `git add` is path-scoped, but a `git commit` without a path
    limit takes everything in the index — and another session's work is in
    the index. Measured 2026-11-09: the step's commit carried
    `other_session_work.py` along with the report.

    The spec asks for the stronger of the two properties: an unrelated
    modification is neither committed nor discarded. A path-limited commit
    gives both; the other session's file stays staged for them.
    """
    import subprocess

    from scripts import publish_release_diff

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, text=True,
            encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    (repo / "docs").mkdir()
    (repo / "docs" / "release-diff.html").write_text("the old report", encoding="utf-8")
    (repo / "other_session_work.py").write_text("# another session\n", encoding="utf-8")
    git("add", "docs/release-diff.html")
    git("commit", "-qm", "base")

    # Another session has staged its work and has not committed it.
    git("add", "other_session_work.py")

    monkeypatch.setattr(publish_release_diff, "ROOT", repo)
    (repo / "docs" / "release-diff.html").write_text("the new report", encoding="utf-8")

    assert publish_release_diff.commit("publish the report") is True

    committed = git("show", "--name-only", "--format=", "HEAD").stdout.split()
    assert "docs/release-diff.html" in committed, "the report was not committed"
    assert "other_session_work.py" not in committed, (
        "the step committed another session's staged work: %r" % (committed,))
    still_staged = git("diff", "--cached", "--name-only").stdout.split()
    assert "other_session_work.py" in still_staged, (
        "the step discarded another session's staged work")


def test_the_step_reports_a_push_that_did_not_land(tmp_path, monkeypatch):
    """A push that exits 0 without moving the remote is not a push.

    Measured 2026-11-09: on a detached HEAD the step's `git push origin main`
    pushes the `main` ref, not the commit the step just made on HEAD. Git
    answers "Everything up-to-date" and exits 0, the remote does not move,
    and the step printed "published" and exited 0 — a silent success.

    The step's promise is that the published page is never a version behind
    the archive. So it must check that the remote actually holds the commit,
    and fail when it does not.
    """
    import subprocess

    from scripts import publish_release_diff

    repo = tmp_path / "repo"
    repo.mkdir()
    remote = tmp_path / "remote.git"

    def git(*args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=str(cwd or repo), capture_output=True, text=True,
            encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    (repo / "docs").mkdir()
    (repo / "docs" / "release-diff.html").write_text("the old report", encoding="utf-8")
    git("add", "docs/release-diff.html")
    git("commit", "-qm", "base")
    git("branch", "-M", "main")

    git("init", "-q", "--bare", str(remote))
    git("remote", "add", "origin", str(remote))
    git("push", "-q", "origin", "main")

    # A detached HEAD. The commit the step makes lands on HEAD, while
    # `git push origin main` pushes the `main` ref, which has not moved —
    # so git answers "Everything up-to-date" and exits 0.
    git("checkout", "-q", "--detach", "HEAD")

    monkeypatch.setattr(publish_release_diff, "ROOT", repo)
    (repo / "docs" / "release-diff.html").write_text("the new report", encoding="utf-8")

    assert publish_release_diff.commit("publish the report") is True
    head = git("rev-parse", "HEAD").stdout.strip()

    with pytest.raises(publish_release_diff.PublishError):
        publish_release_diff.push()

    # The remote must not hold the commit, or the test proves nothing.
    remote_head = git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip()
    assert remote_head != head, (
        "the remote holds the commit; this test no longer covers the case")


def test_the_step_writes_nothing_under_the_emitted_tree():
    """The emitted dataset is only ever written by an explicit ingestion. The
    step's source must not name data/ or viewer/ as something it writes."""
    from scripts import publish_release_diff

    source = (Path(publish_release_diff.__file__)).read_text(encoding="utf-8")
    assert "projects.data.js" not in source
    assert "projects.json" not in source
    assert "raw.tsv" not in source
    assert "clean.tsv" not in source
    assert "merged.tsv" not in source
