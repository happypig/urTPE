# -*- coding: utf-8 -*-
"""section8-gate-anchor-parcel-drift: the §8 gate must keep a case of the
unit's own parcels although its 案名 starts at another parcel.

The measured case (2026-11-15): 萬華區-華中段一小段-247地號等26筆. The 地號 cell
lists 26 parcels and starts at 247; the 案名 names 201-2、352. The project's
land core keys on 247, the city's case names key on 201-2, and the two score
0.45 < LINK_THRESHOLD 0.7. The city's parcel search admits five of the seven
cases by the parcel guard (own_parcels); the two ids the national view page
names (09305081, 09407302) went through the §8 gate and were rejected shape A.
The same gate, run on the five held ids, rejects them too — only the route
decided which ids it saw.

The rule under test: a view-named id whose land core does not match is KEPT
when its city name declares the same district+section as the project AND one
of the unit's own parcels. The section test is needed because the search gets
it from its query; the gate has none. 09608220 (犁和段一小段-102) is the
refusal that proves it: same section as its project, names parcel 165, which
is not the unit's.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as links_mod  # noqa: E402
from urtpe.links import (  # noqa: E402
    DiscoveryResult, attach_links_to_projects, load_project_cache,
    refresh_project, save_project_cache, verify_view_verified_ids,
)
from urtpe.models import Project, make_record  # noqa: E402

PAYLOAD = ROOT / "viewer" / "projects.data.js"

# ── the 華中247 fixture ───────────────────────────────────────────────────────

HZ_PID = "萬華區-華中段一小段-247地號等26筆"
HZ_CORE = "萬華區華中段一小段247地號等26筆"
HZ_PARCELS = ["247", "248", "201-2", "201-3", "202", "240", "241", "241-1", "241-2",
              "242", "243", "244", "245", "246", "352", "353", "354", "355", "362",
              "362-1", "363", "364", "365", "366-11", "366-12", "366-13"]
NAME_81 = "擬訂臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案-A區"
NAME_302 = "變更臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案-B區"
HZ_HELD = ["09305080", "09305082", "09407301", "09407303", "09407304"]


def _decide(own_core, ids_names, own_parcels=None, labels=None):
    kw = {} if own_parcels is None else {"own_parcels": own_parcels}
    return verify_view_verified_ids(
        own_land_core=own_core,
        ids=list(ids_names),
        city_names=dict(ids_names),
        labels=dict(labels if labels is not None else ids_names),
        **kw,
    )


# ── 1.1 the gate ──────────────────────────────────────────────────────────────

class TestTheGate:
    def test_a_case_naming_another_own_parcel_is_kept(self):
        """華中247: land core 201-2 vs 247 scores 0.45, the name carries the
        unit's own parcel 201-2 in the unit's own section."""
        out = _decide(HZ_CORE, {"09305081": NAME_81, "09407302": NAME_302},
                      own_parcels=HZ_PARCELS)
        assert out.kept == ["09305081", "09407302"]
        assert out.rejected == {}

    def test_a_same_section_case_naming_none_of_the_unit_s_parcels_is_rejected(self):
        """09608220 on 信義犁和一小段-102: the same 段小段, parcel 165 — a
        different unit. The section test alone would admit it."""
        name = "擬訂臺北市信義區犁和段一小段165地號等20筆土地都市更新事業計畫案"
        out = _decide("信義區犁和段一小段102地號等3筆", {"09608220": name},
                      own_parcels=["102", "103", "104"])
        assert out.kept == []
        assert out.rejected["09608220"]["shape"] == "A"
        assert out.rejected["09608220"]["reason"] == (
            "label and city name name another project (shape A)")

    def test_the_same_parcel_in_another_district_is_rejected(self):
        """市府220-2's shape: the parcel number matches, the district does not
        (the section text is compared whole, district included)."""
        name = "擬訂臺北市中正區市府段二小段220-2地號等54筆土地都市更新事業計畫案"
        out = _decide("大同區市府段二小段220-2地號等54筆", {"09609301": name},
                      own_parcels=["220-2", "220-3", "221"])
        assert out.kept == []
        assert "09609301" in out.rejected

    def test_the_same_parcel_in_another_section_is_rejected(self):
        name = "擬訂臺北市大同區承德段二小段220-2地號等54筆土地都市更新事業計畫案"
        out = _decide("大同區市府段二小段220-2地號等54筆", {"09609301": name},
                      own_parcels=["220-2", "220-3", "221"])
        assert "09609301" in out.rejected

    def test_without_a_parcel_list_the_land_core_rule_alone_decides(self):
        """No evidence of the unit's parcels: the old result, id for id."""
        out = _decide(HZ_CORE, {"09305081": NAME_81, "09407302": NAME_302})
        assert out.kept == []
        assert set(out.rejected) == {"09305081", "09407302"}
        out = _decide(HZ_CORE, {"09305081": NAME_81}, own_parcels=[])
        assert "09305081" in out.rejected

    def test_a_parcel_less_name_still_does_not_reject(self):
        name = "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案"
        out = _decide("萬華區崇仁新村1地號等2筆", {"09112120": name},
                      own_parcels=["1", "2"])
        assert out.kept == ["09112120"]

    @pytest.mark.parametrize("own, name_parcel", [
        (["220"], "2201地號等3筆"),          # 220 must not match inside 2201
        (["220-3"], "220-31地號等3筆"),      # nor 220-3 inside 220-31
        (["22"], "220地號等3筆"),            # nor 22 inside 220
    ])
    def test_the_parcel_token_boundary(self, own, name_parcel):
        name = f"擬訂臺北市大同區市府段二小段{name_parcel}土地都市更新事業計畫案"
        out = _decide("大同區市府段二小段999地號等3筆", {"09600001": name},
                      own_parcels=own)
        assert "09600001" in out.rejected


