# -*- coding: utf-8 -*-
"""The 地號 cell's district is read from the collected enum (D14(b)).

The city prints three typos in the 地號 column: 臺北大安區 and 臺北士林區 (the
市 is missing) and 臺北市投區 (the 北 is missing). The strict 臺北市-anchored
regex read the first two as no district and the third as the non-district
投區, which then travelled into the record's land core.

The rule: read the cell's district from the enum collected from the corpus's
own 行政區 column. A cell naming a district the enum lacks reads '' — the
system never infers the missing character. The mismatch flag keeps quoting the
PRINTED token, so the 投區 rows keep their flag.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.cleanse import cleanse, cleanse_all  # noqa: E402
from urtpe.models import RawRecord  # noqa: E402

ENUM = ("中山區", "中正區", "信義區", "內湖區", "北投區", "南港區",
        "士林區", "大同區", "大安區", "文山區", "松山區", "萬華區")


def _raw(**kw) -> RawRecord:
    base = dict(
        recno=1, date="113/6/30", district="大安區",
        name="擬訂臺北市大安區辛亥段四小段496-13地號等14筆土地都市更新事業計畫案",
        land="臺北大安區辛亥段四小段 496-13、196-15、507、508、509-2、510、510-1、510-2、511、512、513、514、515地號等14筆",
        implementer="甲公司", planner="乙規劃公司",
    )
    base.update(kw)
    return RawRecord(**base)


def test_a_cell_that_omits_the_city_reads_its_district():
    c = cleanse(_raw(), districts=ENUM)
    assert c.district_land == "大安區"
    assert c.section == "辛亥段四小段"
    assert c.first_parcel == "496-13"
    assert "510-2" in c.parcels
    assert c.land_count == 14


def test_a_cell_that_omits_the_north_reads_nothing():
    """臺北市投區 — 投區 is not a district, and the missing 北 is never
    inferred."""
    c = cleanse(_raw(
        district="北投區",
        name="擬訂臺北市北投區崇仰段三小段156地號等23筆土地都市更新事業計畫案",
        land="臺北市投區崇仰段三小段 156、157、160、161、165、166、168、169、170、171、172、173、174、175、176、177、178、179、180、181、182、183、184地號等23筆",
    ), districts=ENUM)
    assert c.district_land == ""
    assert c.district == "北投區"
    assert "行政區與地號行政區不一致(地號為投區)" in c.review_flags
    assert c.section == "崇仰段三小段"


def test_a_cell_that_omits_the_city_reads_the_district_in_shi_lin():
    c = cleanse(_raw(
        district="士林區",
        name="擬訂臺北市士林區百齡段二小段354地號等14筆土地都市更新事業計畫案",
        land="臺北士林區百齡段二小段 354、355、356、357、357-3、357-4、357-5、357-6、358、359、360、361、362、363地號等14筆",
    ), districts=ENUM)
    assert c.district_land == "士林區"
    assert c.section == "百齡段二小段"


def test_a_normal_cell_is_unchanged():
    c = cleanse(_raw(
        district="中山區",
        name="擬訂臺北市中山區長春段二小段775地號等3筆土地都市更新事業計畫案",
        land="臺北市中山區長春段二小段 775、776、777地號等3筆",
    ), districts=ENUM)
    assert c.district_land == "中山區"
    assert c.section == "長春段二小段"
    assert c.parcels == ["775", "776", "777"]


def test_the_enum_is_not_hard_coded():
    """A district the corpus does not publish reads nothing — the enum comes
    from the data, not from a list in the reader."""
    c = cleanse(_raw(land="臺北市大安區辛亥段四小段 496-13地號等1筆"), districts=("士林區",))
    assert c.district_land == ""


def test_without_an_enum_the_strict_answer_stays():
    """The single-record call sites keep today's behaviour."""
    c = cleanse(_raw())
    assert c.district_land == ""
    c2 = cleanse(_raw(land="臺北市大安區辛亥段四小段 496-13地號等1筆"))
    assert c2.district_land == "大安區"


def test_cleanse_all_collects_the_enum_from_the_records():
    """The corpus's own 行政區 column supplies the enum."""
    records = [
        _raw(recno=1, district="大安區",
             land="臺北大安區辛亥段四小段 496-13地號等1筆"),
        _raw(recno=2, district="士林區",
             name="擬訂臺北市士林區百齡段二小段354地號等1筆土地都市更新事業計畫案",
             land="臺北士林區百齡段二小段 354地號等1筆"),
        _raw(recno=3, district="北投區",
             name="擬訂臺北市北投區崇仰段三小段156地號等1筆土地都市更新事業計畫案",
             land="臺北市投區崇仰段三小段 156地號等1筆"),
    ]
    out = cleanse_all(records)
    assert [r.district_land for r in out] == ["大安區", "士林區", ""]
    assert "行政區與地號行政區不一致(地號為投區)" in out[2].review_flags


def test_the_project_identity_does_not_move():
    """slug_for reads the 行政區 column, so the district re-read cannot move
    the project_id."""
    from urtpe.merge import merge

    records = [
        _raw(recno=1, district="大安區",
             land="臺北大安區辛亥段四小段 496-13、196-15、507、508、509-2、510、510-1、510-2、511、512、513、514、515地號等14筆"),
    ]
    projects = merge(cleanse_all(records))
    assert len(projects) == 1
    assert projects[0].project_id.startswith("大安區-辛亥段四小段-496-13")
