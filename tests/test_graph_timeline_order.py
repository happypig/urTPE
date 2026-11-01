# -*- coding: utf-8 -*-
"""The version graph interleaves approvals and execution events chronologically,
ascending top-to-bottom (fix-graph-timeline-order task 1.1).

The defects, measured live on 通化段四小段-336: execution dates emitted as
`2023/04/27` (slash) sort after every ISO `-`-date of the same year (`/` > `-`
in ASCII), so 建照/開工 land at the newest end instead of between the approvals
they follow; and the SVG draws the newest node at the smallest y. The fixture
carries the 336 shape: approvals 2022-08-02 / 2023-03-21 / 2026-10-15 with 建照
2023-04-27 and 開工 2023-07-03 — both execution dates falling between two
approvals.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "viewer" / "app.js"
FIXTURE = ROOT / "tests" / "fixtures" / "viewer" / "chip_fixture.data.js"


def test_build_construction_chain_emits_iso_event_dates():
    """(a) D1: the event date field is ISO by the time it enters the timeline —
    the slash form must not survive buildConstructionChain's normalisation."""
    text = APP_JS.read_text(encoding="utf-8")
    # the ROC-dot conversion block must end in ISO, not slash-western
    m = re.search(
        r"dateStr = `\$\{1911 \+ Number\(roc\[1\]\)\}/", text)
    assert not m, (
        "buildConstructionChain still emits slash-western dates; it must emit ISO")
    # the slash-form input must be normalised to ISO inside the function
    fn = re.search(r"function buildConstructionChain[\s\S]*?\n\}", text).group(0)
    assert re.search(r"slash", fn) and re.search(r"\$\{slash\[1\]\}-", fn), (
        "the slash-form date must be normalised to ISO inside "
        "buildConstructionChain")


def test_the_display_site_converts_iso_back_for_the_label():
    """(b) D2: the row label converts ISO back to the established display form —
    the render site calls a formatter, not the raw ISO field."""
    text = APP_JS.read_text(encoding="utf-8")
    # the execution label renders through fmtDateReverse (ISO -> slash display)
    assert re.search(r"function fmtDateReverse\b", text), (
        "the display formatter must exist")
    assert "fmtDateReverse(e.date)" in text, (
        "the event label site must convert ISO back to the display form")


def _rendered_rows_top_to_bottom() -> list[str]:
    """(c)/(d) behaviour probe: run the smoke harness against the fixture and
    capture the SVG rows top-to-bottom from the rendered detail pane."""
    probe = ROOT / "tests" / "fixtures" / "viewer" / "_timeline_probe.js"
    result = subprocess.run(
        ["node", str(probe), str(FIXTURE)],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_exec_dates_interleave_between_the_approvals():
    """(c) The 336 shape: approvals 2022-08-02 / 2023-03-21 / 2026-10-15 with
    建照 2023-04-27 and 開工 2023-07-03 — the rendered top-to-bottom order must
    be 2022 node, 建照, 開工, then the later nodes."""
    rows = _rendered_rows_top_to_bottom()
    joined = "\n".join(rows)
    y_2022 = next((i for i, r in enumerate(rows) if "2022-08-02" in r), None)
    y_jianzhao = next((i for i, r in enumerate(rows) if "建照" in r), None)
    y_kaigong = next((i for i, r in enumerate(rows) if "開工" in r), None)
    y_2026 = next((i for i, r in enumerate(rows) if "2026-10-15" in r), None)
    assert None not in (y_2022, y_jianzhao, y_kaigong, y_2026), rows
    assert y_2022 < y_jianzhao < y_kaigong < y_2026, (
        "top-to-bottom must be 2022 node, 建照, 開工, 2026 node; got:\n" + joined)


def test_the_topmost_approval_is_the_oldest():
    """(d) The timeline ascends top-to-bottom: the oldest approval is the
    topmost approval row."""
    rows = _rendered_rows_top_to_bottom()
    approval_ys = [(i, r) for i, r in enumerate(rows)
                   if re.search(r"\d+ · \d{4}-\d{2}-\d{2}", r)]
    assert approval_ys, rows
    dates_in_order = [re.search(r"(\d{4}-\d{2}-\d{2})", r).group(1)
                      for _i, r in approval_ys]
    assert dates_in_order == sorted(dates_in_order), (
        f"approval rows must ascend top-to-bottom; got {dates_in_order}")
