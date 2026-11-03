# -*- coding: utf-8 -*-
"""§8 viewer-UX wave 3b: a view-verified case id must belong to the project.

The defect these pin (docs/viewer-UX.md §8, inspection board B7 + B8): the
national view page's 相關連結 assertion was treated as unconditional, so case
ids of OTHER projects entered a project's cache as view-verified and rendered
as nameless 孤 anchors carrying the other project's 建照 / 開工 dates —
10202065 (中山254), 09511211 (大安557, shape B: label right, id wrong),
09807161 (大安龍泉169), 09608220 (信義犁和102).

The rule (§8 decision 1): the city's own case name decides. The 相關連結 label
is compared only for the reason text. A rejected id is named in view_rejected,
never dropped silently, and offered to its own project by land core.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe import links as links_mod  # noqa: E402
from urtpe.links import attach_links_to_projects  # noqa: E402


def _fn(name: str):
    """Import-time shim: the tests run before the implementation exists, so
    every function under test is resolved lazily — an unimplemented function
    fails as None-call, not as a collection error."""
    fn = getattr(links_mod, name, None)
    if fn is None:
        pytest.skip(f"urtpe.links.{name} not implemented yet (task 2.x)")
    return fn


offer_rejected_ids = lambda *a, **k: _fn("offer_rejected_ids")(*a, **k)
verify_view_verified_ids = lambda *a, **k: _fn("verify_view_verified_ids")(*a, **k)
refresh_project = lambda *a, **k: _fn("refresh_project")(*a, **k)


# ── fixtures ─────────────────────────────────────────────────────────────────

OWN_CORE = "中山區吉林段四小段603地號等40筆"
OTHER_CORE = "大安區大安段一小段557地號等16筆"

CITY_NAME_OWN = "擬訂臺北市中山區吉林段四小段603地號等40筆土地都市更新事業計畫案"
CITY_NAME_OTHER = "擬訂臺北市大安區大安段一小段557地號等16筆土地都市更新事業計畫案"
CITY_NAME_PARCEL_LESS = "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案"


def _write_cache(cache_dir: Path, pid: str, *, land_core: str,
                 city_case_ids: list[str], **extra) -> Path:
    d = cache_dir / pid
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": pid, "land_core": land_core, "status": "resolved",
        "case_milestones": {cid: {"核定日期": "2020/01/02"} for cid in city_case_ids},
        "city_case_ids": city_case_ids,
        "twur_url": "", "twur_view_id": "",
        "national_milestones": {}, "taipei_milestones": {},
        "milestones_source": {}, "implementation": {}, "rewards": {},
        "search_rejected": {}, "candidate_names": {}, "case_schedules": {},
        "error": "",
    }
    payload.update(extra)
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False),
                                   encoding="utf-8")
    return d


def _saved(cache_dir: Path, pid: str) -> dict:
    return json.loads((cache_dir / pid / "result.json").read_text(encoding="utf-8"))


# ── 1.1 the decision-1 table: the city's case name decides ──────────────────


class TestDecisionTable:
    """§8 decision 1: check 2 (the city's CASE_NAME) decides; check 1 (the
    相關連結 label) only writes the reason."""

    def _decide(self, label_matches: bool, city_matches: bool):
        city_name = CITY_NAME_OWN if city_matches else CITY_NAME_OTHER
        label = CITY_NAME_OWN if label_matches else CITY_NAME_OTHER
        return verify_view_verified_ids(
            own_land_core=OWN_CORE,
            ids=["10202065"],
            city_names={"10202065": city_name},
            labels={"10202065": label},
        )

    def test_match_match_accepts(self):
        out = self._decide(label_matches=True, city_matches=True)
        assert out.kept == ["10202065"]
        assert out.rejected == {}

    def test_nomatch_nomatch_rejects_shape_a(self):
        out = self._decide(label_matches=False, city_matches=False)
        assert out.kept == []
        assert out.rejected["10202065"]["shape"] == "A"
        assert out.rejected["10202065"]["reason"] == (
            "label and city name name another project (shape A)")

    def test_label_match_city_nomatch_rejects_shape_b(self):
        """09511211 on 大安557: the label is right, the id is wrong — only the
        city's own case name shows this."""
        out = self._decide(label_matches=True, city_matches=False)
        assert out.kept == []
        assert out.rejected["10202065"]["shape"] == "B"
        assert out.rejected["10202065"]["reason"] == (
            "label is right, id is wrong (shape B)")

    def test_label_nomatch_city_match_accepts_and_logs_label_error(self):
        """10906092 on 中山吉林898: the label names 莒光519-3 but the city's own
        name is 吉林898 — accept, log the label error."""
        out = self._decide(label_matches=False, city_matches=True)
        assert out.kept == ["10202065"]
        assert out.rejected == {}
        assert out.label_errors == ["10202065"]


