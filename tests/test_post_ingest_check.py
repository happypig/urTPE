"""Offline checks for bounded post-ingest verification."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import post_ingest_check as pic


def _doc():
    return {
        "schema_version": 2,
        "published_date": "2026-11-12",
        "generated_at": "2026-11-18T22:36:36+08:00",
        "counts": {"projects": 2, "records": 3},
        "projects": [
            {"project_id": "a", "anchor_recno": 2, "edges": [],
             "nodes": [{"recno": 1}, {"recno": 2}]},
            {"project_id": "b", "anchor_recno": 3, "edges": [],
             "nodes": [{"recno": 3}]},
        ],
    }


def _emission(root: Path):
    (root / "data").mkdir()
    (root / "viewer").mkdir()
    doc = _doc()
    (root / "data" / "projects.json").write_text(json.dumps(doc), encoding="utf-8")
    (root / "viewer" / "projects.data.js").write_text(
        "window.PROJECTS = " + json.dumps(doc) + ";", encoding="utf-8")
    for name, key in [("raw.tsv", "編號"), ("clean.tsv", "recno"), ("merged.tsv", "recno")]:
        (root / "data" / name).write_text(
            key + "\tother\n1\ta\n2\tb\n3\tc\n", encoding="utf-8")
    (root / "data" / "review_report.txt").write_text(
        "tripwire: PASS\nINCOMPLETE: 0 筆\n", encoding="utf-8")
    return doc


def test_partition_covers_all_five_layers(tmp_path):
    _emission(tmp_path)
    assert pic.emission_faults(tmp_path) == []
    (tmp_path / "data" / "clean.tsv").write_text("recno\n1\n2\n", encoding="utf-8")
    assert any("3" in fault for fault in pic.emission_faults(tmp_path))
    (tmp_path / "data" / "clean.tsv").write_text("recno\n1\n2\n2\n3\n", encoding="utf-8")
    assert any("duplicate" in fault for fault in pic.emission_faults(tmp_path))


def test_viewer_mismatch_and_malformed_files_are_named(tmp_path):
    doc = _emission(tmp_path)
    doc["counts"]["records"] = 2
    (tmp_path / "data" / "projects.json").write_text(json.dumps(doc), encoding="utf-8")
    assert any("viewer" in fault for fault in pic.emission_faults(tmp_path))
    (tmp_path / "data" / "projects.json").write_text("{", encoding="utf-8")
    assert any("projects.json" in fault for fault in pic.emission_faults(tmp_path))
    (tmp_path / "data" / "projects.json").unlink()
    assert any("projects.json" in fault for fault in pic.emission_faults(tmp_path))


def test_named_truncation_is_distinct_from_an_unexplained_gap(tmp_path):
    _emission(tmp_path)
    (tmp_path / "data" / "review_report.txt").write_text(
        "tripwire: PASS\n  INCOMPLETE: 1 record(s) excluded because the publisher "
        "truncated their 地號 cell — 編號 194\n", encoding="utf-8")
    assert pic.truncation_exclusions(tmp_path) == [194]
    (tmp_path / "data" / "review_report.txt").write_text(
        "RECOVERED: 0 筆\nINCOMPLETE: 1 筆 (still excluded)\n"
        "  編號 194: residual\n", encoding="utf-8")
    assert pic.truncation_exclusions(tmp_path) == [194]


def _ok(*args, **kwargs):
    return subprocess.CompletedProcess(args, 0, stdout="all checks passed", stderr="")


def test_recovery_is_once_then_rechecked_before_reports(tmp_path, monkeypatch):
    _emission(tmp_path)
    calls = []
    states = iter([["truncated: 194"], [], []])
    monkeypatch.setattr(pic, "archived_pdf_for", lambda *a: Path("archived.pdf"))

    def command(cmd, **kwargs):
        calls.append(cmd)
        return _ok()

    def validator(root):
        calls.append("checks")
        return next(states)

    monkeypatch.setattr(pic, "generate_reports", lambda *a, **k: calls.append("reports"))
    monkeypatch.setattr(pic, "run_command", command)
    assert pic.run(["--root", str(tmp_path)], validator=validator,
                   command_runner=command) == 0
    recovery = next(c for c in calls if isinstance(c, list) and "--recover-truncated" in c)
    assert recovery.count("--recover-truncated") == 1
    assert "--allow-reconcile-block" not in recovery and "--no-archive" not in recovery
    assert calls.index("checks") < calls.index("reports")
    assert not any(isinstance(c, list) and c[0] == "git" for c in calls)


def test_refusal_and_check_only_never_generate(tmp_path, monkeypatch):
    _emission(tmp_path)
    calls = []
    monkeypatch.setattr(pic, "archived_pdf_for", lambda *a: Path("archived.pdf"))
    monkeypatch.setattr(pic, "run_command", lambda *a, **k: calls.append(a) or _ok())
    monkeypatch.setattr(pic, "run_local_checks", lambda *a, **k: None if calls.append("checks") is None else [])
    monkeypatch.setattr(pic, "generate_reports", lambda *a, **k: calls.append("reports") or [])
    assert pic.run(["--root", str(tmp_path)], validator=lambda root: ["truncated: 194"],
                   command_runner=lambda *a, **k: subprocess.CompletedProcess(a, 2)) == 1
    assert "reports" not in calls
    assert pic.run(["--root", str(tmp_path), "--check-only"],
                   validator=lambda root: ["stale documentation"],
                   command_runner=lambda *a, **k: calls.append("unexpected") or _ok()) == 1
    assert "reports" not in calls


def test_latest_p168_snapshot_is_verified_not_copied_blindly(tmp_path):
    rows = [{"case_id": "2", "stage": "核定階段"}, {"case_id": "1", "stage": "審查中"}]
    body = json.dumps(sorted(rows, key=lambda r: r["case_id"]),
                      ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    archive = tmp_path / "archive"
    snap = archive / "p168_snapshots" / ("p168-" + digest[:16] + ".json")
    snap.parent.mkdir(parents=True)
    snap.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    (archive / "p168_state.json").write_text(json.dumps(
        {"sha256": digest, "checked_at": "2026-11-18T12:00:00+00:00"}), encoding="utf-8")
    selected = pic.latest_p168_snapshot(archive)
    assert selected["sha256"] == digest and selected["rows"] == rows
    assert pic.refresh_p168_input(archive, tmp_path / "data")["rows"] == rows
    assert json.loads((tmp_path / "data" / "p168_all.meta.json").read_text())["checked_at"]
    (archive / "p168_state.json").write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(pic.CheckFailure, match="snapshot"):
        pic.latest_p168_snapshot(archive)
