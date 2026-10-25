# -*- coding: utf-8 -*-
"""Declared-count reconciliation and the corrected parcel counter.

Task group 2 of check-declared-parcel-counts, written before implementation
per the openspec test-first gate. The cell texts below are transcribed from
the measured gazettes cited in the change's poc_findings.md: LAND_1005 is the
full 編號 1005 地號 cell (核定案件-2026-10-23.pdf, page 170 row 5, 76 of 77
declared parcels, cut mid-token at `579-`); LAND_140 is 編號 60's cell (page
10 row 3), whose `163 164` is a space standing where a separator belongs.
"""

from __future__ import annotations

from urtpe import extract as E
from urtpe.extract import extract_pdf_with_faults, extract_pdf_with_meta
from tests.gazette_fixtures import write_gazette

# 編號 1005 (2026-10-15 gazette), verbatim: cut mid-token, no closing phrase.
LAND_1005 = (
    "臺北市萬華區雙園段二小段505、506、507、508、509、510、511-1、512、513、"
    "514、514-1、514-2、515、516、516-1、517、518、519、520、521、522、523、"
    "523-1、524、524-1、525、526、527、527-1、529、529-1、541、541-1、542、"
    "542-3、542-4、542-5、542-6、542-12、542-13、542-14、543、544、545、546、"
    "547、548、549、550、551、552、553、566、567、568、569、569-1、570、570-2、"
    "571、572、573、573-1、573-2、573-3、573-4、573-5、573-6、573-7、574、"
    "574-1、575-1、576、577、578、579-"
)
NAME_1005 = "變更臺北市萬華區雙園段二小段505地號等77筆土地都市更新事業計畫案"

# 編號 60 (2026-10-15 gazette), verbatim: `163 164` carries a space where the
# separator belongs; the cell lists all 22 parcels its 案名 declares.
LAND_140 = (
    "臺北市中山區長安段四小段 140 、140-1、141、142、143、144、145、146、"
    "147、148、149、149-1、157、157-1、158、159、160、161、162、163 164、"
    "165地號等22筆土地"
)
NAME_140 = "變更臺北市中山區長安段四小段140地號等22筆土地都市更新權利變換計畫案"


def _pdf(tmp_path, name, rows, **kw):
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), rows, **kw)
    return str(path)


# --- 2.1 the 編號 1005 shape: mid-token hyphen ending ------------------------

def test_mid_token_hyphen_ending_fires_the_tail_pattern():
    assert E.TRUNCATED_TAIL_RE.search(LAND_1005)
    assert not E.closing_phrase_present(LAND_1005)
    assert E.parcel_token_count(LAND_1005) == 76
    assert E.declared_parcel_count(NAME_1005) == 77
    assert not E.land_cell_is_complete(LAND_1005, NAME_1005)


def test_gazette_with_a_mid_token_hyphen_cut_excludes_the_record(tmp_path):
    """The 編號 1005 shape must not reach the dataset with a short parcel list."""
    rows = [
        (1, "115/8/27", "萬華區", NAME_1005,
         "臺北市萬華區雙園段二小段505、506、507、576、577、578、579-",
         "甲公司", "乙顧問"),
        (2, "115/8/26", "大安區",
         "擬訂臺北市大安區測試段二小段200地號等2筆土地都市更新事業計畫案",
         "臺北市大安區測試段二小段 200、201 地號等2筆土地",
         "丙公司", "丁顧問"),
    ]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "hyphen", rows, paginate=False))
    assert [r["recno"] for r in recs] == ["2"]
    assert [f.kind for f in faults] == ["source_truncated_land_cell"]
    assert faults[0].recno == "1"
    assert faults[0].cause == "tail"


# --- 2.2 count check: cut with no tail-pattern ending -----------------------

def test_count_check_catches_a_cut_with_no_tail_pattern(tmp_path):
    """The cell was cut after `(部分)`: the text ends on a paren, no tail
    pattern fires, the closing phrase is gone, and the list is short of the
    declared count."""
    land = "臺北市士林區測試段一小段 501、502、503、547(部分)"
    name = "擬訂臺北市士林區測試段一小段501地號等8筆土地都市更新事業計畫案"
    assert not E.TRUNCATED_TAIL_RE.search(land)
    assert not E.closing_phrase_present(land)
    assert E.parcel_token_count(land) < E.declared_parcel_count(name)
    rows = [(1, "115/8/27", "士林區", name, land, "甲公司", "乙顧問")]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "partial", rows, paginate=False))
    assert recs == []
    assert [f.kind for f in faults] == ["source_truncated_land_cell"]
    assert faults[0].cause == "declared_count"
    assert "8" in faults[0].detail  # the declared count is named