# ── 1.2 parcel-less city name; 1.3 missing city name ────────────────────────


class TestUndecidableAndMissing:
    def test_parcel_less_city_name_does_not_reject(self):
        """崇仁新村 shape: a city name with no 地號 is not decidable by land
        core — it does not reject (§8 evidence: the spec's own legitimate
        example)."""
        out = verify_view_verified_ids(
            own_land_core=OWN_CORE,
            ids=["09112120"],
            city_names={"09112120": CITY_NAME_PARCEL_LESS},
            labels={"09112120": CITY_NAME_PARCEL_LESS},
        )
        assert out.kept == ["09112120"]
        assert out.rejected == {}

    def test_missing_city_name_keeps_the_id_and_reports_not_confirmed(self):
        """§8 open question 3 default: a missing header is no evidence — the
        id stays view-verified and, its label also mismatching, is reported
        'label not confirmed'. The label alone never rejects."""
        out = verify_view_verified_ids(
            own_land_core=OWN_CORE,
            ids=["10202065"],
            city_names={},                       # header fetch failed / absent
            labels={"10202065": CITY_NAME_OTHER},
        )
        assert out.kept == ["10202065"]
        assert out.rejected == {}
        assert out.not_confirmed == ["10202065"]

    def test_missing_city_name_with_matching_label_is_unremarkable(self):
        out = verify_view_verified_ids(
            own_land_core=OWN_CORE,
            ids=["10202065"],
            city_names={},
            labels={"10202065": CITY_NAME_OWN},
        )
        assert out.kept == ["10202065"]
        assert out.not_confirmed == []


# ── 1.4 the offer step ───────────────────────────────────────────────────────


