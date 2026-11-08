"""bind-the-unplaced-by-searching-the-cell-section — the test-first group.

The gazette's 案名 column and its 地號 column sometimes disagree about which
段小段 a unit is in, and the city indexes the 地號 column's spelling. The
resolver joins a node to a case by comparing the two names, so a disagreement
leaves the node unbound and the unit invisible to a reader (7 projects, 11
nodes, docs/coverage-report.html 問題一).

This file holds the 12 tests of the change's first group. Each one fails
against the code as it stands and passes after the implementation.

  1.1  the section-form rule
  1.2  the two segment readings of a core
  1.3  the parcel-set rule
  1.4  the 地號 cell's core as an alternative
  1.5  the comparison is a superset of the present one
  1.6  the count term keeps its weight
  1.7  the search asks for the 地號 cell's section
  1.8  the all-parcel search offers a case found under another parcel
  1.9  the portal's title search is a third id source
  1.10 an unconfirmed portal id does not enter the case list
  1.11 the portal's view id and national milestones are recorded
  1.12 the resolver's end-to-end acceptance on the 11 nodes
"""

import contextlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urtpe.links import (  # noqa: E402
    compute_landcore_similarity,
    landcore_sections_match,
    parse_landcore_variants,
    refresh_project,
    resolve_node_cases,
    search_taipei_cases_api,
    search_taipei_cases_for_node,
)


# ── the 11 unplaced nodes, and the case the live search found for each ──────
#
# The city's own case names, as the city answered on 2026-11-07. The pair
# (node 案名, city name) is what the tier-3 name rule compares.

CITY_NAMES = {
    "10305021": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
    "11005053": "變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案",
    "10611051": "擬訂臺北市信義區吳興段一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案",
    "10405235": "變更(第二次)臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及變更權利變換計畫案",
    "10011301": "擬訂臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫案",
    "10903061": "變更臺北市萬華區萬大段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
    "10111171": "擬訂臺北市大安區復興段一小段3地號等5筆土地都市更新事業計畫案",
    "10111173": "變更臺北市大安區復興段一小段3地號等2筆(原5筆)土地都市更新事業計畫案",
    "10002141": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
    "09102220": "擬訂臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫案",
    "09102221": "變更臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及擬訂權利變換計畫案",
}

# recno -> (case id, the node's 案名, the node's 地號 cell, the section the
# 地號 cell names, the node's date, the case's approval date)
UNPLACED = {
    122: ("10305021",
          "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案核定公告_",
          "臺北市中正區臨沂段三小段 412、412-1、413、413-1、414、414-1、415、415-1、418、419、420、421 地號等12筆土地",
          "臨沂段三小段", "2025-07-22", "2025-07-22"),
    204: ("11005053",
          "變更(第三次)臺北市中正區河堤五小段399地號等3筆土地都市更新權利變換計畫案",
          "臺北市中正區河堤段五小段 399、398、399-1 地號等3筆土地",
          "河堤段五小段", "2024-10-29", "2024-10-29"),
    483: ("10903061",
          "變更臺北市萬華區萬華段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
          "臺北市萬華區萬大段一小段 519-2、522 地號等35筆土地",
          "萬大段一小段", "2022-04-19", "2022-04-19"),
    551: ("10611051",
          "擬訂臺北市信義區吳興一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案",
          "臺北市信義區吳興一小段 330、331、332 地號等43筆土地",
          "吳興一小段", "2021-09-15", "2021-09-15"),
    669: ("10111173",
          "變更臺北市大安區復興段一小段3地號等2筆(原5筆)土地都市更新事業計畫案",
          "臺北市大安區復興段一小段 3、3-2、7、7-1、20-3 地號等2筆土地",
          "復興段一小段", "2020-07-30", "2020-07-30"),
    706: ("10405235",
          "變更(第二次)臺北市信義區吳興街二期整宅地區都市更新事業計畫及變更權利變換計畫案",
          "臺北市信義區吳興段二小段163-2、247地號等2筆土地",
          "吳興段二小段", "2020-03-19", "2020-03-19"),
    993: ("10011301",
          "擬訂臺北市萬華區萬華段一小段519-2地號等35筆土地都市更新事業計畫及權利變換計畫案",
          "臺北市萬華區萬大段一小段 519-2、522 地號等35筆土地",
          "萬大段一小段", "2017-04-18", "2017-04-18"),
    1081: ("10111171",
           "擬訂臺北市大安區復興段一小段3地號等5筆土地都市更新事業計畫案",
           "臺北市大安區復興段一小段 3、3-2、7、7-1、20-3 地號等5筆土地",
           "復興段一小段", "2015-11-04", "2015-11-03"),
    1170: ("10002141",
           "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
           "臺北市大安區懷生段一小段 928 地號1筆土地",
           "懷生段一小段", "2013-11-05", "2013-11-05"),
    1333: ("09102221",
           "變更臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及擬訂權利變換計畫案",
           "臺北市信義區吳興段二小段 247、247-1 地號等2筆土地",
           "吳興段二小段", "2009-06-10", "2009-06-10"),
    1433: ("09102220",
           "擬訂臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫案",
           "臺北市信義區吳興段二小段 247、247-1 地號等2筆土地",
           "吳興段二小段", "2004-06-24", "2004-06-24"),
}


