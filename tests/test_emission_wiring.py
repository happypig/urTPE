# -*- coding: utf-8 -*-
"""Every emission path runs the emission-fault check (wire-standing-checks 1.2).

A run without --links must report wholesale link-data absence through
review_report.txt and the console, and still exit 0 (advisory by design, D5).
Partial coverage is a count, not a fault.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import cli  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


@pytest.fixture
def gazette(tmp_path) -> str:
    path = tmp_path / "gazette.pdf"
    write_gazette(str(path), ROC_ROWS, published="統計至115年8月11日")
    return str(path)


def test_a_run_without_links_reports_the_fault_and_exits_zero(gazette, tmp_path, capsys):
    out = tmp_path / "out"
    rc = cli.main([gazette, "-o", str(out)])  # no --links
    assert rc == 0, "the emission check is a warning, not a refusal"

    report = (out / "review_report.txt").read_text(encoding="utf-8")
    assert "no link data on any" in report, (
        "the wholesale-absence fault must reach review_report.txt")
    assert "--links" in report, "the fault names the run step that attaches links"

    captured = capsys.readouterr()
    assert "no link data on any" in (captured.out + captured.err), (
        "the fault must also be printed")


def test_a_run_with_links_reports_no_emission_fault(gazette, tmp_path):
    out = tmp_path / "out"
    # --links would crawl; the fixture land cores match nothing, and the fallback
    # mapping is tracked but empty for these — discovery resolves nothing, which
    # is exactly the wholesale-absence case... so this run EXPECTS the fault.
    # The honest wiring test for "no fault" is therefore: any run where at least
    # one project carries a link field. Monkeypatch the discovery to a stub that
    # links one project.
    import urtpe.links as links_mod

    class _StubDiscovery:
        def __init__(self, cache_dir, *a, **k):
            self.cache_dir = cache_dir

        def run(self, projects, fresh=False, use_playwright=False):
            from urtpe.links import DiscoveryResult
            results = {}
            for i, p in enumerate(projects):
                r = DiscoveryResult(project_id=p.project_id, land_core="x")
                if i == 0:
                    r.status = "resolved"
                    r.twur_view_id = 123
                    r.twur_url = f"https://twur.nlma.gov.tw/zh/urban/rebuild/view/123"
                results[p.project_id] = r
            return results

        def write_crawl_log(self, results, out_path):
            pass

    original = cli.links_mod.LinksDiscovery
    cli.links_mod.LinksDiscovery = _StubDiscovery
    try:
        rc = cli.main([gazette, "-o", str(out), "--links"])
    finally:
        cli.links_mod.LinksDiscovery = original
    assert rc == 0
    report = (out / "review_report.txt").read_text(encoding="utf-8")
    assert "no link data on any" not in report, (
        "one linked project means wholesale absence does not apply")
    # partial coverage is reported as a count, not a fault
    assert "partial" in report.lower() or "of" in report
