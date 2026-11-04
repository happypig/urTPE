# -*- coding: utf-8 -*-
"""building-permit-adapter task 1.5: the attach-side flag texts. The permit
is a witness, never a repair — the portals' 使照 values stay, the flag names
the value the permit confirms (design D4)."""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urtpe.links import permit_review_flags  # noqa: E402


def _permit(no="102使字第0298號", date="2013-11-12"):
    return SimpleNamespace(permit_no=no, date=date)


class TestPermitFlags(unittest.TestCase):
    def test_city_confirmed(self):
        flags = permit_review_flags(city="2022/11/11", national="2022/01/11",
                                    permits=[_permit("111使字第0140號", "2022-11-11")])
        self.assertTrue(any("使照兩源不一致" in f and "111使字第0140號" in f
                            and "2022/11/11" in f for f in flags), flags)

    def test_national_confirmed(self):
        flags = permit_review_flags(city="2013/09/11", national="2013/11/12",
                                    permits=[_permit()])
        self.assertTrue(any("使照兩源不一致" in f and "102使字第0298號" in f
                            and "2013/11/12" in f for f in flags), flags)

    def test_permit_matches_neither(self):
        flags = permit_review_flags(city="2020/03/01", national="2020/03/02",
                                    permits=[_permit("102使字第0298號", "2013-11-12")])
        self.assertTrue(any("使照兩源不一致" in f and "介於" not in f and "執照" in f
                            for f in flags), flags)

    def test_no_permit(self):
        flags = permit_review_flags(city="2022/09/23", national="2023/09/23",
                                    permits=[])
        self.assertTrue(any("使照兩源不一致" in f and "無執照佐證" in f for f in flags), flags)

    def test_agreement_carries_no_flag(self):
        flags = permit_review_flags(city="2022/11/11", national="2022-11-11",
                                    permits=[_permit("111使字第0140號", "2022-11-11")])
        self.assertEqual(flags, [])

    def test_one_sided_dates_carry_no_disagreement_flag(self):
        flags = permit_review_flags(city="", national="2022-11-11",
                                    permits=[_permit("111使字第0140號", "2022-11-11")])
        # the witness exists but there is nothing to disagree with; the flag
        # vocabulary names only two-source disagreements
        self.assertEqual([f for f in flags if "使照兩源不一致" in f], [])


if __name__ == "__main__":
    unittest.main()
