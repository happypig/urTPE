# -*- coding: utf-8 -*-
"""F1 phase 1 (docs/inspections/inspection-batchF.md): one membership function, named policies.

The code answers "does this case belong to this unit?" in several places. Phase 1
is a BEHAVIOUR-PRESERVING refactor: `membership_verdict(case_name, unit, policy)`
returns a verdict with a reason, and each name-based site calls it with its own
current rule as a named policy. It changes no verdict.

S1 search guard (exact / stem / own parcel / corroborated area), S2 §8 gate,
S3 offer step, S4 node tier-3 match, S5 orphan name branch go through it. S6
(shared dates with anchored cases) and S7 (shared area words) rest on different
evidence, not a case name against a unit, and are left out on purpose.

The golden table (tests/fixtures/membership_golden.json) is a CHARACTERIZATION
test: it was captured from the pre-refactor code on frozen inputs, so it cannot go
red first. It pins every site's verdict over 3,094 (unit, name) pairs and 7,328
(node, name) pairs; the refactor passes only if every bit is unchanged.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as L  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = json.loads((FIXTURES / "membership_golden.json").read_text(encoding="utf-8"))
TIER1 = json.loads((FIXTURES / "membership_tier1.json").read_text(encoding="utf-8"))["units"]


def _unit(row):
    _pid, core, own, counts, anchor_name = row
    return L.Unit(land_core=core, own_parcels=tuple(own), own_counts=tuple(counts),
                  anchor_name=anchor_name)


# ── the golden table ──────────────────────────────────────────────────────────

def test_the_threshold_the_sites_share_is_the_link_threshold():
    """S5 compared with the literal 0.7 and S3 with LINK_THRESHOLD; the shared
    policy uses LINK_THRESHOLD. They are the same number today."""
    assert L._link_threshold() == 0.7


def test_the_golden_table_is_not_vacuous():
    assert len(GOLDEN["pairs"]) == 3094 and len(GOLDEN["node_pairs"]) == 7328
    for col in (3, 4, 5, 6):
        n = sum(r[col] for r in GOLDEN["pairs"])
        assert 1000 < n < len(GOLDEN["pairs"]), (col, n)       # both verdicts occur
    assert 1000 < sum(r[2] for r in GOLDEN["node_pairs"]) < len(GOLDEN["node_pairs"])
    assert all(u[2] for u in GOLDEN["units"]), "a unit without own parcels (S1 needs one)"


@pytest.mark.parametrize("site, policy, col", [
    ("S1 search guard", "search_guard", 3),
    ("S2 §8 gate", "gate", 4),
    ("S3 offer step", "offer", 5),
    ("S5 orphan name", "orphan_name", 6),
])
def test_every_pair_keeps_its_verdict_at_each_name_based_site(site, policy, col):
    units = [_unit(u) for u in GOLDEN["units"]]
    moved = []
    for row in GOLDEN["pairs"]:
        unit = units[row[0]]
        got = L.membership_verdict(row[2], unit, policy,
                                   searched_parcel=unit.own_parcels[0]).accept
        if int(got) != row[col]:
            moved.append((GOLDEN["units"][row[0]][0], row[1]))
    assert not moved, f"{site}: {len(moved)} verdicts moved, e.g. {moved[:3]}"


def test_every_node_pair_keeps_its_verdict_at_the_tier_3_site():
    units = [_unit(u) for u in GOLDEN["units"]]
    nodes = GOLDEN["nodes"]
    cache = {}
    moved = []
    for ni, cid, bit in GOLDEN["node_pairs"]:
        ui, recno, node_name, node_core, nparcels = nodes[ni]
        name = cache.setdefault((ui, cid), None)
        if name is None:
            # the case name sits in the pairs table under the same unit and id
            name = next(r[2] for r in GOLDEN["pairs"] if r[0] == ui and r[1] == cid)
            cache[(ui, cid)] = name
        got = L.membership_verdict(name, units[ui], "node_tier3", node_name=node_name,
                                   node_landcore=node_core,
                                   node_parcels=tuple(nparcels)).accept
        if int(got) != bit:
            moved.append((GOLDEN["units"][ui][0], recno, cid))
    assert not moved, f"S4 node tier-3: {len(moved)} verdicts moved, e.g. {moved[:3]}"


# ── the named policies and their reasons ──────────────────────────────────────

CORE = "文山區華興段一小段8地號等4筆"
OWN = ("8", "9", "18-1")
NAME = "擬訂臺北市文山區華興段一小段{p}土地都市更新事業計畫案"


def _guard(name, parcel="8", own=OWN, anchor="", counts=(4, 13)):
    # D11 (d11-search-guard-count-rule, user decision 2026-11-15): the
    # own-parcel form adopts the count rule, so the guard's Unit now carries
    # the unit's counts — phase 1's empty tuple would refuse every counted
    # own-parcel name but the land-core count's.
    return L.membership_verdict(name, L.Unit(CORE, own, counts, anchor), "search_guard",
                                searched_parcel=parcel)


class TestTheSearchGuardKeepsItsThreeParcelRules:
    def test_exact(self):
        v = _guard(NAME.format(p="8地號等4筆"))
        assert v.accept and v.reason == "exact"

    def test_the_legacy_stem_is_its_own_named_rule(self):
        """F8: a name that carries the pre-subdivision stem (<mono>地號) is admitted
        by the stem rule, which also cross-lists a larger unit's cases."""
        v = _guard(NAME.format(p="18地號等4筆"), parcel="18-1", own=())
        assert v.accept and v.reason == "stem"

    def test_an_own_parcel(self):
        v = _guard(NAME.format(p="18-1地號等13筆"))
        assert v.accept and v.reason == "own_parcel"

    def test_an_own_parcel_with_a_count_the_unit_never_declared_is_refused(self):
        """D11: the own-parcel form adopts the count rule (the 54 measured pairs)."""
        v = _guard(NAME.format(p="18-1地號等9筆"))
        assert not v.accept and v.reason == "count_refused"

    def test_a_parcel_less_name_is_corroborated_by_the_anchor_name(self):
        anchor = "擬訂臺北市大同區崇仁新村都市更新事業計畫案"
        v = _guard("變更臺北市大同區崇仁新村都市更新事業計畫案", parcel="711-3",
                   own=(), anchor=anchor)
        assert v.accept and v.reason == "corroborated_area"

    def test_a_foreign_name_is_dropped(self):
        v = _guard(NAME.format(p="301地號等7筆"))
        assert not v.accept and v.reason == "dropped"


