"""Merging domain tests: similarity scoring, clustering, anchoring."""

from __future__ import annotations

from urtpe.cleanse import cleanse
from urtpe.merge import FLAG_THRESHOLD, LINK_THRESHOLD, merge, pick_anchor, score, slug_for
from urtpe.models import RawRecord, make_record
from tests.fixtures import SAMPLE_ROWS


def _raw(recno, date, name, land, imp="甲公司", district="中正區", planner="乙規劃") -> RawRecord:
    return RawRecord(recno=recno, date=date, district=district, name=name, land=land,
                     implementer=imp, planner=planner)


def _c(district, section, first, parcels, date="113/1/1", name="擬訂案", land_count=None, orig=None, anchor="", recno=1):
    land = f"臺北市{district}{section}{first}地號"
    if parcels:
        land = f"臺北市{district}{section}" + "、".join(parcels) + "地號"
    if land_count:
        land += f"等{land_count}筆"
    if orig:
        land += f"(原{orig}筆)"
    r = _raw(recno, date, name, land)
    c = cleanse(r)
    if anchor:
        c.named_anchor = anchor
    return c


def test_same_record_max_similarity():
    a = _c("中正區", "永昌段三小段", "159", ["159", "161"])
    b = _c("中正區", "永昌段三小段", "159", ["159", "161"])
    assert score(a, b) >= LINK_THRESHOLD


def test_different_section_not_linked():
    a = _c("中正區", "永昌段三小段", "159", ["159"])
    b = _c("中正區", "永昌段四小段", "159", ["159"])
    assert score(a, b) < FLAG_THRESHOLD


def test_named_anchor_unconditional_link():
    a = _c("中正區", "X段一小段", "1", ["1"], anchor="原東星大樓基地")
    b = _c("中正區", "X段一小段", "1", ["1"], anchor="原東星大樓基地")
    assert score(a, b) == 1.0


def test_alias_bridges_renumbering():
    a = _c("松山區", "Y段二小段", "689", ["689", "690"])
    b = _c("松山區", "Y段二小段", "726", ["726", "690"])
    b.aliases = {"726": ["689"]}
    assert score(a, b) >= LINK_THRESHOLD


def test_stage_variants_cluster_into_one_project():
    recs = [
        cleanse(_raw(1, "115/8/11", SAMPLE_ROWS[0][3], SAMPLE_ROWS[0][4])),
        cleanse(_raw(2, "115/7/1", SAMPLE_ROWS[1][3], SAMPLE_ROWS[1][4])),
        cleanse(_raw(3, "115/6/1", SAMPLE_ROWS[2][3], SAMPLE_ROWS[2][4])),
    ]
    projects = merge(recs)
    assert len(projects) == 1
    assert [m.recno for m in projects[0].members] == [1, 2, 3]


def test_distinct_projects_not_merged():
    a = _c("中正區", "永昌段三小段", "159", ["159"], date="115/1/1", recno=1)
    b = _c("中山區", "長安段一小段", "50", ["50"], date="115/1/1", recno=2)
    projects = merge([a, b])
    assert len(projects) == 2


def test_anchor_is_newest_then_lowest_recno():
    a = _c("中正區", "永昌段三小段", "159", ["159"], date="113/1/1", recno=3)
    b = _c("中正區", "永昌段三小段", "159", ["159"], date="115/1/1", recno=1)
    c = _c("中正區", "永昌段三小段", "159", ["159"], date="115/1/1", recno=2)
    members = [a, b, c]
    anchor = pick_anchor(members)
    assert anchor.recno == b.recno


def test_slug_is_anchor_name_core_and_append_stable():
    anchor = _c("中正區", "永昌段三小段", "159", ["159"], land_count=113, date="115/8/11", recno=7)
    slug = slug_for(anchor)
    assert slug == "中正區-永昌段三小段-159地號等113筆"
    assert "7" not in slug  # never 編號-based


def test_coverage_change_bridge_project_id_spans_generations():
    a = _c("中正區", "永昌段三小段", "159", ["159"], date="114/1/1", recno=2)
    b = _c("中正區", "永昌段三小段", "159", ["159"], date="115/1/1", land_count=113, orig=100, recno=1)
    a.land_count = 100
    assert score(a, b) >= LINK_THRESHOLD
    projects = merge([a, b])
    assert len(projects) == 1
    assert all(p.project_id == projects[0].project_id for p in projects)