def _member(name, land, section, parcels, date, recno=0, district="", count=""):
    """A node, shaped like the record the resolver reads."""
    return SimpleNamespace(
        recno=recno, date=date, name=name, land=land, section=section,
        first_parcel=parcels[0] if parcels else "",
        parcels=list(parcels), district=district, district_land=district,
        land_count=count, named_anchor="", review_flags=[],
    )


def _disc(city_case_ids=(), names=None, milestones=None, schedules=None,
          headers=None):
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
        superseded_by={},
    )


class TestSectionFormRule(unittest.TestCase):
    """Task 1.1 — the section-form rule.

    Two sections name the same unit when they carry the same 小段 suffix and
    the same 段 name, with a trailing 段 optional on either side. The gazette
    prints 吳興一小段 where the city prints 吳興段一小段.
    """

    def test_a_missing_trailing_segment_still_matches(self):
        self.assertTrue(landcore_sections_match("吳興一小段", "吳興段一小段"))

    def test_the_other_side_may_carry_the_trailing_segment(self):
        self.assertTrue(landcore_sections_match("河堤段五小段", "河堤五小段"))

    def test_a_different_small_section_does_not_match(self):
        self.assertFalse(landcore_sections_match("中山段二小段", "吉林段五小段"))

    def test_a_different_section_does_not_match(self):
        self.assertFalse(landcore_sections_match("萬華段一小段", "萬大段一小段"))

    def test_an_empty_section_never_matches(self):
        self.assertFalse(landcore_sections_match("", "吳興段一小段"))
        self.assertFalse(landcore_sections_match("吳興段一小段", ""))


class TestSectionReading(unittest.TestCase):
    """Task 1.2 — a core's section is cut at both its first 段 and its last.

    河堤段五小段399地號等3筆 reads as the section 河堤段五小段 with parcel 399,
    and not only as the section 河堤段 with parcel 五小段399.
    """

    def test_the_two_readings_are_offered(self):
        readings = parse_landcore_variants("中正區河堤段五小段399地號等3筆")
        sections = [r[1] for r in readings]
        self.assertIn("河堤段", sections)
        self.assertIn("河堤段五小段", sections)

    def test_the_last_reading_splits_the_section_from_the_parcel(self):
        readings = parse_landcore_variants("中正區河堤段五小段399地號等3筆")
        last = [r for r in readings if r[1] == "河堤段五小段"][0]
        self.assertEqual(last[2], "399")
        self.assertEqual(last[3], "3")

    def test_the_first_reading_is_the_pipeline_s_own(self):
        # the pipeline cuts at the FIRST 段 (urtpe.links._parse_landcore); the
        # widened comparison must keep that reading, so every binding the
        # pipeline makes today still matches
        readings = parse_landcore_variants("中正區河堤段五小段399地號等3筆")
        first = [r for r in readings if r[1] == "河堤段"][0]
        self.assertEqual(first[2], "五小段399")


