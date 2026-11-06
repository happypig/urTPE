# -*- coding: utf-8 -*-
"""A truncated DATE cell is recovered from the name alone (D9f-1, D9f-2).

For a truncated 地號 row the recovery pass anchors on the DATE and the name
filters it. For a truncated DATE row the roles reverse: the 案名 must carry the
identity alone, and the date is what gets recovered.

Measured over 59 gazette rows: 57 recoverable, 2 residual, 0 ambiguous. The
168 list's 核定公告 date joins as a FLAG — it is empty for all 33 cases where
the publication's date and the platform's date disagree, and it is a different
date where it is present.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import recovery as R  # noqa: E402

# 編號 3 of the 2026-10-28 gazette
ROW_NAME = ("變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）"
            "土地都市更新事業計畫案")
CASE_NAME = ("變更(第二次)臺北市大安區通化段四小段336地號等26筆(原22筆)"
             "土地都市更新事業計畫案")


def _identity(name: str = ROW_NAME):
    return R.parse_identity(R.nfkc(name))


def _cand(case_name: str = CASE_NAME, d1: str = "2026-10-15T00:00:00",
          d2: str = "", api: str = "11501034") -> dict:
    return {"case_name": case_name, "api_case_id": api,
            "uro_chk_date": d1, "uro_chk_date2": d2}


# ── the candidate rule ────────────────────────────────────────────────────

def test_the_row_name_carries_the_identity_alone():
    ident = _identity()
    assert ident is not None
    assert ident.district == "大安區"
    assert ident.section == "通化段四小段"
    assert ident.mono == "0336"
    assert ident.declared_count == 26


def test_the_matching_case_is_accepted():
    ident = _identity()
    assert R.name_only_candidate(ident, ROW_NAME, _cand())


def test_a_count_disagreement_refuses():
    """recno 40's shape: the row says 等12筆, the city says 等13筆."""
    ident = _identity("變更臺北市大安區金華段四小段455-3地號等12筆土地都市更新事業計畫及權利變換計畫案")
    cand = _cand("變更臺北市大安區金華段四小段455-3地號等13筆(原508地號等11筆)土地都市更新事業計畫及權利變換計畫案")
    assert not R.name_only_candidate(ident, ROW_NAME.replace("通化段四小段336", "金華段四小段455-3"),
                                     cand)


def test_a_stage_disagreement_refuses():
    ident = _identity()
    cand = _cand("擬訂臺北市大安區通化段四小段336地號等26筆(原22筆)土地都市更新事業計畫案")
    assert not R.name_only_candidate(ident, ROW_NAME, cand)


def test_a_track_disagreement_refuses():
    ident = _identity()
    cand = _cand("變更(第二次)臺北市大安區通化段四小段336地號等26筆(原22筆)土地都市更新事業計畫及權利變換計畫案")
    assert not R.name_only_candidate(ident, ROW_NAME, cand)


def test_the_counts_are_compared_as_numbers():
    """The city writes 地號1筆 as well as 等N筆, on both sides."""
    row = "變更臺北市北投區大業段四小段574地號1筆土地都市更新事業計畫案"
    ident = _identity(row)
    cand = _cand("變更臺北市北投區大業段四小段574地號1筆土地都市更新事業計畫案")
    assert R.name_only_candidate(ident, row, cand), (
        "地號1筆 on both sides must agree")


def test_a_compatibility_ideograph_does_not_hide_the_track():
    """The city writes 利 as U+F9DD in one case name (measured 2026-11-06)."""
    row = "變更臺北市大安區復興段三小段3地號等2筆土地都市更新事業計畫及權利變換計畫案"
    ident = _identity(row)
    # U+F9DD is the CJK COMPATIBILITY IDEOGRAPH for 利 — it renders like 利
    # and is not 利. Built from the codepoint so the source file cannot
    # normalise it away.
    compat_li = chr(0xF9DD)
    cand = _cand("變更臺北市大安區復興段三小段3地號等2筆土地都市更新事業計畫及權"
                 + compat_li + "變換計畫案")
    # the raw text carries the compatibility form, so the keyword misses
    assert "權利變換" not in cand["case_name"]
    assert R.name_only_candidate(ident, row, cand), (
        "NFKC must fold the compatibility ideograph so the track matches")


# ── the acceptance: exactly one date ───────────────────────────────────────

def test_the_candidates_agree_on_one_date():
    cell, cases, seen = R.recover_date_from_name(
        _identity(), ROW_NAME, [_cand()])
    assert cell == "2026/10/15"
    assert cases == ["11501034"]
    assert seen == ["2026-10-15"]


def test_the_recovered_date_is_written_in_the_cells_own_format():
    """The reader's `to_iso` accepts `2026/10/15` and `115/8/27` and REJECTS the
    hyphenated form — so a recovered date in the wrong shape would fail the
    tripwire's date rule and the cleanser."""
    from urtpe.extract import to_iso

    cell, _cases, _seen = R.recover_date_from_name(
        _identity(), ROW_NAME, [_cand()])
    assert cell == "2026/10/15"
    assert to_iso(cell)[0] == "2026-10-15"


def test_zero_dates_leave_the_row_a_residual():
    cell, cases, seen = R.recover_date_from_name(
        _identity(), ROW_NAME, [_cand(d1="", d2="")])
    assert cell == ""
    assert cases == []
    assert seen == []


def test_several_dates_leave_the_row_a_residual():
    cell, cases, seen = R.recover_date_from_name(
        _identity(), ROW_NAME,
        [_cand(d1="2026-10-15T00:00:00", api="11501034"),
         _cand(d1="2026-06-17T00:00:00", api="11410007")])
    assert cell == "", "two dates is a guess, not a recovery"
    assert seen == ["2026-06-17", "2026-10-15"]


def test_the_second_stage_field_carries_the_date():
    """權變 stages carry their date in field 2 alone (measured: 851, 863, 902)."""
    cell, cases, _seen = R.recover_date_from_name(
        _identity(), ROW_NAME, [_cand(d1="", d2="2026-10-15T00:00:00")])
    assert cell == "2026/10/15"
    assert cases == ["11501034"]


# ── D17: the date check refuses an empty wanted date ──────────────────────

def test_the_date_check_refuses_an_empty_wanted_date():
    """Without the guard, the EMPTY second header field matched the empty
    wanted date and the function reported a false exact match."""
    result, field = R.date_check("2026-10-15T00:00:00", "", "")
    assert result == "none", f"an empty wanted date must not close ({result})"
    assert field == ""


def test_the_date_check_still_closes_an_exact_match():
    result, field = R.date_check("2026-10-15T00:00:00", "", "2026-10-15")
    assert result == "exact"
    assert field == "uro_chk_date"
