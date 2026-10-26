# -*- coding: utf-8 -*-
"""End-to-end acceptance for the recovery flag — task 2.9 (offline).

A flagged run on the acceptance gazette (the 15 real truncated rows of the
2026-10-15 gazette plus the real residual row of the 2026-08-11 gazette) against
responses recorded live on 2026-10-26:

* the 15 truncated rows are recovered with provenance and enter the merge;
* 美仁段 stays recovered with a *partial* list (its reconstruction refuses);
* 930 attaches both zone cases flagged ``ambiguous-zone``;
* the residual row stays excluded and named;
* the report shows ``RECOVERED: 15 … / INCOMPLETE: 1 …`` and keeps the
  not-a-faithful-copy statement;
* a run without the flag is byte-identical to the pre-change output
  (``golden_unflagged/``, captured from the pre-change code before any
  implementation) and makes no recovery request at all.

The expected live numbers for the real gazette (task 6.2): ~1,442 records
(1,427 + the 15 recovered), +5 projects, RECOVERED: 15 / INCOMPLETE: 0.
"""

from __future__ import annotations

import json

import pytest

from urtpe import cli
from urtpe import recovery_pass
from urtpe import recovery_sources as RS
from tests.fixtures_recovery import (
    FIXTURE_DIR,
    build_fixture_pdf,
    families,
    geoserver_candidates,
    tops,
)

GOLDEN = FIXTURE_DIR / "golden_unflagged"


# --- fakes standing in for the two HTTP surfaces -----------------------------

class FakeAshx:
    """Serves the recorded family/top bodies (parsed as the adapter would)."""

    def case_family(self, sectstr, mono, suno):
        key = f"{sectstr}|{mono}|{suno}"
        body = families().get(key, "[]")
        return RS.parse_family_body(body)

    def case_top(self, case_id):
        body = tops().get(case_id)
        if body is None:
            return {}
        return RS.parse_top_body(body)


class FakeGeo:
    """Serves the live-computed membership sets (recorded per case id)."""

    def unit_geometry(self, case_id, sect_name):
        entries = geoserver_candidates().get(case_id, [])
        cands = {land: frac for land, frac in entries}
        return RS.UnitGeometry(candidates=cands, section_parcels=set(cands))


def _isolate_archive(monkeypatch, tmp_path):
    # The archive root constant is read at import time (archive.py), so an env
    # override here would be a no-op; the CLI flags bypass it entirely and give
    # each run a private archive — no predecessor, no reconciliation, and the
    # fixture PDF lands in a temp directory instead of the session archive.
    return ["--archive-root", str(tmp_path / "archive")]


def _read(path):
    return (path / "review_report.txt").read_text(encoding="utf-8")


# --- 2.9 the flagged run ------------------------------------------------------