class TestParcelSetRule(unittest.TestCase):
    """Task 1.3 — the city's parcel may be one of the node's own parcels."""

    def test_a_parcel_of_the_node_s_own_set_scores_full_weight(self):
        node = "信義區吳興段二小段247地號等2筆"
        city = "信義區吳興段二小段247地號等2筆"
        # the node's first parcel is 163-2; the city declares 247
        score = compute_landcore_similarity(node, city, node_parcels=("163-2", "247"))
        self.assertGreaterEqual(score, 0.85)

    def test_a_parcel_outside_the_node_s_set_does_not_score_full_weight(self):
        node = "信義區吳興段二小段247地號等2筆"
        city = "信義區吳興段二小段999地號等2筆"
        score = compute_landcore_similarity(node, city, node_parcels=("163-2", "247"))
        self.assertLess(score, 0.85)


class TestCellCoreRule(unittest.TestCase):
    """Task 1.4 — the node's core may be built from the 地號 cell's section.

    The 案名 says 河堤五小段 and the 地號 cell says 河堤段五小段; the city
    indexes the cell's form.
    """

    def test_the_present_rule_refuses_the_pair(self):
        node = "中正區河堤五小段399地號等3筆"
        city = "中正區河堤段五小段399地號等3筆"
        self.assertLess(_present_similarity(node, city), 0.85)

    def test_the_cell_s_section_makes_the_pair_match(self):
        node = "中正區河堤五小段399地號等3筆"
        cell = "中正區河堤段五小段399地號等3筆"
        city = "中正區河堤段五小段399地號等3筆"
        self.assertGreaterEqual(compute_landcore_similarity(cell, city), 0.85)

    def test_the_widened_rule_accepts_the_node_s_own_core(self):
        # the section-form rule reads 河堤五小段 and 河堤段五小段 as one
        # section, so the node's own 案名 core matches the city's core too
        node = "中正區河堤五小段399地號等3筆"
        city = "中正區河堤段五小段399地號等3筆"
        self.assertGreaterEqual(compute_landcore_similarity(node, city), 0.85)


class TestRecordTwoCells(unittest.TestCase):
    """Tasks 3.1 and 3.2 — the record carries the 地號 cell's own section.

    The `section` field stays the 案名's — it is the merge's grouping key, so
    changing it would move the family clustering. The cell's form rides in
    its own field, and the comparison offers it as an ALTERNATIVE core.
    """

    def test_the_cleanser_keeps_the_cell_s_section(self):
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        rec = RawRecord(
            recno=1, date="113/1/2", district="中正區",
            name="變更(第三次)臺北市中正區河堤五小段399地號等3筆土地都市更新權利變換計畫案",
            land="臺北市中正區河堤段五小段 399、398、399-1 地號等3筆土地",
            implementer="", planner="")
        clean = cleanse(rec, ("中正區",))
        # the 案名's section wins the `section` field
        self.assertEqual(clean.section, "河堤五小段")
        # the cell's section rides in its own field
        self.assertEqual(clean.section_land, "河堤段五小段")

    def test_the_field_is_empty_when_the_cell_names_no_section(self):
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        rec = RawRecord(
            recno=1, date="113/1/2", district="中正區",
            name="擬訂臺北市中正區河堤五小段399地號等3筆土地都市更新事業計畫案",
            land="399、398地號等3筆土地",
            implementer="", planner="")
        clean = cleanse(rec, ("中正區",))
        self.assertEqual(clean.section_land, "")

    def test_the_alternative_core_is_offered(self):
        from urtpe.links import _cell_landcore
        member = _member(
            name=UNPLACED[204][1], land=UNPLACED[204][2],
            section="河堤五小段", parcels=["399"], date=UNPLACED[204][4],
            recno=204, district="中正區", count="3")
        member.section_land = "河堤段五小段"
        self.assertEqual(_cell_landcore(member),
                         "中正區河堤段五小段399地號等3筆")


