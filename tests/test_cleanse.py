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

def test_land_recovered_from_name_tail_when_land_cell_empty():
    """recno 1354 崇仁新村: PDF glued the 地號 cell onto 案名, land cell empty.
    The cleanser must recover the trailing land fragment so the record gets a
    land core and clusters with its 擬訂 family instead of becoming 未解析."""
    rec = RawRecord(
        1354, "97/1/2", "萬華區",
        "變更臺北市萬華區崇仁新村都市更新事業計畫及權利變換計畫案臺北市萬華區崇仁新村青年段一小段711-3、青年段二小段18地號土地",
        "", "國防部", "某規劃",
    )
    r = cleanse(rec)
    assert r.section == "崇仁新村青年段一小段"
    assert r.first_parcel == "711-3"
    # cross-section second parcel (青年段二小段18) stays in `land`, consistent with
    # how recno 1399 parses the identical string
    assert r.parcels == ["711-3"]
    assert r.land_count == 2
    assert r.land == "臺北市萬華區崇仁新村青年段一小段711-3、青年段二小段18地號土地"
    assert r.name == "變更臺北市萬華區崇仁新村都市更新事業計畫及權利變換計畫案"
    assert any("地號自案名尾端復原" in f for f in r.auto_fixes)
    from urtpe.links import build_land_core_key
    assert build_land_core_key(r) == "萬華區崇仁新村青年段一小段711-3地號等2筆"




class TestContradictedSingleParcelCell:
    """repair-contradicted-single-parcel-cell: a 地號 cell that prints exactly
    one parcel token while the 案名 declares 1 筆 and names a different exact
    parcel is a publisher typo (recno 759: 案名 615地號1筆, cell `… 1
    地號1筆土地`; the platform and national portal both print 615). The parcel
    set follows the 案名 — the identity authority the record already trusts for
    section/first_parcel/land_count."""

    def test_contradicted_cell_follows_name(self):
        rec = RawRecord(759, "108/10/16", "內湖區",
                        "擬訂臺北市內湖區文德段二小段615地號1筆土地都市更新事業計畫案",
                        "臺北市內湖區文德段二小段 1 地號1筆土地", "廣宇建設實業股份有限公司",
                        "財團法人都市更新研究發展基金會")
        r = cleanse(rec)
        assert r.parcels == ["615"]
        assert r.first_parcel == "615"
        assert r.land_count == 1
        assert any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)
        assert any("1" in f and "615" in f for f in r.review_flags)

    def test_generalizes_to_any_numbers(self):
        """The rule is structural, not keyed to 615: any future PDF with the
        same typo shape (count==1, single differing token) fires it."""
        rec = RawRecord(5001, "115/2/3", "大同區",
                        "變更臺北市大同區大橋段一小段77地號1筆土地都市更新權利變換計畫案",
                        "臺北市大同區大橋段一小段 9 地號1筆土地", "某建設", "某規劃")
        r = cleanse(rec)
        assert r.parcels == ["77"]
        assert any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)

    def test_cross_section_multi_token_cell_untouched(self):
        """recno 269 shape: 1 筆 named on 446-1, cell lists 40 parcels across
        two sections — a different shape, never repaired."""
        rec = RawRecord(269, "99/5/7", "中正區",
                        "擬訂臺北市中正區中正段一小段446-1地號1筆土地及中正段三小段21地號等39筆土地都市更新事業計畫案",
                        "臺北市中正區中正段一小段 446-1地號、臺北市中正區中正段三小段 21、21-1、22-1、22-2、22-4、22-5、22-6、22-7、22-10、24、24-1、24-2、24-3、24-4、24-5、24-6、24-7、24-8、24-9、24-10、24-11、24-12、24-13、24-14、24-15、24-16、24-17、24-18、24-19、24-20、24-21、24-22、24-23、25 、82、82-2、82-3、82-7、82-9 地號等40筆土地",
                        "某建設", "某規劃")
        r = cleanse(rec)
        # the standing chunk-stripper consumes the bare `21、` before the 地號
        # closing phrase (verified against the emitted clean.tsv row — it has
        # 39 tokens, no bare 21); the shape under test is "many tokens", which
        # is what keeps this record outside the repair rule
        assert len(r.parcels) > 1 and "446-1" in r.parcels
        assert not any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)

    def test_merge_history_cell_untouched(self):
        """recno 957 shape: 518地號1筆(原15筆) whose cell lists the absorbed
        parcels — the cell is a faithful record of the merge, never repaired."""
        rec = RawRecord(957, "105/3/11", "大安區",
                        "變更臺北市大安區辛亥段三小段518地號1筆(原15筆)土地都市更新事業計畫案",
                        "臺北市大安區辛亥段三小段 518 地號土地(原 518、519、520、521、522、523、524、525、526、527、528、529、535、536、537 地號等 15 筆土地",
                        "某建設", "某規劃")
        r = cleanse(rec)
        assert "519" in r.parcels and "537" in r.parcels
        assert not any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)

    def test_agreeing_cell_gains_nothing(self):
        rec = RawRecord(758, "108/10/2", "內湖區",
                        "擬訂臺北市內湖區文德段二小段615地號1筆土地都市更新權利變換計畫案",
                        "臺北市內湖區文德段二小段 615 地號1筆土地", "某建設", "某規劃")
        r = cleanse(rec)
        assert r.parcels == ["615"]
        assert not any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)
        assert not any("地號欄單筆" in f for f in r.review_flags)

    def test_multi_count_name_untouched(self):
        """等N筆 with N>1: a first-token mismatch is a coverage shape, not the
        contradiction class."""
        rec = RawRecord(9, "113/1/1", "松山區",
                        "擬訂臺北市松山區西松段二小段54地號等9筆土地都市更新事業計畫案",
                        "臺北市松山區西松段二小段 55、56、57 地號等9筆土地", "某建設", "某規劃")
        r = cleanse(rec)
        assert r.parcels == ["55", "56", "57"]
        assert not any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)

    def test_unparseable_name_untouched(self):
        """No 案名 identity → no authority to repair against; the record stays
        as parsed (and flagged by the standing rules)."""
        rec = RawRecord(632, "104/2/14", "萬華區",
                        "變更臺北市萬華區崇仁新村都市更新事業計畫及權利變換計畫案",
                        "臺北市萬華區崇仁新村青年段一小段 1 地號1筆土地", "某建設", "某規劃")
        r = cleanse(rec)
        assert r.parcels == ["1"]
        assert not any("地號欄單筆地號與案名矛盾" in f for f in r.auto_fixes)


