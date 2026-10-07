"""Gazette archive tests: retention, append-only index, re-read, and git invisibility.

Task group 3 of robust-gazette-ingestion.
"""

from __future__ import annotations

import subprocess

import pytest

from urtpe import extract as E
from urtpe.archive import GazetteArchive, IndexEntry
from tests.gazette_fixtures import ROC_ROWS, write_gazette


@pytest.fixture
def archive(tmp_path) -> GazetteArchive:
    return GazetteArchive(tmp_path / "gazettes")


def _gazette(tmp_path, name: str, published: str, **kw) -> str:
    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), ROC_ROWS, published=published, **kw)
    return str(path)


def test_ingest_retains_a_copy_named_by_publication_date(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    dest, entry = archive.record_ingest(pdf, "2026-08-11", record_count=5)
    assert dest.exists()
    assert dest.name == "核定案件-2026-08-11.pdf"
    assert dest.read_bytes() == open(pdf, "rb").read()
    assert entry.record_count == 5


def test_restoring_same_publication_neither_duplicates_nor_alters(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    dest, _ = archive.record_ingest(pdf, "2026-08-11", record_count=5)
    before = dest.read_bytes(), dest.stat().st_mtime_ns
    archive.record_ingest(pdf, "2026-08-11", record_count=5)
    assert dest.read_bytes() == before[0]
    assert dest.stat().st_mtime_ns == before[1]
    assert len(list(archive.root.glob("*.pdf"))) == 1


def test_one_index_entry_per_ingest_with_full_metadata(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    archive.record_ingest(pdf, "2026-08-11", record_count=5, project_count=3,
                          calendar="roc", published_date="2026-08-11")
    entries = archive.entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.gazette_id == "2026-08-11"
    assert e.published_date == "2026-08-11"
    assert e.record_count == 5
    assert e.project_count == 3
    assert e.calendar == "roc"
    assert e.reader_version
    assert e.ingested_at


def test_later_ingest_does_not_modify_earlier_entries(archive, tmp_path):
    a = _gazette(tmp_path, "a", "統計至115年8月11日")
    b = _gazette(tmp_path, "b", "統計至115年9月24日")
    archive.record_ingest(a, "2026-08-11", record_count=5)
    first_line = archive.index_path.read_text(encoding="utf-8").splitlines()[0]
    archive.record_ingest(b, "2026-09-24", record_count=6)
    lines = archive.index_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == first_line
    assert len(lines) == 2


def test_archived_gazette_is_re_read_by_the_current_reader(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    dest, _ = archive.record_ingest(pdf, "2026-08-11", record_count=5)
    recs, meta = E.extract_pdf_with_meta(str(dest))
    assert len(recs) == 5
    assert meta["published_date"] == "2026-08-11"
    assert recs[0]["recno"] == "1"


def test_archive_lives_outside_the_git_working_tree(tmp_path):
    """The archive must be untracked; a stray PDF in the repo would be a defect."""
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    outside = tmp_path / "outside"
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "data" / "raw.tsv").write_text("x\n", encoding="utf-8")
    arch = GazetteArchive(outside / "gazettes")
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    arch.record_ingest(pdf, "2026-08-11", record_count=5)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            capture_output=True, text=True).stdout
    assert ".pdf" not in status
    assert not list(repo.rglob("*.pdf"))


def test_predecessor_and_newest_follow_publication_order(archive, tmp_path):
    for name, gid in [("a", "2026-08-11"), ("b", "2026-08-20"), ("c", "2026-09-24")]:
        archive.record_ingest(_gazette(tmp_path, name, f"統計至{gid[2:4]}/{gid[5:7]}/{gid[8:10]}"),
                              gid, record_count=1)
    assert archive.archived_ids() == ["2026-08-11", "2026-08-20", "2026-09-24"]
    assert archive.predecessor_of("2026-09-24") == "2026-08-20"
    assert archive.predecessor_of("2026-08-11") is None
    assert archive.newest() == "2026-09-24"


def test_verify_reports_a_member_missing_from_disk(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    dest, _ = archive.record_ingest(pdf, "2026-08-11")
    dest.unlink()
    problems = archive.verify()
    assert any("missing from the archive" in p for p in problems)


def test_malformed_index_line_is_skipped_not_fatal(archive, tmp_path):
    pdf = _gazette(tmp_path, "a", "統計至115年8月11日")
    archive.record_ingest(pdf, "2026-08-11", record_count=5)
    with archive.index_path.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    assert len(archive.entries()) == 1


def test_index_entry_roundtrips_through_json():
    entry = IndexEntry(gazette_id="2026-09-24", published_date="2026-09-24",
                       ingested_at="t", record_count=1436, project_count=713,
                       reader_version="v", filename="f.pdf")
    assert IndexEntry(**entry.__dict__) == entry


# --- change archive-recorded-vs-held: recorded (history) vs held (presence) -------
#
# 2026-10-07. `核定案件-2026-09-24.pdf` was deleted from the archive. The next
# ingestion reported `2026-08-27 -> 2026-10-01` and carried 19 re-dated, 16 edited and
# 41 vanished rows plus a `roc -> gregorian` calendar change that were all 09-24's own
# transition. `blocking: []`, so it persisted without objection. The cause was that
# `predecessor_of()` derived the publication chain from a directory glob, so deleting a
# document promoted an earlier publication into its slot.

def _four_publications(archive, tmp_path, newest: str = "2026-10-01"):
    for name, gid in [("a", "2026-08-11"), ("b", "2026-08-20"),
                      ("c", "2026-08-27"), ("d", "2026-09-24")]:
        archive.record_ingest(
            _gazette(tmp_path, name, f"統計至{gid[2:4]}/{gid[5:7]}/{gid[8:10]}"),
            gid, record_count=1)
    archive.record_ingest(_gazette(tmp_path, "e", "統計至26年10月1日"), newest,
                          record_count=1)


def test_a_publication_the_index_records_outranks_one_the_disk_holds(archive, tmp_path):
    """Two tenses, two answers, from one archive whose index and disk disagree."""
    _four_publications(archive, tmp_path)
    archive.path_of("2026-09-24").unlink()          # recorded, no longer held

    assert archive.recorded_ids() == ["2026-08-11", "2026-08-20", "2026-08-27",
                                      "2026-09-24", "2026-10-01"], (
        "the index still records five publications; a record of what happened does not "
        "change because a file was deleted")
    assert archive.index_ids_on_disk() == {"2026-08-11", "2026-08-20", "2026-08-27", "2026-10-01"}, (
        "the disk holds four; that is a different question and has a different answer")


def test_a_recorded_but_absent_publication_still_occupies_its_position(archive, tmp_path):
    """The exact substitution that produced the 41 phantom vanished rows."""
    _four_publications(archive, tmp_path)
    archive.path_of("2026-09-24").unlink()

    assert archive.predecessor_of("2026-10-01") == "2026-09-24", (
        "09-24 was ingested, so it is 10-01's predecessor even though the document is "
        "gone. Returning 2026-08-27 makes an interval spanning two publications read as "
        "though they were adjacent, and attributes 09-24's changes to 10-01.")
    assert archive.path_of(archive.predecessor_of("2026-10-01")) is None, (
        "and the caller can still tell that the predecessor is recorded but not held")


def test_a_re_read_whose_document_is_absent_still_resolves_its_predecessor(archive, tmp_path):
    """An out-of-order re-read is compared against what came before it, not against
    whatever survives on disk."""
    _four_publications(archive, tmp_path)
    archive.path_of("2026-08-27").unlink()

    assert archive.predecessor_of("2026-08-27") == "2026-08-20"
    assert archive.predecessor_of("2026-09-24") == "2026-08-27", (
        "09-24's predecessor is 08-27 even though 08-27's document is gone")


def test_present_tense_accessors_keep_their_contracts(archive, tmp_path):
    """D1 is rejected if implemented by reinterpreting an existing accessor.

    `publication_count()`'s docstring says "publications archived", `newest()` answers
    "what do we hold" — both present tense, both correct as-is. Re-pointing either at
    the index would change an answer nothing currently depends on and lose a contract.
    """
    _four_publications(archive, tmp_path)
    archive.path_of("2026-08-20").unlink()

    assert archive.publication_count() == 4, (
        "publication_count counts what is archived, so it must not count a document "
        "that is not there")
    assert archive.newest() == "2026-10-01"
    assert archive.archived_ids() == ["2026-08-11", "2026-08-27", "2026-09-24", "2026-10-01"]