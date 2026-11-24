# -*- coding: utf-8 -*-
"""d11-search-guard-count-rule: S1's own-parcel form adopts the count rule.

The user decided D11 = A on 2026-11-15 (docs/inspections/inspection-batchF.md,
D11; docs/inspections/optimization.md Part II). The guard's own-parcel form
(a name declaring any of the unit's own parcels) now also requires a count the
unit declared at some approval — the same count rule the §8 gate has used since
F7. The exact and stem forms keep their behaviour; the stem form's
cross-listings await F8 option C.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from urtpe import links as L  # noqa: E402

CORE = "文山區華興段一小段8地號等4筆"
OWN = ("8", "9", "18-1")
COUNTS = (4, 13)
NAME = "擬訂臺北市文山區華興段一小段{p}土地都市更新事業計畫案"


def _guard(name, parcel="8", own=OWN, counts=COUNTS, core=CORE, anchor=""):
    return L.membership_verdict(
        name, L.Unit(core, own, counts, anchor), "search_guard",
        searched_parcel=parcel)


# ── the policy's new own-parcel behaviour ────────────────────────────────────

class TestTheOwnParcelFormAdoptsTheCountRule:
    def test_a_count_failing_own_parcel_name_reads_count_refused(self):
        # 18-1 is an own parcel; the count 9 is none of 4, 13, or the core's 4
        v = _guard(NAME.format(p="18-1地號等9筆"))
        assert not v.accept and v.reason == "count_refused"

    def test_a_count_passing_own_parcel_name_still_reads_own_parcel(self):
        v = _guard(NAME.format(p="18-1地號等13筆"))
        assert v.accept and v.reason == "own_parcel"

    def test_a_count_matching_only_the_land_core_count_passes(self):
        # 4 is the core's count, absent from own_counts in this call
        v = _guard(NAME.format(p="18-1地號等4筆"), counts=(13,))
        assert v.accept and v.reason == "own_parcel"

    def test_the_exact_form_needs_no_count(self):
        # the searched parcel itself, with a count the unit never declared
        v = _guard(NAME.format(p="8地號等99筆"), parcel="8")
        assert v.accept and v.reason == "exact"

    def test_the_stem_form_is_unchanged_by_the_count(self):
        # stem hit, count the unit never declared — F8-C's territory, untouched
        v = _guard(NAME.format(p="18地號等9筆"), parcel="18-1", own=(), counts=COUNTS)
        assert v.accept and v.reason == "stem"
        # stem hit with a passing count — same verdict
        v = _guard(NAME.format(p="18地號等4筆"), parcel="18-1", own=(), counts=COUNTS)
        assert v.accept and v.reason == "stem"

    def test_a_parcel_less_corroborated_name_is_unchanged(self):
        anchor = "擬訂臺北市大同區崇仁新村都市更新事業計畫案"
        v = _guard("變更臺北市大同區崇仁新村都市更新事業計畫案", parcel="711-3",
                   own=(), counts=(), core="", anchor=anchor)
        assert v.accept and v.reason == "corroborated_area"

    def test_no_counts_falls_back_to_the_land_core_count_alone(self):
        # the narrower rule, named like the gate's
        v = _guard(NAME.format(p="18-1地號等4筆"), counts=())
        assert v.accept and v.reason == "own_parcel"
        v = _guard(NAME.format(p="18-1地號等13筆"), counts=())
        assert not v.accept and v.reason == "count_refused"

    def test_a_foreign_name_still_reads_dropped(self):
        v = _guard(NAME.format(p="301地號等7筆"))
        assert not v.accept and v.reason == "dropped"


# ── the search adapter carries counts ────────────────────────────────────────

def _post(entries):
    import urtpe.links as links
    return lambda url, params, max_retries=3: json.dumps(entries)


def _entry(cid, name):
    return {"details": f"r_progress_detail.aspx?case_id={cid}",
            "case_name": name, "schedule": "已核准"}


class TestTheSearchAdapterCarriesCounts:
    def test_a_count_failing_own_parcel_result_is_dropped_and_named(self, monkeypatch):
        monkeypatch.setattr(L, "_post_taipei_api", _post([
            _entry("09810291", "擬訂臺北市文山區華興段一小段18-1地號等9筆土地都市更新事業概要案"),
            _entry("09708111", "擬訂臺北市文山區華興段一小段18-1地號等13筆土地都市更新事業計畫案"),
        ]))
        dropped: dict[str, str] = {}
        kept = L.search_taipei_cases_api("華興段一小段", "8", dropped_out=dropped,
                                         own_parcels=["8", "9", "18-1"],
                                         own_counts=[4, 13], land_core=CORE)
        assert [e["case_id"] for e in kept] == ["09708111"]
        assert set(dropped) == {"09810291"}

    def test_the_exact_form_is_kept_without_a_count(self, monkeypatch):
        monkeypatch.setattr(L, "_post_taipei_api", _post([
            _entry("10212211", "擬訂臺北市文山區華興段一小段8地號等99筆土地都市更新事業計畫案"),
        ]))
        kept = L.search_taipei_cases_api("華興段一小段", "8", own_parcels=["8"],
                                         own_counts=[4], land_core=CORE)
        assert [e["case_id"] for e in kept] == ["10212211"]

    def test_the_stem_form_is_kept_without_a_count(self, monkeypatch):
        monkeypatch.setattr(L, "_post_taipei_api", _post([
            _entry("10908271", "擬訂臺北市文山區華興段一小段18地號等9筆土地都市更新事業計畫案"),
        ]))
        kept = L.search_taipei_cases_api("華興段一小段", "18-1", own_parcels=["18-1"],
                                         own_counts=[4], land_core=CORE)
        assert [e["case_id"] for e in kept] == ["10908271"]

    def test_no_counts_falls_back_to_the_land_core_count(self, monkeypatch):
        monkeypatch.setattr(L, "_post_taipei_api", _post([
            _entry("09708111", "擬訂臺北市文山區華興段一小段18-1地號等4筆土地都市更新事業計畫案"),
        ]))
        kept = L.search_taipei_cases_api("華興段一小段", "8", own_parcels=["8", "18-1"],
                                         own_counts=None, land_core=CORE)
        assert [e["case_id"] for e in kept] == ["09708111"]


# ── the production callers pass the counts ──────────────────────────────────

def _members():
    from urtpe.cleanse import cleanse
    from urtpe.models import RawRecord
    return [
        cleanse(RawRecord(1, "102/7/5", "文山區",
                          "擬訂臺北市文山區華興段一小段8地號等13筆土地都市更新事業計畫案",
                          "臺北市文山區華興段一小段8、9、18-1地號等13筆土地", "某", "某")),
        cleanse(RawRecord(2, "113/7/5", "文山區",
                          "變更臺北市文山區華興段一小段8地號等4筆(原13筆)土地都市更新事業計畫案",
                          "臺北市文山區華興段一小段8、9、18-1地號等4筆(原13筆)土地", "某", "某")),
    ]


def _project():
    return L.Project(project_id="文山區-華興段一小段-8地號等4筆", anchor_recno=2,
                     members=_members())


class TestTheCallersPassTheCounts:
    def test_discovery_passes_counts_and_core(self, tmp_path, monkeypatch):
        seen = {}

        def fake_search(section, parcel, dropped_out=None, anchor_name="",
                        extra_sections=None, own_parcels=None, own_counts=None,
                        land_core=""):
            seen.update(own_parcels=own_parcels, own_counts=own_counts,
                        land_core=land_core)
            return []

        monkeypatch.setattr(L, "search_taipei_cases_api", fake_search)
        monkeypatch.setattr(L, "_post_taipei_api", lambda *a, **k: "[]")
        p = _project()
        L.discover_project_links(p, tmp_path, fresh=True, delay=0)
        assert seen["own_counts"] == [4, 13]
        assert seen["land_core"] == CORE

    def test_refresh_passes_the_cached_counts_and_the_healed_core(self, tmp_path,
                                                                  monkeypatch):
        seen = {}

        def fake_search(section, parcel, dropped_out=None, anchor_name="",
                        extra_sections=None, own_parcels=None, own_counts=None,
                        land_core=""):
            seen.update(own_parcels=own_parcels, own_counts=own_counts,
                        land_core=land_core)
            return []

        monkeypatch.setattr(L, "search_taipei_cases_api", fake_search)
        monkeypatch.setattr(L, "fetch_taipei_milestones_api", lambda cid: {})
        monkeypatch.setattr(L, "fetch_taipei_case_header_api",
                            lambda cid: {"CASE_NAME": "x"})
        monkeypatch.setattr(L, "fetch_taipei_implementation_api", lambda *a, **k: {})
        monkeypatch.setattr(L, "fetch_taipei_rewards_api", lambda *a, **k: {})
        monkeypatch.setattr(L, "fetch_taipei_168_list_api", lambda: [])
        pid = "文山區-華興段一小段-8地號等4筆"
        d = tmp_path / pid
        d.mkdir(parents=True)
        (d / "result.json").write_text(json.dumps({
            "project_id": pid, "land_core": "文山區華興段一小段8地號等9筆",
            "own_parcels": ["8", "18-1"], "own_counts": [4, 13],
            "city_case_ids": ["09902263"], "case_milestones": {"09902263": {}},
            "search_rejected": {}, "candidate_names": {}, "case_case_names": {},
            "view_verified_case_ids": [], "view_rejected": {},
        }, ensure_ascii=False), encoding="utf-8")
        L.refresh_project(tmp_path, pid, fetch=lambda cid: {},
                          search=fake_search,
                          search_key=("華興段一小段", "8", "擬訂臺北市文山區華興段"
                                      "一小段8地號等4筆土地都市更新事業計畫案"))
        # the healed core: the project id spells 4筆, the cache said 9筆
        assert seen["land_core"] == CORE
        assert seen["own_counts"] == [4, 13]


# ── the frozen 62-pair pin, reinterpreted ────────────────────────────────────

S1_PAIRS = json.loads((ROOT / "tests" / "fixtures" / "s1_accepts_count_rule_refuses.json")
                      .read_text(encoding="utf-8"))["pairs"]


def _names_from_cache(c, cid):
    for key in ("candidate_names", "search_rejected", "case_case_names"):
        v = (c.get(key) or {}).get(cid)
        if isinstance(v, str) and v:
            return v
    return ""


class TestTheFrozenPinReinterpreted:
    def test_the_fixture_holds_62_pairs_and_their_statuses(self):
        assert len(S1_PAIRS) == 62
        statuses = {s for _, _, s in S1_PAIRS}
        assert statuses == {"held_none", "held_here", "held_other"}
        assert sum(1 for _, _, s in S1_PAIRS if s == "held_none") == 46

    def test_after_d11_the_guard_refuses_54_and_admits_the_8_stem_pairs(self):
        cache_root = ROOT / "data" / ".link_cache"
        refused, admitted = [], []
        for pid, cid, _st in S1_PAIRS:
            rf = cache_root / pid / "result.json"
            if not rf.is_file():
                continue
            c = json.loads(rf.read_text(encoding="utf-8"))
            name = _names_from_cache(c, cid)
            core, own = c.get("land_core") or "", tuple(c.get("own_parcels") or [])
            v = L.membership_verdict(name, L.Unit(core, own,
                                                  tuple(c.get("own_counts") or ()),
                                                  ""), "search_guard",
                                     searched_parcel=own[0])
            rule = L._parcel_rule(name, own[0], own)
            (refused if not v.accept else admitted).append((pid, cid, rule))
        assert len(refused) == 54, len(refused)
        assert len(admitted) == 8, admitted
        assert {r for _, _, r in admitted} == {"stem"}, admitted
