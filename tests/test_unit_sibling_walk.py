# -*- coding: utf-8 -*-
"""unit-sibling-id-walk (docs/inspections/inspection-batchF.md F4, D3=A, D4=A).

A unit's sibling cases sit in the interior of the id stems it already holds.
`walk_unit_siblings` probes them by header and accepts a case on positive
evidence only, by the predicate the §8 gate also calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as L  # noqa: E402
from urtpe.links import DiscoveryResult  # noqa: E402

CORE = "大安區懷生段二小段16地號等8筆"
PARCELS = ["16", "17", "18"]
PID = "大安區-懷生段二小段-16地號等8筆"

SIB = "擬訂臺北市大安區懷生段二小段16地號等8筆土地都市更新事業計畫案-A區"
SIB_DRIFT = "變更臺北市大安區懷生段二小段17、16地號等8筆土地都市更新事業計畫案-B區"
SIB_COUNT = "擬訂臺北市大安區懷生段二小段17地號等12筆土地都市更新事業計畫案"
FOREIGN = "擬訂臺北市大安區懷生段四小段301地號等7筆土地都市更新事業計畫案"
NO_PARCEL = "擬訂臺北市大同區崇仁新村都市更新事業計畫案"


# ── 1.1 the predicate ─────────────────────────────────────────────────────────

class TestThePredicate:
    def test_the_fixtures_mean_what_they_say(self):
        """Guard against a vacuous test: the drift and unequal-count names must
        miss the land-core rule, or the own-parcel branch is never exercised."""
        for name in (SIB_DRIFT, SIB_COUNT):
            lc = L.extract_landcore_from_case_name(name)
            assert lc, name
            assert L.compute_landcore_similarity(CORE, lc) < 0.7, (name, lc)

    def test_a_matching_land_core_is_accepted(self):
        assert L.unit_accepts_case_name(CORE, SIB, PARCELS)
        assert L.unit_accepts_case_name(CORE, SIB, PARCELS)

    def test_an_own_parcel_in_the_own_section_with_an_equal_count_is_accepted(self):
        assert L.unit_accepts_case_name(CORE, SIB_DRIFT, PARCELS)
        assert L.unit_accepts_case_name(CORE, SIB_DRIFT, PARCELS)

    def test_an_unequal_count_is_refused_by_the_single_rule(self):
        """unit-count-rule: the walk's provisional hold-back became the rule for
        every caller; the unit never had 12 parcels, so the gate refuses too."""
        assert not L.unit_accepts_case_name(CORE, SIB_COUNT, PARCELS)

    def test_a_name_of_another_section_is_refused(self):
        assert not L.unit_accepts_case_name(CORE, FOREIGN, PARCELS)
        assert not L.unit_accepts_case_name(CORE, FOREIGN, PARCELS)

    def test_a_nameless_or_parcel_less_name_is_refused(self):
        for name in ("", "   ", NO_PARCEL):
            assert not L.unit_accepts_case_name(CORE, name, PARCELS), repr(name)
            assert not L.unit_accepts_case_name(CORE, name, PARCELS), repr(name)

    def test_no_own_parcels_leaves_the_land_core_rule_alone(self):
        assert L.unit_accepts_case_name(CORE, SIB, [])
        assert not L.unit_accepts_case_name(CORE, SIB_DRIFT, [])


# ── 1.2 the gate does not move ────────────────────────────────────────────────

def _old_city_ok(own_core, name, own_parcels):
    """The §8 gate's inline expression before the refactor, verbatim."""
    city_lc = L.extract_landcore_from_case_name(name)
    return (city_lc == own_core
            or L.compute_landcore_similarity(own_core, city_lc) >= L._link_threshold()
            or L._names_an_own_parcel_in_the_own_section(own_core, name, city_lc,
                                                         own_parcels))


def test_the_gate_keeps_every_verdict_on_the_fixtures():
    for name in (SIB, SIB_DRIFT, FOREIGN):
        got = L.verify_view_verified_ids(CORE, ["09500001"], {"09500001": name}, {},
                                         own_parcels=PARCELS)
        assert (("09500001" in got.kept)
                == _old_city_ok(CORE, name, PARCELS)), name
    # the one verdict that moves: an own-parcel name with a count the unit never had
    got = L.verify_view_verified_ids(CORE, ["09500001"], {"09500001": SIB_COUNT}, {},
                                     own_parcels=PARCELS)
    assert "09500001" not in got.kept
    # a parcel-less name stays kept on no-evidence grounds (the gate's own branch)
    got = L.verify_view_verified_ids(CORE, ["09500001"], {"09500001": NO_PARCEL}, {},
                                     own_parcels=PARCELS)
    assert "09500001" in got.kept


