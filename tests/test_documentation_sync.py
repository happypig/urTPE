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


def test_operating_runbook_keeps_acquisition_repair_and_publication_distinct():
    """The runbook must not turn acquisition or a successful CLI into publication."""
    source = (dm.ROOT / "docs" / "pipeline" / "etl_process.md").read_text(encoding="utf-8")
    runbook = source.split("## 11. Operating the pipeline", 1)[1]
    steps = [
        "python scripts/poll_gazette.py",
        "python scripts/poll_p168.py",
        "--recover-truncated",
        "python scripts/post_ingest_check.py",
        "python scripts/post_ingest_check.py --check-only",
        "git push origin main",
        "python scripts/check_deploy.py",
    ]
    positions = [runbook.index(command) for command in steps]
    assert positions == sorted(positions)
    assert "`publish_release_diff.py` regenerates,\ncommits and pushes only the four generated pages" in runbook
    assert "`python scripts/run_cycle.py --resume <sha256>`" in runbook
    assert "Never pass\n   `--allow-reconcile-block` or `--no-archive`" in runbook
    assert "Exit 0 means the CLI wrote its output; it\n   does not mean that git committed it." in runbook
    assert "--allow-reconcile-block" in runbook
    assert "never qualifies for a viewer-only repair" in runbook
    assert "path-limited commit" in runbook
    assert "does not compare release or coverage\n   report freshness" in runbook
    assert "1,494\n  passed, 1 skipped, 4 xfailed from 1,499 collected" in runbook


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


# --- the sync date is a generation timestamp, not a fact the check compares ----
#
# documentation-dataset-sync: "Documentation is current -- check mode after
# successful synchronisation exits successfully", and a re-run changes nothing
# "other than a permitted generation timestamp". `--check` compared the footer
# against date.today(), so it went STALE on the next calendar day with no fact
# changed (measured 2026-11-22: the footer said 2026-11-20). post_ingest_check.py
# --check-only runs the same command, so its read-only pass failed daily too.

_FOOTER = ("footer-provenance-en", "footer-provenance-zh")
_FOOTER_SOURCE = ('<span data-doc-field="footer-provenance-en"></span>'
                  '<span data-doc-field="footer-provenance-zh"></span>')


def _footer_fields(fields):
    return {name: fields[name] for name in _FOOTER}


def test_check_does_not_go_stale_because_the_day_changed():
    from scripts import sync_etl_process as sync

    written = sync.fields_for(_payload(), dm.ROOT, test_count=7, measurement_date="2026-11-20")
    rendered, _ = dm.replace_fields(_FOOTER_SOURCE, _footer_fields(written))
    stored = sync.stored_measurement_date(rendered)
    assert stored == "2026-11-20"
    # a later day: the check reads the stored date back instead of using today
    checked = sync.fields_for(_payload(), dm.ROOT, test_count=7, measurement_date=stored)
    _, changed = dm.replace_fields(rendered, _footer_fields(checked))
    assert changed == []


def test_a_moved_payload_date_is_still_reported_stale():
    from scripts import sync_etl_process as sync

    old = dict(_payload(), published_date="2026-10-28")
    written = sync.fields_for(old, dm.ROOT, test_count=7, measurement_date="2026-11-20")
    rendered, _ = dm.replace_fields(_FOOTER_SOURCE, _footer_fields(written))
    stored = sync.stored_measurement_date(rendered)
    checked = sync.fields_for(_payload(), dm.ROOT, test_count=7, measurement_date=stored)
    _, changed = dm.replace_fields(rendered, _footer_fields(checked))
    assert changed == list(_FOOTER)


def test_no_stored_date_means_the_check_uses_today_and_reports_stale():
    from scripts import sync_etl_process as sync

    assert sync.stored_measurement_date(_FOOTER_SOURCE) is None


def _sandbox_for_main(tmp_path, monkeypatch, written_on):
    """A copy of the real page, synced as of `written_on`, in a temp tree."""
    from scripts import sync_etl_process as sync

    (tmp_path / "docs").mkdir()
    (tmp_path / "viewer").mkdir()
    (tmp_path / "viewer" / "projects.data.js").write_text(
        "window.PROJECTS = " + json.dumps(_payload(), ensure_ascii=False) + ";",
        encoding="utf-8")
    page = tmp_path / "docs" / "etl_process.html"
    page.write_text((dm.ROOT / "docs" / "etl_process.html").read_text(encoding="utf-8"),
                    encoding="utf-8")
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    monkeypatch.setattr(sync, "collected_test_count", lambda root: 7)
    monkeypatch.setattr(sync, "sync_config", lambda doc, root: False)
    dm.write_or_check(page, sync.fields_for(_payload(), tmp_path, 7, written_on))
    return sync, page


