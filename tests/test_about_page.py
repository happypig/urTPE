"""The about page's published contracts.

`viewer/about.html` answers, in one place, the four questions a policy reader
arriving from PUMA.taipei has and the site's other pages do not answer: under
what license the content may be reused, where the data comes from and how it
was processed, how far the numbers can be trusted, and how to reach the
maintainer.

It replaces the viewer header's 歷次公報差異 link, so it also carries the
reachability contract that link used to hold: the release-diff report is
reachable from the site, by a relative path, in the markup rather than added
by script.

These read the committed file rather than a generator, because the page is
hand-written like the headers are — the contract is about what is published,
not about how it is produced.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
ABOUT = ROOT / "viewer" / "about.html"
VIEWER_INDEX = ROOT / "viewer" / "index.html"
DASHBOARD = ROOT / "viewer" / "dashboard.html"
DEPLOY = ROOT / "viewer" / "deploy.json"
RELEASE_DIFF = ROOT / "docs" / "release-diff.html"
COVERAGE_REPORT = ROOT / "docs" / "coverage-report.html"


@pytest.fixture(scope="module")
def about() -> str:
    if not ABOUT.exists():
        pytest.fail("viewer/about.html does not exist — the about page was "
                    "not written")
    return ABOUT.read_text(encoding="utf-8")


# --- the page exists and is zh_TW --------------------------------------------

def test_the_page_declares_traditional_chinese(about):
    m = re.search(r'<html[^>]*lang="([^"]+)"', about)
    assert m, "the page declares no language"
    assert m.group(1) == "zh-Hant", (
        "the about page is for zh_TW readers; got lang=%r" % m.group(1))


def test_the_page_has_a_title(about):
    m = re.search(r"<title>([^<]+)</title>", about)
    assert m and m.group(1).strip(), "the page carries no title"


# --- the license -------------------------------------------------------------

def test_the_license_is_stated_for_the_site_s_own_content(about):
    """CC BY 4.0, scoped to 本站. A license line that read as covering the
    government's data would be a claim this site cannot make."""
    assert "CC BY 4.0" in about or "CC0" not in about and "CC BY 4.0" in about, (
        "the page does not state CC BY 4.0")
    m = re.search(r"[^。\n]*CC BY 4\.0[^。\n]*。", about)
    assert m, "the license is not stated in a full sentence"
    sentence = m.group(0)
    assert "本站" in sentence, (
        "the license sentence is not scoped to the site's own content: %r"
        % sentence)


def test_the_upstream_data_is_covered_by_its_own_terms(about):
    """A separate line: the gazette and both portals follow their own terms.
    It must not sit inside the CC BY 4.0 sentence."""
    m = re.search(r"[^。\n]*(政府資料|公報|機關)[^。\n]*(授權|條款|規定|開放)[^。\n]*。", about)
    assert m, ("no line defers the upstream government data to its own terms; "
               "a reader could read the CC BY 4.0 line as covering it")
    lic = re.search(r"[^。\n]*CC BY 4\.0[^。\n]*。", about)
    assert lic and m.group(0) != lic.group(0), (
        "the upstream-terms line and the license line are the same sentence")


# --- the data sources and the processing -------------------------------------

def test_the_three_data_sources_are_named(about):
    assert "核定案件一覽表" in about, "the gazette is not named as a source"
    assert "gis.uro.taipei" in about, "the Taipei platform is not named"
    assert "twur.nlma.gov.tw" in about, "the national portal is not named"


def test_the_etl_abstract_states_the_flow(about):
    """Concise: from PDF to the per-project history graph the pages render,
    with the merge of repeat approvals named — the one step a reader cannot
    guess from looking at the gazette."""
    assert "歷史" in about or "歷程" in about, (
        "the abstract does not say what the pages render (the history graph)")
    assert re.search(r"(合併|整合|相似)", about), (
        "the abstract does not say how repeat approvals become one project")


