# -*- coding: utf-8 -*-
"""Reconciliation can actually reach its predecessor.

Found by running the cascade measurement rather than by reading the code. Ingesting
1150827 then 1151002 into the same archive produced two change sets, both reporting
`comparable: false` while `index.jsonl` listed both publications -- because
`predecessor_of` required the incoming gazette to be *already archived*, and cli.py writes
it into the archive fifty lines after the reconciliation that wanted it.

So every ingestion reported "no comparison possible". That is the real reason the parked
portal cascade's un-parking trigger -- "a reliable change set across at least two
consecutive ingestions" -- had never been satisfiable: it was structurally impossible,
not merely unproven.

Written against the pre-existing archive API (`store` + `record_ingest` with a real path)
so it tests only the lookup, with no dependency on the index-schema work that shipped
alongside the fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive  # noqa: E402


@pytest.fixture
def archive(tmp_path):
    return GazetteArchive(tmp_path / "gazettes")


def _store(archive, gazette_id, tmp_path, body=b"%PDF-1.7 gazette bytes"):
    src = tmp_path / f"{gazette_id}.pdf"
    src.write_bytes(body)
    archive.record_ingest(src, gazette_id, published_date=gazette_id)


def test_the_predecessor_is_found_while_the_gazette_is_still_unarchived(archive, tmp_path):
    """The ordering that matters: the predecessor is archived, the current one is not."""
    _store(archive, "2026-08-27", tmp_path)

    assert archive.predecessor_of("2026-09-24") == "2026-08-27", (
        "cli.py resolves the predecessor before archiving the current gazette, so it is "
        "absent from the archive at the moment it is looked up")


def test_a_gazette_already_archived_still_resolves_its_predecessor(archive, tmp_path):
    _store(archive, "2026-08-27", tmp_path)
    _store(archive, "2026-09-24", tmp_path)

    assert archive.predecessor_of("2026-09-24") == "2026-08-27"


def test_the_first_publication_has_no_predecessor(archive, tmp_path):
    _store(archive, "2026-08-27", tmp_path)

    assert archive.predecessor_of("2026-08-27") is None, (
        "the oldest publication genuinely has nothing before it")


def test_an_older_gazette_read_later_does_not_borrow_a_newer_predecessor(archive, tmp_path):
    """Re-reading an older publication must compare against what came before it."""
    _store(archive, "2026-08-20", tmp_path)
    _store(archive, "2026-08-27", tmp_path)
    _store(archive, "2026-09-24", tmp_path)

    assert archive.predecessor_of("2026-08-27") == "2026-08-20"


def test_an_unrelated_gazette_id_resolves_to_the_latest_earlier_publication(archive, tmp_path):
    _store(archive, "2026-08-27", tmp_path)
    _store(archive, "2026-09-24", tmp_path)

    assert archive.predecessor_of("2026-12-01") == "2026-09-24"


def test_the_predecessor_resolves_to_a_readable_file(archive, tmp_path):
    """The end the measurement needed: an id that reaches a document."""
    _store(archive, "2026-08-27", tmp_path, b"%PDF-1.7 an older gazette")

    prev_id = archive.predecessor_of("2026-09-24")
    prev_path = archive.path_of(prev_id) if prev_id else None

    assert prev_id == "2026-08-27"
    assert prev_path is not None and prev_path.exists(), (
        "an id resolving to no readable file would still yield no comparison")


def test_an_empty_archive_has_no_predecessor(archive):
    assert archive.predecessor_of("2026-08-27") is None


def test_a_publication_older_than_everything_archived_has_no_predecessor(archive, tmp_path):
    """Re-reading the very oldest gazette compares against nothing, not against itself."""
    _store(archive, "2026-08-20", tmp_path)
    _store(archive, "2026-09-24", tmp_path)

    assert archive.predecessor_of("2026-01-01") is None