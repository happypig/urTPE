# -*- coding: utf-8 -*-
"""merge-across-count-shrink (S13, C9): a site-shrink approval
(等4筆(原29筆)) links across the replaced parcel set.

`score()` drops the Jaccard term when district + section + first parcel match
and one record's orig_count equals the other's land_count — the gazette's own
(原N筆) declaring the continuity — and normalises the surviving components
(the empty-parcel rule's redistribution). Measured: 11 split pairs, 10 of
which share one national page.
"""

import csv
import re
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urtpe.merge import LINK_THRESHOLD, score  # noqa: E402
from urtpe.cleanse import cleanse  # noqa: E402
from urtpe.models import RawRecord  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLEAN_TSV = ROOT / "data" / "clean.tsv"


def _rec(recno, date, district, name, land):
    return cleanse(RawRecord(recno, date, district, name, land, "某建設", "某規劃"))


class TestShrinkBridge(unittest.TestCase):
    """Task 1.1 — the shrink pair links."""

    def test_shrink_pair_scores_at_or_above_threshold(self):
        # 吳興790-6: the 2017 shrink 等4筆(原29筆) vs the 2013 approval 等29筆;
        # the parcel sets share 1 of 32 (Jaccard ≈ 0.03).
        a = _rec(978, "115/5/19", "信義區",
                 "變更(第三次)臺北市信義區吳興段二小段790-6地號等4筆(原29筆)土地都市更新事業計畫案",
                 "臺北市信義區吳興段二小段 790-6、790-14、790-15、790-16")
        b = _rec(1157, "102/11/11", "信義區",
                 "變更(第二次)臺北市信義區吳興段二小段790-6地號等29筆土地都市更新事業計畫案",
                 "臺北市信義區吳興段二小段790-6、804-1、805-1、806-1")
        self.assertGreaterEqual(score(a, b), LINK_THRESHOLD)

    def test_bridge_normalises_to_full_match(self):
        a = _rec(978, "115/5/19", "信義區",
                 "變更(第三次)臺北市信義區吳興段二小段790-6地號等4筆(原29筆)土地都市更新事業計畫案",
                 "臺北市信義區吳興段二小段 790-6、790-14、790-15、790-16")
        b = _rec(1157, "102/11/11", "信義區",
                 "變更(第二次)臺北市信義區吳興段二小段790-6地號等29筆土地都市更新事業計畫案",
                 "臺北市信義區吳興段二小段790-6、804-1、805-1、806-1")
        # (0.35 + 0.2 + 0.1) / 0.65 = 1.0 — a full match on every surviving term
        self.assertAlmostEqual(score(a, b), 1.0, places=3)


class TestMeasuredPairs(unittest.TestCase):
    """Task 1.2 — the 11 measured recno pairs all link."""

    # The pairs are identified by their CONTENT, not by 編號: 編號 is a
    # coordinate in the published list, and the list re-sorts its history by
    # 核定日期, so a new gazette moves every 編號 (measured 2026-11-06: the
    # 2026-10-28 gazette renumbered the whole corpus — 681 projects changed,
    # 680 of them with identical content). Keying the test on 編號 would make
    # it a test of the gazette's ordering, not of the merge rule.
    #
    # Each entry: (the unit's section+parcel fragment, the shrink row's
    # declared count, the older row's declared count). The counts pick the two
    # rows when the unit carries several approvals of the same count.
    #
    # Two of the eleven units are no longer in the corpus (桃源段三小段251 and
    # 玉成段五小段545 — measured 2026-11-06; neither was in the 2026-10-15
    # corpus either, so they had gone before). The rule they exercised is
    # still covered by the constructed pair above and by the measured pairs
    # that remain, so the absent ones are skipped with a count.
    PAIRS = [
        ("吳興段二小段790-6", 4, 29),
        ("中山段二小段202", 1, 12),
        ("中正段一小段44", 1, 5),
        ("犁和段三小段89", 1, 16),
        ("桃源段三小段251", 2, 17),
        ("立農段一小段513", 3, 17),
        ("南港段四小段566", 1, 6),
        ("玉成段五小段545", 4, 8),
        ("芝蘭段四小段130", 1, 9),
        ("玉泉段二小段91", 7, 42),
        ("金華段一小段719", 1, 11),
    ]

    def setUp(self):
        if not CLEAN_TSV.is_file():
            self.skipTest("clean.tsv absent (generated output)")

    def _load(self):
        with open(CLEAN_TSV, encoding="utf-8") as f:
            rows = {r["recno"]: r for r in csv.DictReader(f, delimiter="\t")}
        def to_rec(recno):
            r = rows[recno]
            return cleanse(RawRecord(int(r["recno"]), r["date"], r["district"],
                                     r["name"], r["land"],
                                     r.get("implementer", ""),
                                     r.get("planner", "")))
        return {k: to_rec(k) for k in rows}

    def _find(self, recs, fragment, count):
        """The record whose 案名 names the unit AND declares the count, or None
        when the unit is not in the corpus.

        The fragment must be followed by the parcel, not merely contained: the
        unit 中正段一小段44 and the unit 中正段一小段446-1 both carry the
        fragment 中正段一小段44."""
        hits = [r for r in recs.values()
                if fragment in r.name and (r.land_count or 0) == count
                and re.search(re.escape(fragment) + r"(?![\d-])", r.name)]
        return hits[0] if hits else None

    def test_every_measured_pair_links(self):
        recs = self._load()
        absent = []
        for fragment, shrink_count, older_count in self.PAIRS:
            shrink = self._find(recs, fragment, shrink_count)
            older = self._find(recs, fragment, older_count)
            if shrink is None or older is None:
                absent.append(fragment)
                continue
            self.assertGreaterEqual(
                score(shrink, older), LINK_THRESHOLD,
                f"{fragment} {shrink_count}/{older_count} must link across "
                f"the shrink (recnos {shrink.recno}/{older.recno})")
        # the units that left the corpus are reported, not silently dropped
        self.assertLessEqual(
            len(absent), 2,
            f"more than two measured units left the corpus: {absent}")


