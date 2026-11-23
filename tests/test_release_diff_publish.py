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

def test_the_report_links_back_to_the_about_page():
    """A relative link, so the pair works from a file:// page as well as from
    the published site. The back link pointed at the viewer until the 關於
    page replaced the header's report link (openspec: about-page-links) — the
    chain is now report → 關於 → viewer."""
    html = _report()
    m = re.search(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    assert m, "the report carries no back link"
    href = m.group(1)
    assert href == "../viewer/about.html", (
        "the back link must point at the about page; got %r" % href)
    about = ROOT / "viewer" / "about.html"
    assert (REPORT.parent / href).resolve() == about.resolve()
    assert "回專案歷史圖" not in html, (
        "the report still carries the old 回專案歷史圖 back link; the 關於 "
        "page replaces it")
    assert m.group(2) == "關於"


def test_the_viewer_header_links_to_the_about_page():
    """In the markup, not added by script: a reader who lands on a payload
    that fails to load can still reach the about page, and through it the
    report. The header's direct report link moved to the about page when the
    關於 page replaced it (openspec: about-page)."""
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    about_links = [(h, t) for h, t in links if h == "about.html"]
    assert about_links, (
        "the viewer's header carries no 關於 link; it carries %r" % (links,))
    href = about_links[0][0]
    assert (VIEWER_INDEX.parent / href).resolve() == (ROOT / "viewer" / "about.html").resolve()


def test_the_about_page_links_to_the_report():
    """The report is still reachable from the site, one hop through the about
    page: a relative path, labelled the way a reader would look for it."""
    about = ROOT / "viewer" / "about.html"
    if not about.exists():
        pytest.fail("viewer/about.html does not exist")
    html = about.read_text(encoding="utf-8")
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', html)
    report_links = [(h, t) for h, t in links if h == "../docs/release-diff.html"]
    assert report_links, (
        "the about page carries no link to the release-diff report; "
        "it links %r" % (links,))
    assert report_links[0][1] == "歷次公報差異"
    assert (about.parent / report_links[0][0]).resolve() == REPORT.resolve()


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
    expected = ["viewer/index.html", "viewer/about.html",
                "viewer/app.js", "viewer/app.css",
                "viewer/projects.data.js", "viewer/dashboard.html",
                "viewer/dashboard.js", "viewer/dashboard.css",
                "docs/release-diff.html", "docs/coverage-report.html",
                "docs/domain-model.html"]
    for path in expected:
        assert path in data["artifacts"], (
            "%r is published but the deploy record does not name it; its "
            "served bytes are never checked" % path)


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


# --- "changed" means: differs from the COMMITTED report ------------------------------------------
#
# openspec change a4-pdf-cycle-coordinator (design D13). The cycle runs post_ingest_check.py,
# which regenerates docs/release-diff.html, and only then this step. The step used to compare the
# regenerated report with its OWN copy from before the run. That copy was already the regenerated
# report, so the step answered "nothing to publish" and committed nothing (measured 2026-11-23
# with a unit probe). A person who ran the check and then the step by hand got the same answer.
# "Changed" must mean: differs, ignoring the generation stamp, from what is committed.
#
# Every test here runs in a temporary repository that the module is pointed at. Nothing real is
# touched, and no remote but a temporary bare one is ever pushed to.

STAMP_A = "2026-11-18T10:00:00+08:00"
STAMP_B = "2026-11-23T04:10:00+08:00"
STAMP_C = "2026-11-23T04:12:00+08:00"


def _page(body, stamp):
    return "<html><body>%s</body><p>generated %s</p></html>" % (body, stamp)


class _Done:
    returncode = 0
    stdout = ""
    stderr = ""


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A temporary repository that the publisher is pointed at."""
    import subprocess
    import types

    from scripts import publish_release_diff as pub

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args, cwd=None):
        return subprocess.run(["git", *args], cwd=str(cwd or repo), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    (repo / "docs").mkdir()
    report = repo / "docs" / "release-diff.html"
    box = types.SimpleNamespace(repo=repo, git=git, report=report, pub=pub, generated=None)
    real_run = pub.run

    def fake_run(*args, cwd=None):
        # the generator writes what the archive says; every git call is the real one, in the repo
        if len(args) >= 2 and str(args[1]).endswith("release_diff_report.py"):
            report.write_text(box.generated, encoding="utf-8")
            return _Done()
        return real_run(*args, cwd=cwd)

    monkeypatch.setattr(pub, "ROOT", repo)
    monkeypatch.setattr(pub, "REPORT", report)
    monkeypatch.setattr(pub, "run", fake_run)
    return box


def _commit_base(box, text):
    box.report.write_text(text, encoding="utf-8")
    box.git("add", "docs/release-diff.html")
    box.git("commit", "-qm", "base")
    box.git("branch", "-M", "main")


def test_a_report_already_regenerated_by_the_check_is_still_published(sandbox):
    _commit_base(sandbox, _page("old numbers", STAMP_A))
    # post_ingest_check.py already wrote the new report into the working tree ...
    sandbox.report.write_text(_page("new numbers", STAMP_B), encoding="utf-8")
    # ... and the generator now writes the same content under a later stamp
    sandbox.generated = _page("new numbers", STAMP_C)
    assert sandbox.pub.regenerate() is True
    assert "new numbers" in sandbox.report.read_text(encoding="utf-8"), (
        "the new report was put back to the old one")


def test_a_report_equal_to_the_committed_one_is_unchanged_and_stays_byte_identical(sandbox):
    base = _page("same numbers", STAMP_A)
    _commit_base(sandbox, base)
    sandbox.generated = _page("same numbers", STAMP_C)
    assert sandbox.pub.regenerate() is False
    assert sandbox.report.read_text(encoding="utf-8") == base


def test_a_stamp_only_difference_from_the_committed_report_is_not_a_change(sandbox):
    base = _page("same numbers", STAMP_A)
    _commit_base(sandbox, base)
    # a stamp-only dirty file, as a check run over an unchanged report leaves it
    sandbox.report.write_text(_page("same numbers", STAMP_B), encoding="utf-8")
    sandbox.generated = _page("same numbers", STAMP_C)
    assert sandbox.pub.regenerate() is False
    assert sandbox.report.read_text(encoding="utf-8") == base
    assert sandbox.git("status", "--porcelain", "--", "docs/release-diff.html").stdout.strip() == ""


def test_a_report_with_no_committed_copy_is_published(sandbox):
    (sandbox.repo / "README").write_text("x", encoding="utf-8")
    sandbox.git("add", "README")
    sandbox.git("commit", "-qm", "base")
    sandbox.generated = _page("first report", STAMP_C)
    assert sandbox.pub.regenerate() is True


def test_the_whole_step_commits_and_pushes_a_report_the_check_already_wrote(sandbox, tmp_path):
    remote = tmp_path / "remote.git"
    _commit_base(sandbox, _page("old numbers", STAMP_A))
    sandbox.git("init", "-q", "--bare", str(remote))
    sandbox.git("remote", "add", "origin", str(remote))
    sandbox.git("push", "-q", "origin", "main")
    sandbox.report.write_text(_page("new numbers", STAMP_B), encoding="utf-8")
    sandbox.generated = _page("new numbers", STAMP_C)
    assert sandbox.pub.main([]) == 0
    head = sandbox.git("rev-parse", "HEAD").stdout.strip()
    remote_head = sandbox.git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip()
    assert remote_head == head, "the report was not pushed"
    shown = sandbox.git("show", "HEAD:docs/release-diff.html").stdout
    assert "new numbers" in shown and "old numbers" not in shown


def test_a_dry_run_still_commits_nothing(sandbox):
    _commit_base(sandbox, _page("old numbers", STAMP_A))
    sandbox.report.write_text(_page("new numbers", STAMP_B), encoding="utf-8")
    sandbox.generated = _page("new numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.pub.main(["--dry-run"]) == 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


# --- the step publishes four generated pages as one set (design D13, widened 2026-11-23) --------
#
# The operator chose: after a finished ingest the cycle publishes the release-diff report, the
# coverage report, the domain model and the ETL page together, when the report changed or the
# payload's project or record count changed. The rule lives in the script, so it holds for a hand
# run too. These tests extend the temporary-repository sandbox above with the four pages and a
# payload file. Nothing real is touched; the only remote is a temporary bare one.

PAGES = ["docs/release-diff.html", "docs/coverage-report.html",
         "docs/domain-model.html", "docs/etl_process.html"]


def _payload(projects, records):
    return ('window.PROJECTS = {"schema_version": 2, "generated_at": "x", '
            '"published_date": "2026-11-12", "counts": {"projects": %d, "records": %d}, '
            '"projects": []};' % (projects, records))


def _commit_set(box, report, payload=(676, 1448), pages=PAGES):
    """Commit the owned pages and a payload as the base, then name the branch main."""
    for rel in pages:
        path = box.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report if rel == PAGES[0] else "base %s" % rel, encoding="utf-8")
    if payload is not None:
        (box.repo / "viewer").mkdir(exist_ok=True)
        (box.repo / "viewer" / "projects.data.js").write_text(_payload(*payload), encoding="utf-8")
    box.git("add", ".")
    box.git("commit", "-qm", "base")
    box.git("branch", "-M", "main")


def _with_remote(box, tmp_path):
    remote = tmp_path / "remote.git"
    box.git("init", "-q", "--bare", str(remote))
    box.git("remote", "add", "origin", str(remote))
    box.git("push", "-q", "origin", "main")
    return remote


def _write(box, rel, text):
    path = box.repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _last_commit_files(box):
    return set(box.git("show", "--name-only", "--format=", "HEAD").stdout.split())


def test_when_the_report_changed_the_pages_that_differ_are_committed_together(sandbox, tmp_path):
    _commit_set(sandbox, _page("old numbers", STAMP_A))
    _with_remote(sandbox, tmp_path)
    # post_ingest_check.py regenerated three pages; the ETL page is unchanged
    _write(sandbox, "docs/release-diff.html", _page("new numbers", STAMP_B))
    _write(sandbox, "docs/coverage-report.html", "coverage NEW")
    _write(sandbox, "docs/domain-model.html", "domain NEW")
    # another session has staged work of its own
    _write(sandbox, "other_session_work.py", "# another session\n")
    sandbox.git("add", "other_session_work.py")
    sandbox.generated = _page("new numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()

    assert sandbox.pub.main([]) == 0

    assert sandbox.git("rev-parse", "HEAD").stdout.strip() != before
    assert _last_commit_files(sandbox) == {"docs/release-diff.html", "docs/coverage-report.html",
                                           "docs/domain-model.html"}
    assert "other_session_work.py" in sandbox.git("diff", "--cached", "--name-only").stdout.split()


def test_when_only_the_counts_changed_the_other_pages_are_committed_and_the_report_is_not(sandbox, tmp_path):
    base_report = _page("same numbers", STAMP_A)
    _commit_set(sandbox, base_report)
    _with_remote(sandbox, tmp_path)
    # an ingest left a new payload and regenerated the pages; the report did not change
    _write(sandbox, "viewer/projects.data.js", _payload(677, 1450))
    _write(sandbox, "docs/coverage-report.html", "coverage NEW")
    _write(sandbox, "docs/domain-model.html", "domain NEW")
    _write(sandbox, "docs/etl_process.html", "etl NEW")
    sandbox.generated = _page("same numbers", STAMP_C)

    assert sandbox.pub.main([]) == 0

    assert _last_commit_files(sandbox) == {"docs/coverage-report.html", "docs/domain-model.html",
                                           "docs/etl_process.html"}
    assert sandbox.report.read_text(encoding="utf-8") == base_report
    assert "viewer/projects.data.js" not in _last_commit_files(sandbox), (
        "the step committed the emitted payload")


def test_when_nothing_changed_nothing_is_committed_and_the_other_pages_are_left_alone(sandbox, tmp_path):
    _commit_set(sandbox, _page("same numbers", STAMP_A))
    _with_remote(sandbox, tmp_path)
    # a date-only difference in two pages: it may belong to an emission still waiting for review
    _write(sandbox, "docs/coverage-report.html", "coverage measured 2026-11-24")
    _write(sandbox, "docs/domain-model.html", "domain measured 2026-11-24")
    sandbox.generated = _page("same numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()

    assert sandbox.pub.main([]) == 0

    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before
    assert (sandbox.repo / "docs" / "coverage-report.html").read_text(encoding="utf-8") == "coverage measured 2026-11-24"
    assert (sandbox.repo / "docs" / "domain-model.html").read_text(encoding="utf-8") == "domain measured 2026-11-24"


def test_a_page_that_does_not_exist_is_skipped_and_is_not_an_error(sandbox, tmp_path):
    _commit_set(sandbox, _page("old numbers", STAMP_A), pages=["docs/release-diff.html"])
    _with_remote(sandbox, tmp_path)
    _write(sandbox, "docs/release-diff.html", _page("new numbers", STAMP_B))
    sandbox.generated = _page("new numbers", STAMP_C)
    assert sandbox.pub.main([]) == 0
    assert _last_commit_files(sandbox) == {"docs/release-diff.html"}


@pytest.mark.parametrize("generator", ["scripts/coverage_report.py", "scripts/coverage_checks.py",
                                       "scripts/sync_domain_model.py", "scripts/sync_etl_process.py",
                                       "scripts/doc_measurements.py"])
def test_a_dirty_generator_of_another_page_stops_the_step(sandbox, tmp_path, generator):
    _commit_set(sandbox, _page("old numbers", STAMP_A))
    _with_remote(sandbox, tmp_path)
    _write(sandbox, "docs/coverage-report.html", "coverage NEW")
    (sandbox.repo / "scripts").mkdir(exist_ok=True)
    _write(sandbox, generator, "# committed\n")
    sandbox.git("add", generator)
    sandbox.git("commit", "-qm", "generator")
    _write(sandbox, generator, "# an uncommitted edit\n")
    sandbox.generated = _page("new numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.pub.main([]) == 2
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


def test_counts_that_cannot_be_read_stop_the_step(sandbox, tmp_path):
    _commit_set(sandbox, _page("same numbers", STAMP_A))
    _with_remote(sandbox, tmp_path)
    _write(sandbox, "viewer/projects.data.js", 'window.PROJECTS = {"schema_version": 2};')
    sandbox.generated = _page("same numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.pub.main([]) == 2
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


def test_a_payload_absent_from_both_gives_no_counts_trigger(sandbox, tmp_path):
    _commit_set(sandbox, _page("same numbers", STAMP_A), payload=None)
    _with_remote(sandbox, tmp_path)
    sandbox.generated = _page("same numbers", STAMP_C)
    assert sandbox.pub.counts_changed() is False
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.pub.main([]) == 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before


def test_a_payload_present_only_in_the_working_tree_counts_as_a_change(sandbox, tmp_path):
    _commit_set(sandbox, _page("same numbers", STAMP_A), payload=None)
    _write(sandbox, "viewer/projects.data.js", _payload(676, 1448))
    assert sandbox.pub.counts_changed() is True


def test_a_retry_after_a_failed_push_pushes_the_commit_and_exits_zero(sandbox, tmp_path):
    remote = _with_remote_after_base(sandbox, tmp_path)
    _write(sandbox, "docs/release-diff.html", _page("new numbers", STAMP_B))
    sandbox.generated = _page("new numbers", STAMP_C)
    sandbox.git("remote", "set-url", "origin", str(tmp_path / "no-such-remote.git"))

    assert sandbox.pub.main([]) == 1                    # the commit is made, the push fails
    head = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip() != head

    sandbox.git("remote", "set-url", "origin", str(remote))
    assert sandbox.pub.main([]) == 0                    # nothing new to commit, but the push must land
    assert sandbox.git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip() == head


def _with_remote_after_base(box, tmp_path):
    _commit_set(box, _page("old numbers", STAMP_A))
    return _with_remote(box, tmp_path)


def test_a_dry_run_names_the_trigger_and_commits_nothing(sandbox, tmp_path, capsys):
    _commit_set(sandbox, _page("same numbers", STAMP_A))
    _write(sandbox, "viewer/projects.data.js", _payload(677, 1450))
    sandbox.generated = _page("same numbers", STAMP_C)
    before = sandbox.git("rev-parse", "HEAD").stdout.strip()
    assert sandbox.pub.main(["--dry-run"]) == 0
    assert sandbox.git("rev-parse", "HEAD").stdout.strip() == before
    out = capsys.readouterr().out
    assert "count" in out.lower() and "dry run" in out.lower()


def test_the_counts_are_read_from_the_head_of_the_payload():
    from scripts import publish_release_diff as pub

    assert pub.payload_counts('window.PROJECTS = {"counts": {"projects": 676, "records": 1448}, "projects": []}') == (676, 1448)
    assert pub.payload_counts('window.PROJECTS = {"counts":{"projects":1,"records":2}}') == (1, 2)
    with pytest.raises(pub.PublishError):
        pub.payload_counts('window.PROJECTS = {"schema_version": 2}')


def test_the_step_owns_exactly_the_four_generated_pages_and_nothing_under_the_emitted_tree():
    """Replaces `test_the_step_stages_only_the_paths_it_owns`, which pinned one path."""
    from scripts.publish_release_diff import OWNED_PATHS

    assert OWNED_PATHS == PAGES
    for path in OWNED_PATHS:
        assert path.startswith("docs/"), path
        assert not path.startswith(("data/", "viewer/")), (
            "the step must not stage anything under data/ or viewer/: the emitted dataset is "
            "only written by an explicit ingestion")


def test_the_step_reads_the_payload_but_never_writes_it():
    """Replaces the check that banned the string `projects.data.js` from the source. Reading the
    payload's counts is now part of the rule, so the guard is about writing."""
    from scripts import publish_release_diff

    source = Path(publish_release_diff.__file__).read_text(encoding="utf-8")
    assert not re.search(r"payload[^\n]*\.(write_text|write_bytes)\(|open\([^)\n]*payload[^)\n]*,\s*[\"']w",
                         source, re.I)
    for banned in ("raw.tsv", "clean.tsv", "merged.tsv", "projects.json"):
        assert banned not in source, banned