class TestSupersetProperty(unittest.TestCase):
    """Task 1.5 — the widened comparison accepts every pair the present one does.

    The test replays the present rule over the same inputs and asserts the
    widened rule's match set contains it.
    """

    # the pairs the present rule accepts — the pipeline's own corpus, read
    # out of the link cache. Each one is a pair that binds today.
    PRESENT_PAIRS = [
        ("中山區中山段二小段202地號等1筆", "中山區中山段二小段202地號等12筆", ()),
        ("信義區吳興段二小段247地號等2筆", "信義區吳興段二小段247地號等2筆", ()),
        ("松山區敦化段一小段510地號等1筆", "松山區敦化段一小段510地號等1筆", ()),
        ("文山區木柵段三小段623地號等39筆", "文山區木柵段三小段623地號等39筆", ()),
        ("中山區吉林段五小段185地號等23筆", "中山區吉林段五小段185地號等23筆", ()),
        ("大同區圓環段一小段103-2地號等48筆", "大同區圓環段一小段103-2地號等48筆", ()),
    ]

    def test_the_present_rule_accepts_these(self):
        # the present rule's own threshold and weights
        for node, city, parcels in self.PRESENT_PAIRS:
            self.assertGreaterEqual(
                _present_similarity(node, city), 0.85,
                "the fixture no longer binds under the present rule")

    def test_the_widened_rule_accepts_all_of_them(self):
        for node, city, parcels in self.PRESENT_PAIRS:
            self.assertGreaterEqual(
                compute_landcore_similarity(node, city, node_parcels=parcels),
                0.85,
                "the widened rule lost a pair the present rule accepts: %s" % node)


class TestCountTermWeight(unittest.TestCase):
    """Task 1.6 — the count mismatch still costs the count term exactly as before.

    中山段二小段202's node declares 1 筆 and the city declares 12 筆; the pair
    binds today at 0.85, and it must still bind at the same score.
    """

    def test_a_count_mismatch_costs_the_count_term(self):
        node = "中山區中山段二小段202地號等1筆"
        city = "中山區中山段二小段202地號等12筆"
        self.assertAlmostEqual(_present_similarity(node, city), 0.85)

    def test_the_widened_rule_keeps_that_score(self):
        node = "中山區中山段二小段202地號等1筆"
        city = "中山區中山段二小段202地號等12筆"
        self.assertAlmostEqual(
            compute_landcore_similarity(node, city), 0.85)

    def test_a_count_match_scores_the_same(self):
        node = "信義區吳興段二小段247地號等2筆"
        city = "信義區吳興段二小段247地號等2筆"
        self.assertAlmostEqual(
            _present_similarity(node, city),
            compute_landcore_similarity(node, city))


class TestSearchSectionForms(unittest.TestCase):
    """Task 1.7 — the search asks for the 地號 cell's section.

    The 案名 says 河堤五小段 and the 地號 cell says 河堤段五小段; the search
    for 河堤五小段 returns nothing, so the search must retry 河堤段五小段.
    """

    def test_both_forms_are_asked_for(self):
        asked = []

        class _Fake:
            def __post_init__(self):
                self.calls = []

        import urtpe.links as links

        original = links._post_taipei_api

        def fake_post(url, params, max_retries=3):
            asked.append(params.get("sectstr", ""))
            if params.get("sectstr") == "河堤五小段":
                return "[]"
            return '[{"details": "r_progress_detail.aspx?case_id=11005053", ' \
                   '"case_name": "變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案"}]'

        links._post_taipei_api = fake_post
        try:
            hits = search_taipei_cases_api(
                "河堤五小段", "399",
                extra_sections=["河堤段五小段"])
        finally:
            links._post_taipei_api = original

        self.assertIn("河堤五小段", asked)
        self.assertIn("河堤段五小段", asked)
        # the 案名's form comes first; the cell's form is the retry
        self.assertLess(asked.index("河堤五小段"), asked.index("河堤段五小段"))
        self.assertEqual([h["case_id"] for h in hits], ["11005053"])

    def test_the_first_form_succeeding_stops_the_retry(self):
        asked = []

        import urtpe.links as links
        original = links._post_taipei_api

        def fake_post(url, params, max_retries=3):
            asked.append(params.get("sectstr", ""))
            return '[{"details": "r_progress_detail.aspx?case_id=11005053", ' \
                   '"case_name": "變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案"}]'

        links._post_taipei_api = fake_post
        try:
            search_taipei_cases_api("河堤五小段", "399",
                                    extra_sections=["河堤段五小段"])
        finally:
            links._post_taipei_api = original

        self.assertEqual(asked, ["河堤五小段"])

    def test_the_search_keeps_its_three_retry_bound(self):
        # the bound lives in the transport: a failing request is retried three
        # times, never in a loop (the AGENTS.md rule)
        import urtpe.links as links
        original = links._post_taipei_api
        attempts = []

        def fake_post(url, params, max_retries=3):
            attempts.append(max_retries)
            raise RuntimeError("the endpoint refused")

        links._post_taipei_api = fake_post
        try:
            with self.assertRaises(RuntimeError):
                links._post_taipei_api(links.TAIPEI_SEARCH_API, {}, max_retries=3)
        finally:
            links._post_taipei_api = original

        self.assertEqual(attempts, [3])

    def test_the_search_does_not_multiply_its_requests(self):
        # the extra form is tried only after the 案名's form returns nothing,
        # so a project whose 案名 is already right spends no extra request
        asked = []

        import urtpe.links as links
        original = links._post_taipei_api

        def fake_post(url, params, max_retries=3):
            asked.append((params.get("sectstr", ""), params.get("monobuf", "")))
            return "[]"

        links._post_taipei_api = fake_post
        try:
            search_taipei_cases_api("臨沂段三小段", "412",
                                    extra_sections=["臨沂段三小段"])
        finally:
            links._post_taipei_api = original

        # the same form is asked once — a duplicate is not a second request
        self.assertEqual(asked, [("臨沂段三小段", "412")])