class TestTheOtherPolicies:
    def test_the_gate_names_the_rule_that_accepted(self):
        own, counts = ("8", "9", "18-1"), (4, 13)
        unit = L.Unit(CORE, own, counts)
        land = L.membership_verdict(NAME.format(p="8地號等5筆"), unit, "gate")
        assert land.accept and land.reason == "land_core"
        parcel = L.membership_verdict(NAME.format(p="18-1地號等13筆"), unit, "gate")
        assert parcel.accept and parcel.reason == "own_parcel"
        refused = L.membership_verdict(NAME.format(p="18-1地號等9筆"), unit, "gate")
        assert not refused.accept and refused.reason == "refused"

    def test_offer_and_orphan_name_share_the_land_core_policy(self):
        unit = L.Unit(CORE)
        for policy in ("offer", "orphan_name"):
            ok = L.membership_verdict(NAME.format(p="8地號等5筆"), unit, policy)
            assert ok.accept and ok.reason == "land_core", policy
            no = L.membership_verdict(NAME.format(p="18-1地號等13筆"), unit, policy)
            assert not no.accept and no.reason == "below_threshold", policy
            none = L.membership_verdict("擬訂臺北市大同區崇仁新村都市更新事業計畫案", unit, policy)
            assert not none.accept and none.reason == "no_land_core", policy

    def test_an_unknown_policy_is_an_error_not_a_silent_refusal(self):
        with pytest.raises(ValueError):
            L.membership_verdict("x", L.Unit(CORE), "nope")


# ── every name-based site goes through the one function ──────────────────────

def test_the_sites_call_the_one_function_and_no_longer_hold_their_own_expression():
    src = {
        "S1": inspect.getsource(L._search_taipei_raw),
        "S3": inspect.getsource(L.offer_rejected_ids),
        "S4": inspect.getsource(L._name_tier_hits),
    }
    for site, text in src.items():
        assert "membership_verdict(" in text, f"{site} does not call membership_verdict"
    assert "_case_name_carries_parcel(" not in src["S1"], "S1 still holds its own guard"
    assert "compute_landcore_similarity(" not in src["S3"], "S3 still holds its own rule"
    assert "_tier3_names_match(" not in src["S4"], "S4 still holds its own rule"
    whole = Path(L.__file__).read_text(encoding="utf-8")
    assert "orphan_landcore and compute_landcore_similarity(" not in whole, \
        "S5 still holds its own expression"


# ── F2 tier 1: three hand-checked units, every site must accept their own cases ──
# Every case below is the unit's own (held by the project, read live 2026-11-15
# and checked by hand). A site that refuses one is a disagreement. 華中247's and
# 吳興163-2's anchor-parcel drift is still refused by S3 and S5 (similarity 0.45
# against 0.7): behaviour phase 1 preserves, F1 phase 2's question. Each is a
# strict xfail, so the day a site starts accepting them the test says so.

SITES = {
    "S1 search guard": "search_guard",
    "S2 §8 gate": "gate",
    "S3 offer step": "offer",
    "S4 node tier-3": None,                   # needs a node; covered by the golden table
    "S5 orphan name": "orphan_name",
}
_DRIFT = "anchor-parcel drift: the 案名 starts at another parcel, similarity < 0.7 (F1 phase 2)"
_KNOWN = {("華中247", "S3 offer step"): _DRIFT, ("華中247", "S5 orphan name"): _DRIFT,
          ("吳興163-2", "S3 offer step"): _DRIFT, ("吳興163-2", "S5 orphan name"): _DRIFT}


def _tier1_params():
    for key in TIER1:
        for site, policy in SITES.items():
            if policy is None:
                continue
            marks = []
            if (key, site) in _KNOWN:
                marks.append(pytest.mark.xfail(strict=True, reason=_KNOWN[(key, site)]))
            yield pytest.param(key, site, policy, id=f"{key}-{site}", marks=marks)


@pytest.mark.parametrize("key, site, policy", list(_tier1_params()))
def test_every_site_accepts_the_cases_of_a_hand_checked_unit(key, site, policy):
    u = TIER1[key]
    unit = L.Unit(u["land_core"], tuple(u["own_parcels"]), tuple(u["own_counts"]),
                  u["anchor_name"])
    refused = [cid for cid, name in u["cases"]
               if not L.membership_verdict(name, unit, policy,
                                           searched_parcel=unit.own_parcels[0]).accept]
    assert not refused, f"{site} refuses {len(refused)} of {len(u['cases'])} cases of {key}: {refused}"