# ── 1.2 the re-decision of a recorded rejection ───────────────────────────────

def _view_html(ids_names):
    anchors = "".join(
        f'<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id={cid}" '
        f'title="t">{name}</a>' for cid, name in ids_names.items())
    return (f"<html><body><div class='data_table_box'><table class='type1_table'>"
            f"<tr><td>{anchors}</td></tr></table></div></body></html>")


def _hz_cache(tmp_path, *, rejected, names, own_parcels=None, verified=None,
              city_ids=None):
    d = tmp_path / HZ_PID
    d.mkdir(parents=True)
    payload = {
        "project_id": HZ_PID, "land_core": HZ_CORE, "status": "resolved",
        "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/207",
        "twur_view_id": "207",
        "twur_name": "擬訂臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案",
        "city_case_ids": list(city_ids if city_ids is not None else HZ_HELD),
        "case_milestones": {c: {"核定日期": "2014/04/25"} for c in HZ_HELD},
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {}, "case_schedules": {},
        "case_case_names": dict(names),
        "view_verified_case_ids": list(verified or []),
        "view_rejected": rejected, "error": "",
    }
    if own_parcels is not None:
        payload["own_parcels"] = list(own_parcels)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _shape_a():
    return {"reason": "label and city name name another project (shape A)",
            "shape": "A", "label_ok": False, "city_ok": False}


@pytest.fixture
def city(monkeypatch):
    """No network: the milestone, header and view-page fetchers are stubs."""
    calls = {"milestones": [], "headers": []}
    names = {"09305081": NAME_81, "09407302": NAME_302}

    def milestones(cid):
        calls["milestones"].append(cid)
        return {"核定日期": "2014/04/25"}

    def header(cid):
        calls["headers"].append(cid)
        return {"NAME": "事業計畫階段─業經本府核定", "CASE_NAME": names.get(cid, "")}

    monkeypatch.setattr(links_mod, "fetch_taipei_milestones_api", milestones)
    monkeypatch.setattr(links_mod, "fetch_taipei_case_header_api", header)
    calls["names"] = names
    return calls


