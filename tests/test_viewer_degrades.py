"""Viewer degrades rather than blanking.

Test-writing group 1 of no-silent-data-loss.

The blank-pane regression reached the user as *absence of data* rather than *absence of
one field*, because a single unguarded read threw before the detail pane was written. The
guard for it is not "the dataset has links today" — it is that no field the viewer reads
unguarded can be missing, and that a missing field costs one element rather than the page.

Task 1.4's fixture is built here rather than in gazette_fixtures.py: this is a viewer
concern, not a PDF-reading one.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "viewer" / "app.js"
INDEX = ROOT / "viewer" / "index.html"
DATA = ROOT / "viewer" / "projects.data.js"

OPTIONAL_FIELDS = ("links", "implementation", "rewards")


def _app() -> str:
    return APP.read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    lines = _app().split("\n")
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


def _doc() -> dict:
    if not DATA.exists():
        pytest.skip("projects.data.js not emitted")
    text = DATA.read_text(encoding="utf-8")
    return json.loads(text[len("window.PROJECTS = "):].rstrip().rstrip(";"))


# --- task 1.4 fixture: a dataset with no portal data at all ------------------

def _bare_dataset() -> dict:
    """Two projects whose records carry none of the optional fields.

    Deliberately not derived from the emitted dataset, so the degrade assertions do
    not depend on what today's emission happens to contain.
    """
    def node(recno, date, district, section):
        return {
            "recno": recno, "date": date, "district": district,
            "case_name": "擬訂測試", "name_raw": "擬訂測試",
            "stage": "事業計畫", "track": "事業計畫",
            "stage_事業計畫": "事業計畫", "stage_權利變換": "",
            "land": f"臺北市{district}{section} 1 地號等1筆土地",
            "section": section, "first_parcel": "1", "land_count": 1,
            "parcels": ["1"], "orig_count": None, "aliases": {}, "area": "",
            "area_section": "", "is_current": True, "named_anchor": "",
            "implementer": "甲公司", "planner": "乙顧問", "district_land": district,
            "review_flags": [], "auto_fixes": [],
            # deliberately absent: links, implementation
        }

    return {
        "published_date": "2026-08-27",
        "generated_at": "2026-10-05T00:00:00+08:00",
        "counts": {"projects": 2, "records": 2},
        "projects": [
            {"project_id": "甲區-甲段一小段-1地號等1筆", "district": "甲區",
             "section": "甲段一小段", "name": "測試甲", "implementer": "甲公司",
             "anchor_recno": "1", "member_recnos": ["1"], "published_date": "2026-08-27",
             "edges": [], "links": {},
             "nodes": [node("1", "2020-01-01", "甲區", "甲段一小段")]},
            {"project_id": "乙區-乙段二小段-2地號等1筆", "district": "乙區",
             "section": "乙段二小段", "name": "測試乙", "implementer": "乙公司",
             "anchor_recno": "2", "member_recnos": ["2"], "published_date": "2026-08-27",
             "edges": [], "links": {},
             "nodes": [node("2", "2021-01-01", "乙區", "乙段二小段")]},
        ],
    }


# --- task 1.1 no field is a hard dependency --------------------------------

def _render(doc_path, tmp_path):
    """Drive the real render path against a dataset file. Returns (rc, output)."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    harness = ROOT / "scripts" / "viewer_smoke.js"
    assert harness.exists(), "scripts/viewer_smoke.js must drive the render path"
    proc = subprocess.run(
        [node, "--max-old-space-size=2048", str(harness), str(doc_path)],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def _write(doc: dict, tmp_path, name="d.data.js") -> pathlib.Path:
    p = tmp_path / name
    p.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                 encoding="utf-8")
    return p


@pytest.mark.parametrize("field", OPTIONAL_FIELDS)
def test_dropping_an_optional_field_does_not_break_the_render(field, tmp_path):
    """The requirement, tested behaviourally rather than by pattern-matching app.js.

    A regex can only recognise the guard forms it already knows about, and reports
    false positives on `if (!x.field) return`, ternaries and `?.`. Stripping one
    optional field from the real dataset and rendering it has no such blind spot:
    either the viewer survives the loss or it does not.
    """
    doc = _doc()
    for project in doc["projects"]:
        project.pop(field, None)
        for n in project["nodes"]:
            n.pop(field, None)
    rc, out = _render(_write(doc, tmp_path), tmp_path)
    assert rc == 0, (
        "dropping `%s` broke the viewer; it must degrade, not abort:\n%s" % (field, out))
    assert "clicking a project does not throw" in out and "FAIL" not in out, out


def test_the_schedule_lookup_cannot_throw():
    """Pins the exact expression that blanked 709 detail panes.

    The behavioural test above covers the general case; this one names the regression
    so it cannot be reintroduced quietly.
    """
    body = _function_body("renderDetail")
    assert not re.search(r"(?<!\|\| \{\}\))\bn\.links\.", body), (
        "renderDetail dereferences n.links directly; guard it as "
        "((n.links || {}).taipei || [])[0]")


# --- task 1.2 degrade, not blank ---------------------------------------------

def test_a_record_without_links_still_renders(tmp_path):
    """A dataset with no portal data anywhere still lists and renders every project.

    The fixture carries `links: {}` rather than omitting the key, because that is
    exactly what a rebuild without link discovery produces.
    """
    data = _bare_dataset()
    for project in data["projects"]:
        assert not (project.get("links") or {}), "fixture must carry no link data"
        for n in project["nodes"]:
            assert "links" not in n

    rc, out = _render(_write(data, tmp_path), tmp_path)
    assert rc == 0, (
        "the viewer failed to render a dataset whose records carry no portal data:\n" + out)
    assert "left pane rendered items" in out
    assert "clicking a project does not throw" in out
    assert "detail pane was filled" in out
    assert "FAIL" not in out, out


# --- task 1.3 the 統計至 label ------------------------------------------------

def test_header_distinguishes_the_publication_date_from_a_generation_stamp():
    """Normalising to ISO removed the word that said what the date was.

    `· 2026-08-27` reads as either a publication date or a generation timestamp.
    """
    app = _app()
    assert re.search(r"\$\{[^}]*published_date", app), (
        "the header no longer renders published_date at all")

    # The template is built by string concatenation across lines, so locate the whole
    # assignment rather than a single physical line. There are two assignments: the
    # "not loaded" fallback, and the one that renders the counts and date.
    assignments = re.findall(r"meta\.textContent\s*=(.*?);", app, re.S)
    dated = [a for a in assignments if "published_date" in a]
    assert dated, (
        "the header no longer renders published_date; assignments found: %r"
        % [a.strip()[:60] for a in assignments])
    assignment = dated[0]
    assert "統計至" in assignment, (
        "the 統計至 label must render in the header assignment itself, not merely "
        "somewhere in the file, or the date reads as a generation stamp: %r"
        % assignment.strip()[:120])


def test_index_html_carries_no_hardcoded_date_label():
    """The label belongs in the data-driven header, not baked into the page."""
    if not INDEX.exists():
        pytest.skip("index.html not present")
    html = INDEX.read_text(encoding="utf-8")
    assert "統計至" not in html, (
        "index.html hardcodes the date label; it must come from the dataset so it "
        "tracks the publication")