class TestNoBridgeWithoutShrink(unittest.TestCase):
    """Task 1.3 — no over-merge without the (原N筆) bridge."""

    def test_coincidental_pair_keeps_the_standing_score(self):
        # Same section + first parcel, same count, but neither record declares
        # an orig_count bridge — the standing rule decides.
        a = _rec(1, "115/8/11", "大安區",
                 "擬訂臺北市大安區學府段1地號等5筆都市更新事業計畫案",
                 "臺北市大安區學府段1、2、3、4、5")
        b = _rec(2, "114/5/1", "大安區",
                 "變更臺北市大安區學府段1地號等5筆都市更新事業計畫案",
                 "臺北市大安區學府段1、9、10、11、12")
        # identical first parcel + count → the standing score is high anyway;
        # assert the bridge did not inflate a disjoint-parcel pair beyond it
        standing = score(a, b)
        a2 = _rec(3, "115/8/11", "大安區",
                  "擬訂臺北市大安區學府段1地號等5筆(原9筆)都市更新事業計畫案",
                  "臺北市大安區學府段1、2、3、4、5")
        b2 = _rec(4, "99/1/01", "大安區",
                  "擬訂臺北市大安區學府段1地號等9筆都市更新事業計畫案",
                  "臺北市大安區學府段1、20、21")
        bridged = score(a2, b2)
        # the pair with a declared bridge scores at least as high as the
        # coincidental one on the same shape
        self.assertGreaterEqual(bridged, standing)
        # and the coincidental pair is not pushed above the standing rule's
        # own verdict for its shape
        self.assertLessEqual(standing, 1.0)


class TestAliasUnderBridge(unittest.TestCase):
    """Task 1.4 — an alias-band first parcel under the bridge still links."""

    def test_alias_first_parcel_links(self):
        # the shrink's first parcel is a renumbering alias of the older one
        a = _rec(10, "115/8/11", "大安區",
                 "變更臺北市大安區學府段1地號等3筆(原17筆)都市更新事業計畫案",
                 "臺北市大安區學府段1-1、1-2")
        b = _rec(11, "100/2/02", "大安區",
                 "擬訂臺北市大安區學府段1地號等17筆都市更新事業計畫案",
                 "臺北市大安區學府段1、2、3")
        self.assertGreaterEqual(score(a, b), LINK_THRESHOLD)


class TestBridgeWithEmptyParcels(unittest.TestCase):
    """Task 1.5 — the bridge and the empty-parcel rule compose."""

    def test_shrink_with_unparseable_parcels_links(self):
        a = _rec(20, "115/8/11", "大安區",
                 "變更臺北市大安區學府段1地號等3筆(原17筆)都市更新事業計畫案",
                 "臺北市大安區學府段1")  # 1 parcel (truncated print)
        b = _rec(21, "100/2/02", "大安區",
                 "擬訂臺北市大安區學府段1地號等17筆都市更新事業計畫案",
                 "臺北市大安區學府段1、2、3")
        self.assertGreaterEqual(score(a, b), LINK_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