def test_flagged_run_recovers_all_measured_rows(tmp_path, monkeypatch):
    isolation = _isolate_archive(monkeypatch, tmp_path)
    monkeypatch.setattr(recovery_pass, "default_clients",
                        lambda: (FakeAshx(), FakeGeo()))
    pdf = build_fixture_pdf(str(tmp_path / "gazette.pdf"))
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out), "--recover-truncated", *isolation]) == 0

    # 24 rows read: 8 fillers + 15 recovered + 1 residual kept out of clean/merge
    clean_lines = (out / "clean.tsv").read_text(encoding="utf-8").strip().split("\n")
    assert len(clean_lines) == 24  # 23 records + header
    doc = json.loads((out / "projects.json").read_text(encoding="utf-8"))
    assert doc["counts"]["records"] == 23
    # 8 recovered units + 8 fillers (the real gazette's +5 comes from 3 of the 8
    # units already having projects; in this fixture all 8 are new)
    assert doc["counts"]["projects"] == 16

    # the residual stays in raw.tsv, marked as a source fault, out of clean.tsv
    raw = (out / "raw.tsv").read_text(encoding="utf-8")
    assert "publisher-truncated" in raw
    clean_text = (out / "clean.tsv").read_text(encoding="utf-8")
    assert "南港段一小段561" not in clean_text

    # the 虎林段 unit's full list is reconstructed: the row now closes at 138
    # with the GIS tail, and carries the list source in provenance
    row1 = next(line for line in clean_lines[1:] if line.startswith("1\t"))
    assert "93-41地號等138筆土地" in row1
    assert "93-17" in row1
    # 美仁段 keeps its fragment (post-repair), flagged partial
    row2 = next(line for line in clean_lines[1:] if line.startswith("2\t"))
    assert "718-1" in row2 and "78-1\t" not in row2
    assert "740-1" in row2  # the fragment ends where the publisher stopped
    assert "93-41" not in row2

    # provenance reaches the emitted graph
    projects = {p["project_id"]: p for p in doc["projects"]}
    hulin = projects["信義區-虎林段四小段-38地號等138筆"]
    recovered_nodes = [n for n in hulin["nodes"] if n.get("recovery")]
    assert len(recovered_nodes) == 3  # 編號 1, 3, 6 of the fixture
    prov = recovered_nodes[0]["recovery"]
    assert prov["cases"], "provenance names every attached case id"
    assert prov["list_source"] == "gazette fragment + GIS tail"

    meiren = projects["松山區-美仁段二小段-694地號等74筆"]
    node2 = next(n for n in meiren["nodes"] if n["recno"] == 2)
    assert node2["recovery"]["flags"]["partial"] is True
    assert node2["recovery"]["flags"]["normalized"] == ["78-1→718-1"]

    # the zone pair attaches both cases under a single land core
    shuangyuan = projects["萬華區-雙園段二小段-505地號等77筆"]
    node12 = next(n for n in shuangyuan["nodes"] if n["recno"] == 12)
    assert sorted(node12["recovery"]["cases"]) == ["09610233", "09610237"]
    assert node12["recovery"]["flags"]["ambiguous-zone"] is True

    # the report splits recovered from residual and keeps the honesty statement
    report = _read(out)
    assert "RECOVERED: 15" in report
    assert "INCOMPLETE: 1" in report
    assert "not a faithful copy" in report or "NOT a faithful copy" in report
    assert "11411014" in report  # 編號 79's case id appears with its provenance


# --- 2.9 the unflagged run is the pre-change output ---------------------------

def test_unflagged_run_is_byte_identical_to_pre_change(tmp_path, monkeypatch):
    isolation = _isolate_archive(monkeypatch, tmp_path)

    def no_network(*a, **k):
        raise AssertionError("a run without the flag must not touch the recovery APIs")

    monkeypatch.setattr(RS, "_post_form", no_network)
    monkeypatch.setattr(RS, "_get_json", no_network)

    pdf = build_fixture_pdf(str(tmp_path / "gazette.pdf"))
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out), *isolation]) == 0

    for name in ("raw.tsv", "clean.tsv", "merged.tsv", "review_report.txt"):
        assert (out / name).read_bytes() == (GOLDEN / name).read_bytes(), name

    def norm(text):
        doc = json.loads(text)
        doc.pop("generated_at", None)   # wall-clock emission timestamp
        doc.pop("source", None)         # the run's PDF path
        return json.dumps(doc, sort_keys=True, ensure_ascii=False)

    assert norm((out / "projects.json").read_text(encoding="utf-8")) == \
        norm((GOLDEN / "projects.json").read_text(encoding="utf-8"))


def test_flagged_run_reports_exclusions_it_cannot_recover(tmp_path, monkeypatch):
    """With every source dead, the flagged run equals the plain exclusion path
    plus an honest INCOMPLETE line — recovery never blocks emission."""
    isolation = _isolate_archive(monkeypatch, tmp_path)

    class DeadAshx:
        def case_family(self, *a):
            raise RS.SourceUnavailable("offline")

    class DeadGeo:
        def unit_geometry(self, *a):
            raise RS.SourceUnavailable("offline")

    monkeypatch.setattr(recovery_pass, "default_clients",
                        lambda: (DeadAshx(), DeadGeo()))

    pdf = build_fixture_pdf(str(tmp_path / "gazette.pdf"))
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out), "--recover-truncated", *isolation]) == 0

    report = _read(out)
    assert "RECOVERED: 0" in report
    assert "INCOMPLETE: 16" in report
    doc = json.loads((out / "projects.json").read_text(encoding="utf-8"))
    assert doc["counts"]["records"] == 8
