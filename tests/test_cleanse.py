"""Cleansing domain tests: normalization, derivation, flags."""

from __future__ import annotations

from urtpe.cleanse import cn_to_int, cleanse, roc_to_iso
from urtpe.models import RawRecord, make_record


def _raw(**kw) -> RawRecord:
    base = dict(
        recno=1, date="113/6/30", district="松山區", name="擬訂臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫案",
        land="臺北市松山區X段一小段1、2、3地號等10筆", implementer="甲公司", planner="乙規劃公司",
    )
    base.update(kw)
    return RawRecord(**base)


def test_roc_to_iso():
    assert roc_to_iso("113/6/30") == ("2024-06-30", (2024, 6, 30))
    assert roc_to_iso("99/1/2") == ("2010-01-02", (2010, 1, 2))
    assert roc_to_iso("115/8/11")[0] == "2026-08-11"
    assert roc_to_iso("bad") == (None, None)


def test_cn_to_int():
    assert cn_to_int("一") == 1
    assert cn_to_int("十") == 10
    assert cn_to_int("十三") == 13
    assert cn_to_int("二") == 2


def test_normalize_common_typos():
    c = cleanse(_raw(land="臺北市松山區X段一小段1地號等10筆(原9筆)"))
    assert c.orig_count == 9


def test_shiye_huan_jihua_typo_treated_as_shiye_jihua():
    """Recno 621 (facts): 事業換計畫 is a scrambled 事業計畫 — track must be
    事業計畫, not 其他, and the fix is recorded."""
    c = cleanse(_raw(name="擬訂臺北市北投區大業段三小段184-1地號等10筆土地都市更新事業換計畫案"))
    assert c.track == "事業計畫"
    assert "事業換計畫" not in c.name
    assert any("事業計畫" in f for f in c.auto_fixes)


def test_parcel_parse():
    c = cleanse(_raw())
    assert c.section == "X段一小段"
    assert c.first_parcel == "1"
    assert c.parcels == ["1", "2", "3"]
    assert c.land_count == 10


def test_alias_renumbering():
    c = cleanse(_raw(name="擬訂臺北市松山區X段一小段689地號等10筆土地都市更新事業計畫案",
                     land="臺北市松山區X段一小段689地號(原726地號)等10筆"))
    assert c.aliases == {"689": ["726"]}
    assert c.first_parcel == "689"
    assert "726" in c.parcel_set()


def test_named_anchor_detected():
    c = cleanse(_raw(name="擬訂臺北市松山區X段一小段1地號(原東星大樓基地)都市更新事業計畫案"))
    assert c.named_anchor == "原東星大樓基地"


def test_area_section_detected():
    c = cleanse(_raw(land="臺北市松山區X段一小段1地號等5筆(B區段)"))
    assert c.area_section == "B"


def test_stage_derivation():
    assert cleanse(_raw()).stage == "擬訂"
    c = cleanse(_raw(name="變更臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫案"))
    assert c.stage == "變更" and c.stage_index == 1
    c2 = cleanse(_raw(name="變更(第二次)臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫案"))
    assert c2.stage == "變更(第二次)" and c2.stage_index == 2


def test_name_identity_fills_wrapped_land_cell():
    """A 地號 continuation cell missing its 段小段 prefix still inherits the
    stable identity from the 案名."""
    c = cleanse(_raw(name="擬訂臺北市中正區永昌段三小段159地號等113筆土地都市更新事業計畫案",
                     land="37、37-1、38、39、40地號"))
    assert c.section == "永昌段三小段"
    assert c.first_parcel == "159"
    assert c.land_count == 113
    assert c.parcels == ["37", "37-1", "38", "39", "40"]
    assert any("缺少段小段" in f for f in c.review_flags)


def test_name_land_section_mismatch_flag():
    c = cleanse(_raw(name="擬訂臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫案",
                     land="臺北市松山區Y段二小段1地號等10筆"))
    assert any("不一致" in f for f in c.review_flags)


def test_section_without_xiaoduan():
    c = cleanse(_raw(name="擬訂臺北市松山區民生段77地號等10筆土地都市更新權利變換計畫案"))
    assert c.section == "民生段"
    assert c.first_parcel == "77"
    assert c.land_count == 10


def test_section_with_numeral_only_xiaoduan():
    c = cleanse(_raw(name="擬訂臺北市信義區吳興一小段330地號等43筆土地都市更新事業計畫案"))
    assert c.section == "吳興一小段"
    assert c.first_parcel == "330"
    assert c.land_count == 43


def test_district_typo_auto_fix():
    c = cleanse(_raw(district="松化區"))
    assert c.district == "松山區"
    assert "行政區錯字" in c.auto_fixes[0]


def test_district_mismatch_flag():
    c = cleanse(_raw(district="中正區", land="臺北市大同區X段一小段1地號等10筆"))
    assert any("不一致" in f for f in c.review_flags)


def test_unparseable_date_flag():
    c = cleanse(_raw(date=""))
    assert "日期無法解析" in c.review_flags


def test_missing_section_flag():
    c = cleanse(_raw(land="臺北市松山區X地號"))
    assert any("地號無法解析" in f for f in c.review_flags)


def test_track_detection():
    c = cleanse(_raw())
    assert "事業計畫" in c.track and "權利變換" not in c.track
    c2 = cleanse(_raw(name="擬訂臺北市松山區X段一小段1地號等10筆土地都市更新事業計畫及權利變換計畫案"))
    assert "事業計畫" in c2.track and "權利變換" in c2.track


def test_name_fallback_single_parcel_exact():
    """A malformed 地號 cell missing 地號 (…1251筆土地) yields parcels {125}
    derived from the 案名 land fragment."""
    c = cleanse(_raw(district="中山區",
                     name="擬訂臺北市中山區中山段二小段125地號1筆土地都市更新權利變換計畫案",
                     land="臺北市中山區中山段二小段1251筆土地"))
    assert c.parcels == ["125"]
    assert c.first_parcel == "125"
    assert c.land_count == 1


def test_name_fallback_partial_parcel_preserves_key():
    """A name …531地號等2筆… preserves section, first_parcel 531, and land_count
    2 via the name fallback when the 地號 cell splits on 及 instead of 、."""
    c = cleanse(_raw(district="南港區",
                     name="變更臺北市南港區南港段一小段531地號等2筆土地都市更新權利變換計畫案",
                     land="臺北市南港區南港段一小段531及375-16地號等2筆土地"))
    assert c.section == "南港段一小段"
    assert c.first_parcel == "531"
    assert c.land_count == 2
    assert c.parcels == ["531"]


def test_name_fallback_keeps_missing_list_flag():
    """The malformed source cell still records 缺少地號清單 after the fallback."""
    c = cleanse(_raw(district="中山區",
                     name="擬訂臺北市中山區中山段二小段125地號1筆土地都市更新權利變換計畫案",
                     land="臺北市中山區中山段二小段1251筆土地"))
    assert c.parcels == ["125"]
    assert any("缺少地號清單" in f for f in c.review_flags)