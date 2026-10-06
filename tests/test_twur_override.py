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