class TestPlanAbbreviationNormalization:
    """normalize-plan-abbreviation: 案名 土地都市更新計畫案 is a PDF-era
    abbreviation of 土地都市更新事業計畫案 (platform cross-ref 18/18 spells
    事業計畫案) — normalize + flag, track derives 事業計畫."""

    def test_abbreviated_name_gains_shiye_and_flag(self):
        rec = RawRecord(1041, "98/5/20", "中山區",
                        "擬訂臺北市中山區長春段二小段775地號等3筆土地都市更新計畫案",
                        "臺北市中山區長春段二小段775地號等3筆", "華潤建設", "某規劃")
        r = cleanse(rec)
        assert r.name == "擬訂臺北市中山區長春段二小段775地號等3筆土地都市更新事業計畫案"
        assert any("案名補事業" in f for f in r.auto_fixes)
        assert r.track == "事業計畫"

    def test_full_name_untouched(self):
        rec = RawRecord(810, "99/3/15", "北投區",
                        "變更臺北市北投區奇岩段五小段444地號等7筆土地都市更新事業計畫及擬訂權利變換計畫案",
                        "臺北市北投區奇岩段五小段444地號等7筆", "君岳開發", "某規劃")
        r = cleanse(rec)
        assert "都市更新事業計畫" in r.name
        assert not any("案名補事業" in f for f in r.auto_fixes)

    def test_no_node_derives_gengxin_plan_track_after_fix(self):
        rec = RawRecord(500, "100/6/30", "中正區",
                        "擬訂臺北市中正區南海段二小段41-4地號等55筆土地都市更新計畫案",
                        "臺北市中正區南海段二小段41-4地號等55筆", "全陽建設", "某規劃")
        r = cleanse(rec)
        assert r.track != "都市更新計畫"
        assert r.track == "事業計畫"


class TestPerTrackStageDerivation:
    """normalize/split-track-stage (viewer change §10): combined-track nodes
    carry TWO stage ordinals when the tracks progressed independently.
    507 anchor: 案名 變更…事業計畫及變更(第二次)權利變換計畫案 → 變更 / 變更(第二次)."""

    def test_split_stage_pair_derived(self):
        rec = RawRecord(1, "115/8/11", "中正區",
                        "變更臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫及變更(第二次)權利變換計畫案",
                        "臺北市中正區臨沂段一小段507地號等3筆", "東綺建設", "某規劃")
        r = cleanse(rec)
        assert r.stage == "變更"  # single field unchanged (案名 prefix)
        assert r.track == "事業計畫、權利變換"
        # additive per-track fields on the record
        assert getattr(r, "stage_事業計畫", None) == "變更"
        assert getattr(r, "stage_權利變換", None) == "變更(第二次)"

    def test_uniform_ordinal_keeps_shared_stage(self):
        rec = RawRecord(801, "99/3/1", "中正區",
                        "變更(第四次)臺北市中正區某段1地號等1筆土地都市更新事業計畫及權利變換計畫案",
                        "臺北市中正區某段1地號等1筆", "某建設", "某規劃")
        r = cleanse(rec)
        assert getattr(r, "stage_事業計畫", None) == "變更(第四次)"
        assert getattr(r, "stage_權利變換", None) == "變更(第四次)"

    def test_single_track_record_emits_no_pair(self):
        rec = RawRecord(5, "101/8/27", "中山區",
                        "擬訂臺北市中山區中山段一小段254地號等13筆土地都市更新事業計畫案",
                        "臺北市中山區中山段一小段254地號等13筆", "某建設", "某規劃")
        r = cleanse(rec)
        assert r.track == "事業計畫"
        assert getattr(r, "stage_事業計畫", None) is None
        assert getattr(r, "stage_權利變換", None) is None
