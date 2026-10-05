"""Viewer/data consistency guards.

Task group 11 of robust-gazette-ingestion.

The viewer loads exactly four files: index.html, app.css, app.js and
projects.data.js. Only the last is generated, and it was generated solely when a
viewer target was passed explicitly. Because that flag is optional, a pipeline
could run to completion many times over while the browser kept serving a dataset
an abandoned publication had produced. These tests pin the three ways that
happened: a forgotten target, a hand-edited cache-bust, and no cross-check.
"""

from __future__ import annotations

import json
import re

import pytest

from urtpe import viewer as viewer_mod


def _write(path, doc):
    """Write in the exact shape the viewer loads, wrapper included."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                    encoding="utf-8")


def _read_js(path):
    """Parse projects.data.js the way the page does, wrapper included."""
    text = path.read_text(encoding="utf-8")
    return json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))


def _doc(published="2026-08-27", projects=709, records=1422):
    return {
        "published_date": published,
        "generated_at": "2026-10-05T15:56:22+08:00",
        "counts": {"projects": projects, "records": records},
        "projects": [],
    }


def _run_cli(tmp_path, pdf, outdir, *extra):
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "urtpe.cli", str(pdf), "-o", str(outdir),
           "--no-archive", *extra]
    return subprocess.run(cmd, cwd=str(tmp_path.parent), capture_output=True,
                          text=True, encoding="utf-8")


# --- 11.6 a run refreshes the viewer without being asked ----------------------

def test_repo_run_refreshes_the_viewer_without_an_explicit_target(tmp_path):
    """--viewer is optional, so its absence must not leave the viewer behind.

    Reproduces the drift directly: a repo-shaped output tree with a stale
    projects.data.js, then a run with no viewer target. The viewer must be brought
    up to the dataset the run emitted.
    """
    from tests.gazette_fixtures import ROC_ROWS, write_gazette

    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "viewer").mkdir(parents=True)
    # a viewer directory holding a dataset from a different, abandoned publication
    _write(repo / "viewer" / "projects.data.js", _doc(published="2026-09-24",
                                                       projects=692, records=1436))
    (repo / "viewer" / "index.html").write_text(
        '<script src="projects.data.js?v=20260924a"></script>', encoding="utf-8")

    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")

    from urtpe.cli import _run

    _run(str(pdf), str(repo / "data"), no_tsv=False, viewer_dir=None)

    emitted = _read_js(repo / "viewer" / "projects.data.js")
    on_disk = json.loads((repo / "data" / "projects.json").read_text(encoding="utf-8"))
    assert emitted["published_date"] == on_disk["published_date"]
    assert emitted["counts"] == on_disk["counts"]


def test_explicit_viewer_target_still_writes_elsewhere(tmp_path):
    """The flag keeps working: an explicit target must be honoured as given."""
    from tests.gazette_fixtures import ROC_ROWS, write_gazette

    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    elsewhere = tmp_path / "otherviewer"
    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS)

    from urtpe.cli import _run

    _run(str(pdf), str(repo / "data"), no_tsv=False, viewer_dir=str(elsewhere))
    assert (elsewhere / "projects.data.js").exists()
    assert not (repo / "viewer" / "projects.data.js").exists()


# --- 11.7 the cache-bust is derived, not hand-maintained ---------------------

def test_cache_bust_is_derived_from_the_publication_date(tmp_path):
    """index.html's asset version must not be a literal someone has to remember.

    Starts from a stale literal so the assertion cannot pass by coincidence.
    """
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    index = vdir / "index.html"
    index.write_text(
        '<script src="projects.data.js?v=20200101a"></script>\n'
        '<script src="app.js?v=20200101a"></script>\n',
        encoding="utf-8")

    viewer_mod.write_projects_js(str(vdir), _doc(published="2026-08-27"))

    html = index.read_text(encoding="utf-8")
    assert "20200101" not in html
    versions = set(re.findall(r"\?v=([0-9a-zA-Z]+)", html))
    assert len(versions) == 1, f"assets disagree on the version: {versions}"
    assert versions.pop().startswith("20260827")


def test_cache_bust_is_stable_for_an_identical_re_emit(tmp_path):
    """Re-emitting unchanged data must not churn index.html on every run."""
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    index = vdir / "index.html"
    index.write_text('<script src="projects.data.js?v=x"></script>\n'
                     '<script src="app.js?v=x"></script>\n', encoding="utf-8")

    viewer_mod.write_projects_js(str(vdir), _doc())
    first = index.read_text(encoding="utf-8")
    viewer_mod.write_projects_js(str(vdir), _doc())
    assert index.read_text(encoding="utf-8") == first


def test_cache_bust_tracks_a_new_publication(tmp_path):
    """Re-emitting for a newer gazette must move the version, or browsers keep
    serving the previous dataset."""
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    index = vdir / "index.html"
    index.write_text('<script src="projects.data.js?v=20260827a"></script>\n'
                     '<script src="app.js?v=20260827a"></script>\n', encoding="utf-8")

    viewer_mod.write_projects_js(str(vdir), _doc(published="2026-09-24"))
    html = index.read_text(encoding="utf-8")
    assert "v=20260924" in html
    assert "20260827" not in html


def test_no_index_html_is_created_when_absent(tmp_path):
    """Writing the cache-bust must not invent an index.html."""
    vdir = tmp_path / "viewer"
    vdir.mkdir()
    viewer_mod.write_projects_js(str(vdir), _doc())
    assert not (vdir / "index.html").exists()
    assert (vdir / "projects.data.js").exists()


# --- 11.8 the cross-check ----------------------------------------------------

def test_guard_passes_when_the_viewer_matches_the_dataset(tmp_path):
    doc = _doc()
    js = tmp_path / "projects.data.js"
    _write(js, doc)
    faults = viewer_mod.consistency_faults(doc, str(js))
    assert faults == []


@pytest.mark.parametrize("field,value", [
    ("published_date", "2026-09-24"),
    ("counts", {"projects": 692, "records": 1436}),
])
def test_guard_reports_a_disagreeing_viewer(tmp_path, field, value):
    """The drift that shipped: a viewer holding a dataset the run never emitted."""
    on_disk = _doc()
    stale = _doc()
    stale[field] = value
    js = tmp_path / "projects.data.js"
    _write(js, stale)

    faults = viewer_mod.consistency_faults(on_disk, str(js))
    assert len(faults) == 1
    assert field in faults[0]
    assert "projects.data.js" in faults[0]


def test_guard_reports_a_missing_viewer_data_file(tmp_path):
    faults = viewer_mod.consistency_faults(_doc(), str(tmp_path / "absent.js"))
    assert faults and "absent.js" in faults[0]


def test_guard_names_both_values_so_the_fault_is_actionable(tmp_path):
    on_disk = _doc()
    stale = _doc(published="2026-09-24")
    js = tmp_path / "projects.data.js"
    _write(js, stale)
    fault = viewer_mod.consistency_faults(on_disk, str(js))[0]
    assert "2026-08-27" in fault and "2026-09-24" in fault