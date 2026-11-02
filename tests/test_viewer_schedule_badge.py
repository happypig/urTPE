# -*- coding: utf-8 -*-
"""The 相關連結 schedule badge treats both approved words as the default state
(refresh-case-status-and-drop-withdrawn-fields task 1.6, D6).

The city's search list uses 已核准 and 已核定 for an approved case (cache,
2026-11-02: 739 / 14). The viewer omitted only 已核准, so one status rendered
as ``[已核定]`` in one project and as nothing in the next. The function is
evaluated from the shipped app.js in Node, not re-implemented here.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "viewer" / "app.js"


def _badge(values: list[str]) -> list[str]:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    js = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"const scheduleBadgeText = [^\n]+;", js)
    assert m, "scheduleBadgeText must stay a one-line arrow in app.js"
    prog = m.group(0) + f"\nconsole.log(JSON.stringify({json.dumps(values, ensure_ascii=False)}.map(scheduleBadgeText)));"
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_both_approved_words_omit_the_badge():
    assert _badge(["已核准", "已核定", ""]) == ["", "", ""]


def test_exceptional_states_keep_their_badge():
    assert _badge(["審查中", "自行撤回", "已駁回", "施工中"]) == [
        " [審查中]", " [自行撤回]", " [已駁回]", " [施工中]"]
