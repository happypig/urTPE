# -*- coding: utf-8 -*-
"""Pure matching logic for truncated-row recovery — task group 2.1–2.3, 2.5, 2.7.

Written before any implementation per the openspec test-first gate. The candidate
data is assembled from responses recorded live on 2026-10-26
(``probes/capture_recordings.py`` → ``tests/fixtures/recovery/``), so every
accepting assertion is pinned to what the city's APIs actually answer:

* 編號 79 (美仁段二小段694) — one exact candidate, ``uro_chk_date``;
* 編號 851 (雙連段一小段197) — exact only in ``uro_chk_date2`` (權變 stage);
* 編號 930 (雙園段二小段505) — the −A區/−B區 zone pair, both exact on the same date;
* 編號 100 of the 2026-08-11 gazette (南港段一小段561) — a real residual.
"""

from __future__ import annotations

import pytest

from urtpe import recovery as R
from tests.fixtures_recovery import recorded_candidates

NAME_79 = ("變更臺北市松山區美仁段二小段694地號等74筆(原54筆)土地都市更新事業計畫"
           "及擬訂權利變換計畫案")
DATE_79 = "2026-01-14"

NAME_851 = "變更(第三次)臺北市大同區雙連段一小段197地號等72筆土地都市更新權利變換計畫案"
DATE_851 = "2018-12-04"

NAME_930 = "變更(第二次)臺北市萬華區雙園段二小段505地號等77筆土地都市更新權利變換計畫案"
DATE_930 = "2017-12-12"

# The real residual row (task 1.5, poc_findings.md T4 Part A).
NAME_RESIDUAL = "擬訂臺北市南港區南港段一小段561地號1筆(原5筆)土地都市更新事業計畫案"
DATE_RESIDUAL = "2025-07-15"


def _match(name, date, family_key):
    identity = R.parse_identity(name)
    assert identity is not None, f"identity must parse from {name!r}"
    return R.match_row(identity, date, recorded_candidates(family_key))


# --- 2.1 the four checks accept 編號 79 --------------------------------------

def test_four_checks_accept_row_79():
    match = _match(NAME_79, DATE_79, "美仁段二小段|0694|0000")
    assert match.status == "matched"
    # provenance carries both id spaces: the display id is the GeoServer/portal
    # key (R-form), the api id keys get_project168_top
    assert [c["case_id"] for c in match.cases] == ["R098505"]
    assert [c["api_case_id"] for c in match.cases] == ["11411014"]
    assert match.cases[0]["date_result"] == "exact"
    assert match.cases[0]["date_field"] == "uro_chk_date"
    assert match.flags == []


def test_recovery_records_case_name_char_for_char():
    """Design.md's 美仁段 evidence: CASE_NAME == 案名 char-for-char."""
    match = _match(NAME_79, DATE_79, "美仁段二小段|0694|0000")
    assert R.normalize_name(match.cases[0]["case_name"]) == R.normalize_name(NAME_79)


# --- 2.1 four refusal tests: each check broken alone ------------------------

def test_refuse_when_section_differs():
    """Check 1: a candidate in another 小段 is never a match."""
    identity = R.parse_identity(NAME_79)
    identity = R.RowIdentity(**{**identity.__dict__, "section": "美仁段三小段"})
    match = R.match_row(identity, DATE_79, recorded_candidates("美仁段二小段|0694|0000"))
    assert match.status == "residual"
    assert match.cases == []


def test_refuse_when_fragment_not_contained():
    """Check 2: the surviving 案名 address core must appear in the candidate name."""
    identity = R.parse_identity(NAME_79)
    cands = recorded_candidates("美仁段二小段|0694|0000")
    for c in cands:  # strip the addressing from every candidate
        c["case_name"] = "都市更新事業計畫案(名稱缺漏)"
    match = R.match_row(identity, DATE_79, cands)
    assert match.status == "residual"


def test_refuse_when_count_fragment_missing():
    """Check 3: the declared-count fragment must appear in the candidate name."""
    identity = R.parse_identity(NAME_79)
    cands = recorded_candidates("美仁段二小段|0694|0000")
    for c in cands:  # a family of cases that all declare a different count
        c["case_name"] = c["case_name"].replace("74筆(原54筆)", "64筆(原54筆)")
    match = R.match_row(identity, DATE_79, cands)
    assert match.status == "residual"


