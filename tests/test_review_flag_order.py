# -*- coding: utf-8 -*-
"""A node's review_flags are emitted in a stable order (D15).

The order used to depend on the order the pipeline raised the flags, and the
pipeline's traversal order depends on the family's member order. The D5
ledger's 吉林676 merge reordered one family, and three 孤兒案件未達相似度門檻
flags on 大龍265-7 node 1242 swapped places. The flag texts did not change.

The emitter now sorts by (case id, text). The flag SET is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.graph import build_project_graph  # noqa: E402
from urtpe.models import CleanRecord, Project  # noqa: E402

ORPHAN = ("孤兒案件未達相似度門檻(案{cid}:0.54<0.70:變更臺北市大同區"
          "大龍段一小段265地號等30筆(原27筆)土地都市更新事業計畫案)")
STAGE = "階段與平台案件狀態不一致(公報變更(第二次)/平台變更)"


def _record(recno: int, flags: list[str]) -> CleanRecord:
    return CleanRecord(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district="大同區", district_land="大同區",
        name="擬訂臺北市大同區大龍段一小段265地號等30筆土地都市更新事業計畫案",
        name_raw="", land="臺北市大同區大龍段一小段265地號等30筆土地",
        section="大龍段一小段", first_parcel="265", parcels=["265"],
        aliases={}, land_count=30, orig_count=None, named_anchor="",
        area_section="", stage="變更", stage_index=1,
        track="事業計畫", implementer="甲", planner="乙",
        auto_fixes=[], review_flags=list(flags),
    )


def _emitted(flags: list[str]) -> list[str]:
    p = Project(project_id="大同區-大龍段一小段-265-7地號等2筆", anchor_recno=1242,
                members=[_record(1242, flags)])
    graph = build_project_graph(p, implementer="甲", name="案")
    return graph["nodes"][0]["review_flags"]


def test_two_orphan_flags_are_emitted_in_case_id_order():
    a, b = ORPHAN.format(cid="10908274"), ORPHAN.format(cid="11411017")
    out = _emitted([b, a])
    assert out == [a, b], "10908274 must come before 11411017"


def test_the_order_does_not_depend_on_the_raising_order():
    a, b = ORPHAN.format(cid="10908274"), ORPHAN.format(cid="11411017")
    assert _emitted([a, b]) == _emitted([b, a])


def test_a_flag_that_names_no_case_id_sorts_first():
    orphan = ORPHAN.format(cid="10908274")
    out = _emitted([orphan, STAGE])
    assert out[0] == STAGE, "the cleansing flag must come first"
    assert out[1] == orphan


def test_the_flag_set_is_unchanged():
    a, b = ORPHAN.format(cid="10908274"), ORPHAN.format(cid="11411017")
    out = _emitted([b, a, STAGE])
    assert set(out) == {a, b, STAGE}
    assert len(out) == len(set(out)), "no flag is duplicated"


def test_a_duplicate_flag_still_collapses_to_one():
    a = ORPHAN.format(cid="10908274")
    out = _emitted([a, a, a])
    assert out == [a]


def test_a_single_flag_is_unaffected():
    assert _emitted([STAGE]) == [STAGE]


def test_the_dalong265_7_shape():
    """The board's example: three orphan flags on node 1242."""
    ids = ["11411017", "10908272", "10908271"]
    flags = [ORPHAN.format(cid=c) for c in ids]
    out = _emitted(flags)
    assert out == [ORPHAN.format(cid="10908271"),
                   ORPHAN.format(cid="10908272"),
                   ORPHAN.format(cid="11411017")]
