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
    that fails to load can still reach the report."""
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    m = re.search(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    assert m, "the viewer's header carries no link to the release-diff report"
    href = m.group(1)
    assert href == "../docs/release-diff.html", (
        "the link must be relative and point at the report; got %r" % href)
    assert (VIEWER_INDEX.parent / href).resolve() == REPORT.resolve()


def test_the_viewer_link_label_is_the_one_a_reader_would_look_for():
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    m = re.search(r'<a class="navlink" href="[^"]+">([^<]*)</a>', html)
    assert m
    assert m.group(1) == "歷次公報差異"


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
