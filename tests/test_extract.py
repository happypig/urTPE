"""Extraction adapter tests: positional parse of a synthetic PDF."""

from __future__ import annotations

import pymupdf

from urtpe.extract import extract_pdf, to_raw_records
from tests.fixtures import SAMPLE_ROWS, build_sample_pdf


def _fixture(tmp_path):
    path = tmp_path / "sample.pdf"
    build_sample_pdf(str(path), SAMPLE_ROWS)
    return path


def test_extracts_all_records(tmp_path):
    recs = extract_pdf(str(_fixture(tmp_path)))
    assert len(recs) == len(SAMPLE_ROWS)


def test_recno_order_preserved(tmp_path):
    recs = extract_pdf(str(_fixture(tmp_path)))
    assert [r["recno"] for r in recs] == ["1", "2", "3"]


def test_cells_are_joined_without_whitespace(tmp_path):
    recs = extract_pdf(str(_fixture(tmp_path)))
    assert recs[0]["name"] == SAMPLE_ROWS[0][3]
    assert recs[0]["land"] == SAMPLE_ROWS[0][4]
    assert recs[0]["implementer"] == SAMPLE_ROWS[0][5]


def test_furniture_is_excluded(tmp_path):
    """Header words and footer page numbers must not leak into records."""
    recs = extract_pdf(str(_fixture(tmp_path)))
    for r in recs:
        for value in r.values():
            assert "一覽表" not in value
            assert "統計至" not in value
    assert "編號" not in recs[0]["recno"]


def test_to_raw_records_marks_missing_required_cells(tmp_path):
    recs = extract_pdf(str(_fixture(tmp_path)))
    recs[1]["name"] = ""
    recs[1]["land"] = ""
    raws = to_raw_records(recs)
    assert "案名缺漏" in raws[1].parse_error
    assert "地號缺漏" in raws[1].parse_error
    assert raws[0].parse_error == ""
    assert raws[0].recno == 1


def test_raw_tsv_roundtrip(tmp_path):
    from urtpe.io import raw_to_tsv

    raws = to_raw_records(extract_pdf(str(_fixture(tmp_path))))
    tsv = raw_to_tsv(raws)
    lines = tsv.strip().split("\n")
    assert len(lines) == len(raws) + 1
    assert lines[0].startswith("編號\t核定日期")