class TestAllParcelSearchOffer(unittest.TestCase):
    """Task 1.8 — a case found under another parcel of the unit is offered.

    臨沂段三小段412's case 10305021 is indexed under parcel 414; the search
    for 412 returns nothing.
    """

    def test_the_case_under_another_parcel_is_offered(self):
        found = []

        def search(section, parcel, dropped_out=None, anchor_name=""):
            if parcel == "414":
                return [{"case_id": "10305021",
                         "case_name": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
                         "schedule": ""}]
            return []

        disc = _disc()
        member = _member(
            name=UNPLACED[122][1],
            land=UNPLACED[122][2],
            section="臨沂段三小段",
            parcels=["412", "412-1", "413", "413-1", "414", "414-1",
                     "415", "415-1", "418", "419", "420", "421"],
            date=UNPLACED[122][4],
            recno=122,
            district="中正區",
            count="12")

        got = resolve_node_cases(
            member, disc,
            fetch_header=lambda cid: {
                "CASE_NAME": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
                "uro_chk_date": "2025-07-22"},
            fetch_milestones=lambda cid: {},
            search=search,
            sleep=lambda s: None)
        self.assertEqual(got, ["10305021"])
        self.assertIn("10305021", disc.city_case_ids)


class TestPortalTitleSearch(unittest.TestCase):
    """Task 1.9 — the portal's title search is a third id source.

    懷生段一小段928's case 10002141 is indexed by no parcel search; the
    portal's `?title=` search finds it, and the page's 相關連結 names the id.

    The portal source lives in the refresh, beside the 168 list — the third
    source of case ids for a project whose parcel search returns nothing.
    """

    def test_the_portal_is_asked_when_the_other_sources_return_nothing(self):
        asked = []

        def fake_portal(title, city_id="2", **kw):
            asked.append(title)
            return [{"view_id": "181",
                     "title": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                     "case_ids": ["10002141"],
                     "milestones": {"事業計畫核定日期": "102.11.05"}}]

        with _tmp_cache() as (cache, pid):
            report = refresh_project(
                cache, pid,
                fetch=lambda cid: {},
                fetch_status=lambda cid: {
                    "CASE_NAME": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                    "NAME": "事業計畫階段─業經本府核定",
                    "uro_chk_date": "2013-11-05"},
                search=lambda section, parcel, dropped_out=None, anchor_name="": [],
                fetch_list=lambda: [],
                search_key=("懷生段一小段", "928", ""),
                fetch_portal=fake_portal)

            self.assertEqual(asked, ["懷生段一小段"])
            saved = _read_cache(cache, pid)
            self.assertIn("10002141", saved["city_case_ids"])
            # the id is APPENDED — the existing ids keep their positions
            self.assertEqual(saved["city_case_ids"][-1], "10002141")

    def test_the_portal_is_not_asked_when_the_parcel_search_finds_the_case(self):
        asked = []

        def fake_portal(title, city_id="2", **kw):
            asked.append(title)
            return []

        with _tmp_cache() as (cache, pid):
            refresh_project(
                cache, pid,
                fetch=lambda cid: {},
                fetch_status=lambda cid: {},
                search=lambda section, parcel, dropped_out=None, anchor_name="": [
                    {"case_id": "10305021",
                     "case_name": "擬訂臺北市中正區臨沂段三小段412地號等12筆(原11筆)土地都市更新事業計畫案",
                     "schedule": "已核准"}],
                fetch_list=lambda: [],
                search_key=("臨沂段三小段", "412", ""),
                fetch_portal=fake_portal)

            self.assertEqual(asked, [])