def test_the_truncated_record_rule_is_stated(about):
    """The rule that keeps a short gazette from reading as a complete one:
    excluded and named, never repaired by inference."""
    m = re.search(r"[^。\n]*(截斷|排除)[^。\n]*。", about)
    assert m, "the page does not state what happens to truncated records"
    sentence = m.group(0)
    assert ("具名" in sentence or "列出" in sentence or "標示" in sentence
            or "排除" in sentence), (
        "the truncation sentence does not say the records are excluded and "
        "named: %r" % sentence)
    # Repair may be mentioned only to be negated (不以推測補值). An
    # affirmative repair word outside a 不/非/無 scope means the page
    # promises what the pipeline refuses to do.
    negated = re.search(r"(不|非|無|絕)[^。，]{0,6}(推測|推估|補值|修復)", sentence)
    affirmative = [m for m in re.finditer(r"(推測|推估|補值|修復)", sentence)
                   if not negated or m.start() > negated.end()]
    assert negated and not affirmative, (
        "the truncation sentence must negate repair, not promise it: %r"
        % sentence)


def test_the_full_etl_writeup_is_linked(about):
    m = re.search(r'<a[^>]+href="(\.\./docs/etl_process\.html[^"]*)"', about)
    assert m, "the full ETL write-up (docs/etl_process.html) is not linked"
    assert (ABOUT.parent / m.group(1)).resolve() == (
        ROOT / "docs" / "etl_process.html").resolve()


# --- the two reports and the policy tie-in -----------------------------------

def test_the_release_diff_report_is_linked(about):
    m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', about)
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', about)
    report_links = [(h, t) for h, t in links
                    if h == "../docs/release-diff.html"]
    assert report_links, (
        "the about page carries no link to the release-diff report; "
        "it links %r" % (links,))
    assert report_links[0][1] == "歷次公報差異", (
        "the release-diff link's label is not the one a reader would look "
        "for: %r" % (report_links[0][1],))
    assert (ABOUT.parent / report_links[0][0]).resolve() == RELEASE_DIFF.resolve()


def test_the_coverage_report_is_linked(about):
    """The coverage report was unreachable from the site before the about
    page — the point of this page is that it no longer is."""
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', about)
    cov = [(h, t) for h, t in links if h == "../docs/coverage-report.html"]
    assert cov, (
        "the about page carries no link to the coverage report; it links %r"
        % (links,))
    assert cov[0][1] == "資料覆蓋度報告"
    assert (ABOUT.parent / cov[0][0]).resolve() == COVERAGE_REPORT.resolve()


def test_each_report_has_a_one_sentence_abstract(about):
    """A reader must be able to decide whether to open the report. A bare
    link name does not do that; a section does not survive into tests."""
    text = re.sub(r"<[^>]+>", "", about)
    for label, marker in [
        ("release-diff", "公報"),
        ("coverage", "覆蓋"),
    ]:
        assert marker in text, "the %s abstract is missing" % label
    # the two abstracts name what each report establishes
    assert re.search(r"(總數|件數|專案數).{0,40}(不同|差異|變化)", text), (
        "the release-diff abstract does not say what the report establishes")
    assert re.search(r"(完整|不重複|覆蓋).{0,60}(證明|檢查|驗證)", text), (
        "the coverage abstract does not say what the report establishes")


def test_the_puma_policy_pages_are_linked(about):
    """The dashboard supports these two pages; the about page says so and
    links them, so a policy reader can see the connection both ways."""
    links = re.findall(r'<a[^>]+href="(https://puma\.taipei/[^"]+)"', about)
    assert links, "no PUMA policy page is linked"
    assert any(" policies" in l or "%E6%94%BF%E7%AD%96" in l for l in links), (
        "the PUMA links do not point at policy pages: %r" % links)
    assert any("pillar=h" in l for l in links), (
        "the housing policy page (pillar=h) is not linked")


def test_the_contact_is_the_threads_address(about):
    m = re.search(r'<a[^>]+href="(https://www\.threads\.com/[^"]+)"', about)
    assert m, "no contact link"
    assert m.group(1) == "https://www.threads.com/@twhappypig", (
        "the contact is not the maintainer's Threads address: %r"
        % m.group(1))


# --- self-contained ----------------------------------------------------------

