"""E3 (7.3.x) — never-approved classification + liveness policy (TDD).

The classification data comes from scripts/explore_twurless_status.py
(top.ashx phase/NAME per case) — the ledger annotation + exclusion behavior
are the pure logic under test here.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from urtpe.links import classify_case_outcome, project_twur_class


class TestClassifyCaseOutcome:
    """top.ashx phase/NAME → outcome class (§6.5 taxonomy)."""

    def test_lapsed_gaiyao(self):
        assert classify_case_outcome({"NAME": "事業概要階段─事業概要業已失效", "phase": "A"}) == "never-approved"

    def test_rejected(self):
        assert classify_case_outcome({"NAME": "事業計畫階段─本府駁回", "phase": "B"}) == "never-approved"

    def test_withdrawn(self):
        assert classify_case_outcome({"NAME": "權利變換計畫階段─實施者自行撤回", "phase": "C"}) == "never-approved"

    def test_approved(self):
        assert classify_case_outcome({"NAME": "事業計畫階段─業經本府核定", "phase": "B"}) == "approved"

    def test_combined_track_approved(self):
        assert classify_case_outcome({"NAME": "事業計畫及權利變換計畫階段─業經本府核定", "phase": "D"}) == "approved"

    def test_in_review(self):
        assert classify_case_outcome({"NAME": "權利變換計畫階段─業已提出申請審查", "phase": "C"}) == "in-progress"

    def test_construction(self):
        assert classify_case_outcome({"NAME": "執行階段_更新案施工中", "phase": "E"}) == "in-progress"


class TestProjectTwurClass:
    def test_all_never_approved(self):
        cases = {"A": "never-approved", "B": "never-approved"}
        assert project_twur_class(cases) == "never-approved"

    def test_any_approved_is_recoverable(self):
        cases = {"A": "never-approved", "B": "approved"}
        assert project_twur_class(cases) == "recoverable"

    def test_in_progress_is_recoverable(self):
        cases = {"A": "in-progress", "B": "never-approved"}
        assert project_twur_class(cases) == "recoverable"

    def test_empty_cases_is_unknown(self):
        assert project_twur_class({}) == "unknown"

    def test_mixed_never_and_other(self):
        cases = {"A": "never-approved", "B": "other"}
        assert project_twur_class(cases) == "recoverable"