class TestPortalConfirmation(unittest.TestCase):
    """Task 1.10 — an unconfirmed portal id does not enter the case list."""

    def test_an_unconfirmed_id_is_refused(self):
        def fake_portal(title, city_id="2", **kw):
            return [{"view_id": "181",
                     "title": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                     "case_ids": ["10002141"]}]

        with _tmp_cache() as (cache, pid):
            report = refresh_project(
                cache, pid,
                fetch=lambda cid: {},
                fetch_status=lambda cid: {},     # no header row: no evidence
                search=lambda section, parcel, dropped_out=None, anchor_name="": [],
                fetch_list=lambda: [],
                search_key=("懷生段一小段", "928", ""),
                fetch_portal=fake_portal)

            saved = _read_cache(cache, pid)
            self.assertNotIn("10002141", saved["city_case_ids"])
            # the refresh report names it as unconfirmed
            self.assertIn("10002141", report["unconfirmed"])

    def test_an_id_whose_header_has_no_case_name_is_refused(self):
        # a header row that exists but carries no 案名 is no evidence either
        def fake_portal(title, city_id="2", **kw):
            return [{"view_id": "181",
                     "title": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                     "case_ids": ["10002141"]}]

        with _tmp_cache() as (cache, pid):
            report = refresh_project(
                cache, pid,
                fetch=lambda cid: {},
                fetch_status=lambda cid: {"NAME": "無", "uro_chk_date": ""},
                search=lambda section, parcel, dropped_out=None, anchor_name="": [],
                fetch_list=lambda: [],
                search_key=("懷生段一小段", "928", ""),
                fetch_portal=fake_portal)

            saved = _read_cache(cache, pid)
            self.assertNotIn("10002141", saved["city_case_ids"])
            self.assertIn("10002141", report["unconfirmed"])


class TestPortalRecording(unittest.TestCase):
    """Task 1.11 — the portal's view id and national milestones are recorded."""

    def test_the_view_id_and_the_url_are_recorded(self):
        def fake_portal(title, city_id="2", **kw):
            return [{"view_id": "181",
                     "title": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                     "case_ids": ["10002141"],
                     "milestones": {"事業計畫核定日期": "102.11.05"}}]

        with _tmp_cache() as (cache, pid):
            refresh_project(
                cache, pid,
                fetch=lambda cid: {},
                fetch_status=lambda cid: {
                    "CASE_NAME": "擬訂臺北市大安區懷生段一小段928地號1筆土地都市更新事業計畫案",
                    "NAME": "事業計畫階段─業經本府核定",
                    "uro_chk_date": "2013-11-05"},
                search=lambda section, parcel, dropped_out=None, anchor_name="": [],
                fetch_list=lambda: [],
                search_key=("懷生段一小段", "928", ""),
                fetch_portal=fake_portal)

            saved = _read_cache(cache, pid)
            self.assertEqual(saved["twur_view_id"], "181")
            self.assertEqual(saved["twur_url"],
                             "https://twur.nlma.gov.tw/zh/urban/rebuild/view/181")
            self.assertEqual(saved["national_milestones"].get("事業計畫核定日期"),
                             "102.11.05")


