"""Contract between viewer/app.js and the data it renders.

The pipeline can emit a structurally valid projects.data.js — correct counts, correct
published_date, every project and node present — and still leave app.js unable to render
it. That happened: a rebuild without --links produced projects whose `links` were empty
objects, and app.js read `n.links.taipei[0]` without a guard, so one throw inside
renderDetail left the detail pane showing its placeholder for all 709 projects while
every test still passed.

These tests pin the two things that went unchecked: that the fields app.js reads
*unguarded* exist on the data, and that the guarded-by-convention ones are optional.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "viewer" / "app.js").read_text(encoding="utf-8")
DATA = ROOT / "viewer" / "projects.data.js"


def _doc() -> dict:
    if not DATA.exists():
        pytest.skip("projects.data.js not emitted")
    text = DATA.read_text(encoding="utf-8")
    return json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))


def _function_body(name: str) -> str:
    lines = APP.split("\n")
    start = next((i for i, l in enumerate(lines)
                  if re.match(r"\s*function %s\b" % name, l)), None)
    assert start is not None, f"{name} not found in app.js"
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and (len(line) - len(line.lstrip())) <= indent \
                and not line.strip().startswith("//"):
            break
        end += 1
    return "\n".join(lines[start:end])


def _unguarded_accesses(fn: str, var: str) -> list[tuple[str, str]]:
    """`<var>.<prop>` reads not followed by `?.` — i.e. ones that would throw."""
    body = _function_body(fn)
    out = []
    for m in re.finditer(r"\b%s\.([A-Za-z_][A-Za-z0-9_]*)(\??\.\w+|\s*[\[(])" % var, body):
        if m.group(2).startswith("?."):
            continue
        out.append((m.group(1), m.group(2)))
    return out


def test_the_detail_view_reads_no_project_field_without_a_guard():
    """A project-level field read unguarded inside renderDetail must always exist.

    Guards against reintroducing an access like `p.implementation.something` after a
    rebuild that drops the field.
    """
    doc = _doc()
    for project in doc["projects"]:
        for prop, _tail in _unguarded_accesses("renderDetail", "p"):
            assert prop in project, (
                "app.js renderDetail reads p.%s unguarded, but project %s has no "
                "such field; the detail pane would throw for every project"
                % (prop, project.get("project_id")))
        break  # one project is enough to prove the field's presence is not incidental


def test_the_detail_view_reads_no_node_field_without_a_guard():
    """The failure that blanked the viewer: n.links.taipei[0] with no guard.

    Any unguarded read is only safe if the field is always present, so each one found
    is checked against every node in the dataset. A single node missing the field is
    enough to throw, and it would blank the pane for all projects. Finding no unguarded
    reads at all is the desired end state and passes trivially.
    """
    doc = _doc()
    accesses = _unguarded_accesses("renderDetail", "n")
    offenders = []
    for project in doc["projects"]:
        for node in project["nodes"]:
            for prop, _tail in accesses:
                if prop not in node:
                    offenders.append((project.get("project_id"), node.get("recno"), prop))
    assert not offenders, (
        "renderDetail has %d unguarded node read(s) and %d node(s) lack the field, "
        "e.g. %s" % (len(accesses), len(offenders), offenders[:5]))


def test_the_schedule_lookup_cannot_throw_on_a_node_without_links():
    """Pins the exact expression that blanked every project's detail pane.

    app.js:1011 read `n.links.taipei[0]` directly while every other read of the same
    field went through `(n.links || {}).taipei || []`. One node without links — which
    is what a rebuild without --links produces — threw before detail.innerHTML was
    assigned, so the placeholder stayed on screen for all 709 projects.
    """
    body = _function_body("renderDetail")
    unguarded = re.search(r"(?<!\|\| \{\}\))\bn\.links\.", body)
    assert not unguarded, (
        "renderDetail dereferences n.links directly; guard it as "
        "((n.links || {}).taipei || [])[0] so a node without portal data degrades "
        "one badge instead of blanking the pane")


def test_every_node_carries_links_so_the_schedule_badge_resolves():
    """The specific chain: caseScheduleOf(p, n.links.taipei[0])."""
    doc = _doc()
    missing = [n.get("recno") for p in doc["projects"] for n in p["nodes"] if "links" not in n]
    assert not missing, "%d node(s) have no links: %s" % (len(missing), missing[:10])


def test_project_links_is_not_silently_empty():
    """An empty links object is what a rebuild without --links produces.

    It passes every count and date check while removing the milestone chips, the
    national-portal badge and the orphan-node counts.
    """
    doc = _doc()
    empty = [p.get("project_id") for p in doc["projects"] if not (p.get("links") or {})]
    assert not empty, (
        "%d project(s) have empty links; was the dataset built without --links? %s"
        % (len(empty), empty[:10]))


def test_counts_agree_with_the_projects_actually_present():
    """Counts are read straight into the header, so a stale count is a visible lie."""
    doc = _doc()
    projects = doc["projects"]
    nodes = sum(len(p["nodes"]) for p in projects)
    assert doc["counts"]["projects"] == len(projects)
    assert doc["counts"]["records"] == nodes


def test_cache_bust_in_index_html_names_the_publication_the_data_carries():
    """The cache-bust is derived, so it cannot drift — unless something else
    rewrote index.html after the emit."""
    index = (ROOT / "viewer" / "index.html").read_text(encoding="utf-8")
    versions = set(re.findall(r"\?v=([0-9a-zA-Z]+)", index))
    assert len(versions) == 1, f"assets disagree on the version: {versions}"
    published = _doc().get("published_date") or ""
    assert published, "dataset carries no published_date"
    assert versions.pop().startswith(published.replace("-", "")), (
        "index.html cache-bust does not name %s" % published)