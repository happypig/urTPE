# -*- coding: utf-8 -*-
"""A review flag quotes a normalised date (D15 follow-up).

The unplaced-node flag quotes the node's own date, which reached it in
whatever form the pipeline held: slash-western from the PDF (97/1/2), ISO
from a --from-js rebuild. The flag text then changed between runs, so the
duplicate collapse (by exact text) stopped working and the same finding
appeared twice in two spellings — 15 nodes carried it after the D7 re-emit.

The flag's text must be a function of the node, not of the run.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.cli import _normalise_flags  # noqa: E402
from urtpe.links import _flag_date  # noqa: E402

FLAG = ("節點未能對應平台案件(案名:擬訂臺北市大安區懷生段一小段928地號1筆"
        "土地都市更新事業計畫案, 日期:{date})")


def test_a_slash_date_is_normalised():
    assert _flag_date("2013/11/5") == "2013-11-05"


def test_an_iso_date_passes_through():
    assert _flag_date("2013-11-05") == "2013-11-05"


def test_a_roc_date_becomes_iso():
    assert _flag_date("97/1/2") == "2008-01-02"


def test_the_loader_normalises_the_flag_text():
    out = _normalise_flags([FLAG.format(date="2013/11/5")])
    assert out == [FLAG.format(date="2013-11-05")]


def test_the_two_spellings_collapse_to_one():
    from urtpe.graph import _stable_flags

    flags = [FLAG.format(date="2013/11/5"), FLAG.format(date="2013-11-05")]
    out = _stable_flags(_normalise_flags(flags))
    assert out == [FLAG.format(date="2013-11-05")], (
        "the same finding must appear once, not twice in two spellings")


def test_other_flags_are_untouched():
    out = _normalise_flags(["階段與平台案件狀態不一致(公報變更(第二次)/平台變更)"])
    assert out == ["階段與平台案件狀態不一致(公報變更(第二次)/平台變更)"]
