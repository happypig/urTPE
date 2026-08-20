"""End-to-end pipeline test on the synthetic sample PDF."""

from __future__ import annotations

from urtpe import cli
from tests.fixtures import SAMPLE_ROWS, build_sample_pdf


def test_full_pipeline_emits_all_outputs(tmp_path):
    pdf = tmp_path / "sample.pdf"
    build_sample_pdf(str(pdf), SAMPLE_ROWS)
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out)]) == 0

    assert (out / "raw.tsv").exists()
    assert (out / "clean.tsv").exists()
    assert (out / "merged.tsv").exists()
    assert (out / "review_report.txt").exists()
    assert (out / "projects.json").exists()

    raw = (out / "raw.tsv").read_text(encoding="utf-8").strip().split("\n")
    assert len(raw) == len(SAMPLE_ROWS) + 1

    import json

    doc = json.loads((out / "projects.json").read_text(encoding="utf-8"))
    assert doc["counts"]["records"] == len(SAMPLE_ROWS)
    assert len(doc["projects"]) == 1


def test_cli_accepts_no_tsv_flag(tmp_path):
    pdf = tmp_path / "sample.pdf"
    build_sample_pdf(str(pdf), SAMPLE_ROWS[:1])
    out = tmp_path / "out2"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out), "--no-tsv"]) == 0
    assert (out / "projects.json").exists()
    assert not (out / "raw.tsv").exists()