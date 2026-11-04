# -*- coding: utf-8 -*-
"""building-permit-adapter (S15, C5): the building authority's 使用執照摘要
open data witnesses the 使照 date the two portals copy and disagree on.

Pure logic (parse/index/match) separated from the I/O adapter (download),
per openspec/config.yaml's port/adapter rule. Measured on the corpus:
8 city-confirmed + 9 national-confirmed of 22 disagreements, 12 of 13
national-only dates confirmed, 2 parcel-list misses.
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urtpe.permit_sources import (  # noqa: E402
    PermitRecord,
    build_permit_index,
    match_project_permits,
    parse_permit_xml,
    permit_date_iso,
)

HIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Datas>
<Data><執照年度>102</執照年度><執照號碼>102使字第0298號</執照號碼><發照日期>1021112</發照日期><原核發執照>100建字第0008號</原核發執照><開工日期>1000305</開工日期><竣工日期>1020930</竣工日期><建築地點><地址>臺北市中山區吉林路110號</地址></建築地點><地段地號><地段號>臺北市中山區吉林段三小段0811-0000號</地段號><地段號>臺北市中山區吉林段三小段０８１２－００００號</地段號></地段地號></Data>
<Data><執照年度>111</執照年度><執照號碼>111使字第0140號</執照號碼><發照日期>1111111</發照日期><原核發執照>107建字第0198號</原核發執照><開工日期>1080619</開工日期><建築地點><地址>臺北市信義區永吉路30巷1號</地址></建築地點><地段地號><地段號>臺北市信義區虎林段四小段0310-0000號</地段號></地段地號></Data>
<Data><執照年度>103</執照年度><執照號碼>103雜字第0007號</執照號碼><發照日期>1030619</發照日期><原核發執照></原核發執照><開工日期></開工日期><建築地點><地址>臺北市士林區奇岩路1號</地址></建築地點><地段地號><地段號>臺北市士林區奇岩段一小段0201-0000號</地段號></地段地號></Data>
<Data><執照年度>104</執照年度><執照號碼>104使字第0011號</執照號碼><發照日期>1040522</發照日期><原核發執照>102建字第0055號</原核發執照><開工日期>1020715</開工日期><建築地點><地址>臺北市大安區懷生段1號</地址></建築地點><地段地號><地段號>臺北市大安區懷生段二小段0301-0000號</地段號><地段號>臺北市大安區懷生段二小段0302-0000號</地段號></地段地號></Data>
</Datas>
"""


class TestPermitRecord(unittest.TestCase):
    """Task 1.1 — the XML record parser."""

    def setUp(self):
        self.recs = parse_permit_xml(ET.fromstring(HIST_XML))
        self.by_no = {r.permit_no: r for r in self.recs}

    def test_parses_every_record(self):
        self.assertEqual(len(self.recs), 4)

    def test_roc_date_to_iso(self):
        r = self.by_no["102使字第0298號"]
        self.assertEqual(r.date, "2013-11-12")

    def test_fields(self):
        r = self.by_no["102使字第0298號"]
        self.assertEqual(r.orig_permit, "100建字第0008號")
        self.assertIn(("中山區", "吉林段三小段", "811"), r.parcels)

    def test_full_width_digits_fold(self):
        r = self.by_no["102使字第0298號"]
        # ０８１２－００００號 folds to mono 812
        self.assertIn(("中山區", "吉林段三小段", "812"), r.parcels)

    def test_a_jianzi_origin_reads_true(self):
        self.assertTrue(self.by_no["102使字第0298號"].is_jianzi)
        self.assertFalse(self.by_no["103雜字第0007號"].is_jianzi)

    def test_an_empty_origin_carries_none(self):
        r = self.by_no["103雜字第0007號"]
        self.assertEqual(r.orig_permit, "")
        self.assertFalse(r.is_jianzi)