def test_borderline_pair_is_flagged_not_linked():
    a = _c("中正區", "永昌段三小段", "159", ["159", "888"], land_count=200, recno=1)
    b = _c("中正區", "永昌段三小段", "888", ["888", "777"], land_count=200, recno=2)
    projects = merge([a, b])
    assert len(projects) == 2
    assert projects[0].borderline or projects[1].borderline


def _empty(district, section, first, count, recno=1, date="113/1/1", name="擬訂案"):
    """A CleanRecord with an empty parcel set (unparseable 地號 cell)."""
    r = make_record(recno, date, district, name, "", "甲公司", "乙規劃")
    r.section = section
    r.first_parcel = first
    r.land_count = count
    return r


def test_empty_parcels_full_land_key_links():
    a = _empty("中山區", "中山段二小段", "125", 1, recno=1)
    b = _empty("中山區", "中山段二小段", "125", 1, recno=2)
    assert score(a, b) >= LINK_THRESHOLD
    projects = merge([a, b])
    assert len(projects) == 1


def test_125_family_merges_across_implementer_change():
    recs = [
        cleanse(_raw(478, "111/3/9", "擬訂臺北市中山區中山段二小段125地號1筆土地都市更新權利變換計畫案",
                     "臺北市中山區中山段二小段1251筆土地", imp="新碩建設股份有限公司", district="中山區")),
        cleanse(_raw(234, "113/4/9", "變更臺北市中山區中山段二小段125地號1筆土地都市更新權利變換計畫案",
                     "臺北市中山區中山段二小段1251筆土地", imp="中國建築經理股份有限公司", district="中山區")),
    ]
    projects = merge(recs)
    assert len(projects) == 1
    assert projects[0].anchor_recno == 234
    assert {m.recno for m in projects[0].members} == {234, 478}


def test_531_family_merges_into_one_project_not_four():
    rows = [
        (971, "106/7/20", "變更臺北市南港區南港段一小段531地號等2筆土地都市更新事業計畫及權利變換計畫案",
         "台灣肥料股份有限公司"),
        (748, "108/10/25", "變更(第二次)臺北市南港區南港段一小段531地號等2筆土地都市更新事業計畫及權利變換計畫案",
         "愛山林建設開發股份有限公司"),
        (473, "111/3/23", "變更(第三次)臺北市南港區南港段一小段531地號等2筆土地都市更新事業計畫及權利變換計畫案",
         "愛山林建設開發股份有限公司"),
        (416, "111/9/15", "變更(第四次)臺北市南港區南港段一小段531地號等2筆土地都市更新權利變換計畫案",
         "愛山林建設開發股份有限公司"),
    ]
    land = "臺北市南港區南港段一小段531及375-16地號等2筆土地"
    recs = [cleanse(_raw(recno, date, name, land, imp=imp, district="南港區"))
            for recno, date, name, imp in rows]
    projects = merge(recs)
    assert len(projects) == 1
    assert projects[0].anchor_recno == 416
    assert {m.recno for m in projects[0].members} == {971, 748, 473, 416}


def test_302_family_merges_into_one_project():
    rows = [
        (830, "108/1/31", "擬訂臺北市信義區犁和段三小段302地號等2筆土地都市更新事業計畫及權利變換計畫案",
         "潤泰創新國際股份有限公司"),
        (261, "112/12/28", "變更臺北市信義區犁和段三小段302地號等2筆土地都市更新權利變換計畫案",
         "潤泰創新國際股份有限公司"),
    ]
    land = "臺北市信義區犁和段三小段302及303地號等2筆土地"
    recs = [cleanse(_raw(recno, date, name, land, imp=imp, district="信義區"))
            for recno, date, name, imp in rows]
    projects = merge(recs)
    assert len(projects) == 1
    assert projects[0].anchor_recno == 261
    assert {m.recno for m in projects[0].members} == {830, 261}


def test_empty_parcels_different_first_or_count_not_linked():
    """No over-merging: empty parcel sets with a differing first parcel or
    count must not link, even under the rebalanced weight."""
    a = _empty("中山區", "中山段二小段", "125", 1, recno=1)
    b = _empty("中山區", "中山段二小段", "126", 1, recno=2)
    c = _empty("中山區", "中山段二小段", "125", 2, recno=3)
    assert score(a, b) < LINK_THRESHOLD
    assert score(a, c) < LINK_THRESHOLD
    projects = merge([a, b, c])
    assert len(projects) == 3