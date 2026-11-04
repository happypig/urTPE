"""CLI helper tests: projects.data.js round-trip preserves emitted state."""

from __future__ import annotations

import json

from urtpe.cli import _load_projects_from_js


def _write_js(tmp_path, doc):
    path = tmp_path / "projects.data.js"
    path.write_text("window.PROJECTS = " + json.dumps(doc, ensure_ascii=False) + ";", encoding="utf-8")
    return str(path)


def test_load_from_js_restores_implementation_state(tmp_path):
    node = {
        "recno": 991,
        "date": "2026-08-11",
        "stage": "核定",
        "track": "事業計畫",
        "case_name": "擬訂中山區中山段一小段254地號等13筆都市更新事業計畫案",
        "district": "中山區",
        "implementation": {"Exe_Way": "權利變換", "case_id": "09811141"},
        "links": {"taipei": ["09811141"]},
    }
    doc = {
        "schema_version": 2,
        "generated_at": "t",
        "source": "s",
        "published_date": "",
        "projects": [
            {
                "project_id": "中山區-中山段一小段-254地號等13筆",
                "anchor_recno": 991,
                "nodes": [node],
                "links": {},
                "implementation": {"Exe_Way": "權利變換", "case_id": "09811141"},
                "rewards": {"F0": "8,982.01", "case_id": "09811141"},
            }
        ],
    }
    path = _write_js(tmp_path, doc)
    projects, meta = _load_projects_from_js(path)

    assert meta["generated_at"] == "t"
    project = projects[0]
    assert project.implementation == {"Exe_Way": "權利變換", "case_id": "09811141"}
    assert project.rewards["F0"] == "8,982.01"
    rec = next(r for r in project.members if r.recno == 991)
    assert rec.implementation == {"Exe_Way": "權利變換", "case_id": "09811141"}


def test_load_from_js_aliases_orphan_milestones_key(tmp_path):
    """D1 (inspection-batchD): an old payload's orphan `milestones_national`
    (Taipei ashx data under a false name) loads as `milestones_taipei_case`;
    a project-level `milestones_national` is NOT aliased (it IS national)."""
    orphan_node = {
        "recno": "v09907221",
        "virtual": True,
        "case_id": "09907221",
        "date": "",
        "stage": "擬訂",
        "track": "事業計畫",
        "case_name": "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案",
        "links": {"taipei": ["09907221"], "milestones_national": {"核定日期": "2019/01/31"}},
    }
    doc = {
        "schema_version": 2,
        "generated_at": "t",
        "source": "s",
        "published_date": "",
        "projects": [
            {
                "project_id": "文山區-木柵段三小段-623地號等39筆",
                "anchor_recno": 1,
                "nodes": [orphan_node],
                "links": {"milestones_national": {"使用核發日期": "109.10.25"}},
            }
        ],
    }
    path = _write_js(tmp_path, doc)
    projects, _ = _load_projects_from_js(path)
    rec = projects[0].members[0]
    assert rec.links.get("milestones_taipei_case") == {"核定日期": "2019/01/31"}
    assert "milestones_national" not in rec.links
