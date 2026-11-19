"""Offline contracts for the two documentation synchronization commands."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import doc_measurements as dm


def test_marked_regions_are_replaced_once_and_repeatable():
    source = ('<p data-doc-field="summary">old</p>\n'
              '<span data-doc-field="count">1</span>\n'
              '<p data-history>the old 1,444 records stay historical</p>')
    fields = {"summary": '<span class="en">2 records</span>'
                         '<span class="zh">2 筆</span>',
              "count": "2"}
    rendered, changed = dm.replace_fields(source, fields)
    assert "2 records" in rendered and "2 筆" in rendered
    assert ">2</span>" in rendered
    assert "the old 1,444 records stay historical" in rendered
    assert changed == ["count", "summary"]
    again, unchanged = dm.replace_fields(rendered, fields)
    assert again == rendered
    assert unchanged == []


def test_missing_or_duplicate_markers_are_refused():
    with pytest.raises(dm.DocSyncError, match="missing"):
        dm.replace_fields("<p>unmarked</p>", {"count": "2"})
    duplicated = '<span data-doc-field="count">1</span>' * 2
    with pytest.raises(dm.DocSyncError, match="duplicate"):
        dm.replace_fields(duplicated, {"count": "2"})


def _payload():
    return {
        "schema_version": 2,
        "published_date": "2026-11-12",
        "generated_at": "2026-11-18T22:36:36+08:00",
        "counts": {"projects": 2, "records": 3},
        "projects": [
            {"project_id": "a", "nodes": [
                {"recno": 1, "date": "2026-11-12", "name_raw": "事業計畫",
                 "review_flags": ["flag"], "links": {"taipei": ["001"]}},
                {"recno": 2, "date": "2002-03-21", "name_raw": "事業換計畫",
                 "review_flags": [], "recovery": {"cases": ["R000001-01"]},
                 "links": {"taipei": ["002"]}},
            ], "links": {"orphan_nodes": [
                {"case_id": "v1", "case_name": "案", "stage": "擬訂",
                 "track": "事業概要", "node_date": ""}]}},
            {"project_id": "b", "nodes": [
                {"recno": 3, "date": "2020-01-01", "name_raw": "權利變換",
                 "review_flags": ["flag", "other"], "links": {"taipei": ["003"]}},
            ], "links": {}},
        ],
    }


def test_payload_measurement_uses_every_node_and_project():
    from scripts.probe_tab2_numbers import measure_payload

    m = measure_payload(_payload())
    assert m["records"] == 3 and m["projects"] == 2
    assert m["bindings"] == 3 and m["distinct_real_cases"] == 3
    assert m["records_multiple_cases"] == 0
    assert m["recovered_nodes"] == 1
    assert m["virtual_entries"] == 1 and m["virtual_undated"] == 1
    assert m["lanes"]["事業計畫"] == 2  # 事業計畫 matches the repaired 事業換計畫
    assert m["lanes"].get("事業計畫、權利變換", 0) == 0
    etl = dm.measure_etl(_payload(), Path("D:/unused"))
    assert etl["date_first"] == "2002-03-21"
    assert etl["flagged_nodes"] == 2 and etl["flagged_projects"] == 2
    assert etl["repeat_records"] == 1 and etl["repeat_percent"] == 33


def test_node_measurement_adapter_requires_the_real_viewer_results():
    required = {key: 0 for key in dm.NODE_MEASUREMENT_KEYS}
    parsed = dm.parse_node_measurements(json.dumps(required))
    assert parsed["construction_events"] == 0
    with pytest.raises(dm.DocSyncError, match="missing"):
        dm.parse_node_measurements('{"construction_events": 1}')
    with pytest.raises(dm.DocSyncError):
        dm.parse_node_measurements("not json")


def test_real_documentation_pages_have_current_marked_facts():
    from scripts import sync_domain_model, sync_etl_process

    doc = dm.load_payload(dm.ROOT / "viewer" / "projects.data.js")
    etl, _ = sync_etl_process.render_current(doc, root=dm.ROOT, test_count=1484)
    assert 'data-doc-field="dataset-summary-en"' in etl
    assert "2026-11-12" in etl and "1,448" in etl and "676" in etl
    assert "1,444 records → 675 projects" not in etl
    assert "48 rows per Gregorian gazette" not in etl
    domain, _ = sync_domain_model.render_current(doc, root=dm.ROOT)
    assert 'data-doc-field="current-facts"' in domain
    assert "2026-11-12" in domain and "1,448 / 676" in domain
    assert "2026-10-15 payload" in domain  # historical evidence survives
    assert "83b7b2e" in domain


def test_configured_count_is_updated_only_in_the_current_dataset_sentence():
    source = ("context: |\n"
              "    Project: urTPE — list (臺北市都市更新核定案件一覽表, 1,444 approvals as emitted from the 2026-10-28\n"
              "    gazette, dated 2002-03-21–2026-10-28,\n"
              "    統計至 2026-10-28) into a dataset. ~70% stays a design observation.\n")
    updated = dm.sync_config_text(source, _payload())
    assert "3 approvals" in updated and "2002-03-21–2026-11-12" in updated
    assert "統計至 2026-11-12" in updated
    assert "~70% stays a design observation" in updated
    assert dm.sync_config_text(updated, _payload()) == updated
