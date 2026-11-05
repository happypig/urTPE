# -*- coding: utf-8 -*-
"""The --from-js loader round-trips four node fields (D14, inspection-batchD).

The bug: _load_projects_from_js built each CleanRecord without
stage_事業計畫, stage_權利變換 or recovery, so every --from-js re-emit dropped
them from every node. It also read district_land with `or node_district`, so an
emitted '' became the node's district on the first rebuild and later runs
carried that value forward (4 nodes: 153, 382, 926, 928).

The gate: emit -> load with the real loader -> emit again. The four fields must
be identical on every node.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.graph import build_project_graph  # noqa: E402
from urtpe.models import CleanRecord, Project  # noqa: E402

ROUNDTRIP_FIELDS = ("stage_事業計畫", "stage_權利變換", "recovery", "district_land")


def _record(recno: int, **over) -> CleanRecord:
    base = dict(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district="中正區", district_land="中正區",
        name=f"擬訂臺北市中正區甲段一小段{recno}地號等1筆土地都市更新事業計畫案",
        name_raw="", land=f"臺北市中正區甲段一小段{recno}地號等1筆土地",
        section="甲段一小段", first_parcel=str(recno), parcels=[str(recno)],
        aliases={}, land_count=1, orig_count=None, named_anchor="",
        area_section="", stage="擬訂", stage_index=0,
        track="事業計畫、權利變換", implementer="甲", planner="乙",
        auto_fixes=[], review_flags=[],
    )
    base.update(over)
    return CleanRecord(**base)


def _family() -> Project:
    """Three members covering every field the loader used to drop.

    - recno 1: both sub-stages filled (the 533-node shape).
    - recno 2: an empty district_land (the 4-node shape: '' must survive).
    - recno 3: recovery provenance (the 4-node shape).
    """
    return Project(
        project_id="中正區-甲段一小段-1地號等3筆", anchor_recno=3,
        members=[
            _record(1, stage_事業計畫="擬訂", stage_權利變換="變更(第二次)"),
            _record(2, district_land=""),
            _record(3, recovery={"cases": ["11501041"], "endpoint": "x"}),
        ])


def _emit(project: Project) -> dict:
    return build_project_graph(project, implementer="甲", name="案")


def _roundtrip(tmp_path: Path, project: Project) -> tuple[dict, dict]:
    """Emit, load through the real --from-js loader, emit again."""
    from urtpe import cli

    original = _emit(project)
    doc = {"projects": [original], "published_date": "2026-01-01",
           "counts": {"projects": 1, "records": 3}}
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                  encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))
    rebuilt = _emit(projects[0])
    return original, rebuilt


def test_the_emitter_writes_the_four_fields():
    graph = _emit(_family())
    by_recno = {n["recno"]: n for n in graph["nodes"]}
    assert by_recno[1]["stage_事業計畫"] == "擬訂"
    assert by_recno[1]["stage_權利變換"] == "變更(第二次)"
    assert by_recno[2]["district_land"] == ""
    assert by_recno[3]["recovery"] == {"cases": ["11501041"], "endpoint": "x"}


def test_roundtrip_is_lossless_for_the_four_fields(tmp_path):
    original, rebuilt = _roundtrip(tmp_path, _family())
    a = {n["recno"]: {f: n.get(f) for f in ROUNDTRIP_FIELDS}
         for n in original["nodes"]}
    b = {n["recno"]: {f: n.get(f) for f in ROUNDTRIP_FIELDS}
         for n in rebuilt["nodes"]}
    assert a == b, (
        "emit -> load -> emit must be lossless for "
        f"{', '.join(ROUNDTRIP_FIELDS)}\n  before: {a}\n  after:  {b}")


def test_an_empty_district_land_survives_the_rebuild(tmp_path):
    """The coercion: '' became the node's district on the first --from-js run."""
    from urtpe import cli

    original, rebuilt = _roundtrip(tmp_path, _family())
    by_recno = {n["recno"]: n for n in rebuilt["nodes"]}
    assert by_recno[2]["district_land"] == "", (
        "an emitted '' district_land must stay '' across a rebuild")


def test_a_missing_district_land_key_falls_back_to_the_district(tmp_path):
    """Older payloads lack the key. The fallback applies only when the key is
    ABSENT — not when it is present and empty."""
    from urtpe import cli

    node = {
        "recno": 9, "date": "2026-01-01", "stage": "擬訂", "track": "事業計畫",
        "area": "", "case_name": "案9", "land": "臺北市中正區甲段一小段9地號等1筆土地",
        "section": "甲段一小段", "first_parcel": "9", "parcels": ["9"],
        "aliases": {}, "land_count": 1, "district": "中正區",
        "area_section": "", "is_current": True,
        "implementer": "甲", "planner": "乙", "review_flags": [], "auto_fixes": [],
        # deliberately NO district_land key
    }
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(
        {"projects": [{"project_id": "中正區-甲段一小段-9地號等1筆",
                       "anchor_recno": 9, "nodes": [node]}],
         "published_date": "2026-01-01",
         "counts": {"projects": 1, "records": 1}}, ensure_ascii=False) + ";",
        encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))
    assert projects[0].members[0].district_land == "中正區"


def test_the_loader_restores_the_sub_stages_and_recovery(tmp_path):
    from urtpe import cli

    original, rebuilt = _roundtrip(tmp_path, _family())
    assert original["nodes"][0]["stage_事業計畫"] is not None
    rec = {n["recno"]: n for n in rebuilt["nodes"]}
    assert rec[1]["stage_事業計畫"] == "擬訂"
    assert rec[1]["stage_權利變換"] == "變更(第二次)"
    assert rec[3]["recovery"] == {"cases": ["11501041"], "endpoint": "x"}