# (the live pair-by-pair parity moved to tests/test_unit_count_rule.py: the count
# rule newly refuses the own-parcel pairs with a count the unit never had.)


# ── 1.3 the walk ──────────────────────────────────────────────────────────────

HELD = ["09503200", "09503204", "09503208"]


def _disc(**kw):
    d = DiscoveryResult(project_id=PID, land_core=CORE, own_parcels=list(PARCELS),
                        city_case_ids=list(HELD))
    for k, v in kw.items():
        setattr(d, k, v)
    return d


class Adapters:
    """Injected header and milestone fetchers that count their requests."""

    def __init__(self, headers, fail=()):
        self.headers = headers
        self.fail = set(fail)
        self.header_calls, self.ms_calls = [], []

    def header(self, cid):
        self.header_calls.append(cid)
        if cid in self.fail:
            raise ConnectionError("boom")
        return self.headers.get(cid, {})

    def milestones(self, cid):
        self.ms_calls.append(cid)
        return {"核定日期": "2006/03/20"}


def _row(name, state="事業計畫階段─業經本府核定", d="2006/03/20"):
    return {"CASE_NAME": name, "NAME": state, "uro_chk_date": d}


def _walk(disc, adapters, **kw):
    return L.walk_unit_siblings(disc, CORE, PARCELS, fetch_header=adapters.header,
                                fetch_milestones=adapters.milestones,
                                sleep=lambda s: None, **kw)


def test_the_candidates_are_the_interior_of_each_held_stem():
    assert L.sibling_candidates(_disc()) == [f"0950320{d}" for d in (1, 2, 3, 5, 6, 7)]


def test_no_id_outside_the_held_minimum_and_maximum_is_probed():
    ad = Adapters({})
    _walk(_disc(), ad)
    assert set(ad.header_calls) == {f"0950320{d}" for d in (1, 2, 3, 5, 6, 7)}
    assert not {f"0950320{d}" for d in (0, 4, 8, 9)} & set(ad.header_calls)


def test_a_view_rejected_id_counts_as_held_for_the_stem_but_is_not_probed():
    d = _disc(city_case_ids=["09503200"], view_rejected={"09503208": {"shape": "A"}})
    cands = L.sibling_candidates(d)
    assert "09503208" not in cands and "09503204" in cands and "09503207" in cands


def test_the_kaishen_16_shape_three_siblings_join():
    ad = Adapters({"09503201": _row(SIB), "09503202": _row(SIB), "09503207": _row(SIB_DRIFT)})
    d = _disc()
    rep = _walk(d, ad)
    assert rep["added"] == ["09503201", "09503202", "09503207"]
    assert d.city_case_ids == HELD + ["09503201", "09503202", "09503207"]
    for cid in rep["added"]:
        assert cid in d.candidate_names and cid in d.case_case_names
        assert d.case_milestones[cid] == {"核定日期": "2006/03/20"}
        assert d.case_headers[cid]["NAME"] == "事業計畫階段─業經本府核定"
    assert d.case_case_names["09503207"] == SIB_DRIFT


def test_the_join_is_append_only():
    d = _disc(candidate_names={"09503200": "kept"}, case_case_names={"09503200": "kept"})
    _walk(d, Adapters({"09503201": _row(SIB)}))
    assert d.city_case_ids[:3] == HELD
    assert d.candidate_names["09503200"] == "kept"


def test_a_foreign_id_is_refused_and_remembered():
    d = _disc()
    rep = _walk(d, Adapters({"09503205": _row(FOREIGN)}))
    assert rep["added"] == [] and rep["other_unit"] == ["09503205"]
    assert d.sibling_probed["09503205"] == "other_unit"
    assert "09503205" not in d.city_case_ids


def test_an_empty_header_is_recorded_as_no_case():
    d = _disc()
    _walk(d, Adapters({}))
    assert set(d.sibling_probed.values()) == {"none"}
    assert set(d.sibling_probed) == {f"0950320{x}" for x in (1, 2, 3, 5, 6, 7)}


def test_a_parcel_less_name_is_refused():
    d = _disc()
    rep = _walk(d, Adapters({"09503206": _row(NO_PARCEL)}))
    assert "09503206" not in rep["added"]
    assert d.sibling_probed["09503206"] == "other_unit"


def test_an_unequal_count_own_parcel_name_is_held_back():
    d = _disc()
    rep = _walk(d, Adapters({"09503203": _row(SIB_COUNT)}))
    assert "09503203" not in rep["added"]
    assert d.sibling_probed["09503203"] == "other_unit"


def test_an_id_held_by_another_project_is_skipped_without_a_request():
    ad = Adapters({"09503202": _row(SIB)})
    d = _disc()
    rep = _walk(d, ad, held_elsewhere={"09503202"})
    assert "09503202" not in ad.header_calls
    assert "09503202" not in d.city_case_ids
    assert rep["skipped_held_elsewhere"] == ["09503202"]


