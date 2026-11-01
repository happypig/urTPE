# -*- coding: utf-8 -*-
"""_iso_date zero-pads, so the unpadded Gregorian gazette form matches the padded
case-milestone form (fix for the 484 residual stale bindings).

The defect: `_iso_date("2016/8/23")` returned `2016-8-23` while the case side
yields `2016-08-23`; the two never string-compare equal, `_match_case_by_date`
missed, and the per-node attach fell through to the positional fallback
(`city_case_ids[0]`) — binding 484 date-matchable nodes to the wrong case.
Measured: 1,164 of the 1,442 raw rows carry an unpadded Gregorian date.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import _iso_date, _match_case_by_date  # noqa: E402


def test_unpadded_slash_date_pads_to_iso():
    assert _iso_date("2016/8/23") == "2016-08-23"


def test_unpadded_dash_date_pads_to_iso():
    assert _iso_date("2016-8-23") == "2016-08-23"


def test_already_padded_dates_are_unchanged():
    assert _iso_date("2016/08/23") == "2016-08-23"
    assert _iso_date("2016-08-23") == "2016-08-23"


def test_empty_stays_empty():
    assert _iso_date("") == ""


def test_roc_forms_are_not_mangled_by_padding():
    """The ROC branch is the caller's job (roc_to_iso); _iso_date must not turn a
    ROC year into a 4-digit-looking string that then matches nothing."""
    assert _iso_date("115/8/27") == "115-08-27"


def test_the_two_forms_now_match_a_case_milestone():
    """The end-to-end point: a node dated `2016/8/23` finds the case whose 核定日期
    is `2016/08/23` instead of falling to the positional fallback."""

    class Disc:
        case_milestones = {"09811141": {"核定日期": "2012/08/27"},
                           "09811142": {"核定日期": "2016/08/23"}}
        city_case_ids = ["09811141", "09811142"]

    assert _match_case_by_date("2016/8/23", Disc) == "09811142"
    assert _match_case_by_date("105/8/23", Disc) == "09811142"  # ROC still works
