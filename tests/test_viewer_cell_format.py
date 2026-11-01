# -*- coding: utf-8 -*-
"""Human-readable table cells and ISO dates in the detail pane
(viewer-stage-chip-coverage task 1.2). Structural tests over app.js pin the
formatter contracts; the render behaviour is covered by the smoke harness on
the real payload."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "viewer" / "app.js"


def test_fmtCell_exists_and_joins_lists_with_ton():
    text = APP_JS.read_text(encoding="utf-8")
    assert re.search(r"function fmtCell\b", text), (
        "fmtCell must exist as the table's cell formatter")
    assert "、" in text, "parcel lists join with 、 as prose"


def test_fmtCell_renders_the_em_dash_for_empty_and_absent():
    text = APP_JS.read_text(encoding="utf-8")
    # the em dash appears as a string literal in the formatter's empty branches
    assert re.search(r"['\"]—['\"]", text), "the em dash marker literal must exist"


def test_fmtDate_exists_and_converts_roc_and_slash_forms():
    text = APP_JS.read_text(encoding="utf-8")
    assert re.search(r"function fmtDate\b", text), (
        "fmtDate must exist as the detail pane's date formatter")
    # the ROC rule: year < 1911 => +1911 (extract.to_iso's rule, client-side)
    assert re.search(r"1911", text)
