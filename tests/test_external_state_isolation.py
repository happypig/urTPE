"""Regression tests for state that lives outside the git working tree.

The gazette archive and the correction ledger default to a sibling of the
repository, so every process that imports urtpe shares them — including the test
suite. Fixture PDFs can carry a real publication's 統計至 date, which is how a test
run came to overwrite a live archive member.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from urtpe.archive import DEFAULT_ARCHIVE_ROOT, GazetteArchive
from urtpe.ledger import DEFAULT_LEDGER_PATH, CorrectionLedger
from tests.gazette_fixtures import ROC_ROWS, write_gazette


def test_defaults_are_redirected_by_the_environment():
    """conftest points both at a temp dir, so a test cannot reach the live state."""
    root = Path(DEFAULT_ARCHIVE_ROOT)
    assert "urtpe-test-state" in str(root), root
    ledger = Path(DEFAULT_LEDGER_PATH)
    assert "urtpe-test-state" in str(ledger), ledger
    assert ledger.parent == root.parent


def test_fixture_dates_cannot_collide_with_a_real_publication():
    """The sample fixtures use 115年8月11日, which is a genuine gazette date.

    That is why isolation has to be structural rather than a matter of remembering
    a flag: the collision is invisible at the call site.
    """
    import tempfile

    from urtpe.extract import gazette_id_for

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "fixture.pdf")
        write_gazette(path, ROC_ROWS, published="統計至115年8月11日")
        assert gazette_id_for(path) == "2026-08-11"


def test_cli_run_archives_into_the_session_directory_not_the_repo(tmp_path):
    from urtpe import cli

    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([str(pdf), "-o", str(out)]) == 0

    root = Path(GazetteArchive().root)
    repo_root = Path(__file__).resolve().parents[1]
    stored = root / "核定案件-2026-08-11.pdf"
    assert stored.exists(), "the gazette should have been archived"
    assert repo_root not in stored.parents, f"archived inside the repo: {stored}"
    assert "urtpe-test-state" in str(stored), stored


def test_ledger_is_not_appended_to_by_a_plain_run(tmp_path):
    from urtpe import cli

    pdf = tmp_path / "g.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()
    before = Path(CorrectionLedger().path).read_bytes() if Path(CorrectionLedger().path).exists() else b""
    assert cli.main([str(pdf), "-o", str(out)]) == 0
    after = Path(CorrectionLedger().path).read_bytes() if Path(CorrectionLedger().path).exists() else b""
    assert before == after


def test_archive_verify_detects_a_member_swapped_for_another(tmp_path):
    """An *undocumented* substitution is damage; a recorded re-store is not.

    restore-2026-09-24-gazette changed store() to append a re-store entry naming
    the superseded digest, so a store() call no longer leaves verify() reporting
    damage — the replacement is documented in the index. The damage path this
    test guards is bytes changed with no such entry, which the second half pins.
    """
    arch = GazetteArchive(tmp_path / "gazettes")
    pdf = tmp_path / "a.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    dest, _entry = arch.record_ingest(str(pdf), "2026-08-11", record_count=5)

    other = tmp_path / "b.pdf"
    write_gazette(str(other), ROC_ROWS[:2], published="統計至115年8月11日")

    # Through store(): a recorded re-store — verify() accepts it, the chain
    # documents it.
    arch.store(str(other), "2026-08-11")
    assert not arch.verify(), (
        "a recorded re-store is not damage; verify() must not cry wolf")

    # Direct byte replacement with no re-store entry: still damage.
    swapped = tmp_path / "c.pdf"
    write_gazette(str(swapped), ROC_ROWS[:3], published="統計至115年8月11日",
                  footer_inside_last_cell=True)
    dest.write_bytes(swapped.read_bytes())
    assert arch.verify(), "an undocumented substitution must be reported"


def test_index_entries_are_never_rewritten(tmp_path):
    arch = GazetteArchive(tmp_path / "gazettes")
    pdf = tmp_path / "a.pdf"
    write_gazette(str(pdf), ROC_ROWS, published="統計至115年8月11日")
    arch.record_ingest(str(pdf), "2026-08-11", record_count=5)
    first = arch.index_path.read_text(encoding="utf-8")
    arch.append_index(type(arch.entries()[0])(**{**arch.entries()[0].__dict__,
                                                "record_count": 99}))
    lines = arch.index_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == first.splitlines()[0]
    assert json.loads(lines[1])["record_count"] == 99