def test_a_second_run_issues_zero_requests():
    ad = Adapters({"09503201": _row(SIB), "09503205": _row(FOREIGN)})
    d = _disc()
    _walk(d, ad)
    again = Adapters({"09503201": _row(SIB), "09503205": _row(FOREIGN)})
    rep = _walk(d, again)
    assert again.header_calls == [] and rep["requests"] == 0 and rep["added"] == []


def test_an_adapter_failure_is_not_recorded_and_is_retried():
    d = _disc()
    rep = _walk(d, Adapters({}, fail={"09503203"}))
    assert rep["errors"] == ["09503203"]
    assert "09503203" not in d.sibling_probed
    ok = Adapters({"09503203": _row(SIB)})
    _walk(d, ok)
    assert "09503203" in ok.header_calls and "09503203" in d.city_case_ids


def test_the_request_cap_stops_the_walk_and_says_so():
    ad = Adapters({})
    d = _disc()
    rep = _walk(d, ad, max_requests=2)
    assert len(ad.header_calls) == 2 and rep["requests"] == 2
    assert rep["capped"] is True
    assert len(d.sibling_probed) == 2          # the rest is left for the next run


def test_a_probe_with_no_name_in_the_milestone_step_does_not_join_nameless():
    d = _disc()
    rep = _walk(d, Adapters({"09503201": {"NAME": "x", "uro_chk_date": "2006/03/20"}}))
    assert "09503201" not in rep["added"] and d.sibling_probed["09503201"] == "none"


# ── 1.4 the cache field ───────────────────────────────────────────────────────

def test_sibling_probed_round_trips(tmp_path):
    r = DiscoveryResult(project_id="甲", land_core="x")
    assert r.sibling_probed == {}
    r.sibling_probed = {"09503205": "other_unit", "09503203": "none"}
    L.save_project_cache(tmp_path, "甲", r)
    assert L.load_project_cache(tmp_path, "甲").sibling_probed == r.sibling_probed


def test_a_cache_written_before_the_field_loads_with_an_empty_record(tmp_path):
    d = tmp_path / "乙"
    d.mkdir()
    (d / "result.json").write_text(json.dumps({"project_id": "乙", "land_core": "x"},
                                              ensure_ascii=False), encoding="utf-8")
    assert L.load_project_cache(tmp_path, "乙").sibling_probed == {}


# ── 4.3 the live pins (after the 2026-11-15 run and re-emit) ──────────────────

SEVEN = {
    "大安區-懷生段二小段-16地號等6筆": {"09503201", "09503202", "09503207"},
    "文山區-萬隆段二小段-463地號等5筆": {"09205141", "09205142"},
    "士林區-百齡段五小段-342地號等19筆": {"10405264"},
    "萬華區-雙園段二小段-505地號等77筆": {"09610232"},
}


def _payload_projects():
    return json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))["projects"]


def test_the_seven_siblings_are_held_by_their_projects_on_the_live_payload():
    by_id = {p["project_id"]: p for p in _payload_projects()}
    for pid, ids in SEVEN.items():
        taipei = set((by_id[pid].get("links") or {}).get("taipei") or [])
        assert ids <= taipei, (pid, sorted(ids - taipei))


def test_the_walk_s_held_back_id_stays_out_until_f7():
    """長春559-5's 09012312 passes the own-parcel rule with counts 69 against 80;
    the walk refuses it and F7 decides it. A change that admits it must say so."""
    by_id = {p["project_id"]: p for p in _payload_projects()}
    taipei = set((by_id["中山區-長春段二小段-559-5地號等80筆"].get("links") or {}).get("taipei") or [])
    assert "09012312" not in taipei, "09012312 joined: F7's count rule must have decided it"


def test_no_id_is_both_held_and_recorded_as_probed_and_none_is_held_twice_by_the_walk():
    cache = ROOT / "data" / ".link_cache"
    if not cache.is_dir():
        pytest.skip("no live caches")
    payload_ids = {p["project_id"] for p in _payload_projects()}
    holders = {}
    for rf in sorted(cache.glob("*/result.json")):
        c = json.loads(rf.read_text(encoding="utf-8"))
        if c.get("project_id") not in payload_ids:
            continue
        held = set(c.get("city_case_ids") or [])
        both = held & set(c.get("sibling_probed") or {})
        assert not both, (c["project_id"], sorted(both))
        for cid in held:
            holders.setdefault(cid, set()).add(c["project_id"])
    walked = set().union(*SEVEN.values())
    twice = {cid: sorted(holders[cid]) for cid in walked if len(holders.get(cid, ())) != 1}
    assert not twice, f"walk-added ids held by other than one project: {twice}"