class TestTheRedecision:
    def _setup(self, tmp_path, monkeypatch, *, rejected, names, view_names,
               own_parcels=HZ_PARCELS):
        _hz_cache(tmp_path, rejected=rejected, names=names, own_parcels=own_parcels)
        monkeypatch.setattr(links_mod, "fetch_view_page",
                            lambda vid, cache_dir=None, fresh=False: _view_html(view_names))

    def test_a_rejection_from_the_old_rule_is_lifted(self, tmp_path, monkeypatch, city):
        both = {"09305081": NAME_81, "09407302": NAME_302}
        self._setup(tmp_path, monkeypatch,
                    rejected={c: _shape_a() for c in both}, names=both, view_names=both)
        report = refresh_project(tmp_path, HZ_PID)
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert saved["view_rejected"] == {}
        assert set(saved["view_verified_case_ids"]) >= {"09305081", "09407302"}
        assert {"09305081", "09407302"} <= set(saved["city_case_ids"])
        assert {"09305081", "09407302"} <= set(saved["case_milestones"])
        assert sorted(report["view_rejection_lifted"]) == ["09305081", "09407302"]

    def test_a_rejection_the_current_rule_still_holds_is_not_refetched(
            self, tmp_path, monkeypatch, city):
        foreign = "擬訂臺北市中山區吉林段四小段603地號等40筆土地都市更新事業計畫案"
        self._setup(tmp_path, monkeypatch,
                    rejected={"09511211": {**_shape_a(), "shape": "B",
                                           "reason": "label is right, id is wrong (shape B)"}},
                    names={"09511211": foreign}, view_names={"09511211": foreign})
        report = refresh_project(tmp_path, HZ_PID)
        assert report["error"] == "", report["error"]
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert "09511211" in saved["view_rejected"]
        assert "09511211" not in city["milestones"]
        assert report.get("view_rejection_lifted", []) == []

    def test_a_rejection_with_no_held_city_name_stands(self, tmp_path, monkeypatch, city):
        self._setup(tmp_path, monkeypatch,
                    rejected={"09305081": _shape_a()}, names={},
                    view_names={"09305081": NAME_81})
        # the header fetch also returns no name for this id
        city["names"].pop("09305081", None)
        report = refresh_project(tmp_path, HZ_PID)
        assert report["error"] == "", report["error"]
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert "09305081" in saved["view_rejected"]
        assert "09305081" not in saved["view_verified_case_ids"]

    def test_a_second_run_lifts_nothing(self, tmp_path, monkeypatch, city):
        both = {"09305081": NAME_81, "09407302": NAME_302}
        self._setup(tmp_path, monkeypatch,
                    rejected={c: _shape_a() for c in both}, names=both, view_names=both)
        refresh_project(tmp_path, HZ_PID)
        report = refresh_project(tmp_path, HZ_PID)
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert report.get("view_rejection_lifted", []) == []
        assert saved["view_rejected"] == {}
        assert set(saved["view_verified_case_ids"]) >= {"09305081", "09407302"}


# ── 1.3 the cache carries the unit's own parcels ──────────────────────────────

class TestOwnParcelsInTheCache:
    def test_a_result_defaults_to_no_parcels_and_round_trips(self, tmp_path):
        r = DiscoveryResult(project_id="甲", land_core="萬華區華中段一小段247地號等26筆")
        assert r.own_parcels == []
        r.own_parcels = ["247", "201-2"]
        save_project_cache(tmp_path, "甲", r)
        assert load_project_cache(tmp_path, "甲").own_parcels == ["247", "201-2"]

    def test_a_cache_without_the_field_loads_with_an_empty_list(self, tmp_path):
        d = tmp_path / "乙"
        d.mkdir()
        (d / "result.json").write_text(json.dumps(
            {"project_id": "乙", "land_core": "中山區吉林段四小段603地號等40筆"},
            ensure_ascii=False), encoding="utf-8")
        assert load_project_cache(tmp_path, "乙").own_parcels == []

    def test_the_key_s_parcel_list_overwrites_the_cache_field(self, tmp_path, monkeypatch, city):
        _hz_cache(tmp_path, rejected={}, names={}, own_parcels=["247"])
        monkeypatch.setattr(links_mod, "fetch_view_page",
                            lambda vid, cache_dir=None, fresh=False: _view_html({}))
        key = ("華中段一小段", "247", "", HZ_PARCELS, "")
        refresh_project(tmp_path, HZ_PID, search_key=key)
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert saved["own_parcels"] == HZ_PARCELS

    def test_the_gate_reads_the_cache_when_no_key_carries_parcels(
            self, tmp_path, monkeypatch, city):
        """A call with no search_key gives the same answer as one with it —
        two of six callers pass no key at all."""
        both = {"09305081": NAME_81, "09407302": NAME_302}
        for label, kwargs in (("nokey", {}),
                              ("threepart", {"search_key": ("華中段一小段", "247", "")})):
            root = tmp_path / label
            root.mkdir()
            _hz_cache(root, rejected={}, names=both, own_parcels=HZ_PARCELS,
                      verified=list(both), city_ids=HZ_HELD + list(both))
            monkeypatch.setattr(links_mod, "fetch_view_page",
                                lambda vid, cache_dir=None, fresh=False: _view_html(both))
            report = refresh_project(root, HZ_PID, **kwargs)
            assert report["error"] == "", (label, report["error"])
            saved = json.loads((root / HZ_PID / "result.json").read_text(encoding="utf-8"))
            assert set(saved["view_verified_case_ids"]) >= set(both), label
            assert saved["view_rejected"] == {}, label

    def test_a_cache_with_no_parcels_behaves_as_before(self, tmp_path, monkeypatch, city):
        both = {"09305081": NAME_81}
        _hz_cache(tmp_path, rejected={}, names=both, verified=list(both),
                  city_ids=HZ_HELD + list(both))
        monkeypatch.setattr(links_mod, "fetch_view_page",
                            lambda vid, cache_dir=None, fresh=False: _view_html(both))
        refresh_project(tmp_path, HZ_PID)
        saved = json.loads((tmp_path / HZ_PID / "result.json").read_text(encoding="utf-8"))
        assert "09305081" in saved["view_rejected"]

    def test_discovery_takes_the_parcels_from_the_anchor_record(self):
        """A cleansed record carries the 地號 cell's parcels (make_record builds a
        bare record with none, so the fixture goes through cleanse)."""
        from urtpe.cleanse import cleanse
        from urtpe.models import RawRecord
        raw = RawRecord(1131, "103/4/25", "萬華區",
                        NAME_81.replace("-A區", ""),
                        "臺北市萬華區華中段一小段247、248、201-2、352地號等4筆土地",
                        "某建設", "某規劃")
        rec = cleanse(raw)
        assert links_mod.own_parcels_of(rec) == ["247", "248", "201-2", "352"]

    def test_a_record_without_parcels_gives_an_empty_list(self):
        rec = make_record(1, "103/4/25", "萬華區", "x", "y", "某", "某")
        assert links_mod.own_parcels_of(rec) == []


