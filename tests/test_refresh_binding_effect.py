# -*- coding: utf-8 -*-
"""After a refresh recovers a missing approval date, the node binds by date
(refresh-awaiting-approval-caches task 1.2).

Pinned on the 336 shape the user specified: nodes 453 (2022-08-02), 370
(2023-03-21), 1 (2026-10-15) must bind 10011271, 10011273, 11501034 — the third
only once its 核定日期 2026/10/15 is present, as the city's API reports today.
Without it the node falls to the positional fallback (city_case_ids[0]).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import _match_case_by_date  # noqa: E402


class _Disc:
    def __init__(self, case_milestones):
        self.case_milestones = case_milestones
        self.city_case_ids = sorted(case_milestones)


STALE = {
    "10011271": {"核定日期": "2022/08/02"},
    "10011273": {"核定日期": "2023/03/21"},
    "11501034": {"申請計畫日期": "2025/09/10", "申請核定日期": "2026/07/30"},
}
REFRESHED = {
    **STALE,
    "11501034": {"申請計畫日期": "2025/09/10", "申請核定日期": "2026/07/30",
                 "核定日期": "2026/10/15"},
}


def test_before_the_refresh_the_newest_node_has_no_match():
    """The stale cache cannot answer for 2026-10-15 — which is exactly why the
    attach falls through to the positional fallback."""
    assert _match_case_by_date("2026-10-15", _Disc(STALE)) == ""


def test_after_the_refresh_the_newest_node_binds_by_date():
    assert _match_case_by_date("2026-10-15", _Disc(REFRESHED)) == "11501034"


def test_the_other_two_nodes_were_already_correct():
    assert _match_case_by_date("2022-08-02", _Disc(REFRESHED)) == "10011271"
    assert _match_case_by_date("2023-03-21", _Disc(REFRESHED)) == "10011273"


def test_the_case_key_order_then_equals_the_date_order():
    """With all three bound, the ascending case-id order is the date order — so no
    tie-break fires and the graph rows ascend without a sort change."""
    disc = _Disc(REFRESHED)
    bound = [(n["date"], _match_case_by_date(n["date"], disc))
             for n in ({"date": "2022-08-02"}, {"date": "2023-03-21"},
                       {"date": "2026-10-15"})]
    keys = [cid for _d, cid in bound]
    assert keys == sorted(keys), f"case keys must ascend with the dates: {keys}"
    assert keys == ["10011271", "10011273", "11501034"]


# --- the 303 shape (fix-row-order-tiebreak-and-view-badges task 1.3) --------
# 北投區-關渡段二小段-303地號等5筆: node 5 (2026-09-30, 權利變換) must bind
# 11505020 once the refresh recovers its 核定日期 2026/09/30 (live-verified on
# the API 2026-11-02). Stale, it falls to the positional fallback
# city_case_ids[1] = 10803151 — the case node 669 (2020-07-28) date-matched —
# and the shared key renders node 5 above node 669.

STALE_303 = {
    "10105152": {"核定日期": "2019/02/14", "建照核發日期": "2021/04/26"},
    "10803151": {"權變核定日期": "2020/07/28"},
    "11503009": {"申請權變日期": "2025/10/15"},
    "11505020": {"申請計畫日期": "2026/05/15", "申請權變日期": "2026/05/15"},
}
REFRESHED_303 = {
    "10105152": {"核定日期": "2019/02/14", "建照核發日期": "2021/04/26"},
    "10803151": {"權變核定日期": "2020/07/28"},
    "11503009": {"申請權變日期": "2025/10/15"},
    "11505020": {"申請計畫日期": "2026/05/15", "申請權變日期": "2026/05/15",
                 "核定日期": "2026/09/30", "權變核定日期": "2026/09/30"},
}


def test_303_before_the_refresh_the_newest_node_has_no_match():
    disc = _Disc(STALE_303)
    disc.city_case_ids = ["10105152", "10803151", "11503009", "11505020"]
    assert _match_case_by_date("2026-09-30", disc) == ""


def test_303_after_the_refresh_the_newest_node_binds_by_date():
    disc = _Disc(REFRESHED_303)
    disc.city_case_ids = ["10105152", "10803151", "11503009", "11505020"]
    assert _match_case_by_date("2026-09-30", disc) == "11505020"


def test_303_the_older_nodes_were_already_correct():
    disc = _Disc(REFRESHED_303)
    disc.city_case_ids = ["10105152", "10803151", "11503009", "11505020"]
    assert _match_case_by_date("2019-02-14", disc) == "10105152"
    assert _match_case_by_date("2020-07-28", disc) == "10803151"


def test_303_after_the_refresh_no_two_nodes_share_a_key():
    """The whole failure was the shared key: node 5 fell back onto 10803151,
    node 669's case. After the refresh each node carries its own key, so the
    recno tie-break cannot invert the pair."""
    disc = _Disc(REFRESHED_303)
    disc.city_case_ids = ["10105152", "10803151", "11503009", "11505020"]
    bound = [_match_case_by_date(d, disc)
             for d in ("2019-02-14", "2020-07-28", "2026-09-30")]
    assert bound == ["10105152", "10803151", "11505020"]
    assert len(set(bound)) == 3
