# -*- coding: utf-8 -*-
"""A4 — the cycle status page (`scripts/cycle_status.py`).

openspec change a4-pdf-cycle-coordinator, capability `cycle-status-page` (optional: delete
that spec and task group 4 and the coordinator does not notice). The page lets the operator
see the last runs without reading JSON. It is read-only and local: it reads the cycle record,
writes only its own file, and that file sits outside the repository, so an operational log is
never committed or served by GitHub Pages.

A stopped schedule writes no new page, so a warning computed only when the page is generated
would never appear. The newest record's time is therefore embedded, and a small inline script
compares it with the clock when the page is OPENED.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cycle  # noqa: E402

SCRIPT = ROOT / "scripts" / "cycle_status.py"


@pytest.fixture(scope="module")
def cs():
    spec = importlib.util.spec_from_file_location("cycle_status_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod            # dataclasses looks its own module up here
    spec.loader.exec_module(mod)
    return mod


def _rec(time, outcome, **kw):
    return cycle.make_record(time, kw.pop("polls", {"gazette": "unchanged", "p168": "unchanged"}),
                             outcome, **kw)


T1 = "2026-11-21T06:00:00+08:00"
T2 = "2026-11-22T06:00:00+08:00"
T3 = "2026-11-23T06:00:00+08:00"
NOW_FRESH = "2026-11-23T07:00:00+08:00"
NOW_OLD = "2026-11-25T08:00:00+08:00"          # 50 h after T3


# --- 1.18 the runs ----------------------------------------------------------------------------

def test_runs_are_listed_newest_first_with_every_field(cs):
    records = [
        _rec(T1, "nothing_new"),
        _rec(T2, "refused", sha256="b" * 64, gazette_id="2026-11-19", last_stage="detect",
             failed_stage="ingest", exit_code=4, reason="tripwire"),
        _rec(T3, "ingested", sha256="c" * 64, gazette_id="2026-11-26", last_stage="viewer_smoke"),
    ]
    html = cs.render(records, NOW_FRESH)
    assert html.index(T3) < html.index(T2) < html.index(T1)
    row = re.search(r'<tr class="run [a-z]+" data-outcome="refused".*?</tr>', html, re.S).group(0)
    for needle in (T2, "refused", "detect", "ingest", "4"):
        assert needle in row, needle


def test_a_stopped_run_looks_different_from_a_finished_one_and_a_quiet_one(cs):
    html = cs.render([_rec(T1, "nothing_new"), _rec(T2, "stopped", failed_stage="refresh", exit_code=1),
                      _rec(T3, "ingested")], NOW_FRESH)
    assert 'class="run quiet" data-outcome="nothing_new"' in html
    assert 'class="run stopped" data-outcome="stopped"' in html
    assert 'class="run finished" data-outcome="ingested"' in html


@pytest.mark.parametrize("outcome,klass", [
    ("ingested", "finished"), ("nothing_new", "quiet"), ("already_done", "quiet"),
    ("refused", "stopped"), ("stopped", "stopped"), ("awaiting_diagnosis", "stopped"),
    ("locked", "waiting"), ("dirty_tree", "waiting"), ("another_cycle", "waiting"),
    ("publish_failed", "stopped"),
])
def test_every_outcome_has_a_style(cs, outcome, klass):
    html = cs.render([_rec(T3, outcome)], NOW_FRESH)
    assert 'class="run %s" data-outcome="%s"' % (klass, outcome) in html


def test_a_quiet_day_is_not_shown_as_a_failure(cs):
    html = cs.render([_rec(T3, "nothing_new")], NOW_FRESH)
    row = re.search(r'<tr class="run [a-z]+" data-outcome="nothing_new"', html).group(0)
    assert "stopped" not in row


def test_the_stopped_cycle_names_its_failed_stage_and_exit_code(cs):
    html = cs.render([_rec(T3, "locked", failed_stage="refresh", exit_code=5)], NOW_FRESH)
    row = re.search(r'<tr class="run waiting" data-outcome="locked".*?</tr>', html, re.S).group(0)
    assert "refresh" in row and ">5<" in row.replace(" ", "")


# --- the newest record and the stale warning -----------------------------------------------------

def test_the_time_of_the_newest_record_is_shown_and_embedded(cs):
    html = cs.render([_rec(T1, "nothing_new"), _rec(T3, "nothing_new")], NOW_FRESH)
    assert 'id="newest"' in html
    assert 'data-newest="%s"' % T3 in html


def test_an_old_newest_record_shows_the_warning(cs):
    html = cs.render([_rec(T3, "nothing_new")], NOW_OLD)
    assert re.search(r'id="stale"[^>]*class="[^"]*\bshow\b', html) or \
        re.search(r'class="[^"]*\bshow\b[^"]*"[^>]*id="stale"', html)


def test_a_fresh_newest_record_shows_no_warning_when_generated(cs):
    html = cs.render([_rec(T3, "nothing_new")], NOW_FRESH)
    assert not re.search(r'id="stale"[^>]*class="[^"]*\bshow\b', html)
    assert not re.search(r'class="[^"]*\bshow\b[^"]*"[^>]*id="stale"', html)


def test_the_page_compares_the_newest_record_with_the_clock_when_it_is_opened(cs):
    """A stopped schedule writes no new page, so the check must run in the browser."""
    html = cs.render([_rec(T3, "nothing_new")], NOW_FRESH)
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    assert "data-newest" in script or "dataset.newest" in script
    assert "36" in script
    assert "Date" in script


def test_an_empty_record_says_so_and_warns(cs):
    html = cs.render([], NOW_FRESH)
    assert "沒有" in html or "no run" in html.lower()
    assert re.search(r'id="stale"[^>]*class="[^"]*\bshow\b', html) or \
        re.search(r'class="[^"]*\bshow\b[^"]*"[^>]*id="stale"', html)


# --- 1.19 read-only, local, self-contained --------------------------------------------------------

def test_the_page_makes_no_external_request(cs):
    html = cs.render([_rec(T3, "nothing_new")], NOW_FRESH)
    assert not re.search(r'<script[^>]+src=', html)
    assert not re.search(r'<link[^>]+href=', html)
    assert "@import" not in html
    assert not re.search(r'url\(\s*[\'"]?https?:', html)
    assert not re.search(r'(?:src|href)\s*=\s*["\']https?:', html)


def test_generating_the_page_writes_only_its_own_file_and_leaves_the_record_alone(cs, tmp_path):
    root = tmp_path / "gazettes"
    root.mkdir()
    log = root / "cycle_log.jsonl"
    log.write_text("\n".join(json.dumps(_rec(t, "nothing_new")) for t in (T1, T2, T3)) + "\n",
                   encoding="utf-8")
    (root / "poll_log.jsonl").write_text("{}\n", encoding="utf-8")
    before_log = log.read_bytes()
    before = sorted(p.name for p in root.iterdir())
    out = cs.write_page(root, now_iso=NOW_FRESH)
    after = sorted(p.name for p in root.iterdir())
    assert out == root / "cycle_status.html"
    assert after == sorted(before + ["cycle_status.html"])
    assert log.read_bytes() == before_log


def test_the_default_output_sits_in_the_archive_root_outside_the_repository(cs, tmp_path):
    assert cs.default_output_path(tmp_path) == tmp_path / "cycle_status.html"
    from urtpe.archive import DEFAULT_ARCHIVE_ROOT
    cs.assert_outside_repo(Path(DEFAULT_ARCHIVE_ROOT) / "cycle_status.html")      # must not raise


@pytest.mark.parametrize("rel", ["docs/cycle_status.html", "viewer/cycle_status.html",
                                 "cycle_status.html", "data/cycle_status.html"])
def test_a_path_inside_the_repository_is_refused(cs, rel):
    with pytest.raises(ValueError):
        cs.assert_outside_repo(ROOT / rel)


def test_write_page_refuses_a_path_in_the_repository_and_writes_nothing(cs, tmp_path):
    root = tmp_path / "gazettes"
    root.mkdir()
    target = ROOT / "docs" / "cycle_status_must_not_exist.html"
    with pytest.raises(ValueError):
        cs.write_page(root, now_iso=NOW_FRESH, out=target)
    assert not target.exists()


def test_a_missing_record_gives_an_empty_page_not_an_error(cs, tmp_path):
    out = cs.write_page(tmp_path, now_iso=NOW_FRESH)
    assert out.is_file()
    assert "stale" in out.read_text(encoding="utf-8")


def test_the_page_is_light_only_with_the_project_cream_ground(cs):
    html = cs.render([], NOW_FRESH)
    assert "#fff8f4" in html
    assert "prefers-color-scheme: dark" not in html
    assert 'lang="zh-Hant"' in html
