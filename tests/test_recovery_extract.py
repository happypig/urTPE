# -*- coding: utf-8 -*-
"""Extraction keep-and-mark under the recovery flag — backs tasks 3.1 and 3.2.

Without the flag nothing changes: publisher-truncated rows are dropped before
emission and named in the faults (the behaviour pinned by
tests/test_declared_count_check.py). With ``retain_truncated=True`` the truncated
row is retained carrying its surviving cells (核定日期, 行政區, 案名 fragment,
地號 fragment), marked as a source fault, and is not reported as excluded — the
recovery pass owns the decision from there.
"""

from __future__ import annotations

from urtpe.extract import extract_pdf_with_meta
from tests.gazette_fixtures import write_gazette

TRUNCATED = (
    (1, "115/8/27", "萬華區",
     "變更臺北市萬華區雙園段二小段505地號等77筆土地都市更新事業計畫案",
     "臺北市萬華區雙園段二小段505、506、507、508、509、510、511-1、512、513、"),
    (2, "115/8/26", "大安區",
     "擬訂臺北市大安區測試段二小段200地號等2筆土地都市更新事業計畫案",
     "臺北市大安區測試段二小段200、201地號等2筆土地"),
)
IMPLEMENTER, PLANNER = "甲公司", "乙顧問"


def _rows():
    return [(*r, IMPLEMENTER, PLANNER) for r in TRUNCATED]


def test_without_the_flag_the_row_is_dropped_and_named(tmp_path):
    pdf = str(tmp_path / "plain.pdf")
    write_gazette(pdf, _rows(), paginate=False)
    recs, meta = extract_pdf_with_meta(pdf)
    assert [r["recno"] for r in recs] == ["2"]
    assert meta["excluded_recnos"] == "1"
    assert meta["excluded_count"] == "1"


def test_with_the_flag_the_row_is_retained_and_marked(tmp_path):
    pdf = str(tmp_path / "keep.pdf")
    write_gazette(pdf, _rows(), paginate=False)
    recs, meta = extract_pdf_with_meta(pdf, retain_truncated=True)
    assert [r["recno"] for r in recs] == ["1", "2"]
    marked = next(r for r in recs if r["recno"] == "1")
    # the surviving cells ride along: date, district, 案名 fragment, 地號 fragment
    assert marked["source_fault"] == "truncated_land_cell"
    assert marked["fault_cause"] == "tail"
    assert marked["date"] == "115/8/27"
    assert marked["district"] == "萬華區"
    assert "雙園段二小段505地號等77筆" in marked["name"]
    assert marked["land"].startswith("臺北市萬華區雙園段二小段505、506、")
    # the row is pending, not excluded: the recovery pass owns the outcome
    assert "excluded_recnos" not in meta
    assert "excluded_count" not in meta


def test_a_completed_cell_is_never_marked(tmp_path):
    """A cell that lost only its closing phrase is sound data, under either flag."""
    rows = [(1, "115/8/27", "士林區",
             "擬訂臺北市士林區測試段一小段501地號等3筆土地都市更新事業計畫案",
             "臺北市士林區測試段一小段501、502、503",
             IMPLEMENTER, PLANNER)]
    pdf = str(tmp_path / "sound.pdf")
    write_gazette(pdf, rows, paginate=False)
    recs, meta = extract_pdf_with_meta(pdf, retain_truncated=True)
    assert [r["recno"] for r in recs] == ["1"]
    assert "source_fault" not in recs[0]
    assert meta.get("excluded_recnos") is None
