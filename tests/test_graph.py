"""History graph tests: JSON structure and edge semantics."""

from __future__ import annotations

from urtpe.cleanse import cleanse
from urtpe.graph import build_graph_document, build_project_graph
from urtpe.merge import merge
from urtpe.models import RawRecord, Project
from tests.fixtures import SAMPLE_ROWS


def _projects():
    recs = [
        cleanse(RawRecord(1, "115/8/11", "中正區", SAMPLE_ROWS[0][3], SAMPLE_ROWS[0][4], "甲公司", "乙規劃")),
        cleanse(RawRecord(2, "115/7/1", "中正區", SAMPLE_ROWS[1][3], SAMPLE_ROWS[1][4], "甲公司", "乙規劃")),
        cleanse(RawRecord(3, "115/6/1", "中正區", SAMPLE_ROWS[2][3], SAMPLE_ROWS[2][4], "甲公司", "乙規劃")),
    ]
    return merge(recs)


def test_graph_document_shape():
    doc = build_graph_document(_projects(), {"generated_at": "t", "source": "s"})
    assert doc["schema_version"] == 2
    assert doc["counts"]["projects"] == 1
    assert doc["counts"]["records"] == 3
    g = doc["projects"][0]
    assert g["project_id"].startswith("中正區-")
    assert g["anchor_recno"] == 1
    assert sorted(g["member_recnos"]) == [1, 2, 3]
    assert len(g["nodes"]) == 3


def test_anchor_marked_current():
    g = build_project_graph(_projects()[0], implementer="甲公司", name=SAMPLE_ROWS[0][3])
    by_recno = {n["recno"]: n for n in g["nodes"]}
    assert by_recno[1]["is_current"] is True
    assert by_recno[2]["is_current"] is False


def test_revision_edges_connect_chronologically():
    g = build_project_graph(_projects()[0], implementer="甲公司", name="x")
    edges = {(e["from"], e["to"], e["kind"]) for e in g["edges"]}
    assert (3, 2, "revision") in edges
    assert (2, 1, "revision") in edges


def test_stage_and_track_labels():
    g = build_project_graph(_projects()[0], implementer="甲公司", name="x")
    stages = {n["recno"]: n["stage"] for n in g["nodes"]}
    assert stages[1] == "擬訂"
    assert stages[2] == "變更"


def test_section_branch_edges():
    """Two A/B section records of one unit get a section-kind edge."""
    recs = [
        cleanse(RawRecord(819, "113/5/1", "松山區", "擬訂臺北市松山區X段一小段151地號等10筆都市更新事業計畫案(A區段)",
                          "臺北市松山區X段一小段151地號等10筆(A區段)", "甲公司", "乙規劃")),
        cleanse(RawRecord(838, "113/5/1", "松山區", "擬訂臺北市松山區X段一小段151地號等10筆都市更新事業計畫案(B區段)",
                          "臺北市松山區X段一小段151地號等10筆(B區段)", "甲公司", "乙規劃")),
    ]
    projects = merge(recs)
    assert len(projects) == 1
    g = build_project_graph(projects[0], implementer="甲公司", name="x")
    kinds = {e["kind"] for e in g["edges"]}
    assert "section" in kinds
    assert len(g["nodes"]) == 2


def test_project_with_borderline_is_flagged():
    a = cleanse(RawRecord(1, "115/1/1", "中正區", "擬訂臺北市中正區永昌段三小段159地號等113筆都市更新事業計畫案",
                          "臺北市中正區永昌段三小段159、888地號", "甲公司", "乙規劃"))
    b = cleanse(RawRecord(2, "115/2/1", "中正區", "擬訂臺北市中正區永昌段三小段888地號等77筆都市更新事業計畫案",
                          "臺北市中正區永昌段三小段888、777地號", "甲公司", "乙規劃"))
    projects = merge([a, b])
    assert len(projects) == 2
    assert sum(len(p.borderline) for p in projects) == 1


def test_graph_nodes_contain_full_cleanrecord_fields():
    """Each node should contain all CleanRecord fields for the detail table."""
    g = build_project_graph(_projects()[0], implementer="甲公司", name=SAMPLE_ROWS[0][3])
    node = g["nodes"][0]
    # Essential fields (existing)
    assert "recno" in node
    assert "date" in node
    assert "stage" in node
    assert "track" in node
    assert "area" in node
    assert "is_current" in node
    # New fields from CleanRecord that should be included
    expected_fields = [
        "case_name", "land", "parcels", "aliases", "land_count",
        "orig_count", "named_anchor", "area_section", "implementer",
        "planner", "review_flags", "auto_fixes"
    ]
    for field in expected_fields:
        assert field in node, f"Missing field: {field}"


def test_graph_project_contains_published_date():
    """Project should carry the official published_date from PDF metadata."""
    doc = build_graph_document(_projects(), {"generated_at": "t", "source": "s", "published_date": "統計至 115年8月11日"})
    project = doc["projects"][0]
    assert "published_date" in project
    assert project["published_date"] == "統計至 115年8月11日"


def test_graph_project_published_date_empty_when_not_provided():
    """Project published_date should be empty string when not in meta."""
    doc = build_graph_document(_projects(), {"generated_at": "t", "source": "s"})
    project = doc["projects"][0]
    assert "published_date" in project
    assert project["published_date"] == ""