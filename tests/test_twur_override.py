# -*- coding: utf-8 -*-
"""A human-verified portal link, applied as configuration.

Test-writing group 1 of twur-manual-override.

`萬華區-崇仁新村青年段一小段-711-3地號等?筆` does have a portal page (`view/18`) and the
sweep cannot reach it: we search `崇仁新村青年段一小段` while the portal indexes the unit as
`崇仁新村`, and our parcel is `711-3` where the portal says `711`. `parse_name_id` extracts
nothing from the portal's two-section title, so the strict matcher correctly refuses.

The recorded link fills a gap and never displaces a discovered one. That asymmetry is the
safety property: a wrong record does nothing at all while discovery succeeds, and reaches only
the project discovery had nothing for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.links import (  # noqa: E402
    load_project_cache,
    unattached_overrides,
    load_twur_overrides,
    save_project_cache,
)
from urtpe.links import DiscoveryResult  # noqa: E402

PID = "萬華區-崇仁新村青年段一小段-711-3地號等?筆"


def _write_table(cache_dir: Path, payload) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir.parent / "twur_overrides.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _seed(cache_dir: Path, pid: str = PID, **kw):
    save_project_cache(cache_dir, pid, DiscoveryResult(
        project_id=pid, land_core="萬華區-崇仁新村青年段一小段-711-3地號等?筆", **kw))


# --- 1.1: it fills a gap ---------------------------------------------------

def test_a_recorded_link_is_applied_when_the_project_has_none(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache)
    _write_table(cache, {"overrides": {PID: {
        "twur_view_id": "18",
        "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
        "portal_title": "擬訂臺北市萬華區青年段一小段711地號、二小段18地號(原崇仁新村)…",
        "verified_on": "2026-10-06",
        "reason": "portal writes 711 where the gazette has 711-3; two-section title",
    }}})

    result = load_project_cache(cache, PID)

    assert result is not None
    assert result.twur_view_id == "18", result.twur_view_id
    assert result.twur_url.endswith("/view/18")


# --- 1.2: it never displaces discovery --------------------------------------

def test_a_recorded_link_does_not_displace_a_discovered_one(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache, twur_view_id="999", twur_url="https://example.invalid/999")
    _write_table(cache, {"overrides": {PID: {
        "twur_view_id": "18",
        "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
        "portal_title": "t", "verified_on": "2026-10-06", "reason": "r"}}})

    result = load_project_cache(cache, PID)

    assert result.twur_view_id == "999", (
        "discovery answered from the portal itself; a recorded link must not overwrite it")


def test_a_recorded_link_does_not_displace_a_discovered_url(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache, twur_view_id="999", twur_url="")
    _write_table(cache, {"overrides": {PID: {
        "twur_view_id": "18", "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
        "portal_title": "t", "verified_on": "2026-10-06", "reason": "r"}}})

    result = load_project_cache(cache, PID)

    assert result.twur_view_id == "999"
    assert result.twur_url == "", "a discovered view id keeps its own url, empty or not"


# --- 1.3: evidence is required ---------------------------------------------

def test_a_record_without_evidence_is_refused(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache)
    _write_table(cache, {"overrides": {PID: {"twur_view_id": "18"}}})

    result = load_project_cache(cache, PID)

    assert result.twur_view_id is None, (
        "a link with no record of where it was seen cannot be audited, and a wrong one "
        "attaches another project's milestones invisibly")


@pytest.mark.parametrize("missing", ["twur_url", "portal_title", "verified_on"])
def test_every_evidence_field_is_required(tmp_path, missing):
    cache = tmp_path / ".link_cache"
    _seed(cache)
    entry = {"twur_view_id": "18",
             "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
             "portal_title": "t", "verified_on": "2026-10-06", "reason": "r"}
    entry.pop(missing)
    _write_table(cache, {"overrides": {PID: entry}})

    result = load_project_cache(cache, PID)

    assert result.twur_view_id is None, "%s is required for an auditable record" % missing


# --- 1.4 / 1.6: loading is forgiving ---------------------------------------

def test_the_table_is_found_beside_the_cache_like_the_alias_table(tmp_path):
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True, exist_ok=True)
    _write_table(cache, {"overrides": {}})

    assert load_twur_overrides(cache) == {}, (
        "the lookup must mirror load_alias_table: cache_dir.parent then cache_dir")


def test_a_malformed_table_degrades_to_no_overrides(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache)
    path = cache.parent / "twur_overrides.json"
    path.write_text("{not json", encoding="utf-8")

    result = load_project_cache(cache, PID)

    assert result is not None and result.twur_view_id is None, (
        "an unreadable table must not break the pipeline or invent links")


def test_an_absent_table_is_not_an_error(tmp_path):
    cache = tmp_path / ".link_cache"
    _seed(cache)

    assert load_twur_overrides(cache) == {}


# --- 1.5: a record for an unknown project is reportable ---------------------

def test_a_record_naming_an_unknown_project_is_reported(tmp_path, capsys):
    """Reported by `unattached_overrides`, which needs the whole dataset.

    `load_project_cache` sees one project at a time and cannot know the set, so the check
    belongs where the dataset is enumerated — otherwise an identity churn would silently
    stop the record applying.
    """
    cache = tmp_path / ".link_cache"
    _seed(cache)
    _write_table(cache, {"overrides": {"district-somewhere-gone-999地號等1筆": {
        "twur_view_id": "18", "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
        "portal_title": "t", "verified_on": "2026-10-06", "reason": "r"}}})

    orphans = unattached_overrides(cache, [PID])
    out = capsys.readouterr().out

    assert orphans == ["district-somewhere-gone-999地號等1筆"], orphans
    assert "district-somewhere-gone-999" in out, (
        "an unattached record means the identity moved; silence would hide that")


def test_a_record_naming_a_known_project_is_not_reported(tmp_path, capsys):
    cache = tmp_path / ".link_cache"
    _seed(cache)
    _write_table(cache, {"overrides": {PID: {
        "twur_view_id": "18", "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
        "portal_title": "t", "verified_on": "2026-10-06", "reason": "r"}}})

    assert unattached_overrides(cache, [PID]) == []
    assert capsys.readouterr().out == ""


# --- 1.7: the shipped table is well-formed ---------------------------------

def test_the_shipped_override_table_is_well_formed():
    path = ROOT / "data" / "twur_overrides.json"
    if not path.exists():
        pytest.skip("table not present yet")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data.get("schema"), "the table declares its own shape"
    overrides = data.get("overrides") or {}
    assert overrides, "the table is not empty"
    for pid, entry in overrides.items():
        for field in ("twur_view_id", "twur_url", "portal_title", "verified_on", "reason"):
            assert entry.get(field), "%s: %s is required" % (pid, field)


def test_the_shipped_table_points_at_a_real_portal_url():
    path = ROOT / "data" / "twur_overrides.json"
    if not path.exists():
        pytest.skip("table not present yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    for pid, entry in (data.get("overrides") or {}).items():
        assert entry["twur_url"].startswith("https://twur.nlma.gov.tw/"), pid
        assert entry["twur_view_id"] in entry["twur_url"], pid


# =============================================================================
# Test-writing group 2 of twur-override-clean-cache.
#
# Group 1 above all seed a cache entry first. That is the shape every one of them
# needed, and it is exactly why the record appeared to work: a warm cache satisfies
# the gap-fill, so no test ever asked what happens with no cache entry -- which is
# the state a clean clone is in, since `.link_cache/` is gitignored.
#
# `load_project_cache` reaches the table only from inside its `result.json` branch,
# so on an empty cache it returns None and the record is never read. The dataset in
# the repository carries the link because this machine's cache carries it.
# =============================================================================

from urtpe.links import LinksDiscovery, discover_project_links  # noqa: E402
from urtpe.models import Project  # noqa: E402

ENTRY = {
    "twur_view_id": "18",
    "twur_url": "https://twur.nlma.gov.tw/zh/urban/rebuild/view/18",
    "portal_title": "擬訂臺北市萬華區青年段一小段711地號、二小段18地號(原崇仁新村)…",
    "verified_on": "2026-10-06",
    "reason": "portal writes 711 where the gazette has 711-3; two-section title",
}

VIEW_HTML = "<html><body>崇仁新村 推動歷程</body></html>"

# The national view page carries the city case ids under 縣市政府案件連結. For a project
# whose parcel the city API cannot match -- the reason this override exists at all -- that
# block is the only place its case id is written down anywhere.
VIEW_HTML_WITH_CITY_LINK = """<!DOCTYPE html>
<html><body>
<div class="data_table_box">
實施者 弘千建設股份有限公司
相關連結
縣市政府案件連結
<a href="https://gis.uro.taipei/r_progress_detail.aspx?case_id=09112120">擬訂臺北市萬華區崇仁新村青年段一小段土地都市更新事業計畫案</a>
</div>
<div class="data_table_box">
推動歷程
項目 日期
事業計畫申請日期 093.04.22
使用核發日期 097.01.03
</div>
</body></html>
"""


def _project(pid: str = PID, recno: int = 1) -> Project:
    """A project whose Taipei search will match, as the real one does.

    `section` is set directly because cleanse derives it from the gazette's 段 wording and
    this fixture is about link discovery, not about parsing 段. The search is gated on
    section *and* parcel being present, so leaving it blank would silently skip the very
    step the next test asserts on.
    """
    from urtpe.models import RawRecord
    from urtpe.cleanse import cleanse
    district = pid.split("-")[0]
    raw = RawRecord(recno, "115/8/11", district, "崇仁新村青年段一小段", "711-3地號等1筆",
                    "某建設", "某規劃")
    rec = cleanse(raw)
    rec.section = "青年段一小段"
    return Project(project_id=pid, anchor_recno=recno, members=[rec], borderline=())


def _offline(monkeypatch, city_cases=None):
    """No network. Taipei search returns ``city_cases``; the view page is canned."""
    import urtpe.links as links
    monkeypatch.setattr(links, "search_taipei_cases_api",
                        lambda section, parcel, dropped_out=None: list(city_cases or []))
    monkeypatch.setattr(links, "fetch_view_page", lambda *a, **k: VIEW_HTML)
    monkeypatch.setattr(links, "extract_tuidui_history_from_view",
                        lambda html: {"使用核發日期": "2008/01/03"})
    monkeypatch.setattr(links, "build_portal_index", lambda *a, **k: [])
    monkeypatch.setattr(links, "_OVERRIDE_CACHE", {})
    return links


# --- 2.1: the record applies with no cache entry at all ----------------------

def test_a_recorded_link_applies_with_no_cache_entry(tmp_path, monkeypatch):
    """The fresh-clone case: `.link_cache/` holds nothing but the record applies."""
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch)

    assert load_project_cache(cache, PID) is None, (
        "precondition: with no result.json the cache read finds nothing, which is why "
        "the record below has to be reached during discovery instead")

    result = discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=[])

    assert result.twur_view_id == "18", (
        "the record is configuration, not a cache artefact; a rebuild from an empty cache "
        "must still produce the link or the committed dataset cannot be reproduced")
    assert result.twur_url.endswith("/view/18")
    assert result.national_milestones == {"使用核發日期": "2008/01/03"}, (
        "milestones come from the portal page the record points at, not from hand values")


def test_the_result_is_written_to_the_cache_in_the_ordinary_shape(tmp_path, monkeypatch):
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch)

    discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=[])

    entry = next(cache.glob("*/result.json"), None)
    assert entry is not None, "a completed result must be cached so the next run resumes"
    saved = json.loads(entry.read_text(encoding="utf-8"))
    assert saved["twur_view_id"] == "18"
    assert saved["national_milestones"] == {"使用核發日期": "2008/01/03"}


# --- 2.2: applying the record must not suppress the rest of discovery --------

def test_applying_the_record_still_runs_the_city_search(tmp_path, monkeypatch):
    """Guards the tempting wrong fix.

    Returning a synthetic `DiscoveryResult` from `load_project_cache` would satisfy the
    test above and leave every other field empty -- the project would render a portal
    link, no city link, and no milestones, which is the defect this change exists to
    prevent rather than repeat.
    """
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch, city_cases=[{"case_id": "09112120", "case_name": "崇仁新村", "schedule": ""}])
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                        lambda cid: {"概要核准日期": "2005/04/01"})

    result = discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=[])

    assert result.city_case_ids == ["09112120"], (
        "the record supplies the national-portal link only; the city-platform half of the "
        "project is still discovery's job and must not be skipped")
    assert result.taipei_milestones == {"概要核准日期": "2005/04/01"}
    assert result.twur_view_id == "18", "and the record applies alongside all of it"


def test_the_record_applies_with_no_portal_index_available(tmp_path, monkeypatch):
    """The whole national-portal step used to sit behind `if portal_index:`.

    With an empty index that gate skipped the fetch entirely, stranding the record
    precisely when the portal index is the thing that is missing.
    """
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch)

    result = discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=None)

    assert result.twur_view_id == "18", result.twur_view_id
    assert result.national_milestones == {"使用核發日期": "2008/01/03"}


# --- 2.3: gap-fill asymmetry survives the move ------------------------------

def test_a_discovered_view_id_still_beats_the_record(tmp_path, monkeypatch):
    from urtpe.links import build_land_core_key
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch)
    project = _project()

    result = discover_project_links(
        project, cache, fresh=False, delay=0,
        portal_index=[{"core": build_land_core_key(project.members[0]), "view_id": "999"}])

    assert result.twur_view_id == "999", (
        "the whole point of the record is that it fills a gap; if the portal answers, "
        "the portal's answer stands. got %r" % (result.twur_view_id,))


# --- 2.4: end to end, and the reporting that had no caller ------------------

def test_a_full_run_from_an_empty_cache_reproduces_the_record(tmp_path, monkeypatch):
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch, city_cases=[{"case_id": "09112120", "case_name": "崇仁新村", "schedule": ""}])

    results = LinksDiscovery(str(cache), delay=0).run([_project()], fresh=False)

    assert results[PID].twur_view_id == "18", (
        "end to end on an empty tree: this is what a fresh clone actually does")
    assert results[PID].city_case_ids == ["09112120"]


def test_a_run_reports_a_record_naming_an_absent_project(tmp_path, monkeypatch, capsys):
    """`unattached_overrides` existed with no caller, so nothing ever reported."""
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY, "district-somewhere-gone-999地號等1筆": ENTRY}})
    _offline(monkeypatch)

    LinksDiscovery(str(cache), delay=0).run([_project()], fresh=False)

    assert "district-somewhere-gone-999" in capsys.readouterr().out, (
        "an identity churn would otherwise stop the record applying with no sign")


# --- 2.5: the view page is also where the city case id is written ------------
#
# `extract_case_ids_from_view` and the `view_verified_case_ids` field both exist, and
# `attach_links_to_projects` already trusts the latter -- but nothing ever populated it.
# `extract_case_ids_from_view` was called from tests and nowhere else.
#
# That is why the cold rebuild above produced twur_view_id 18 and `city_case_ids: []`:
# the page we fetched says 09112120 in as many words. The project rendered a portal link
# and no city link, which is the state this whole exercise started from.

def test_city_case_ids_are_read_off_the_view_page_when_the_search_cannot_match(tmp_path, monkeypatch):
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch, city_cases=[])          # the parcel search finds nothing
    monkeypatch.setattr("urtpe.links.fetch_view_page",
                        lambda *a, **k: VIEW_HTML_WITH_CITY_LINK)
    monkeypatch.setattr("urtpe.links.extract_tuidui_history_from_view",
                        lambda html: {"使用核發日期": "2008/01/03"})
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api",
                        lambda cid: {"概要核准日期": "2005/04/01"})

    result = discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=[])

    assert result.city_case_ids == ["09112120"], (
        "the portal page names this project's own case; that is the only place it is written "
        "down when the parcel search misses, which is exactly this project")
    assert result.view_verified_case_ids == ["09112120"], (
        "attach_links_to_projects skips its similarity gate for view-verified ids, and a "
        "parcel-less case name would otherwise score 0.0 and be dropped as unrelated")
    assert result.taipei_milestones == {"概要核准日期": "2005/04/01"}, (
        "the id is useless without its milestones; the project renders 使用 dates from them")
    assert result.status == "resolved", result.status


def test_case_ids_from_the_page_do_not_duplicate_the_parcel_search(tmp_path, monkeypatch):
    cache = tmp_path / ".link_cache"
    cache.mkdir(parents=True)
    _write_table(cache, {"overrides": {PID: ENTRY}})
    _offline(monkeypatch, city_cases=[{"case_id": "09112120", "case_name": "崇仁新村", "schedule": ""}])
    monkeypatch.setattr("urtpe.links.fetch_view_page",
                        lambda *a, **k: VIEW_HTML_WITH_CITY_LINK)
    monkeypatch.setattr("urtpe.links.fetch_taipei_milestones_api", lambda cid: {})

    result = discover_project_links(_project(), cache, fresh=False, delay=0, portal_index=[])

    assert result.city_case_ids == ["09112120"], result.city_case_ids