def test_the_page_makes_no_request_to_render(about):
    """No script, no stylesheet from another file, no image. The page renders
    from `file://` with the network off; its palette is inline. A request the
    page issues on its own would fail from file:// or hang the render."""
    assert "<script" not in about, "the page carries a script tag"
    in_src = re.findall(r'src="(https?://[^"]+)"', about)
    assert in_src == [], "the page loads %s from another origin" % in_src
    assert not re.search(r'<link[^>]+href="https?://', about), (
        "the page pulls a stylesheet from another origin")
    assert not re.search(r'<link[^>]+href="(?!https?:)[^"]+\.css', about), (
        "the page pulls a stylesheet file; its palette must be inline")
    assert not re.search(r'@import\s+url\(', about)


def test_every_local_link_resolves(about):
    """A relative link that does not resolve on disk is the 404 the viewer
    cannot see: the page renders and the link is dead."""
    for href in re.findall(r'href="([^"]+)"', about):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = (ABOUT.parent / href.split("#")[0]).resolve()
        assert target.exists(), "the about page links to a missing file: %s" % href


# --- the reachability chain ---------------------------------------------------

def test_the_viewer_header_links_to_the_about_page(about):
    """In the markup, not added by script: a reader who lands on a payload
    that fails to load can still reach the about page."""
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    about_links = [(h, t) for h, t in links if h == "about.html"]
    assert about_links, (
        "the viewer's header carries no 關於 link; it carries %r" % (links,))
    assert about_links[0][1] == "關於"
    assert (VIEWER_INDEX.parent / about_links[0][0]).resolve() == ABOUT.resolve()


def test_the_viewer_header_no_longer_links_the_report():
    """The replacement is deliberate: the report is reachable from the about
    page, and the header link that named one report in pipeline jargon is
    gone."""
    html = VIEWER_INDEX.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', html)
    targets = [h for h, _ in links]
    assert "../docs/release-diff.html" not in targets, (
        "the viewer's header still links the release-diff report directly; "
        "it now belongs one hop away, on the about page")


def test_the_dashboard_header_links_to_the_about_page():
    """The dashboard is where policy readers land; the 關於 link must be
    reachable from there too."""
    html = DASHBOARD.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink"[^>]*href="([^"]+)"[^>]*>([^<]*)</a>', html)
    about_links = [(h, t) for h, t in links if h == "about.html"]
    assert about_links, (
        "the dashboard's header carries no 關於 link; it carries %r" % (links,))
    assert about_links[0][1] == "關於"
    assert (DASHBOARD.parent / about_links[0][0]).resolve() == ABOUT.resolve()
    # the back link to the viewer stays pinned
    assert any(h == "index.html" for h, _ in links), (
        "the dashboard's back link to the viewer is gone")


# --- the deploy record --------------------------------------------------------

def test_the_about_page_is_listed_as_a_deploy_artifact():
    """Otherwise its served bytes are never compared against the committed
    build, and it can serve superseded content while every check passes."""
    data = __import__("json").loads(DEPLOY.read_text(encoding="utf-8"))
    assert "viewer/about.html" in data["artifacts"], (
        "the about page is not listed among the deploy artifacts; the "
        "deployment check does not cover it")


# --- the chain survives regeneration ------------------------------------------

def test_the_reports_are_generated_at_the_paths_the_page_links():
    """The generators' own output paths are the ones the about page links. A
    generator that moved its output would leave the page linking a file
    nothing writes any more."""
    import subprocess
    for script, expected in [
        (ROOT / "scripts" / "release_diff_report.py", RELEASE_DIFF),
        (ROOT / "scripts" / "coverage_report.py", COVERAGE_REPORT),
    ]:
        text = script.read_text(encoding="utf-8")
        default = re.search(r'--out", default=str\(ROOT / "([^"]+)" / "([^"]+)"\)', text)
        assert default, "%s declares no default output path" % script.name
        assert (ROOT / default.group(1) / default.group(2)).resolve() == expected.resolve(), (
            "%s writes %r but the about page links %s"
            % (script.name, "/".join(default.groups()), expected))
