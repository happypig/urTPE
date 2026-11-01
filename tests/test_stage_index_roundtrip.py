# -*- coding: utf-8 -*-
"""stage_index survives a rebuild from emitted state (emit-stage-index 1.1).

The bug: build_project_graph never emitted stage_index; the --from-js loader
read it with a -1 default; graph.py:108 groups section branches by
(stage_index, track), so on a rebuild every stage of a track collapsed into one
group and 區段 branch edges could never form. These tests pin the fix
end-to-end: emit, load through the real loader, re-emit, and the section edges
must be identical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.graph import build_project_graph, build_graph_document  # noqa: E402
from urtpe.models import CleanRecord, Project  # noqa: E402


def _record(recno: int, stage: str, area: str) -> CleanRecord:
    return CleanRecord(
        recno=recno, date="2026-01-01", iso_date="2026-01-01", ymd=(2026, 1, 1),
        district="中正區", district_land="中正區",
        name=f"擬訂臺北市中正區甲段一小段{recno}地號等1筆土地都市更新事業計畫案",
        name_raw="", land=f"臺北市中正區甲段一小段{recno}地號等1筆土地",
        section="甲段一小段", first_parcel=str(recno), parcels=[str(recno)],
        aliases={}, land_count=1, orig_count=None, named_anchor="",
        area_section=area, stage=stage,
        stage_index={"擬訂": 0, "變更": 1, "變更(第二次)": 2}.get(stage, -1),
        track="事業計畫", implementer="甲", planner="乙",
        auto_fixes=[], review_flags=[],
    )


def _family() -> Project:
    """Three stages × three 區段 values — the shape whose section edges the bug
    collapses."""
    return Project(
        project_id="中正區-甲段一小段-1地號等3筆", anchor_recno=1,
        members=[_record(1, "擬訂", "甲"), _record(2, "變更", "A"),
                 _record(3, "變更(第二次)", "B")])


def _section_edges(doc: dict) -> set:
    edges = set()
    for p in doc["projects"]:
        for e in p["edges"]:
            if e["kind"] == "section":
                edges.add((e["from"], e["to"]))
    return edges


def test_build_emits_stage_index_on_every_node():
    p = _family()
    graph = build_project_graph(p, implementer="甲", name="案")
    for node in graph["nodes"]:
        assert "stage_index" in node, node["recno"]
        assert node["stage_index"] != -1


def test_section_edges_form_on_the_original_build():
    p = _family()
    doc = {"projects": [build_project_graph(p, implementer="甲", name="案")],
           "published_date": "2026-01-01"}
    # 3 distinct stage groups × 1 member each with distinct area → each pair of
    # members within the same (stage_index, track) group... the fixture gives one
    # member per stage, so section edges need members sharing a stage with
    # distinct areas. Extend: a second family shape with two members per stage.
    p2 = Project(
        project_id="中正區-甲段一小段-2地號等4筆", anchor_recno=4,
        members=[_record(4, "變更", "甲"), _record(5, "變更", "A"),
                 _record(6, "變更(第二次)", "甲"), _record(7, "變更(第二次)", "B")])
    doc["projects"].append(build_project_graph(p2, implementer="甲", name="案2"))
    edges = _section_edges(doc)
    assert edges, "two members per stage with distinct areas must form section edges"


def test_rebuild_from_emitted_state_forms_identical_section_edges(tmp_path):
    """The bug's end-to-end statement: emit → load (the real --from-js loader)
    → re-emit, and the section edges are identical."""
    from urtpe import cli
    p2 = Project(
        project_id="中正區-甲段一小段-2地號等4筆", anchor_recno=4,
        members=[_record(4, "變更", "甲"), _record(5, "變更", "A"),
                 _record(6, "變更(第二次)", "甲"), _record(7, "變更(第二次)", "B")])
    p1 = _family()
    meta = {"generated_at": "x", "source": "y", "published_date": "2026-01-01"}
    original = {"projects": [
        build_project_graph(p1, implementer="甲", name="案"),
        build_project_graph(p2, implementer="甲", name="案2")],
        "published_date": "2026-01-01"}

    # write the emitted document as projects.data.js and load it back through
    # the real loader
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(
        {**original, "counts": {"projects": 2, "records": 7}},
        ensure_ascii=False) + ";", encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))
    rebuilt = {"projects": [
        build_project_graph(p, implementer="甲", name="案") for p in projects],
        "published_date": "2026-01-01"}
    assert _section_edges(rebuilt) == _section_edges(original), (
        "section edges must survive a rebuild from emitted state")


def test_a_node_without_the_key_derives_from_stage_text(tmp_path):
    """An already-deployed document lacking stage_index repairs on load — no -1
    sentinel unless the stage text yields none."""
    from urtpe import cli
    node = {
        "recno": 9, "date": "2026-01-01", "stage": "變更(第二次)", "track": "事業計畫",
        "area": "B", "case_name": "案9", "land": "臺北市中正區甲段一小段9地號等1筆土地",
        "section": "甲段一小段", "first_parcel": "9", "parcels": ["9"],
        "aliases": {}, "land_count": 1, "district": "中正區",
        "district_land": "中正區", "area_section": "B", "is_current": True,
        "implementer": "甲", "planner": "乙", "review_flags": [], "auto_fixes": [],
        # deliberately NO stage_index key
    }
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(
        {"projects": [{"project_id": "中正區-甲段一小段-9地號等1筆",
                       "anchor_recno": 9, "nodes": [node]}],
         "published_date": "2026-01-01",
         "counts": {"projects": 1, "records": 1}}, ensure_ascii=False) + ";",
        encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))
    rec = projects[0].members[0]
    assert rec.stage_index == 2, (
        f"變更(第二次) must derive to index 2, got {rec.stage_index}")


def test_roundtrip_is_lossless_for_stage_index(tmp_path):
    from urtpe import cli
    p = _family()
    doc = {"projects": [build_project_graph(p, implementer="甲", name="案")],
           "published_date": "2026-01-01",
           "counts": {"projects": 1, "records": 3}}
    js = tmp_path / "projects.data.js"
    js.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";",
                  encoding="utf-8")
    projects, _meta = cli._load_projects_from_js(str(js))
    reemitted = build_project_graph(projects[0], implementer="甲", name="案")
    original_idx = {n["recno"]: n["stage_index"] for n in doc["projects"][0]["nodes"]}
    rebuilt_idx = {n["recno"]: n["stage_index"] for n in reemitted["nodes"]}
    assert original_idx == rebuilt_idx, "emit → load → emit must be lossless"
