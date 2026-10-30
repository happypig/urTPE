# -*- coding: utf-8 -*-
"""Re-filing a quarantined member preserves the evidence (task 3.2).

restore-2026-09-24-gazette: the 09-24 PDF sat in `skipped since abnormal SN\`
under its download name while the poller's index recorded its digest. The
refile path copies it into the archive under its publication name with
provenance naming the quarantine, and refuses a candidate whose digest matches
nothing previously recorded.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.archive import GazetteArchive, IndexEntry  # noqa: E402
from tests.gazette_fixtures import ROC_ROWS, write_gazette  # noqa: E402


@pytest.fixture
def quarantine(tmp_path) -> Path:
    d = tmp_path / "skipped since abnormal SN"
    d.mkdir()
    return d


def _candidate(tmp_path, name="candidate", **kw) -> Path:
    p = tmp_path / f"{name}.pdf"
    write_gazette(str(p), ROC_ROWS, **kw)
    return p


def _seed_digest(archive: GazetteArchive, gazette_id: str, digest: str) -> None:
    """Record a digest the way the poller did for 09-24: an ingest record whose
    document is no longer held (the 2026-10-07 rebuild dropped the file, the
    entry's digest is what survived)."""
    archive.append_index(IndexEntry(
        gazette_id=gazette_id,
        published_date=gazette_id,
        ingested_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        record_count=1436,
        project_count=692,
        reader_version="table-lines-v1",
        filename="核定案件-gone.pdf",  # not held
        sha256=digest,
    ))


def test_refile_copies_under_the_publication_name_with_provenance(tmp_path, quarantine):
    quarantined = _candidate(tmp_path, "核定案件-2026-10-02",
                             published="統計至115年9月24日")
    digest = hashlib.sha256(quarantined.read_bytes()).hexdigest()
    archive = GazetteArchive(tmp_path / "gazettes")
    _seed_digest(archive, "2026-09-24", digest)

    dest, entry = archive.refile_from_quarantine(
        quarantined, "2026-09-24", published_date="2026-09-24", record_count=1436)

    assert dest == archive.path_for("2026-09-24")
    assert dest.exists() and dest != quarantined, "copy, not move"
    assert quarantined.exists(), "the quarantine file is evidence; never deleted"
    assert entry.event == "restored"
    assert entry.restored_from == str(quarantined)
    assert entry.sha256 == digest
    assert entry.record_count == 1436


def test_refile_refuses_a_candidate_matching_nothing(tmp_path, quarantine):
    orphan = _candidate(tmp_path, "核定案件-unknown", published="統計至115年1月1日")
    archive = GazetteArchive(tmp_path / "gazettes")
    _seed_digest(archive, "2026-09-24", "0" * 64)  # a digest the candidate does not match

    with pytest.raises(ValueError, match="refusing to re-file"):
        archive.refile_from_quarantine(orphan, "2026-09-24")
    assert not archive.path_for("2026-09-24").exists(), "nothing written on refusal"
    assert any(e.gazette_id == "2026-09-24" for e in archive.entries()), (
        "the refusal does not disturb the recorded entry")


def test_refile_refuses_when_no_digest_was_ever_recorded(tmp_path, quarantine):
    quarantined = _candidate(tmp_path, "c", published="統計至115年9月24日")
    archive = GazetteArchive(tmp_path / "gazettes")  # empty index

    with pytest.raises(ValueError, match="refusing to re-file"):
        archive.refile_from_quarantine(quarantined, "2026-09-24")


def test_verify_reports_the_refiled_member_as_held(tmp_path, quarantine):
    """After re-filing, the member is present, indexed, and digest-matched:
    verify() falls silent about it (the recorded-but-missing problem for the
    same id is replaced by a held-and-verified member)."""
    quarantined = _candidate(tmp_path, "核定案件-2026-10-02",
                             published="統計至115年9月24日")
    digest = hashlib.sha256(quarantined.read_bytes()).hexdigest()
    archive = GazetteArchive(tmp_path / "gazettes")
    _seed_digest(archive, "2026-09-24", digest)

    assert any("missing from the archive" in p for p in archive.verify()), (
        "before re-filing: recorded but not held")

    archive.refile_from_quarantine(quarantined, "2026-09-24", published_date="2026-09-24")

    problems = [p for p in archive.verify() if "2026-09-24" in p]
    # The held member verifies. The only remaining report names the legacy entry's
    # filename (核定案件-gone.pdf) — that entry was recorded against a document the
    # rebuild dropped, and it is honest to keep saying so. The re-filed copy is a
    # second entry for the same publication, pointing at the held file.
    assert all("gone.pdf" in p or "missing" in p for p in problems), problems
    held_entries = [e for e in archive.entries()
                    if e.event == "restored" and e.restored_from]
    assert held_entries, "the restored entry is in the index"
    assert (archive.root / held_entries[-1].filename).exists(), (
        "the restored member is on disk under its publication name")


def test_refile_into_an_archive_that_already_holds_identical_content(tmp_path, quarantine):
    """Idempotence: re-filing a candidate whose content is already held appends
    the restored entry but replaces nothing (store() short-circuits)."""
    quarantined = _candidate(tmp_path, "c", published="統計至115年9月24日")
    digest = hashlib.sha256(quarantined.read_bytes()).hexdigest()
    archive = GazetteArchive(tmp_path / "gazettes")
    archive.record_ingest(str(quarantined), "2026-09-24", record_count=5)
    before = len(archive.entries())

    archive.refile_from_quarantine(quarantined, "2026-09-24", published_date="2026-09-24")

    assert len(archive.entries()) == before + 1, (
        "the restored provenance entry is still appended")
    last = archive.entries()[-1]
    assert last.event == "restored" and last.restored_from
    held = hashlib.sha256(archive.path_for("2026-09-24").read_bytes()).hexdigest()
    assert held == digest, "content unchanged"
