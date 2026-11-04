"""resolve-recno-case (S10, C6): every recno binds its city case by the
4-step resolver — never by list position.

Steps: (1) 案名 over cached cases in three tiers with the live-set filter
and the area-split rule, (2) the same-day id probe accepted only on
CASE_NAME + date, (3) the header's uro_chk_date/uro_chk_date2 as a second
approval source, (4) the parcel search on every parcel of the node.
"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urtpe.links import (  # noqa: E402
    attach_links_to_projects,
    filter_live_cases,
    node_name_key,
    node_name_loose,
    node_stage_kind,
    resolve_node_cases,
)


def _disc(city_case_ids=(), names=None, milestones=None, schedules=None,
          headers=None, superseded_by=None):
    return SimpleNamespace(
        project_id="測試專案",
        twur_url="",
        national_milestones={},
        taipei_milestones={},
        milestones_source={},
        implementation={},
        rewards={},
        search_rejected={},
        view_verified_case_ids=[],
        city_case_ids=list(city_case_ids),
        candidate_names=dict(names or {}),
        case_milestones={k: dict(v) for k, v in (milestones or {}).items()},
        case_schedules=dict(schedules or {}),
        case_headers=dict(headers or {}),
        superseded_by=dict(superseded_by or {}),
    )


def _member(date="2023-12-28", name="擬訂臺北市信義區犁和段三小段302地號等16筆",
            stage="變更", track="權利變換", parcels=None, recno=281):
    return SimpleNamespace(
        date=date, name=name, stage=stage, track=track, recno=recno,
        parcels=list(parcels or ["302"]),
        review_flags=[],
    )


class TestNameTiers(unittest.TestCase):
    """Task 1.1 — the three name tiers."""

    def test_exact_ignores_spaces(self):
        self.assertEqual(node_name_key("擬訂臺北市 松山區 民生段 140-9地號"),
                         node_name_key("擬訂臺北市松山區民生段140-9地號"))

    def test_loose_strips_count_noise(self):
        a = "擬訂臺北市中山區吉林段110-1地號等47筆(原50筆)土地都市更新事業計畫案"
        b = "擬訂臺北市中山區吉林段110-1地號等47筆土地都市更新事業計畫案"
        self.assertEqual(node_name_loose(a), node_name_loose(b))

    def test_loose_normalises_擬定_and_area_suffix(self):
        self.assertEqual(
            node_name_loose("擬定臺北市中山區吉林段四小段705-1地號等47筆-A區(段)土地都市更新事業計畫案"),
            node_name_loose("擬訂臺北市中山區吉林段四小段705-1地號等47筆土地都市更新事業計畫案"))

    def test_loose_normalises_權利變換案(self):
        self.assertEqual(
            node_name_loose("變更臺北市大安區學府段1地號等5筆都市更新權利變換案"),
            node_name_loose("變更臺北市大安區學府段1地號等5筆都市更新權利變換計畫案"))

    def test_stage_kind_ignores_釐正圖冊(self):
        a = node_stage_kind("變更(第二次)臺北市信義區犁和段302地號等16筆都市更新事業計畫案")
        b = node_stage_kind("變更(第二次)臺北市信義區犁和段302地號等16筆都市更新事業計畫(含釐正圖冊)暨權利變換案")
        self.assertEqual(a[0], b[0])  # stage equal
        self.assertIn("權", a[1] + b[1])  # plan type detected


class TestLiveSet(unittest.TestCase):
    """Task 1.2 — the live-set filter."""

    def test_terminal_schedules_excluded(self):
        disc = _disc(names={"1": "甲案", "2": "甲案"},
                     schedules={"1": "自行撤回", "2": "已核准"})
        live = filter_live_cases(["1", "2"], disc)
        self.assertEqual(live, ["2"])

    def test_無_yields_to_approved_same_name_sibling(self):
        # 東湖34: 11302181 (無, no milestones) vs 11502008 (approved, same name)
        disc = _disc(
            names={"11302181": "擬訂臺北市內湖區東湖段49地號等1筆", "11502008": "擬訂臺北市內湖區東湖段49地號等1筆"},
            schedules={"11302181": "無", "11502008": "已核准"},
            milestones={"11502008": {"核定日期": "2026/02/11"}},
        )
        live = filter_live_cases(["11302181", "11502008"], disc,
                                 names=("擬訂臺北市內湖區東湖段49地號等1筆",))
        self.assertEqual(live, ["11502008"])

    def test_combined_track_case_matches_a_single_track_node(self):
        # 東湖34 r73: the gazette prints 擬訂…事業計畫案; the city's re-filed
        # case 11502008 names 事業計畫及權利變換計畫 (one approval, both
        # tracks) — the tier-3 kind-subset rule matches them, then the date
        # (2026-02-11 = the node's 2026-02-21 within the name bind? no: the
        # node's date is 2026-02-21, the case's 核定 2026/02/11 — 10 days off,
        # the header drift). The probe memo carries the header date.
        disc = _disc(
            city_case_ids=["11302181", "11502008"],
            names={"11302181": "擬訂臺北市內湖區東湖段一小段34地號等1筆土地都市更新事業計畫案",
                   "11502008": "擬訂臺北市內湖區東湖段一小段34地號1筆土地都市更新事業計畫及權利變換計畫案"},
            schedules={"11302181": "無", "11502008": "已核准"},
            milestones={"11502008": {"核定日期": "2026/02/11"}},
            headers={"11502008": {"NAME": "事業計畫階段─業經本府核定",
                                  "uro_chk_date": "2026-02-21T00:00:00"}},
        )
        got = resolve_node_cases(
            _member(date="2026-02-21", stage="擬訂", track="事業計畫",
                    name="擬訂臺北市內湖區東湖段一小段34地號等1筆土地都市更新事業計畫案"),
            disc)
        self.assertEqual(got, ["11502008"])

    def test_no_approved_sibling_keeps_the_無_case(self):
        disc = _disc(
            names={"11302181": "擬訂臺北市內湖區東湖段49地號等1筆"},
            schedules={"11302181": "無"},
        )
        live = filter_live_cases(["11302181"], disc,
                                 names=("擬訂臺北市內湖區東湖段49地號等1筆",))
        self.assertEqual(live, ["11302181"])


class TestAreaSplit(unittest.TestCase):
    """Task 1.3 — the area-split rule (user decision 2026-11-03)."""

    def test_distinct_suffixes_bind_all(self):
        disc = _disc(
            city_case_ids=["11011241", "11011242"],
            names={"11011241": "變更臺北市中山區吉林段四小段259-1地號等26筆( FridA區段)土地都市更新事業計畫案"},
            schedules={"11011241": "已核准", "11011242": "施工中"},
        )
        # realistic names: -A區 / -B區
        disc.candidate_names = {
            "11011241": "變更臺北市中山區吉林段四小段259-1地號等26筆-A區土地都市更新事業計畫案",
            "11011242": "變更臺北市中山區吉林段四小段259-1地號等26筆-B區土地都市更新事業計畫案",
        }
        got = resolve_node_cases(
            _member(name="變更臺北市中山區吉林段四小段259-1地號等26筆土地都市更新事業計畫案",
                    date="2025-01-09"), disc)
        self.assertEqual(got, ["11011241", "11011242"])

    def test_same_suffix_does_not_split_bind(self):
        disc = _disc(
            city_case_ids=["a1", "a2"],
            names={"a1": "擬訂臺北市大安區學府段1地號-A區案", "a2": "擬訂臺北市大安區學府段1地號-A區案"},
            schedules={"a1": "已核准", "a2": "審查中"},
            milestones={"a1": {"核定日期": "2020/01/01"}, "a2": {}},
        )
        got = resolve_node_cases(_member(name="擬訂臺北市大安區學府段1地號案"), disc)
        # two live matches, no split → nothing binds at the name step
        self.assertEqual(got, [])

    def test_北南_suffixes_split(self):
        # 榮星53: 北區 09001120 + 南區 09001123 on one gazette row
        disc = _disc(
            city_case_ids=["09001120", "09001123"],
            names={"09001120": "擬訂臺北市中山區榮星段六小段53地號等2筆北區都市更新事業計畫案",
                   "09001123": "擬訂臺北市中山區榮星段六小段53地號等2筆南區都市更新事業計畫案"},
            schedules={"09001120": "已核准", "09001123": "已核准"},
            milestones={"09001120": {"核定日期": "2005/11/03"},
                        "09001123": {"核定日期": "2005/11/03"}},
        )
        got = resolve_node_cases(
            _member(name="擬訂臺北市中山區榮星段六小段53地號等2筆都市更新事業計畫案",
                    date="2005-11-03"), disc)
        self.assertEqual(got, ["09001120", "09001123"])


class TestSameDayProbe(unittest.TestCase):
    """Task 1.4 — probe acceptance requires CASE_NAME + date."""

    def setUp(self):
        # 犁和302 recno 281: the cache holds only 10203251 (2019 擬訂); the
        # probe finds 10203253 (變更 權變, header 2023-12-28).
        self.disc = _disc(
            city_case_ids=["10203251"],
            names={"10203251": "擬訂臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案"},
            schedules={"10203251": "已核准"},
            milestones={"10203251": {"核定日期": "2019/06/10"}},
        )
        self.member = _member(
            date="2023-12-28", stage="變更", track="權利變換",
            name="變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案")

    def test_accepts_on_name_and_date(self):
        headers = {
            "10203250": {"CASE_NAME": "擬訂臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
                         "uro_chk_date": "2019/06/10"},
            "10203252": {"CASE_NAME": "擬訂臺北市中山區中山段一小段111地號等13筆土地都市更新事業計畫案",
                         "uro_chk_date": "2023/12/28"},  # city-wide serial: another project
            "10203253": {"CASE_NAME": "變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
                         "uro_chk_date": "2023/12/28"},
        }
        fetched = {}

        def fetch_header(cid):
            return headers.get(cid, {})

        def fetch_milestones(cid):
            fetched[cid] = {"核定日期": "2023/12/28"} if cid == "10203253" else {}
            return fetched[cid]

        got = resolve_node_cases(self.member, self.disc,
                                 fetch_header=fetch_header,
                                 fetch_milestones=fetch_milestones,
                                 sleep=lambda s: None)
        self.assertEqual(got, ["10203253"])
        # the accepted id joined the cache
        self.assertIn("10203253", self.disc.city_case_ids)
        self.assertEqual(self.disc.candidate_names["10203253"],
                         headers["10203253"]["CASE_NAME"])

    def test_rejects_a_name_mismatch_even_on_the_date(self):
        headers = {
            "10203252": {"CASE_NAME": "擬訂臺北市中山區中山段一小段111地號等13筆土地都市更新事業計畫案",
                         "uro_chk_date": "2023/12/28"},
        }
        got = resolve_node_cases(self.member, self.disc,
                                 fetch_header=lambda cid: headers.get(cid, {}),
                                 fetch_milestones=lambda cid: {},
                                 sleep=lambda s: None)
        self.assertEqual(got, [])
        self.assertNotIn("10203252", self.disc.city_case_ids)


class TestHeaderDateStep(unittest.TestCase):
    """Task 1.5 — the header as a second approval source."""

    def test_header_date_overrides_copied_data2(self):
        # 玉泉11 recno 1180 → 09504263: data2 says 2008/05/15, header 2013-08-20
        disc = _disc(
            city_case_ids=["09504263"],
            names={"09504263": "變更臺北市萬華區玉泉段二小段91地號等42筆都市更新事業計畫案"},
            schedules={"09504263": "已核准"},
            milestones={"09504263": {"核定日期": "2008/05/15"}},
            headers={"09504263": {"NAME": "事業計畫階段─業經本府核定",
                                  "uro_chk_date": "2013/08/20"}},
        )
        got = resolve_node_cases(
            _member(date="2013-08-20", stage="變更", track="事業計畫",
                    name="變更臺北市萬華區玉泉段二小段91地號等42筆都市更新事業計畫案"),
            disc)
        self.assertEqual(got, ["09504263"])

    def test_bounded_drift_binds_on_equal_stage(self):
        # 康寧626 recno 1019 → 09712204: header 2016-11-12, node 2016-11-02
        disc = _disc(
            city_case_ids=["09712203", "09712204"],
            names={"09712203": "擬訂臺北市內湖區康寧段三小段626地號等2筆都市更新事業計畫及權利變換計畫案",
                   "09712204": "變更(第二次)臺北市內湖區康寧段三小段626地號等2筆都市更新事業計畫及權利變換計畫案"},
            schedules={"09712203": "已核准", "09712204": "已核准"},
            milestones={"09712203": {"核定日期": "2009/01/20"},
                        "09712204": {"核定日期": "2010/03/03"}},
            headers={"09712204": {"NAME": "事業計畫及權利變換計畫階段─業經本府核定",
                                  "uro_chk_date": "2016/11/12"}},
        )
        got = resolve_node_cases(
            _member(date="2016-11-02", stage="變更(第二次)", track="權利變換",
                    name="變更(第二次)臺北市內湖區康寧段三小段626地號等2筆都市更新事業計畫及權利變換計畫案"),
            disc)
        self.assertEqual(got, ["09712204"])

    def test_drift_with_a_mismatched_stage_does_not_bind(self):
        # the case name differs from the node's 案名 (擬訂 vs 變更(第二次)), so
        # only the header-date step can reach it — and its stage disagrees
        disc = _disc(
            city_case_ids=["c1"],
            names={"c1": "擬訂臺北市內湖區康寧段三小段626地號等2筆都市更新事業計畫案"},
            schedules={"c1": "已核准"},
            milestones={"c1": {"核定日期": "2009/01/20"}},
            headers={"c1": {"NAME": "事業計畫階段─業經本府核定",
                            "uro_chk_date": "2016/11/12"}},
        )
        got = resolve_node_cases(
            _member(date="2016-11-02", stage="變更(第二次)", track="權利變換",
                    name="變更(第二次)臺北市內湖區康寧段三小段626地號等2筆都市更新事業計畫案"),
            disc)
        self.assertEqual(got, [])


class TestAllParcelStep(unittest.TestCase):
    """Task 1.6 — the parcel search on every parcel of the node."""

    def test_second_parcel_finds_the_case(self):
        # 南港566 recno 1063: parcel 566 returns only the newest case; the
        # 2016 擬訂 10006032 hides under parcel 567.
        disc = _disc(
            city_case_ids=["10708312"],
            names={"10708312": "變更臺北市南港區南港段四小段566地號等6筆都市更新事業計畫及權利變換計畫案"},
            schedules={"10708312": "已核准"},
            milestones={"10708312": {"核定日期": "2021/05/10"}},
        )
        searched = []

        def search(section, parcel, dropped_out=None, anchor_name=""):
            searched.append(parcel)
            if parcel == "567":
                return [{"case_id": "10006032",
                         "case_name": "擬訂臺北市南港區南港段四小段566地號等6筆都市更新事業計畫及權利變換計畫案",
                         "schedule": "已核准"}]
            return []

        def fetch_milestones(cid):
            return {"核定日期": "2016/02/25"} if cid == "10006032" else {}

        got = resolve_node_cases(
            _member(date="2016-02-25", stage="擬訂", track="事業計畫、權利變換",
                    name="擬訂臺北市南港區南港段四小段566地號等6筆都市更新事業計畫及權利變換計畫案",
                    parcels=["566", "567"]),
            disc, search=search, fetch_milestones=fetch_milestones,
            fetch_header=lambda cid: ({"CASE_NAME": "擬訂臺北市南港區南港段四小段566地號等6筆都市更新事業計畫及權利變換計畫案",
                                       "uro_chk_date": "2016/02/25"} if cid == "10006032" else {}),
            sleep=lambda s: None)
        self.assertEqual(got, ["10006032"])
        self.assertIn("567", searched)
        self.assertIn("10006032", disc.city_case_ids)

    def test_a_wrong_name_result_does_not_bind(self):
        disc = _disc(city_case_ids=["10708312"],
                     names={"10708312": "變更臺北市南港區南港段四小段566地號等6筆都市更新事業計畫案"},
                     schedules={"10708312": "已核准"},
                     milestones={"10708312": {"核定日期": "2021/05/10"}})

        def search(section, parcel, dropped_out=None, anchor_name=""):
            return [{"case_id": "10006032",
                     "case_name": "擬訂臺北市南港區南港段四小段999地號等3筆都市更新事業計畫案",
                     "schedule": "已核准"}]

        got = resolve_node_cases(
            _member(date="2016-02-25", stage="擬訂", track="事業計畫",
                    name="擬訂臺北市南港區南港段四小段566地號等6筆都市更新事業計畫案",
                    parcels=["566"]),
            disc, search=search, fetch_milestones=lambda cid: {},
            fetch_header=lambda cid: {"CASE_NAME": "擬訂臺北市南港區南港段四小段999地號等3筆都市更新事業計畫案",
                                      "uro_chk_date": "2016/02/25"},
            sleep=lambda s: None)
        self.assertEqual(got, [])


class TestUnplacedNode(unittest.TestCase):
    """Task 1.7 — an unplaced node is reported, never positionally bound.

    Design D6: resolve_node_cases returns [] and attach_links_to_projects
    raises the review flag on the member record."""

    def test_miss_gains_flag_and_no_binding(self):
        disc = _disc(city_case_ids=["10203251"],
                     names={"10203251": "擬訂臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫案"},
                     schedules={"10203251": "已核准"},
                     milestones={"10203251": {"核定日期": "2019/06/10"}})
        member = _member(date="2023-12-28", stage="變更", track="權利變換",
                         name="變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫案")
        member.district = "信義區"
        member.district_land = "信義區"
        member.section = "犁和段三小段"
        member.first_parcel = "302"
        member.land_count = 16
        member.orig_count = None
        got = resolve_node_cases(member, disc,
                                 search=lambda *a, **k: [],
                                 fetch_header=lambda cid: {},
                                 fetch_milestones=lambda cid: {},
                                 sleep=lambda s: None)
        self.assertEqual(got, [])
        project = SimpleNamespace(
            project_id="信義區-犁和段三小段-302地號等16筆",
            anchor_recno=281, members=[member])
        attach_links_to_projects(
            [project], {"信義區-犁和段三小段-302地號等16筆": disc},
            probe_headers={})
        self.assertTrue(any("節點未能對應平台案件" in f for f in member.review_flags))
        self.assertEqual(member.links["taipei"], [])

    def test_the_flag_is_idempotent(self):
        disc = _disc(city_case_ids=["10203251"],
                     names={"10203251": "擬訂臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫案"},
                     schedules={"10203251": "已核准"},
                     milestones={"10203251": {"核定日期": "2019/06/10"}})
        member = _member(date="2023-12-28", stage="變更", track="權利變換",
                         name="變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫案")
        member.district = "信義區"
        member.district_land = "信義區"
        member.section = "犁和段三小段"
        member.first_parcel = "302"
        member.land_count = 16
        member.orig_count = None
        project = SimpleNamespace(
            project_id="信義區-犁和段三小段-302地號等16筆",
            anchor_recno=281, members=[member])
        for _ in range(2):
            attach_links_to_projects(
                [project], {"信義區-犁和段三小段-302地號等16筆": disc},
                probe_headers={})
        flags = [f for f in member.review_flags
                 if f.startswith("節點未能對應平台案件")]
        self.assertEqual(len(flags), 1)


class TestAttachIntegration(unittest.TestCase):
    """Task 1.8 — the attach path uses the resolver; the date-matched nodes
    keep their binding."""

    def test_fallback_node_resolves_instead_of_position(self):
        # The positional fallback would bind city_case_ids[0] (the 2019
        # 擬訂 case) on the 2023 變更 node; the resolver must bind 10203253.
        # The probe reads the seeded header from case_headers (offline memo);
        # the live adapter would fetch get_project168_top for the same id.
        disc = _disc(
            city_case_ids=["10203251"],
            names={"10203251": "擬訂臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案"},
            schedules={"10203251": "已核准"},
            milestones={"10203251": {"核定日期": "2019/06/10"}},
            headers={"10203253": {"CASE_NAME": "變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
                                  "uro_chk_date": "2023/12/28",
                                  "NAME": "事業計畫及權利變換計畫階段─業經本府核定"}},
        )
        disc.view_verified_case_ids = []
        project = SimpleNamespace(
            project_id="信義區-犁和段三小段-302地號等16筆",
            anchor_recno=281,
            members=[_member(date="2023-12-28", stage="變更", track="權利變換",
                             name="變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
                             parcels=["302"])],
            district="信義區", district_land="信義區", section="犁和段三小段",
            first_parcel="302", land_count=16, orig_count=None,
            name="變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
        )
        project.members[0].district = "信義區"
        project.members[0].district_land = "信義區"
        project.members[0].section = "犁和段三小段"
        project.members[0].first_parcel = "302"
        project.members[0].land_count = 16
        project.members[0].orig_count = None
        # the probe's offline memo: case_headers holds the probed sibling
        attach_links_to_projects(
            [project], {"信義區-犁和段三小段-302地號等16筆": disc},
            probe_headers={"10203253": {"CASE_NAME": "變更臺北市信義區犁和段三小段302地號等16筆都市更新事業計畫及權利變換計畫案",
                                        "uro_chk_date": "2023/12/28"}})
        got = project.members[0].links["taipei"]
        self.assertEqual(got, ["10203253"])

    def test_date_matched_node_keeps_its_binding(self):
        disc = _disc(
            city_case_ids=["09307101", "09307104"],
            names={"09307101": "變更臺北市中山區吉林段四小段705地號等47筆( FridA區段)都市更新事業計畫及擬訂權利變換計畫案",
                   "09307104": "變更臺北市中山區吉林段四小段705地號等47筆都市更新事業計畫案"},
            schedules={"09307101": "已核准", "09307104": "已核准"},
            milestones={"09307101": {"核定日期": "2010/01/08"},
                        "09307104": {"核定日期": "2008/03/10"}},
        )
        disc.candidate_names = {
            "09307101": "變更臺北市中山區吉林段四小段705地號等47筆都市更新事業計畫及擬訂權利變換計畫案",
            "09307104": "變更臺北市中山區吉林段四小段705地號等47筆都市更新事業計畫案",
        }
        disc.view_verified_case_ids = []
        member = _member(date="2008-03-10", stage="變更", track="事業計畫",
                         name="變更臺北市中山區吉林段四小段705地號等47筆都市更新事業計畫案",
                         recno=1370)
        member.district = "中山區"
        member.district_land = "中山區"
        member.section = "吉林段四小段"
        member.first_parcel = "705"
        member.land_count = 47
        member.orig_count = None
        project = SimpleNamespace(
            project_id="中山區-吉林段四小段-705地號等47筆",
            anchor_recno=1370,
            members=[member],
            district="中山區", district_land="中山區", section="吉林段四小段",
            first_parcel="705", land_count=47, orig_count=None,
            name="變更臺北市中山區吉林段四小段705地號等47筆都市更新事業計畫案",
        )
        attach_links_to_projects([project],
                                 {"中山區-吉林段四小段-705地號等47筆": disc})
        # the date matcher already binds this one — the resolver must not
        # change it
        self.assertEqual(project.members[0].links["taipei"], ["09307104"])


if __name__ == "__main__":
    unittest.main()