# --- 2.3 rows whose 案名 declares no count ----------------------------------

def test_no_declared_count_and_no_tail_is_emitted_normally(tmp_path):
    rows = [(1, "115/8/27", "士林區",
             "擬訂臺北市士林區測試段一小段501地號土地都市更新事業計畫案",
             "臺北市士林區測試段一小段 501、502、503等筆土地",
             "甲公司", "乙顧問")]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "nocount", rows, paginate=False))
    assert faults == []
    assert [r["recno"] for r in recs] == ["1"]


def test_no_declared_count_but_mid_token_hyphen_is_still_tail_caught(tmp_path):
    """A cell ending `579-` is incomplete whatever the 案名 says; completion is
    refused because no count closes it."""
    rows = [(1, "115/8/27", "萬華區",
             "擬訂臺北市萬華區雙園段二小段505地號土地都市更新事業計畫案",
             "臺北市萬華區雙園段二小段505、506、579-",
             "甲公司", "乙顧問")]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "nocount2", rows, paginate=False))
    assert recs == []
    assert [f.kind for f in faults] == ["source_truncated_land_cell"]


# --- 2.4 closing phrase present: never count-checked ------------------------

def test_closing_phrase_present_cell_with_mismatch_is_emitted(tmp_path):
    """A cell whose closing phrase is present was drawn to completion; a
    mismatch against the 案名 is a city-side inconsistency, not a cut. Measured
    as 編號 427 (2026-10-15): the 案名 declares 521 while the cell declares and
    lists 52. Also exercised: `163 164` with a space where the separator
    belongs (編號 60's shape, shortened to one line — the fixture's textbox
    wrapper drops the space at a line break, which the real publisher keeps,
    so the wrapped original is asserted at counter level only)."""
    rows = [
        (1, "115/8/27", "南港區",
         "擬訂臺北市南港區南港段二小段671-6地號等521筆土地更新事業計畫及權利變換計畫案",
         "臺北市南港區南港段二小段 671-6、672、673、674地號等52筆土地",
         "甲公司", "乙顧問"),
        (2, "115/8/26", "中山區", NAME_140,
         "臺北市中山區長安段四小段 162、163 164、165地號等4筆土地",
         "丙公司", "丁顧問"),
    ]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "phrase", rows, paginate=False))
    assert faults == []
    assert [r["recno"] for r in recs] == ["1", "2"]
    assert E.parcel_token_count(LAND_140) == 22


# --- 2.5 the closing-phrase rescue is unchanged -----------------------------

def test_visible_equals_declared_with_dangling_tail_is_kept(tmp_path):
    rows = [(1, "115/8/27", "萬華區",
             "擬訂臺北市萬華區測試段一小段100地號等4筆土地都市更新事業計畫案",
             "臺北市萬華區測試段一小段 100、101、102、103 、",
             "甲公司", "乙顧問")]
    recs, faults = extract_pdf_with_faults(_pdf(tmp_path, "rescue", rows, paginate=False))
    assert faults == []
    assert [r["recno"] for r in recs] == ["1"]


# --- 2.6 corpus completion for count-caught rows ----------------------------

_CAND = {
    "recno": "900", "district": "士林區",
    "name": "擬訂臺北市士林區測試段一小段501地號等8筆土地都市更新事業計畫案",
    "land": "臺北市士林區測試段一小段 501、502、503、547(部分)、548、549、550、551地號等8筆土地",
    "section": "測試段一小段", "parcel_count": 8, "gazette_id": "115-08-11",
}


def test_count_caught_row_is_completed_from_the_corpus(tmp_path):
    land = "臺北市士林區測試段一小段 501、502、503、547(部分)"
    name = "擬訂臺北市士林區測試段一小段501地號等8筆土地都市更新事業計畫案"
    rows = [(1, "115/8/27", "士林區", name, land, "甲公司", "乙顧問")]
    recs, meta = extract_pdf_with_meta(
        _pdf(tmp_path, "complete", rows, paginate=False), corpus=[dict(_CAND)])
    assert meta.get("completed_count") == "1"
    assert [r["recno"] for r in recs] == ["1"]
    assert "548" in recs[0]["land"]  # the completed list, not the cut cell