class TestOfferToOwningProject:
    SRC = "中山區-吉林段四小段-603地號等40筆"
    TARGET = "大安區-大安段一小段-557地號等16筆"

    def _setup(self, tmp_path, target_ids: list[str]):
        _write_cache(tmp_path, self.SRC, land_core=OWN_CORE,
                     city_case_ids=["09511210"],
                     view_verified_case_ids=["09511211"],
                     case_case_names={"09511211": CITY_NAME_OTHER})
        _write_cache(tmp_path, self.TARGET, land_core=OTHER_CORE,
                     city_case_ids=list(target_ids))

    def test_exactly_one_match_moves_the_id(self, tmp_path):
        self._setup(tmp_path, target_ids=["10202061"])
        moves = offer_rejected_ids(
            tmp_path,
            rejected={self.SRC: {"09511211": CITY_NAME_OTHER}},
        )
        assert moves == [(self.SRC, self.TARGET, "09511211")]
        target = _saved(tmp_path, self.TARGET)
        assert target["city_case_ids"] == ["10202061", "09511211"]  # appended, order kept
        assert target["adopted_from_view"] == {"09511211": self.SRC}
        assert _saved(tmp_path, self.SRC)["view_rejected"]["09511211"]["reason"]

    def test_target_already_holding_the_id_is_not_duplicated(self, tmp_path):
        """09807161 → 內湖康寧262 already holds it: no duplicate append, the
        adoption is still recorded."""
        self._setup(tmp_path, target_ids=["09511211"])
        moves = offer_rejected_ids(
            tmp_path,
            rejected={self.SRC: {"09511211": CITY_NAME_OTHER}},
        )
        assert moves == [(self.SRC, self.TARGET, "09511211")]
        target = _saved(tmp_path, self.TARGET)
        assert target["city_case_ids"].count("09511211") == 1
        assert target["adopted_from_view"] == {"09511211": self.SRC}

    def test_no_match_moves_nothing(self, tmp_path):
        _write_cache(tmp_path, self.SRC, land_core=OWN_CORE,
                     city_case_ids=["09511210"],
                     view_verified_case_ids=["09511211"],
                     case_case_names={"09511211": CITY_NAME_OTHER})
        _write_cache(tmp_path, self.TARGET, land_core="信義區犁和段一小段102地號等3筆",
                     city_case_ids=[])
        moves = offer_rejected_ids(
            tmp_path,
            rejected={self.SRC: {"09511211": "擬訂臺北市中正區城中段一小段5地號等1筆土地都市更新事業計畫案"}},
        )
        assert moves == []
        assert "adopted_from_view" not in _saved(tmp_path, self.TARGET)

    def test_ambiguous_owner_moves_nothing(self, tmp_path):
        """Two caches match the city name's land core → no guess (the
        project_aliases.json rule)."""
        self._setup(tmp_path, target_ids=[])
        _write_cache(tmp_path, "大安區-大安段一小段-557地號等16筆-2",
                     land_core=OTHER_CORE, city_case_ids=[])
        moves = offer_rejected_ids(
            tmp_path,
            rejected={self.SRC: {"09511211": CITY_NAME_OTHER}},
        )
        assert moves == []
        for pid in (self.TARGET, "大安區-大安段一小段-557地號等16筆-2"):
            assert "adopted_from_view" not in _saved(tmp_path, pid)


# ── 1.6 the refresh runs the pass on a fully-approved cache ─────────────────


class TestRefreshRunsThePass:
    VIEW_HTML = """
    <html><body><div class='data_table_box'><table class='type1_table'><tr><td>
    <a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=09511211" title="t">擬訂臺北市大安區大安段一小段557地號等16筆土地都市更新事業計畫案</a>
    </td></tr></table></div></body></html>
    """

    def test_fully_approved_cache_is_still_verified(self, tmp_path, monkeypatch):
        """The awaiting-approval selector would skip this cache: every case has
        a 核定日期. The view-verified verification must run regardless — the
        defect does not depend on the awaiting state. Fixture = the real
        09511211-on-大安557 shape: the label names the holder's own unit
        (matching its land core) while the city's own case name names
        吉林603 — shape B, only the city name shows it."""
        pid = "大安區-大安段一小段-557地號等16筆"
        d = _write_cache(tmp_path, pid, land_core=OTHER_CORE,
                         city_case_ids=["09901161", "09511211"],
                         view_verified_case_ids=["09511211"])
        (d / "view.html").write_text(self.VIEW_HTML, encoding="utf-8")

        monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                            lambda cid: {"核定日期": "2013/06/18"})
        monkeypatch.setattr("urtpe.links.fetch_taipei_case_header_api",
                            lambda cid: {"NAME": "執行階段_更新案施工中",
                                         "CASE_NAME": CITY_NAME_OWN})

        report = refresh_project(tmp_path, pid)

        saved = _saved(tmp_path, pid)
        assert "09511211" not in saved["view_verified_case_ids"]
        assert saved["view_rejected"]["09511211"]["shape"] == "B"
        # the city's own case name is persisted for the offer step
        assert saved["case_case_names"]["09511211"] == CITY_NAME_OWN
        assert report["view_rejected_ids"] == ["09511211"]

    def test_row4_accept_logs_the_label_error_in_the_report(self, tmp_path, monkeypatch):
        pid = "中山區-吉林段四小段-603地號等40筆"
        _write_cache(tmp_path, pid, land_core=OWN_CORE,
                     city_case_ids=["09511210", "10906092"],
                     view_verified_case_ids=["10906092"])

        monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})
        monkeypatch.setattr("urtpe.links.fetch_taipei_case_header_api",
                            lambda cid: {"NAME": "執行階段_更新案施工中",
                                         "CASE_NAME": CITY_NAME_OWN})

        report = refresh_project(tmp_path, pid)

        saved = _saved(tmp_path, pid)
        assert saved["view_verified_case_ids"] == ["10906092"]   # kept
        assert saved.get("view_rejected", {}) == {}
        assert report["view_label_errors"] == ["10906092"]

    def test_missing_city_name_keeps_the_id(self, tmp_path, monkeypatch):
        pid = "甲"
        _write_cache(tmp_path, pid, land_core=OWN_CORE,
                     city_case_ids=["10202065"],
                     view_verified_case_ids=["10202065"])

        monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})
        monkeypatch.setattr("urtpe.links.fetch_taipei_case_header_api",
                            lambda cid: {})   # no row — no evidence

        report = refresh_project(tmp_path, pid)

        saved = _saved(tmp_path, pid)
        assert saved["view_verified_case_ids"] == ["10202065"]
        assert report["view_not_confirmed"] == ["10202065"]