def test_refuse_when_date_missing_in_both_fields():
    """Check 4: no date in either field, no recovery."""
    identity = R.parse_identity(NAME_79)
    cands = recorded_candidates("美仁段二小段|0694|0000")
    for c in cands:
        c["uro_chk_date"] = ""
        c["uro_chk_date2"] = ""
    match = R.match_row(identity, DATE_79, cands)
    assert match.status == "residual"


# --- 2.2 date-field resolution and the ±1 rule ------------------------------

def test_date_check_passes_on_uro_chk_date2_alone():
    """編號 851: a 權變 stage whose date exists only in uro_chk_date2."""
    match = _match(NAME_851, DATE_851, "雙連段一小段|0197|0000")
    assert match.status == "matched"
    assert [c["case_id"] for c in match.cases] == ["09902027"]
    assert match.cases[0]["date_field"] == "uro_chk_date2"


def test_pm1_accepted_only_without_exact_candidate_and_flagged():
    """A ±1-day match is accepted when no exact candidate exists — and flagged."""
    identity = R.parse_identity(NAME_79)
    base = next(c for c in recorded_candidates("美仁段二小段|0694|0000")
                if "74筆" in c["case_name"])
    exact = {**base, "case_id": "X1", "uro_chk_date": DATE_79, "uro_chk_date2": ""}
    pm1 = {**base, "case_id": "X2", "uro_chk_date": "2026-01-13", "uro_chk_date2": ""}

    both = R.match_row(identity, DATE_79, [pm1, exact])
    assert [c["case_id"] for c in both.cases] == ["X1"]  # exact wins
    assert both.flags == []

    only_pm1 = R.match_row(identity, DATE_79, [pm1])
    assert only_pm1.status == "matched"
    assert only_pm1.flags == ["date-pm1"]


def test_pm1_beyond_one_day_is_refused():
    identity = R.parse_identity(NAME_79)
    base = next(c for c in recorded_candidates("美仁段二小段|0694|0000")
                if "74筆" in c["case_name"])
    off = {**base, "uro_chk_date": "2026-01-12", "uro_chk_date2": ""}
    assert R.match_row(identity, DATE_79, [off]).status == "residual"


# --- 2.3 multi-case attachment (the 編號 930 zone pair) ----------------------

def test_row_930_attaches_both_zone_cases():
    match = _match(NAME_930, DATE_930, "雙園段二小段|0505|0000")
    assert match.status == "matched"
    assert sorted(c["case_id"] for c in match.cases) == ["09610233", "09610237"]
    assert match.flags == ["ambiguous-zone"]
    # a single land core, taken from the row's own 案名 — the zone split does not
    # split the identity (D-C/D-E)
    identity = R.parse_identity(NAME_930)
    assert identity.address_core == "臺北市萬華區雙園段二小段505地號等77筆"
    assert match.date_field == "uro_chk_date2"


# --- 2.5 named anchors are not zone markers ---------------------------------

def test_named_anchor_is_never_a_zone_marker():
    assert not R.is_zone_marker("(原東星大樓基地)")
    assert not R.is_zone_marker("擬訂…土地(原東星大樓基地)都市更新事業計畫案")


def test_zone_markers_are_recognised():
    assert R.is_zone_marker("變更(第二次)…權利變換計畫案-A區")
    assert R.is_zone_marker("變更(第二次)…權利變換計畫案-B區")
    assert R.is_zone_marker("擬訂…土地(甲區段)都市更新事業計畫案")
    assert R.is_zone_marker("擬訂…土地(乙區段)都市更新事業計畫案")


# --- 2.7 the residual path ---------------------------------------------------

def test_a_row_the_apis_do_not_know_stays_residual():
    """The real residual (南港段一小段561): 22 recorded candidates, none carries
    the declared-count fragment, so no candidate qualifies."""
    family = recorded_candidates("南港段一小段|0561|0000")
    assert len(family) == 22
    match = _match(NAME_RESIDUAL, DATE_RESIDUAL, "南港段一小段|0561|0000")
    assert match.status == "residual"
    assert match.cases == []
    assert match.flags == []


def test_identity_refusal_when_the_case_name_has_no_land_core():
    assert R.parse_identity("擬訂臺北市士林區某處整宅更新計畫案") is None


# --- the similarity fallback stays configured but is not exercised here ------

def test_thresholds_default_to_the_configured_band():
    """The band reuses the link thresholds (0.7 link, 0.5–0.7 flag); the POC
    measured 0 rows in the band (poc_findings.md T2), so acceptance must not
    depend on it."""
    assert R.LINK_THRESHOLD == 0.7
    assert R.FLAG_THRESHOLD == 0.5