def test_count_caught_row_is_excluded_when_no_candidate_closes(tmp_path):
    land = "臺北市士林區測試段一小段 501、502、503、547(部分)"
    name = "擬訂臺北市士林區測試段一小段501地號等8筆土地都市更新事業計畫案"
    short = dict(_CAND, land="臺北市士林區測試段一小段 501、502、503、547(部分)、548地號等6筆土地",
                 parcel_count=6)
    rows = [(1, "115/8/27", "士林區", name, land, "甲公司", "乙顧問")]
    recs, meta = extract_pdf_with_meta(
        _pdf(tmp_path, "refuse", rows, paginate=False), corpus=[short])
    assert recs == []
    assert meta.get("excluded_count") == "1"


# --- 2.7 the corrected counter ----------------------------------------------

def test_space_where_a_separator_belongs_delimits_two_parcels():
    # 編號 60 measured: 163 164 is two parcels, and the whole cell counts 22.
    assert E.parcel_token_count(LAND_140) == 22
    assert E.parcel_token_count("臺北市中山區長安段四小段 162、163 164、165地號等4筆土地") == 4


def test_space_before_a_sub_parcel_hyphen_continues_the_token():
    # 雙園段505 cells measured: `573 -6` is the single parcel 573-6.
    assert E.parcel_token_count("臺北市萬華區雙園段二小段573 -6、573-7地號等2筆土地") == 2


def test_closing_phrase_variants_leak_no_count_digits():
    assert E.parcel_token_count("臺北市萬華區萬華段二小段901、902地號等22土地") == 2
    assert E.parcel_token_count("臺北市北投區桃源段二小段251、252地號等2筆(原17筆)土地") == 2
    assert E.parcel_token_count(
        "臺北市中正區臨沂段二小段233、234、246-3地號等 18 筆土地)等 4 筆土地") == 3
    assert E.parcel_token_count("臺北市信義區丁段四小段 11、12 地號等2筆") == 2


def test_closing_phrase_detection():
    assert E.closing_phrase_present("臺北市中正區甲段一小段 1、2 地號等共 3筆土地")
    assert E.closing_phrase_present("臺北市大安區乙段二小段 5、6 地號等 2 筆土地)")
    assert E.closing_phrase_present("臺北市松山區丙段三小段 9、10 地號等 2 筆土 地")
    assert E.closing_phrase_present("臺北市信義區丁段四小段 11、12 地號等2筆")
    assert E.closing_phrase_present("臺北市萬華區萬華段二小段901、902地號等22土地")
    assert E.closing_phrase_present("臺北市北投區桃源段二小段251、252地號等2筆(原17筆)土地")
    assert not E.closing_phrase_present(LAND_1005)
    assert not E.closing_phrase_present("臺北市萬華區雙園段二小段505、506、507、762地號等")
    assert not E.closing_phrase_present("臺北市士林區測試段一小段 501、502、503、547(部分)")


# --- 2.8 acceptance: the run report names every exclusion and its cause -----

def test_acceptance_hyphen_cut_and_count_cut_are_both_named(tmp_path):
    rows = [
        (1, "115/8/27", "大安區",
         "擬訂臺北市大安區測試段二小段200地號等2筆土地都市更新事業計畫案",
         "臺北市大安區測試段二小段 200、201 地號等2筆土地",
         "丙公司", "丁顧問"),
        (2, "115/8/26", "萬華區", NAME_1005,
         "臺北市萬華區雙園段二小段505、506、507、576、577、578、579-",
         "甲公司", "乙顧問"),
        (3, "115/8/25", "士林區",
         "擬訂臺北市士林區測試段一小段501地號等8筆土地都市更新事業計畫案",
         "臺北市士林區測試段一小段 501、502、503、547(部分)",
         "戊公司", "己顧問"),
    ]
    path = _pdf(tmp_path, "accept", rows, paginate=False)
    recs, faults = extract_pdf_with_faults(path)
    _recs2, meta = extract_pdf_with_meta(path)
    assert [r["recno"] for r in recs] == ["1"]
    assert [f.recno for f in faults] == ["2", "3"]
    assert {f.kind for f in faults} == {"source_truncated_land_cell"}
    causes = {f.recno: f.cause for f in faults}
    assert causes == {"2": "tail", "3": "declared_count"}
    assert meta["excluded_count"] == "2"
    assert meta["excluded_recnos"] == "2,3"
    assert meta["excluded_by_tail"] == "1"
    assert meta["excluded_by_count"] == "1"
