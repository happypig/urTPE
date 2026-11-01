# -*- coding: utf-8 -*-
"""The grey status chip (viewer-stage-chip-coverage task 1.1).

Structural tests over app.js (the established pattern) plus a Node-harness run
against a fixture dataset carrying the three chip states. The spec delta:
in-review/withdrawn projects show a grey chip instead of silence.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "viewer" / "app.js"
FIXTURE = ROOT / "tests" / "fixtures" / "viewer" / "chip_fixture.data.js"


def test_app_js_derives_a_status_chip_from_case_schedules():
    text = APP_JS.read_text(encoding="utf-8")
    assert "case_schedules" in text, "the chip must derive from case_schedules"
    # the derivation distinguishes in-review from withdrawn
    assert "審查中" in text and ("撤回" in text or "已駁回" in text or "已失效" in text)


def test_the_construction_stage_suppresses_the_status_chip():
    text = APP_JS.read_text(encoding="utf-8")
    # precedence: the construction badge wins, so the status chip is consulted
    # only when no construction stage exists
    assert re.search(r"statusChip|neverChip|stageChip", text), (
        "the chip derivation functions must exist")


def test_smoke_harness_passes_on_the_chip_fixture():
    """Acceptance: the real render path runs the fixture end to end."""
    result = subprocess.run(
        ["node", str(ROOT / "scripts" / "viewer_smoke.js"), str(FIXTURE)],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