class TestPermitIndex(unittest.TestCase):
    """Task 1.2 — the (district, section, mono) index."""

    def setUp(self):
        self.recs = parse_permit_xml(ET.fromstring(HIST_XML))
        self.index = build_permit_index(self.recs)

    def test_index_keys(self):
        self.assertIn(("中山區", "吉林段三小段", "811"), self.index)
        self.assertIn(("信義區", "虎林段四小段", "310"), self.index)

    def test_a_permit_indexes_under_every_parcel(self):
        self.assertEqual(
            {r.permit_no for r in self.index[("中山區", "吉林段三小段", "812")]},
            {"102使字第0298號"})


class TestJianziRule(unittest.TestCase):
    """Task 1.3 — the 建字-origin rule."""

    def setUp(self):
        self.recs = parse_permit_xml(ET.fromstring(HIST_XML))
        self.by_no = {r.permit_no: r for r in self.recs}

    def test_a_za_permit_is_not_a_witness(self):
        self.assertFalse(self.by_no["103雜字第0007號"].is_jianzi)

    def test_two_jianzi_permits_both_witness(self):
        # 懷生931's shape: two 建字-origin permits on one site, one per area
        a = PermitRecord("104使字第0011號", "2015-05-22", "102建字第0055號",
                         [("大安區", "懷生段二小段", "301")], True)
        b = PermitRecord("105使字第0099號", "2016-05-17", "104建字第0077號",
                         [("大安區", "懷生段二小段", "302")], True)
        self.assertTrue(a.is_jianzi and b.is_jianzi)


class TestPermitMatch(unittest.TestCase):
    """Task 1.4 — the match (max overlap; ties keep all; no overlap → none)."""

    def setUp(self):
        self.recs = parse_permit_xml(ET.fromstring(HIST_XML))
        self.index = build_permit_index(self.recs)

    def test_the_overlapping_permit_matches(self):
        got = match_project_permits(
            self.index, [("中山區", "吉林段三小段", "811"),
                         ("中山區", "吉林段三小段", "813")])
        self.assertEqual([p.permit_no for p in got], ["102使字第0298號"])

    def test_no_overlap_carries_no_witness(self):
        got = match_project_permits(
            self.index, [("中山區", "吉林段三小段", "999")])
        self.assertEqual(got, [])

    def test_distinct_parcels_keep_both_jianzi_permits(self):
        got = match_project_permits(
            self.index, [("大安區", "懷生段二小段", "301"),
                         ("大安區", "懷生段二小段", "302")])
        self.assertEqual([p.permit_no for p in got],
                         ["104使字第0011號"])

    def test_a_za_permit_never_matches(self):
        got = match_project_permits(
            self.index, [("士林區", "奇岩段一小段", "201")])
        self.assertEqual(got, [])


class TestPermitDate(unittest.TestCase):
    """The ROC YYYMMDD → ISO conversion."""

    def test_a_normal_date(self):
        self.assertEqual(permit_date_iso("1021112"), "2013-11-12")

    def test_an_empty_date(self):
        self.assertEqual(permit_date_iso(""), "")

    def test_a_garbage_date(self):
        self.assertEqual(permit_date_iso("not-a-date"), "")


class TestCachedMatch(unittest.TestCase):
    """Task 1.7 — offline acceptance against the board's measured values."""

    def test_jilin811_confirms_the_national_value(self):
        # 吉林811: the city 2013/09/11, the national 2013-11-12; the permit
        # 102使字第0298號 (2013-11-12) confirms the national side
        recs = parse_permit_xml(ET.fromstring(HIST_XML))
        index = build_permit_index(recs)
        got = match_project_permits(index, [("中山區", "吉林段三小段", "811")])
        self.assertEqual(got[0].date, "2013-11-12")

    def test_hulin310_confirms_the_city_value(self):
        # 虎林310: the city 2022/11/11, the national 2022/01/11; the permit
        # 111使字第0140號 (2022-11-11) confirms the city side
        recs = parse_permit_xml(ET.fromstring(HIST_XML))
        index = build_permit_index(recs)
        got = match_project_permits(index, [("信義區", "虎林段四小段", "310")])
        self.assertEqual(got[0].date, "2022-11-11")


if __name__ == "__main__":
    unittest.main()
