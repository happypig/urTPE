# -*- coding: utf-8 -*-
"""Case-id normalisation and join precedence (case-record-join-discriminator
task 1.1).

G1: recovery's four-check binding wins precedence over the discovery candidate
set; ambiguous-zone travels as provenance. G2: the R-form and numeric spellings
of one case id normalise to a single space before any join; stored fields are
never rewritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.case_join import join_case_ids, normalise_case_id  # noqa: E402


def test_rform_with_suffix_normalises_to_the_registry_number():
    assert normalise_case_id("R089213-02") == "089213"


def test_bare_rform_normalises_too():
    assert normalise_case_id("R089213") == "089213"


def test_numeric_ids_are_their_own_normalisation():
    assert normalise_case_id("09610235") == "09610235"
    assert normalise_case_id("10403071") == "10403071"


def test_an_unrecognised_shape_is_never_destroyed():
    assert normalise_case_id("案情參考") == "案情參考"
    assert normalise_case_id("") == ""


def test_recovery_subset_of_discovery_yields_precedence():
    result = join_case_ids(
        recovery_cases=["09610235", "09610236"],
        api_cases=["09610235", "09610236"],
        links_taipei=["09610231", "09610233", "09610234",
                      "09610235", "09610236", "09610237"],
        ambiguous_zone=True,
    )
    assert result.anchored == ["09610235", "09610236"]
    assert result.candidates == ["09610231", "09610233", "09610234",
                                 "09610235", "09610236", "09610237"]
    assert result.ambiguous is True


def test_the_live_1005_payload_shape():
    """The measured payload: 2 recovery cases inside 6 candidates, ambiguous."""
    result = join_case_ids(
        recovery_cases=["09610235", "09610236"],
        api_cases=["09610235", "09610236"],
        links_taipei=["09610231", "09610233", "09610234",
                      "09610235", "09610236", "09610237"],
        ambiguous_zone=True,
    )
    assert len(result.anchored) == 2 and len(result.candidates) == 6
    assert result.ambiguous


def test_rform_and_numeric_spellings_join_via_normalisation():
    """The recno 188 shape: recovery holds the R-form; a consumer holding the
    numeric registry id must match through normalisation."""
    result = join_case_ids(
        recovery_cases=["R089213-02"],
        api_cases=["10403071"],
        links_taipei=["089213"],
        ambiguous_zone=False,
    )
    normalised_recovery = {normalise_case_id(c) for c in result.anchored}
    assert "089213" in normalised_recovery, (
        "R089213-02 must normalise into the numeric space the candidate set uses")
    assert "089213" in {normalise_case_id(c) for c in result.candidates}


def test_agreement_yields_the_common_set_without_a_flag():
    result = join_case_ids(
        recovery_cases=["09610235"],
        api_cases=["09610235"],
        links_taipei=["09610235"],
        ambiguous_zone=False,
    )
    assert result.anchored == ["09610235"]
    assert result.candidates == ["09610235"]
    assert result.ambiguous is False
