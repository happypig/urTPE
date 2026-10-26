# -*- coding: utf-8 -*-
"""Two-tier list completion and normalized typo repair — tasks 2.4 and 2.6.

Written before implementation (test-first gate). The GIS candidate sets are the
live-computed memberships recorded on 2026-10-26 (`geoserver_candidates.json`):
虎林段 R089601 has 148 candidate parcels (≥1 ring vertex inside the boundary) and
must reconstruct exactly the declared 138; 美仁段 R098505 has 86 and must REFUSE
(72 fragment + 3 tail candidates = 75 ≠ 74) — the calibration measured in
poc_findings.md T8.
"""

from __future__ import annotations

from urtpe import recovery as R
from tests.fixtures_recovery import FRAGMENT_67, FRAGMENT_79, geoserver_candidates

CANDS_67 = {land for land, _frac in geoserver_candidates()["R089601"]}
CANDS_79 = {land for land, _frac in geoserver_candidates()["R098505"]}


# --- 2.4 the 虎林段 fixture reconstructs to exactly the declared 138 ----------

def test_hulin_reconstruction_closes_at_138():
    done = R.complete_unit_list(FRAGMENT_67, CANDS_67, 138)
    assert done.ok, f"the calibration anchors must close: {done.reason}"
    assert len(done.parcels) == 138
    # every parcel visible in the PDF fragment survives
    assert set(R.fragment_parcels(FRAGMENT_67)) <= set(done.parcels)
    # the 25 added parcels are exactly the continuation of the truncated series
    visible = set(R.fragment_parcels(FRAGMENT_67))
    added = sorted(set(done.parcels) - visible, key=R.gazette_order_key)
    assert added == [f"93-{n}" for n in range(17, 42)]
    # the 10 in-gap surplus (37, 42-44, 70, 85, 87, 89, 91, 92) are excluded
    assert "42" not in done.parcels and "37" not in done.parcels
    assert "70" not in done.parcels and "91" not in done.parcels


def test_meiren_refuses_and_keeps_the_fragment_partial():
    """美仁段: 3 tail candidates for 2 slots — refuse rather than pick a subset
    to force the declared count (the refuse-to-ambiguous rule, T8)."""
    repaired, repairs = R.repair_fragment(FRAGMENT_79, CANDS_79, CANDS_79)
    assert repairs == [("78-1", "718-1")]
    done = R.complete_unit_list(repaired, CANDS_79, 74)
    assert not done.ok
    assert done.reason == "count-mismatch"
    assert len(done.parcels) == 75  # 72 fragment (post-repair) + 3 tail candidates


def test_fragment_containment_is_a_precondition():
    """A fragment carrying a parcel the GIS set never heard of is refused —
    that is the guard that refused R089305's wrong-unit polygons (T10)."""
    done = R.complete_unit_list(
        "臺北市信義區虎林段四小段38、41、9999-9、", CANDS_67, 138)
    assert not done.ok
    assert done.reason == "fragment-not-contained"


def test_numeric_form_units_have_no_candidates():
    """Numeric-form case ids have no boundary polygons — recorded as empty."""
    assert geoserver_candidates()["09610233"] == []
    assert geoserver_candidates()["09902025"] == []


# --- 2.6 normalized typo repair ---------------------------------------------

def test_typo_repair_is_flagged_and_auditable():
    repaired, repairs = R.repair_fragment(FRAGMENT_79, CANDS_79, CANDS_79)
    assert repairs == [("78-1", "718-1")]
    assert "78-1" not in repaired
    assert "718-1" in repaired
    # the repair never silently changes anything else
    for token in R.fragment_parcels(FRAGMENT_79):
        if token != "78-1":
            assert token in repaired


def test_no_repair_when_the_token_is_already_in_the_cadastre():
    land = "臺北市信義區虎林段四小段38、41、45、"
    repaired, repairs = R.repair_fragment(land, CANDS_67)
    assert repairs == []
    assert repaired == land


def test_no_repair_when_no_one_deletion_matches():
    """A token the cadastre contradicts with no unique repair stays as printed:
    no parcel is ever invented."""
    land = "臺北市信義區虎林段四小段38、41、5799-9、"
    repaired, repairs = R.repair_fragment(land, CANDS_67)
    assert repairs == []
    assert "5799-9" in repaired


def test_ambiguous_repair_is_refused():
    """Two one-deletion matches that both fit the printed slot — the repair is
    ambiguous, so none is made."""
    land = "臺北市測試段710、79-1、730、"
    cadastre = {"719-1", "729-1"}
    repaired, repairs = R.repair_fragment(land, cadastre)
    assert repairs == []
    assert "79-1" in repaired
