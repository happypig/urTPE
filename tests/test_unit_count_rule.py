# -*- coding: utf-8 -*-
"""unit-count-rule (docs/inspections/inspection-batchF.md F7 addendum, D1 and D2).

One declared-count rule for the §8 gate, the sibling walk and the admission of
held-by-no-project pairs: a case name passes the own-parcel form when its
declared count (`等N筆`), or one of its `原N筆`, equals the unit's count at ANY
approval of the unit. A matching land core needs no count test.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from urtpe import links as L  # noqa: E402
from urtpe.cleanse import cleanse  # noqa: E402
from urtpe.links import DiscoveryResult  # noqa: E402
from urtpe.models import Project, RawRecord  # noqa: E402

CORE = "文山區華興段一小段8地號等4筆"
PARCELS = ["8", "9", "10", "18-1", "19-1"]
COUNTS = [4, 13]

N13 = "擬訂臺北市文山區華興段一小段18-1地號等13筆土地都市更新事業計畫案"      # an earlier approval's count
N4 = "變更臺北市文山區華興段一小段18-1地號等4筆土地都市更新事業計畫案"        # the unit's own count
N9 = "擬訂臺北市文山區華興段一小段18-1地號等9筆土地都市更新事業計畫案"        # a count the unit never had
NORIG = "變更臺北市文山區華興段一小段18-1地號等15筆(原13筆)土地都市更新事業計畫案"  # 原N筆 is an earlier count
NMATCH = "擬訂臺北市文山區華興段一小段8地號等5筆土地都市更新事業計畫案"          # land core matches at 0.7


# ── 1.1 the predicate's truth table ───────────────────────────────────────────

class TestTheRule:
    def test_the_fixtures_exercise_the_own_parcel_branch(self):
        """Guard against a vacuous test: these names must miss the land-core rule."""
        for name in (N13, N4, N9, NORIG):
            lc = L.extract_landcore_from_case_name(name)
            assert lc and L.compute_landcore_similarity(CORE, lc) < 0.7, (name, lc)
        lc = L.extract_landcore_from_case_name(NMATCH)
        assert L.compute_landcore_similarity(CORE, lc) >= 0.7

    def test_an_equal_count_passes(self):
        assert L.unit_accepts_case_name(CORE, N4, PARCELS, COUNTS)

    def test_a_count_of_an_earlier_approval_passes(self):
        assert L.unit_accepts_case_name(CORE, N13, PARCELS, COUNTS)

    def test_an_original_count_equal_to_a_unit_count_passes(self):
        assert L.unit_accepts_case_name(CORE, NORIG, PARCELS, COUNTS)

    def test_a_count_the_unit_never_had_is_refused(self):
        assert not L.unit_accepts_case_name(CORE, N9, PARCELS, COUNTS)

    def test_a_matching_land_core_needs_no_count(self):
        assert L.unit_accepts_case_name(CORE, NMATCH, PARCELS, COUNTS)
        assert L.unit_accepts_case_name(CORE, NMATCH, PARCELS)

    def test_with_no_counts_only_the_land_core_count_counts(self):
        """The narrower rule, never a silent widening."""
        assert L.unit_accepts_case_name(CORE, N4, PARCELS)
        assert L.unit_accepts_case_name(CORE, N4, PARCELS, [])
        assert not L.unit_accepts_case_name(CORE, N13, PARCELS)
        assert not L.unit_accepts_case_name(CORE, N13, PARCELS, [])

    def test_a_nameless_or_parcel_less_name_is_refused(self):
        for name in ("", "  ", "擬訂臺北市大同區崇仁新村都市更新事業計畫案"):
            assert not L.unit_accepts_case_name(CORE, name, PARCELS, COUNTS), repr(name)

    def test_the_keyword_of_the_walk_s_hold_back_is_gone(self):
        with pytest.raises(TypeError):
            L.unit_accepts_case_name(CORE, N4, PARCELS, COUNTS, require_equal_count=True)


# ── 1.2 gate parity on the live caches ───────────────────────────────────────

def _payload_counts():
    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    out = {}
    for p in doc["projects"]:
        counts = set()
        for n in p["nodes"]:
            for k in ("land_count", "orig_count"):
                if n.get(k):
                    counts.add(int(n[k]))
        out[p["project_id"]] = sorted(counts)
    return out


def _old_rule(core, name, own):
    lc = L.extract_landcore_from_case_name(name)
    return bool(lc) and (lc == core
                         or L.compute_landcore_similarity(core, lc) >= 0.7
                         or L._names_an_own_parcel_in_the_own_section(core, name, lc, own))


def _live_pairs():
    counts = _payload_counts()
    cache = ROOT / "data" / ".link_cache"
    for pid, cnt in counts.items():
        rf = cache / pid / "result.json"
        if not rf.is_file():
            continue
        c = json.loads(rf.read_text(encoding="utf-8"))
        views = set(c.get("view_verified_case_ids") or []) | set(c.get("view_rejected") or {})
        names = {}
        for key in ("candidate_names", "search_rejected", "case_case_names"):
            for cid, nm in (c.get(key) or {}).items():
                if isinstance(nm, str) and L.extract_landcore_from_case_name(nm):
                    names.setdefault(cid, nm)
        yield pid, c, cnt, views, names


def test_the_count_rule_newly_refuses_only_pairs_the_gate_never_sees():
    """Pinned set (F7 addendum): of the guard-only pairs (86 before F5's land-core
    repair; 84 after it, because 寶清51-13's two cases now match by land core),
    22 pass the rule and 62 are newly refused; the 3 that reach the gate all pass.
    A change to these numbers fails here and names the drift."""
    refused, passed, gate_visible_refused = [], [], []
    for pid, c, cnt, views, names in _live_pairs():
        core, own = c.get("land_core") or "", c.get("own_parcels") or []
        for cid, nm in names.items():
            old = _old_rule(core, nm, own)
            new = L.unit_accepts_case_name(core, nm, own, cnt)
            lc = L.extract_landcore_from_case_name(nm)
            guard_only = old and not (lc == core
                                      or L.compute_landcore_similarity(core, lc) >= 0.7)
            if old and not new:
                refused.append((pid, cid))
                if cid in views:
                    gate_visible_refused.append((pid, cid))
            elif guard_only and new:
                passed.append((pid, cid))
            assert new <= old, (pid, cid)          # the rule only narrows
    assert gate_visible_refused == [], gate_visible_refused
    assert (len(passed), len(refused)) == (22, 62), (len(passed), len(refused))


# ── 1.3 the walk uses the single rule ─────────────────────────────────────────

W_CORE = "大安區懷生段二小段16地號等8筆"
W_PARCELS = ["16", "17", "18"]
W_OLD = "擬訂臺北市大安區懷生段二小段17地號等12筆土地都市更新事業計畫案"
W_NEVER = "擬訂臺北市大安區懷生段二小段17地號等9筆土地都市更新事業計畫案"


class _Ad:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def header(self, cid):
        self.calls.append(cid)
        return self.rows.get(cid, {})

    def milestones(self, cid):
        return {"核定日期": "2006/03/20"}


def _row(name):
    return {"CASE_NAME": name, "NAME": "事業計畫階段─業經本府核定", "uro_chk_date": "2006/03/20"}


def _walk(own_counts, rows):
    d = DiscoveryResult(project_id="p", land_core=W_CORE, own_parcels=W_PARCELS,
                        own_counts=own_counts,
                        city_case_ids=["09503200", "09503204"])
    ad = _Ad(rows)
    rep = L.walk_unit_siblings(d, W_CORE, W_PARCELS, fetch_header=ad.header,
                               fetch_milestones=ad.milestones, sleep=lambda s: None)
    return d, rep


def test_the_walk_joins_a_count_of_an_earlier_approval():
    d, rep = _walk([8, 12], {"09503201": _row(W_OLD)})
    assert rep["added"] == ["09503201"]


def test_the_walk_holds_back_a_count_the_unit_never_had():
    d, rep = _walk([8, 12], {"09503201": _row(W_NEVER)})
    assert rep["added"] == [] and d.sibling_probed["09503201"] == "other_unit"


def test_the_walk_with_no_counts_holds_the_earlier_count_back():
    d, rep = _walk([], {"09503201": _row(W_OLD)})
    assert rep["added"] == []


# ── 1.4 the field and its writers ─────────────────────────────────────────────

def _project(*specs):
    members = []
    for i, (name, land) in enumerate(specs, 1):
        members.append(cleanse(RawRecord(i, "102/7/5", "文山區", name, land, "某", "某")))
    return Project(project_id="文山區-華興段一小段-8地號等4筆", anchor_recno=len(specs),
                   members=members)


HX = _project(
    ("擬訂臺北市文山區華興段一小段8地號等13筆土地都市更新事業計畫案",
     "臺北市文山區華興段一小段8、9、18-1地號等13筆土地"),
    ("變更臺北市文山區華興段一小段8地號等4筆(原13筆)土地都市更新事業計畫案",
     "臺北市文山區華興段一小段8、9、18-1地號等4筆(原13筆)土地"))


def test_own_counts_defaults_empty_and_round_trips(tmp_path):
    r = DiscoveryResult(project_id="甲", land_core="x")
    assert r.own_counts == []
    r.own_counts = [4, 13]
    L.save_project_cache(tmp_path, "甲", r)
    assert L.load_project_cache(tmp_path, "甲").own_counts == [4, 13]


def test_a_cache_written_before_the_field_loads_with_no_counts(tmp_path):
    d = tmp_path / "乙"
    d.mkdir()
    (d / "result.json").write_text(json.dumps({"project_id": "乙", "land_core": "x"},
                                              ensure_ascii=False), encoding="utf-8")
    assert L.load_project_cache(tmp_path, "乙").own_counts == []


def test_own_counts_of_reads_land_and_original_counts_of_every_member():
    assert L.own_counts_of(HX) == [4, 13]


def test_discovery_sets_the_counts_on_a_fresh_result(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "search_taipei_cases_api", lambda *a, **k: [])
    monkeypatch.setattr(L, "_post_taipei_api", lambda *a, **k: "[]")
    got = L.discover_project_links(HX, tmp_path, fresh=True, delay=0)
    assert got.own_counts == [4, 13]


def test_the_cached_path_follows_the_project_s_counts_and_writes_only_on_change(tmp_path):
    stale = DiscoveryResult(project_id=HX.project_id, land_core=CORE, own_counts=[4])
    L.save_project_cache(tmp_path, HX.project_id, stale)
    got = L.discover_project_links(HX, tmp_path, delay=0)
    assert got.own_counts == [4, 13]
    f = tmp_path / HX.project_id / "result.json"
    before = f.stat().st_mtime_ns
    L.discover_project_links(HX, tmp_path, delay=0)
    assert f.stat().st_mtime_ns == before


def test_the_backfill_writes_the_counts_with_a_backup(tmp_path):
    import backfill_own_parcels as bf
    cache = tmp_path / "cache"
    d = cache / "p"
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps(
        {"project_id": "p", "land_core": "x", "own_parcels": ["8", "9"]},
        ensure_ascii=False), encoding="utf-8")
    project = {"project_id": "p", "anchor_recno": 2, "nodes": [
        {"recno": 1, "first_parcel": "8", "parcels": ["8", "9"], "land_count": 13},
        {"recno": 2, "first_parcel": "8", "parcels": ["8", "9"], "land_count": 4,
         "orig_count": 13}]}
    rep = bf.backfill(cache, {"p": project}, tmp_path / "bak")
    assert rep["written"] == ["p"]
    assert json.loads((d / "result.json").read_text(encoding="utf-8"))["own_counts"] == [4, 13]
    bak = json.loads((tmp_path / "bak" / "p" / "result.json").read_text(encoding="utf-8"))
    assert "own_counts" not in bak
    assert bf.backfill(cache, {"p": project}, tmp_path / "bak2")["written"] == []


def test_every_payload_project_cache_holds_the_payload_counts():
    """Live pin: the cache's own_counts equals the payload nodes' counts."""
    cache = ROOT / "data" / ".link_cache"
    bad = {}
    for pid, want in _payload_counts().items():
        rf = cache / pid / "result.json"
        if not rf.is_file():
            continue
        have = json.loads(rf.read_text(encoding="utf-8")).get("own_counts") or []
        if have != want:
            bad[pid] = [have, want]
    assert not bad, (f"{len(bad)} caches hold own_counts that differ from the payload's: "
                     f"{dict(list(bad.items())[:5])}. Run scripts/backfill_own_parcels.py.")


# ── 1.5 the named empty state ─────────────────────────────────────────────────

def _view_html(ids_names):
    anchors = "".join(
        f'<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id={cid}" '
        f'title="t">{n}</a>' for cid, n in ids_names.items())
    return (f"<html><body><div class='data_table_box'><table class='type1_table'>"
            f"<tr><td>{anchors}</td></tr></table></div></body></html>")


def _hx_cache(root, own_counts):
    pid = HX.project_id
    d = root / pid
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({
        "project_id": pid, "land_core": CORE, "status": "resolved",
        "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/9", "twur_view_id": "9",
        "twur_name": N4, "city_case_ids": ["09902263", "09708111"],
        "case_milestones": {"09902263": {"核定日期": "2013/07/05"}, "09708111": {}},
        "national_milestones": {}, "taipei_milestones": {}, "milestones_source": {},
        "implementation": {}, "rewards": {}, "search_rejected": {}, "candidate_names": {},
        "case_schedules": {}, "case_case_names": {"09902263": N4, "09708111": N13},
        "view_verified_case_ids": ["09708111"], "view_rejected": {},
        "own_parcels": PARCELS, "own_counts": own_counts, "error": ""},
        ensure_ascii=False), encoding="utf-8")
    return pid


@pytest.fixture
def city(monkeypatch):
    names = {"09902263": N4, "09708111": N13}
    monkeypatch.setattr(L, "fetch_taipei_milestones_api", lambda cid: {"核定日期": "2013/07/05"})
    monkeypatch.setattr(L, "fetch_taipei_case_header_api",
                        lambda cid: {"NAME": "事業計畫階段─業經本府核定",
                                     "CASE_NAME": names.get(cid, "")})
    monkeypatch.setattr(L, "fetch_view_page",
                        lambda vid, cache_dir=None, fresh=False: _view_html({"09708111": N13}))


def test_an_empty_count_list_is_named_and_the_narrower_rule_decides(tmp_path, city):
    pid = _hx_cache(tmp_path, [])
    rep = L.refresh_project(tmp_path, pid)
    assert rep["error"] == "", rep["error"]
    assert rep["view_gate_no_counts"] == ["09708111"]
    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert "09708111" in saved["view_rejected"]          # 13 is not the land core's count


def test_counts_in_the_cache_are_not_named_and_the_earlier_count_passes(tmp_path, city):
    pid = _hx_cache(tmp_path, [4, 13])
    rep = L.refresh_project(tmp_path, pid)
    assert rep["error"] == "", rep["error"]
    assert rep["view_gate_no_counts"] == []
    saved = json.loads((tmp_path / pid / "result.json").read_text(encoding="utf-8"))
    assert saved["view_rejected"] == {} and "09708111" in saved["view_verified_case_ids"]


# ── 4.5 the live pins after the 2026-11-15 admission ──────────────────────────

ADMITTED = {
    "內湖區-潭美段四小段-579-2地號等21筆": {"09506191"},
    "士林區-光華段四小段-508-6地號等29筆": {"09808102"},
    "大同區-雙連段一小段-197地號等72筆": {"09410261", "09611191"},
    "大同區-雙連段一小段-407地號等13筆": {"09803212"},
    "大安區-大安段一小段-590地號等18筆": {"09705021"},
    "文山區-華興段一小段-8地號等4筆": {"09708111"},
}


def test_the_seven_admitted_cases_are_held_by_their_projects_and_by_no_other():
    doc = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    holders = {}
    for p in doc["projects"]:
        for cid in (p.get("links") or {}).get("taipei") or []:
            holders.setdefault(cid, []).append(p["project_id"])
    assert sum(len(v) for v in ADMITTED.values()) == 7
    for pid, ids in ADMITTED.items():
        for cid in ids:
            assert holders.get(cid) == [pid], (cid, holders.get(cid))


def test_no_case_the_count_rule_accepts_is_left_held_by_no_project():
    """After the admission the rule's candidates are all held. A new one means a
    cache gained a search_rejected case the rule accepts: run
    scripts/admit_unit_cases.py (dry run first)."""
    left = []
    held = set()
    rows = list(_live_pairs())
    for pid, c, cnt, views, names in rows:
        held |= set(c.get("city_case_ids") or [])
    for pid, c, cnt, views, names in rows:
        for cid, nm in (c.get("search_rejected") or {}).items():
            if (isinstance(nm, str) and cid not in held and cid not in (c.get("view_rejected") or {})
                    and L.unit_accepts_case_name(c.get("land_core") or "", nm,
                                                 c.get("own_parcels") or [],
                                                 c.get("own_counts") or [])):
                left.append((pid, cid))
    assert left == [], left


def test_the_walk_s_held_back_case_stays_refused_by_the_single_rule():
    """09012312 (長春559-5): its count 69 is not among the unit's 80 and 83."""
    pid = "中山區-長春段二小段-559-5地號等80筆"
    c = json.loads((ROOT / "data" / ".link_cache" / pid / "result.json").read_text(encoding="utf-8"))
    name = "擬訂臺北市中山區長春段二小段635地號等69筆土地都市更新事業概要案"
    assert 69 not in c["own_counts"]
    assert not L.unit_accepts_case_name(c["land_core"], name, c["own_parcels"], c["own_counts"])
    assert c["sibling_probed"]["09012312"] == "other_unit"


# ── the S1 / D2 conflict (advisor, 2026-11-15): pin it, do not resolve it ─────

S1_PAIRS = json.loads((ROOT / "tests" / "fixtures" / "s1_accepts_count_rule_refuses.json")
                      .read_text(encoding="utf-8"))["pairs"]


def _s1_accepts_rule_refuses():
    out = {}
    for pid, c, cnt, views, names in _live_pairs():
        core, own = c.get("land_core") or "", c.get("own_parcels") or []
        if not own:
            continue
        for cid, nm in names.items():
            lc = L.extract_landcore_from_case_name(nm)
            if (L._section_text(lc) == L._section_text(core)
                    and L._case_name_carries_parcel(nm, own[0], own)
                    and not L.unit_accepts_case_name(core, nm, own, c.get("own_counts") or [])):
                out[(pid, cid)] = ("held_here" if cid in (c.get("city_case_ids") or [])
                                   else None)
    return out


def test_the_search_guard_accepts_62_pairs_the_count_rule_refuses_and_may_only_shrink():
    """F3 made discovery pass own_parcels to the search guard (S1); S1's own-parcel
    form had no count test, so a FRESH discovery (or a refresh with a 5-part key)
    would re-accept the held_none pairs below, the 'other 46' that D2 left out.
    That conflict (docs/inspections/inspection-batchF.md, D11) the user decided
    2026-11-15: option A, the own-parcel form adopts the count rule — implemented
    by d11-search-guard-count-rule. The fixture still freezes the 62-pair
    form-versus-rule population the decision was measured on; it may shrink, never
    grow. The guard's post-D11 verdicts are pinned by the companion test."""
    frozen = {(a, b) for a, b, _ in S1_PAIRS}
    live = set(_s1_accepts_rule_refuses())
    assert live <= frozen, f"new S1-only pairs: {sorted(live - frozen)}"
    assert len(S1_PAIRS) == 62
    assert sum(1 for _, _, st in S1_PAIRS if st == "held_none") == 46


def test_after_d11_the_guard_refuses_the_54_own_parcel_pairs_and_keeps_the_8_stem():
    """The post-D11 guard over the same frozen 62: every own-parcel-form pair is
    refused (the count rule), every stem-form pair keeps its pre-D11 verdict —
    the stem cross-listings are F8 option C, which waits for D11 and the S3/S5
    choice (user decision 2026-11-15). Measured 2026-11-24: 54 own_parcel, 8 stem."""
    cache_root = ROOT / "data" / ".link_cache"
    refused, stem_admitted = [], []
    for pid, cid, _st in S1_PAIRS:
        rf = cache_root / pid / "result.json"
        if not rf.is_file():
            continue
        c = json.loads(rf.read_text(encoding="utf-8"))
        name = ""
        for key in ("candidate_names", "search_rejected", "case_case_names"):
            v = (c.get(key) or {}).get(cid)
            if isinstance(v, str) and v:
                name = v
                break
        core, own = c.get("land_core") or "", tuple(c.get("own_parcels") or [])
        rule = L._parcel_rule(name, own[0], own)
        v = L.membership_verdict(name, L.Unit(core, own,
                                              tuple(c.get("own_counts") or ()), ""),
                                 "search_guard", searched_parcel=own[0])
        if rule == "stem":
            if v.accept:
                stem_admitted.append((pid, cid))
        else:
            assert not v.accept, f"own-parcel pair still admitted: {pid} {cid} ({name[:40]})"
    assert len(stem_admitted) == 8, stem_admitted
