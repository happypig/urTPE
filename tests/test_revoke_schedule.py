# -*- coding: utf-8 -*-
"""revoke-dead-schedule: the revoked state (業經本府撤銷核准) joins the dead set.

Measured 2026-11-10: 7 corpus cases carry the header NAME 業經本府撤銷核准
(中山57's 09801092/09801094, 正義315's 10410211, 臨沂396's 10601181,
溫泉559's 09504082, 辛亥277's 10010091, 美仁800's 09707196), and none is
gazetted — the city prints approvals, not revocations (inspection-batchD §D9a).
Every dead set enumerated 自行撤回 / 已駁回 / 已失效 and missed 撤銷, so the
refresh re-selected such a case forever and the viewer rendered it stateless.
"""
import json

import pytest

from urtpe.links import (
    TERMINAL_SCHEDULES,
    _DEAD_SCHEDULES,
    filter_live_cases,
    schedule_from_top,
)


class TestScheduleFromTopRevoked:
    """schedule_from_top maps the revoked header to its own state."""

    def test_a_revoked_header_derives_yi_che_xiao(self):
        assert schedule_from_top({"NAME": "業經本府撤銷核准"}) == "已撤銷"

    def test_a_stage_prefixed_revoked_header_derives_yi_che_xiao(self):
        assert schedule_from_top(
            {"NAME": "事業計畫及權利變換計畫階段─業經本府撤銷核准"}) == "已撤銷"

    def test_the_word_is_he_zhun_not_he_ding(self):
        """撤銷核准 holds 核准 — the approved branch keys on 核定, so without the
        explicit branch the case derived "" (no state at all). The branch must
        also precede any 核准-keyed rule a future edit adds."""
        assert "核定" not in "業經本府撤銷核准"
        assert schedule_from_top({"NAME": "業經本府撤銷核准"}) != "已核准"

    def test_the_neighbouring_words_are_unchanged(self):
        assert schedule_from_top({"NAME": "權利變換計畫階段─實施者自行撤回"}) == "自行撤回"
        assert schedule_from_top({"NAME": "事業計畫階段─本府駁回"}) == "已駁回"
        assert schedule_from_top({"NAME": "事業計畫階段─業經本府核定"}) == "已核准"


def test_terminal_schedules_gain_yi_che_xiao():
    """The awaiting-approval selection and the closed-case report both read
    TERMINAL_SCHEDULES; a revoked case is closed without a standing approval."""
    assert "已撤銷" in TERMINAL_SCHEDULES


def test_dead_schedules_gain_yi_che_xiao():
    assert "已撤銷" in _DEAD_SCHEDULES


def test_the_selector_skips_a_revoked_case():
    """A revoked case carries uro_chk_date but never a 核定日期 milestone, so the
    awaiting-approval selection would re-select it on every refresh."""
    from urtpe.links import cached_cases_awaiting_approval

    ms = {"10010091": {"申請計畫日期": "2010/08/20"}}
    assert cached_cases_awaiting_approval(ms, {"10010091": "已撤銷"}) is False


def test_a_revoked_case_yields_to_an_approved_same_name_sibling():
    """The 吉林705 shape (withdrawn yields to approved) with 撤銷 in place of
    撤回: a revoked case never binds, the approved same-name sibling does."""
    class D:
        case_schedules = {"09307103": "已撤銷", "09307104": "已核准"}
        case_milestones = {}

    live = filter_live_cases(["09307103", "09307104"], D())
    assert live == ["09307104"], f"the revoked case must not bind, got {live}"


def test_a_revoked_case_binds_nothing_when_alone():
    class D:
        case_schedules = {"10410211": "已撤銷"}
        case_milestones = {}

    assert filter_live_cases(["10410211"], D()) == []


def test_refreshed_schedule_keeps_a_revoked_state():
    """A cached 已撤銷 survives a refresh whose header names no other outcome —
    the terminal-keep rule, now with the revoked state in the terminal set."""
    from urtpe.links import refreshed_schedule

    assert refreshed_schedule("已撤銷", "", None) == "已撤銷"
    assert refreshed_schedule("已撤銷", "審查中", None) == "審查中", (
        "a live header still overrides the revoked state")