# ── 1.5 + 1.7 payload round-trip of the new fields ──────────────────────────


class TestPayloadRoundTrip:
    def test_view_rejected_and_adopted_from_view_reach_the_payload(self):
        from urtpe.models import Project, make_record
        pid = "中山區-吉林段四小段-603地號等40筆"
        rec = make_record(9, "102/6/9", "中山區", "擬訂…案",
                          "臺北市中山區吉林段四小段603地號等40筆", "某建設", "某規劃")
        project = Project(project_id=pid, anchor_recno=9, members=[rec])
        disc = {
            "twur": "", "taipei": [], "milestones_national": {},
            "milestones_taipei": {}, "case_milestones": {}, "milestones_source": {},
            "implementation": {}, "rewards": {}, "search_rejected": {},
            "candidate_names": {}, "case_schedules": {},
            "view_rejected": {"09511211": {"reason": "label is right, id is wrong (shape B)",
                                           "shape": "B"}},
            "adopted_from_view": {"10202065": "中山區-中山段一小段-254地號等13筆"},
        }
        attach_links_to_projects([project], {pid: disc})
        assert project.links["view_rejected"]["09511211"]["shape"] == "B"
        assert project.links["adopted_from_view"]["10202065"].startswith("中山區")

    def test_a_result_without_the_fields_emits_without_the_keys(self):
        from urtpe.models import Project, make_record
        pid = "乙"
        rec = make_record(9, "102/6/9", "中山區", "擬訂…案",
                          "臺北市中山區吉林段四小段603地號等40筆", "某建設", "某規劃")
        project = Project(project_id=pid, anchor_recno=9, members=[rec])
        disc = {
            "twur": "", "taipei": [], "milestones_national": {},
            "milestones_taipei": {}, "case_milestones": {}, "milestones_source": {},
            "implementation": {}, "rewards": {}, "search_rejected": {},
            "candidate_names": {}, "case_schedules": {},
        }
        attach_links_to_projects([project], {pid: disc})
        assert "view_rejected" not in project.links
        assert "adopted_from_view" not in project.links

    def test_new_fields_survive_the_from_js_reader(self):
        """The --from-js payload reader builds its objects field by field; a
        field missing there is dropped on the next --from-js run (the
        superseded_by round-trip lesson). The new fields must ride it."""
        src = (ROOT / "urtpe" / "links.py").read_text(encoding="utf-8")
        start = src.index("def attach_links_to_projects")
        end = src.index("\nclass LinksDiscovery", start)
        reader = src[start:end]
        for field in ("case_case_names", "view_rejected", "adopted_from_view"):
            assert f'v.get("{field}"' in reader, (
                f"the --from-js reader must carry {field} or the next "
                f"--from-js run drops it")