# ── 1.4 the anchoring of a re-accepted id ─────────────────────────────────────

def test_a_drifted_case_anchors_on_the_node_of_its_date():
    """09305081 (擬訂 A區, 核定 2014-04-25) shares the node of 09305082."""
    rec = make_record(1131, "103/4/25", "萬華區", NAME_81.replace("-A區", ""),
                      "臺北市萬華區華中段一小段247、201-2、352地號等26筆土地",
                      "某建設", "某規劃")
    project = Project(project_id=HZ_PID, anchor_recno=1131, members=[rec])
    disc = {HZ_PID: {
        "twur": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/207",
        "taipei": ["09305082", "09305081"],
        "milestones_national": {}, "milestones_taipei": {},
        "case_milestones": {"09305082": {"核定日期": "2014/04/25"},
                            "09305081": {"核定日期": "2014/04/25"}},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {"09305081": NAME_81, "09305082": NAME_81.replace("A區", "B區")},
        "candidate_names": {}, "case_schedules": {},
        "view_verified_case_ids": ["09305081"],
    }}
    attach_links_to_projects([project], disc)
    assert project.links["view_verified_case_ids"] == ["09305081"]
    assert set(project.links["taipei"]) == {"09305081", "09305082"}


# ── 1.5 the live pins ─────────────────────────────────────────────────────────

def _payload():
    text = PAYLOAD.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def test_the_view_rejected_population_on_the_live_payload():
    """Before the correction: 11 ids in 10 projects. After: 8 ids in 8
    projects — 7 foreign ids and 市府220-2 (a wrong district in its cache's
    land core, a separate defect). The three drifted ids returned."""
    ids = {}
    for p in _payload()["projects"]:
        vr = (p.get("links") or {}).get("view_rejected") or {}
        if vr:
            ids[p["project_id"]] = set(vr)
    n_ids = sum(len(v) for v in ids.values())
    assert (n_ids, len(ids)) == (8, 8), (
        f"the rejected population moved: {n_ids} ids in {len(ids)} projects "
        "(8 in 8 after the 2026-11-15 correction; 11 in 10 before it)")
    assert "09609301" in ids.get("大同區-市府段二小段-220-2地號等54筆", set())
    for returned in ("09305081", "09407302", "09102220"):
        assert not any(returned in v for v in ids.values()), returned


def test_the_hua_zhong_247_project_holds_all_seven_cases():
    proj = next(p for p in _payload()["projects"] if p["project_id"] == HZ_PID)
    taipei = set((proj.get("links") or {}).get("taipei") or [])
    assert taipei == set(HZ_HELD) | {"09305081", "09407302"}, sorted(taipei)
    assert (proj["links"].get("view_rejected") or {}) == {}


def test_the_two_hua_zhong_nodes_each_carry_both_of_their_cases():
    """The node of 2014-04-25 holds 09305081 (A區) and 09305082 (B區); the
    node of 2015-10-02 holds 09407301 (A區) and 09407302 (B區)."""
    proj = next(p for p in _payload()["projects"] if p["project_id"] == HZ_PID)
    by_date = {}
    for n in proj["nodes"]:
        if n.get("date") in ("2014-04-25", "2015-10-02"):
            by_date[n["date"]] = set((n.get("links") or {}).get("taipei") or [])
    assert by_date.get("2014-04-25") == {"09305081", "09305082"}, by_date
    assert by_date.get("2015-10-02") == {"09407301", "09407302"}, by_date
