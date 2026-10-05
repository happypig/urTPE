"""Gate behaviour: a refused ingestion must leave the working tree untouched.

Tasks 1.5 and 2.2 of robust-gazette-ingestion — both require that a failure writes
nothing, not merely that it is reported.
"""

from __future__ import annotations

import hashlib

import pytest

from urtpe import cli, extract as E
from urtpe.tripwire import Tripwire, TripwireResult, TripwireFailure
from tests.gazette_fixtures import ROC_ROWS, write_gazette

ARTIFACTS = ["raw.tsv", "clean.tsv", "merged.tsv", "projects.json",
             "review_report.txt", "projects.data.js"]


def _digest(out) -> dict[str, str]:
    return {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
            for name in ARTIFACTS if (out / name).exists()}


def _good_pdf(tmp_path, published="統計至115年8月11日") -> str:
    path = tmp_path / "good.pdf"
    write_gazette(str(path), ROC_ROWS, published=published)
    return str(path)


def test_gate_failure_writes_no_artifact(tmp_path):
    """A structural fault must abort before the first write."""
    pdf = tmp_path / "borderless.pdf"
    write_gazette(str(pdf), ROC_ROWS, borderless_pages=(0,))
    out = tmp_path / "out"
    out.mkdir()
    (out / "raw.tsv").write_text("PRE-EXISTING\n", encoding="utf-8")
    before = _digest(out)

    assert cli.main([str(pdf), "-o", str(out)]) == 3

    assert _digest(out) == before
    assert (out / "raw.tsv").read_text(encoding="utf-8") == "PRE-EXISTING\n"


def test_tripwire_failure_leaves_every_artifact_byte_identical(tmp_path):
    """A contiguous-編號 gap must not reach disk, whatever was there before."""
    pdf = _good_pdf(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out)]) == 0
    baseline = _digest(out)
    assert baseline, "the first run must produce artifacts"

    # Now feed a gazette whose 編號 has a hole: drop 編號 3 from the source data.
    holed = [r for r in ROC_ROWS if r[0] != 3]
    path = tmp_path / "holed.pdf"
    write_gazette(str(path), holed, published="統計至115年9月24日")

    assert cli.main([str(path), "-o", str(out)]) == 4

    assert _digest(out) == baseline


def test_unparseable_date_aborts_and_writes_nothing(tmp_path):
    pdf = tmp_path / "baddate.pdf"
    rows = [(r[0], "not-a-date", *r[2:]) for r in ROC_ROWS]
    write_gazette(str(pdf), rows, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out)]) == 4
    for name in ARTIFACTS:
        assert not (out / name).exists(), name


def test_tripwire_names_the_missing_recno(tmp_path):
    recs = [{"recno": str(i), "date": "115/8/27"} for i in (1, 2, 4, 5)]
    faults = Tripwire().check(recs)
    assert any("(expected 1..5): 3" in f for f in faults)
    result = TripwireResult(ok=False, faults=faults, record_count=4)
    with pytest.raises(TripwireFailure) as excinfo:
        raise TripwireFailure(result)
    assert "(expected 1..5): 3" in str(excinfo.value)