def test_main_check_exits_zero_on_a_page_synced_on_an_earlier_day(tmp_path, monkeypatch):
    sync, page = _sandbox_for_main(tmp_path, monkeypatch, "2000-01-01")
    assert sync.main(["--check"]) == 0


def test_main_check_still_exits_nonzero_when_a_figure_is_stale(tmp_path, monkeypatch):
    sync, page = _sandbox_for_main(tmp_path, monkeypatch, "2000-01-01")
    monkeypatch.setattr(sync, "collected_test_count", lambda root: 8)
    assert sync.main(["--check"]) == 1


def test_a_write_run_stamps_the_day_it_ran(tmp_path, monkeypatch):
    sync, page = _sandbox_for_main(tmp_path, monkeypatch, "2000-01-01")
    monkeypatch.setattr(sync, "collected_test_count", lambda root: 8)
    assert sync.main([]) == 0
    assert "synchronised 2000-01-01" not in page.read_text(encoding="utf-8")
    assert sync.main(["--check"]) == 0


# ---- domain-model.html: the same day-change rule as the ETL page --------------------------
# Measured 2026-11-23: `sync_domain_model.py --check` reported six fields STALE with no figure
# changed, because `fields_for` stamped today's date into "measured <date>" and the check
# compared it with the date the page already carried (written 2026-11-20).

_VIEWER = {"construction_events": 10, "ambiguous_markers": 3, "source_case_missing": 1,
           "inverted_pairs": 2, "inverted_projects": 2}


def _domain_sandbox(tmp_path, monkeypatch, written_on):
    import shutil
    from scripts import sync_domain_model as sync

    (tmp_path / "docs").mkdir()
    (tmp_path / "viewer").mkdir()
    shutil.copy(dm.ROOT / "viewer" / "projects.data.js", tmp_path / "viewer" / "projects.data.js")
    page = tmp_path / "docs" / "domain-model.html"
    shutil.copy(dm.ROOT / "docs" / "domain-model.html", page)
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    monkeypatch.setattr(sync, "measure_viewer", lambda: dict(_VIEWER))
    doc = dm.load_payload(tmp_path / "viewer" / "projects.data.js")
    dm.write_or_check(page, sync.fields_for(doc, dict(_VIEWER), measurement_date=written_on))
    return sync, page, doc


def test_domain_model_fields_carry_the_given_measurement_date(tmp_path, monkeypatch):
    sync, page, doc = _domain_sandbox(tmp_path, monkeypatch, "2000-01-01")
    fields = sync.fields_for(doc, dict(_VIEWER), measurement_date="2000-01-01")
    assert "measured 2000-01-01" in fields["measurement-source"]
    assert sync.stored_measurement_date(page.read_text(encoding="utf-8")) == "2000-01-01"


def test_domain_model_with_no_stored_date_reads_none():
    from scripts import sync_domain_model as sync

    assert sync.stored_measurement_date('<span data-doc-field="measurement-source"></span>') is None


def test_domain_model_check_exits_zero_on_a_page_synced_on_an_earlier_day(tmp_path, monkeypatch):
    sync, page, doc = _domain_sandbox(tmp_path, monkeypatch, "2000-01-01")
    assert sync.main(["--check"]) == 0


def test_domain_model_check_still_exits_nonzero_when_a_figure_moved(tmp_path, monkeypatch):
    sync, page, doc = _domain_sandbox(tmp_path, monkeypatch, "2000-01-01")
    monkeypatch.setattr(sync, "measure_viewer", lambda: dict(_VIEWER, ambiguous_markers=4))
    assert sync.main(["--check"]) == 1


def test_domain_model_write_run_stamps_today(tmp_path, monkeypatch):
    import datetime as dt
    sync, page, doc = _domain_sandbox(tmp_path, monkeypatch, "2000-01-01")
    assert sync.main([]) == 0
    assert sync.stored_measurement_date(page.read_text(encoding="utf-8")) == dt.date.today().isoformat()