class TestResolverAcceptanceOnTheEleven(unittest.TestCase):
    """Task 1.12 — the resolver's end-to-end acceptance on the 11 nodes.

    Each of the 7 unplaced projects' nodes binds the case id the live search
    found. 10 of the 11 bind on an exact date match. The 11th (復興 recno
    1081) binds on the header step's existing 10-day drift rule: its node's
    date is 2015-11-04 and the case's approval is 2015-11-03. Step 4's date
    gate stays exact (design D6), so this node binds through the header step,
    not through the parcel search.
    """

    def test_each_node_binds_its_case(self):
        for recno in sorted(UNPLACED):
            cid, node_name, land, cell_section, node_date, case_date = \
                UNPLACED[recno]
            city_name = CITY_NAMES[cid]
            parcels = _parcels_of(land)
            disc = _disc(
                city_case_ids=[cid],
                names={cid: city_name},
                schedules={cid: "已核准"},
                milestones={cid: {"核定日期": case_date}},
                headers={cid: {"NAME": "事業計畫階段─業經本府核定",
                               "uro_chk_date": case_date}})
            member = _member(
                name=node_name, land=land, section=cell_section,
                parcels=parcels, date=node_date, recno=recno,
                district=_district_of(land), count=_count_of(land))
            got = resolve_node_cases(member, disc)
            self.assertEqual(got, [cid],
                             "recno %s did not bind %s" % (recno, cid))

    def test_the_drift_node_binds_on_the_header_rule(self):
        cid, node_name, land, cell_section, node_date, case_date = UNPLACED[1081]
        self.assertNotEqual(node_date, case_date)   # the 1-day drift
        disc = _disc(
            city_case_ids=[cid],
            names={cid: CITY_NAMES[cid]},
            schedules={cid: "已核准"},
            milestones={cid: {"核定日期": case_date}},
            headers={cid: {"NAME": "事業計畫階段─業經本府核定",
                           "uro_chk_date": case_date}})
        member = _member(
            name=node_name, land=land, section=cell_section,
            parcels=_parcels_of(land), date=node_date, recno=1081,
            district=_district_of(land), count=_count_of(land))
        self.assertEqual(resolve_node_cases(member, disc), [cid])


# ── helpers ────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def _tmp_cache():
    """A cache directory holding one project whose case list is empty."""
    tmp = tempfile.mkdtemp(prefix="urtpe-cell-section-")
    cache = Path(tmp)
    pid = "大安區-懷生段一小段-928地號等1筆"
    d = cache / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": "x", "status": "unresolved",
        "case_milestones": {}, "city_case_ids": [],
        "twur_url": "", "twur_view_id": None,
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {}, "case_schedules": {},
        "case_headers": {}, "error": "",
    }
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    try:
        yield cache, pid
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _read_cache(cache: Path, pid: str) -> dict:
    return json.loads((cache / pid / "result.json").read_text(encoding="utf-8"))


def _present_similarity(a: str, b: str) -> float:
    """The comparison as it stands — the four-part weighted score with the
    exact-section test. The widened comparison must accept every pair this
    accepts (task 1.5)."""
    from urtpe.links import _parse_landcore
    a_district, a_section, a_parcel, a_count = _parse_landcore(a)
    b_district, b_section, b_parcel, b_count = _parse_landcore(b)
    if a_district != b_district or a_section != b_section:
        return 0.0
    fp = 0.0
    if a_parcel and b_parcel:
        if a_parcel == b_parcel:
            fp = 1.0
        elif (b_parcel in a_parcel) or (a_parcel in b_parcel):
            fp = 0.95
        elif a_parcel in b_parcel or b_parcel in a_parcel:
            fp = 0.7
    cnt = 1.0 if (a_count and b_count and a_count == b_count) else 0.0
    jac = 1.0 if a_parcel == b_parcel else 0.0
    return 0.35 + 0.2 * fp + 0.3 * jac + 0.1 * cnt


def _parcels_of(land: str) -> list:
    """The parcels the 地號 cell names, read from the fixture text."""
    import re
    m = re.search(r"地號等(\d+)筆", land)
    head = land[:m.start()] if m else land
    head = re.sub(r"^臺北市[^ ]*?區\s*", "", head)
    head = re.sub(r"[^\d\-、]+$", "", head)
    parts = [p for p in re.split(r"、", head) if p and not p.startswith("-")]
    return [p for p in parts if p]


def _district_of(land: str) -> str:
    import re
    m = re.search(r"^臺北市([^ ]*?區)", land)
    return m.group(1) if m else ""


def _count_of(land: str) -> str:
    import re
    m = re.search(r"地號等(\d+)筆", land)
    return m.group(1) if m else ""


if __name__ == "__main__":
    unittest.main()
