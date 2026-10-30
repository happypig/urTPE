# -*- coding: utf-8 -*-
"""Superseded digests: a corrected re-upload is recorded, not silent (P3.7).

The defect this pins: ``store()`` replaces same-``gazette_id`` content with no
record, so every older index entry for that publication then fails its digest
check on every future run — noise that teaches operators to ignore the one line
that would report a real substitution. restore-2026-09-24-gazette, tasks 2.1/2.2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


@pytest.fixture
def archive(tmp_path) -> GazetteArchive:
    return GazetteArchive(tmp_path / "gazettes")


def _gazette(tmp_path, name: str, **kw) -> str:
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), ROC_ROWS, **kw)
    return str(path)


def test_re_store_with_different_bytes_records_the_superseded_digest(archive, tmp_path):
    """Same publication date, different content: the replacement is appended to
    the index as a re-store entry naming both digests, before the file changes."""
    original = _gazette(tmp_path, "orig", published="統計至115年8月11日")
    archive.record_ingest(original, "2026-08-11", record_count=5)
    old_sha = archive.entries()[-1].sha256
    n_entries = len(archive.entries())

    corrected = _gazette(tmp_path, "corrected", published="統計至115年8月11日",
                         footer_inside_last_cell=True)  # different bytes
    archive.store(corrected, "2026-08-11")

    entries = archive.entries()
    assert len(entries) == n_entries + 1, "the re-store appends exactly one entry"
    entry = entries[-1]
    assert entry.event == "re-store"
    assert entry.supersedes == old_sha, (
        "the entry must name the digest it replaced")
    assert entry.sha256 and entry.sha256 != old_sha
    # The held file now hashes to the new digest.
    assert archive.entries()[-1].sha256 == entry.sha256


def test_re_store_with_identical_bytes_is_still_a_no_op(archive, tmp_path):
    original = _gazette(tmp_path, "a", published="統計至115年8月11日")
    archive.record_ingest(original, "2026-08-11", record_count=5)
    before = len(archive.entries())
    archive.store(original, "2026-08-11")
    assert len(archive.entries()) == before, (
        "identical content must not append anything")


def test_verify_accepts_a_digest_the_index_documents_as_superseded(archive, tmp_path):
    """After a recorded re-store, the older entry's digest no longer matches the
    held file — but the index itself documents that replacement, so reporting it
    as damage would train operators to ignore verify() output."""
    original = _gazette(tmp_path, "orig", published="統計至115年8月11日")
    archive.record_ingest(original, "2026-08-11", record_count=5)
    corrected = _gazette(tmp_path, "corrected", published="統計至115年8月11日",
                         footer_inside_last_cell=True)
    archive.store(corrected, "2026-08-11")

    problems = archive.verify()
    digest_problems = [p for p in problems if "content differs" in p
                       and "2026-08-11" in p]
    assert digest_problems == [], (
        f"a recorded re-store must not read as damage: {digest_problems}")


def test_verify_still_reports_an_undocumented_substitution(archive, tmp_path):
    """A member whose bytes were swapped *without* a re-store entry is damage,
    exactly as before. The chain exception applies only when the index itself
    recorded the replacement."""
    original = _gazette(tmp_path, "orig", published="統計至115年8月11日")
    dest, _entry = archive.record_ingest(original, "2026-08-11", record_count=5)

    swapped = _gazette(tmp_path, "swapped", published="統計至115年8月11日",
                       footer_inside_last_cell=True)
    dest.write_bytes(Path(swapped).read_bytes())

    problems = archive.verify()
    assert any("content differs" in p and "2026-08-11" in p for p in problems), (
        "an undocumented substitution must still be reported")


def test_the_index_stays_append_only_across_a_re_store(archive, tmp_path):
    original = _gazette(tmp_path, "orig", published="統計至115年8月11日")
    archive.record_ingest(original, "2026-08-11", record_count=5)
    first = json.loads(archive.index_path.read_text(encoding="utf-8").splitlines()[0])
    n = len(archive.entries())

    corrected = _gazette(tmp_path, "corrected", published="統計至115年8月11日",
                         footer_inside_last_cell=True)
    archive.store(corrected, "2026-08-11")

    lines = archive.index_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == n + 1
    assert json.loads(lines[0]) == first, "earlier entries are never rewritten"


def test_predecessor_logic_is_unchanged_by_a_re_store(archive, tmp_path):
    """A re-store replaces bytes, never the publication's position in the chain."""
    a = _gazette(tmp_path, "a", published="統計至115年8月11日")
    archive.record_ingest(a, "2026-08-11", record_count=5)
    b = _gazette(tmp_path, "b", published="統計至115年9月24日")
    archive.record_ingest(b, "2026-09-24", record_count=6)

    corrected_a = _gazette(tmp_path, "a2", published="統計至115年8月11日",
                           footer_inside_last_cell=True)
    archive.store(corrected_a, "2026-08-11")

    assert archive.predecessor_of("2026-09-24") == "2026-08-11"
    assert archive.newest() == "2026-09-24"
