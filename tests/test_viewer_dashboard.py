"""The policy dashboard page's published contracts.

The dashboard is a second published page, so the same three questions apply
to it that apply to the viewer:

- the deploy record names it and its assets, so `scripts/check_deploy.py`
  compares their served bytes against the committed build;
- its own assets carry the derived cache-bust, so a browser cannot pair a
  re-fetched `dashboard.js` with a stale cached `dashboard.css` — the §41
  shape, measured, which shipped a CSS fix only to viewers whose cache
  happened to be empty;
- the header links to it and it links back, each by a relative path, so the
  pair works from `file://` as well as from the published site.

These read the committed files rather than the generator, because the contract
is about what is published, not about how it is produced.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from urtpe import viewer as viewer_mod

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "viewer"
DASHBOARD_HTML = VIEWER / "dashboard.html"
DEPLOY = VIEWER / "deploy.json"


# --- the deploy record names the page and its assets -------------------------

def test_the_deploy_record_names_the_dashboard():
    """A published page that is not listed is a page whose served bytes are
    never compared against the committed build, so it can serve superseded
    content indefinitely while every check passes."""
    data = json.loads(DEPLOY.read_text(encoding="utf-8"))
    artifacts = data["artifacts"]
    for path in ("viewer/dashboard.html", "viewer/dashboard.js",
                 "viewer/dashboard.css"):
        assert path in artifacts, (
            "%s is published but the deploy record does not name it; its "
            "served bytes are never checked" % path)


def test_every_named_artifact_is_tracked_by_git():
    """The check compares against the HEAD blob, so an untracked path can
    never be compared against anything."""
    import subprocess

    data = json.loads(DEPLOY.read_text(encoding="utf-8"))
    tracked = set(subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True,
    ).stdout.splitlines())
    missing = [a for a in data["artifacts"] if a not in tracked]
    assert not missing, "the deploy record names untracked paths: %s" % missing


# --- the cache-bust ----------------------------------------------------------

def test_the_dashboard_assets_carry_the_cache_bust():
    """Every script and stylesheet the dashboard loads must carry the derived
    version. An unversioned one is the §41 hole: the rewrite had nothing to
    match, so the run said nothing while browsers paired a re-fetched script
    with a stale cached stylesheet."""
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="(dashboard\.css|dashboard\.js)([^"]*)"', html)
    assert refs, "the dashboard page loads no asset of its own"
    unversioned = [name for name, tail in refs if "?v=" not in tail]
    assert not unversioned, (
        "the dashboard loads without the derived cache-bust: %s — a changed "
        "asset would serve stale to cached browsers" % unversioned)


def test_the_dashboard_and_the_viewer_agree_on_the_version():
    """Both pages read the same dataset, so they must name the same version.
    A mismatch pairs one page's fresh script with the other's stale data."""
    index = (VIEWER / "index.html").read_text(encoding="utf-8")
    dash = DASHBOARD_HTML.read_text(encoding="utf-8")
    index_v = set(re.findall(r"\?v=([0-9a-zA-Z]+)", index))
    dash_v = set(re.findall(r"\?v=([0-9a-zA-Z]+)", dash))
    assert index_v and dash_v, "one of the two pages names no version"
    assert index_v == dash_v, (
        "the pages disagree on the asset version: %s against %s"
        % (sorted(index_v), sorted(dash_v)))


def test_the_rewrite_covers_the_dashboard_page(tmp_path):
    """A run that rewrites the viewer's version must rewrite the dashboard's
    too, or the two pages drift apart on the next publication."""
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    (vdir / "index.html").write_text(
        '<link rel="stylesheet" href="app.css?v=old1">\n'
        '<script src="projects.data.js?v=old1"></script>\n'
        '<script src="app.js?v=old1"></script>\n', encoding="utf-8")
    (vdir / "dashboard.html").write_text(
        '<link rel="stylesheet" href="dashboard.css?v=old1">\n'
        '<script src="dashboard.js?v=old1"></script>\n', encoding="utf-8")

    viewer_mod.write_projects_js(str(vdir), {
        "published_date": "2026-09-24",
        "generated_at": "2026-10-05T15:56:22+08:00",
        "counts": {"projects": 700, "records": 1400},
        "projects": [],
    })

    for name in ("index.html", "dashboard.html"):
        html = (vdir / name).read_text(encoding="utf-8")
        assert "v=20260924" in html, "%s was not rewritten" % name
        assert "old1" not in html, "%s still names the old version" % name


def test_an_unversioned_dashboard_reference_is_reported(tmp_path, capsys):
    """Report, do not fix. The page's HTML is hand-maintained, and inventing a
    version attribute the author never wrote would mask the drift."""
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    (vdir / "dashboard.html").write_text(
        '<link rel="stylesheet" href="dashboard.css">\n'
        '<script src="dashboard.js?v=20260827a"></script>\n', encoding="utf-8")

    viewer_mod.write_projects_js(str(vdir), {
        "published_date": "2026-09-24",
        "generated_at": "2026-10-05T15:56:22+08:00",
        "counts": {"projects": 700, "records": 1400},
        "projects": [],
    })

    err = capsys.readouterr().err
    assert "dashboard.html" in err and "dashboard.css" in err and "cache-bust" in err


# --- the two links -----------------------------------------------------------

def test_the_viewer_header_links_to_the_dashboard():
    """In the markup, not added by script: a reader who lands on a payload
    that fails to load can still reach the dashboard."""
    index = (VIEWER / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink" href="([^"]+)">([^<]*)</a>', index)
    targets = [h for h, _ in links]
    assert "dashboard.html" in targets, (
        "the viewer's header carries no link to the dashboard; it carries %r"
        % (links,))
    assert (VIEWER / "dashboard.html").exists()


def test_the_dashboard_links_back_to_the_viewer():
    """A relative link, so the pair works from a file:// page as well as from
    the published site. The pattern allows other attributes (the link carries
    an id) in any order between class and href."""
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    links = re.findall(r'<a class="navlink"[^>]*href="([^"]+)"[^>]*>([^<]*)</a>', html)
    assert links, "the dashboard carries no link back to the viewer"
    href = links[0][0]
    assert href == "index.html", (
        "the back link must be relative and point at the viewer; got %r" % href)
    assert (DASHBOARD_HTML.parent / href).resolve() == (VIEWER / "index.html").resolve()


# --- the page computes its own figures ---------------------------------------

def test_the_dashboard_computes_its_figures_from_the_payload():
    """No hand-typed figure. The corpus moves and every aggregate moves with
    it, so a number typed by hand reads as current until it does not."""
    js = (VIEWER / "dashboard.js").read_text(encoding="utf-8")
    for field in ("projects", "records", "published_date"):
        assert field in js, (
            "the dashboard does not read %r from the payload" % field)
    # the aggregate is built from the payload's own rows
    assert "payload.projects" in js, (
        "the dashboard does not iterate the payload's projects")
