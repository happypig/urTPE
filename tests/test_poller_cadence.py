# -*- coding: utf-8 -*-
"""Change detection is by content hash, never by the publisher's timestamp.

Test-writing group 1 of gazette-ingest-cadence.

The measurement behind this group, taken against the live page on 2026-10-05:

    page ETag / Last-Modified  absent, Cache-Control: no-cache, 86,586 bytes
    page 資料更新               115-09-29 13:55
    newest gazette held        2026-09-24
    PDF Last-Modified          Tue, 29 Sep 2026 05:55:30 GMT
    SHA-256 served PDF         5066b108...8a92a
    SHA-256 archived copy      5066b108...8a92a   -- identical

The publisher re-uploads the same document under a later timestamp. A poller keyed on
Last-Modified therefore reports a new gazette every week for a gazette it already holds,
and cannot distinguish that from a genuine re-publication. Hash is the detection
mechanism; a timestamp is provenance and is never consulted to decide.

The second theme in this group is that a check which finds nothing and a check which never
ran must be distinguishable from each other. Same failure shape as the `coverage.py`
total re-key already fixed: a check that cannot observe the failure it exists to catch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtpe.poller import (  # noqa: E402
    Poller,
    PollerError,
    classify_offer,
)

PAGE_URL = "https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E"
PDF_URL = "https://example.invalid/gazette.pdf"


def _gazette(tmp_path, name: str, **kw) -> bytes:
    """A real gazette PDF, so hashing and archiving behave as they do in production.

    The rows matter only in that they make the document parseable and give it a 統計至
    line; the poller's decision is made on bytes, never on their content.
    """
    from tests.gazette_fixtures import ROC_ROWS, write_gazette

    path = tmp_path / f"{name}.pdf"
    write_gazette(str(path), ROC_ROWS, **kw)
    return path.read_bytes()


def _page(pdf_url: str = PDF_URL, stamp: str = "115-09-29 13:55",
          hitcount: int = 153285) -> bytes:
    """A page shaped like the real one: the stamp and the link live in the body.

    The `hitcount` span is deliberate. The live page carries one, and it increments on
    page view — measured 153284 → 153285 between two polls minutes apart. Comparing raw
    page bytes therefore reports a change on nearly every check, which defeats the
    1.9 MB saving the comparison exists to provide.
    """
    return (
        "<html><body><ul>"
        f"<li><i class=\"mark\">資料更新：</i>{stamp}</span></li>"
        "<li><i class=\"mark\">資料維護：</i>臺北市都市更新處</span></li>"
        "</ul>"
        f'<span id="hitcount">{hitcount}</span>'
        f'<a href="{pdf_url}">下載</a>'
        "</body></html>"
    ).encode("utf-8")


class _Net:
    """A scripted network. Every poll states what it saw; nothing is implicit."""

    def __init__(self, pages, pdfs):
        self.pages = list(pages)
        self.pdfs = dict(pdfs)
        self.page_fetches = 0
        self.pdf_fetches = 0

    def fetch_page(self, url):
        self.page_fetches += 1
        item = self.pages.pop(0) if self.pages else self.pages
        if isinstance(item, Exception):
            raise item
        return item

    def fetch_pdf(self, url):
        self.pdf_fetches += 1
        if url not in self.pdfs:
            raise PollerError("no scripted PDF at %s" % url)
        return self.pdfs[url]


@pytest.fixture
def archive(tmp_path):
    from urtpe.archive import GazetteArchive
    return GazetteArchive(tmp_path / "gazettes")


def _poll(archive, net, emitted=None, dry_run=False):
    return Poller(
        archive,
        page_url=PAGE_URL,
        net=net,
        emitted_dir=emitted,
        dry_run=dry_run,
    ).poll()


# --- tasks 1.1, 1.2: the hash decides, one way only --------------------------

def test_a_pdf_matching_an_archived_member_is_not_ingested_again(archive, tmp_path):
    """The live page's actual case: a re-upload of a gazette already held."""
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    net = _Net([_page()], {PDF_URL: body})
    outcome = _poll(archive, net)

    assert outcome.status == "reuploaded", outcome
    assert outcome.gazette_id == "2026-09-24", outcome
    assert len(archive.entries()) == 1, "a re-upload must not append an index entry"


def test_a_pdf_matching_nothing_archived_is_acquired_as_a_new_gazette(archive, tmp_path):
    body = _gazette(tmp_path, "fresh")
    net = _Net([_page()], {PDF_URL: body})

    outcome = _poll(archive, net)

    assert outcome.status == "new_gazette", outcome
    assert archive.entries(), "a genuinely new gazette must be recorded in the index"
    assert archive.path_of(outcome.gazette_id) is not None


# --- tasks 1.3, 1.4: the timestamp is provenance, never the decision --------

def test_a_newer_timestamp_over_an_unchanged_hash_does_not_create_an_entry(archive, tmp_path):
    """This is the false positive that motivates the whole capability.

    The page advances its stamp on 2026-09-29 while still serving the gazette whose
    publication date is 2026-09-24. A timestamp comparison reports a new gazette.
    """
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    net = _Net([_page(stamp="115-10-20 09:00")], {PDF_URL: body})
    outcome = _poll(archive, net)

    assert outcome.status == "reuploaded", outcome
    assert len(archive.entries()) == 1, (
        "a later publisher timestamp over identical content must not append an entry")


def test_the_newer_timestamp_is_recorded_as_provenance_on_a_reupload(archive, tmp_path):
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    net = _Net([_page(stamp="115-10-20 09:00")], {PDF_URL: body})
    outcome = _poll(archive, net)

    assert outcome.publisher_stamp == "115-10-20 09:00", (
        "the stamp is exactly what should be kept: it explains why the page changed")


def test_the_timestamp_never_replaces_the_hash_as_the_decision(archive, tmp_path):
    """Both directions of the invariant, asserted on one body of content."""
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    older = _poll(archive, _Net([_page(stamp="115-01-01 00:00")], {PDF_URL: body}))
    newer = _poll(archive, _Net([_page(stamp="115-12-31 23:59")], {PDF_URL: body}))

    assert older.status == newer.status == "reuploaded", (older, newer)
    assert len(archive.entries()) == 1


# --- tasks 1.5, 1.6, 1.7: a check that finds nothing is recorded -------------

def test_a_check_finding_nothing_writes_a_dated_record(archive, tmp_path):
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    outcome = _poll(archive, _Net([_page()], {PDF_URL: body}))
    records = Poller.read_records(archive)

    assert records, "a check that found nothing must still leave a record"
    assert records[-1]["status"] == "reuploaded"
    assert records[-1]["checked_at"], "a record without its time cannot show a gap"


def test_a_second_identical_check_reports_unchanged(archive, tmp_path):
    """Once the page bytes are known, no PDF is fetched at all."""
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    net = _Net([_page(), _page()], {PDF_URL: body})

    first = _poll(archive, net)
    second = _poll(archive, net)

    assert first.status == "reuploaded"
    assert second.status == "unchanged", second
    assert net.pdf_fetches == 1, (
        "the 1.9 MB PDF must not be re-fetched when the page has not changed "
        "(fetched %d times)" % net.pdf_fetches)


def test_a_failed_fetch_is_recorded_as_a_failure_not_as_finding_nothing(archive):
    net = _Net([PollerError("connection reset")], {})

    outcome = _poll(archive, net)

    assert outcome.status == "failed", outcome
    record = Poller.read_records(archive)[-1]
    assert record["status"] == "failed"
    assert record.get("error"), "a failure must say why, or it reads as a quiet week"


def test_a_gap_in_the_record_series_is_detectable_without_the_publisher(archive):
    """A missed publication and a quiet week must not look alike."""
    body = b"%PDF-1.7 held already"
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    net = _Net([_page(), _page()], {PDF_URL: body})
    _poll(archive, net)
    _poll(archive, net)

    records = Poller.read_records(archive)
    gap = Poller.max_gap_days(records)
    assert gap is not None and gap < 1.0 / 24, (
        "two consecutive checks must leave no gap (got %r days)" % gap)

    stale = [dict(records[0], checked_at="2026-01-01T00:00:00+08:00")]
    assert Poller.max_gap_days(stale, cadence_days=7, now="2026-10-05T00:00:00+08:00") > 7, (
        "a lone check from long ago must read as a gap, not as a completed series"
    )


def test_no_records_at_all_is_reported_as_no_history(archive):
    assert Poller.max_gap_days([]) is None, (
        "an empty series is missing history, which is not the same as a gap in it")


# --- task 1.8: an unattended check cannot overwrite an emitted dataset --------

def test_the_poller_writes_nothing_into_the_emitted_dataset(archive, tmp_path):
    body = _gazette(tmp_path, "fresh")
    emitted = tmp_path / "data"
    emitted.mkdir()
    (emitted / "projects.json").write_text('{"projects": []}', encoding="utf-8")
    before = sorted(p.name for p in emitted.iterdir())

    outcome = _poll(archive, _Net([_page()], {PDF_URL: body}), emitted=emitted)

    assert outcome.status == "new_gazette"
    assert sorted(p.name for p in emitted.iterdir()) == before, (
        "acquisition must not touch the emitted dataset")
    assert (emitted / "projects.json").read_text(encoding="utf-8") == '{"projects": []}'


def test_the_poller_reports_that_a_new_gazette_awaits_a_separate_ingestion(archive, tmp_path):
    """Detection is automated; the decision to ingest is not (design D4)."""
    emitted = tmp_path / "data"
    emitted.mkdir()
    body = _gazette(tmp_path, "fresh")

    outcome = _poll(archive, _Net([_page()], {PDF_URL: body}), emitted=emitted)

    assert outcome.status == "new_gazette"
    assert outcome.ingested is False, (
        "the poller must not ingest; an unattended run that can ingest is one that "
        "can overwrite a good dataset")
    assert outcome.pending_gazette_id == outcome.gazette_id


def test_a_dry_run_downloads_nothing_and_changes_nothing(archive, tmp_path):
    body = _gazette(tmp_path, "fresh")
    net = _Net([_page()], {PDF_URL: body})

    outcome = _poll(archive, net, dry_run=True)

    assert outcome.status == "would_download", (
        "a dry run must not claim to have classified content it never downloaded")
    assert net.pdf_fetches == 0, "a dry run must not spend the download"
    assert not archive.entries(), "a dry run must not write to the archive"
    assert not (archive.root / "poll_state.json").exists(), (
        "a dry run must not persist state, or the next real check compares against a "
        "page it never saw")


# --- tasks 1.9, 1.10: provenance is proven, not assumed ----------------------

def test_an_ingestion_is_refused_when_the_offered_pdf_does_not_match_its_entry(archive, tmp_path):
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    tmp = archive.root / "offered.pdf"
    tmp.write_bytes(_gazette(tmp_path, "imposter", shift=8.0))

    with pytest.raises(Exception):
        archive.assert_matches_entry(tmp, "2026-09-24")


def test_an_archive_entry_with_no_hash_is_reported_as_unverified(archive, tmp_path):
    """An unprovenanced member must not read as a verified one."""
    from urtpe import archive as archive_mod
    from urtpe.archive import IndexEntry
    import datetime as _dt

    body = _gazette(tmp_path, "nohash")
    path = archive.store(_write(tmp_path / "nh.pdf", body), "2026-09-24", published_date="2026-09-24")
    archive.append_index(IndexEntry(
        gazette_id="2026-09-24", published_date="2026-09-24",
        ingested_at=_dt.datetime.now().isoformat(),
        record_count=0, project_count=0,
        reader_version=archive_mod.READER_VERSION,
        filename=path.name, sha256="",
    ))

    entry = archive.entries()[-1]
    assert not entry.is_verified(), "an entry with no digest must not count as verified"
    assert "2026-09-24" in archive.unverified_members()


def test_an_entry_with_a_hash_is_verified(archive, tmp_path):
    body = _gazette(tmp_path, "hashed")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")

    entry = archive.entries()[-1]
    assert entry.is_verified()
    assert not archive.unverified_members()


# --- task 3.6: a re-read must not overwrite the first ingestion --------------

def test_a_reread_does_not_overwrite_the_first_ingestion(archive, tmp_path):
    """Both events stay readable; the re-read does not claim to be the origin."""
    body = _gazette(tmp_path, "shared")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24",
                                event="first_ingest", reader_version="table-lines-v1")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24",
                                event="reread", reader_version="table-lines-v2")

    entries = archive.entries()
    assert len(entries) == 2, "both events are recorded"
    assert entries[0].event == "first_ingest"
    assert entries[1].event == "reread"
    assert entries[0].reader_version == "table-lines-v1", (
        "the first ingestion's reader must survive the re-read's entry")


def test_a_legacy_reader_makes_a_publication_unverified(archive, tmp_path):
    """`table-lines-v1` truncated cells; an entry stamped with it cannot prove anything."""
    body = _gazette(tmp_path, "legacy")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24",
                                reader_version="table-lines-v1")

    entry = archive.entries()[-1]
    assert not entry.is_verified(), (
        "a digest alone is not provenance if the reader could have truncated cells")
    assert archive.unverified_members() == ["2026-09-24"]


def test_a_corrected_reader_with_a_digest_is_verified(archive, tmp_path):
    from urtpe import archive as archive_mod

    body = _gazette(tmp_path, "v2")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24",
                                reader_version=archive_mod.READER_VERSION)
    assert archive.entries()[-1].is_verified()
    assert not archive.unverified_members()


# --- task 3.5: publications are countable separately from ingestions ---------

def test_publications_are_countable_apart_from_ingestions(archive, tmp_path):
    """Twelve entries previously described three publications."""
    body = _gazette(tmp_path, "many")
    for _ in range(4):
        archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    archive.record_ingest_bytes(_gazette(tmp_path, "other"), "2026-08-20",
                                published_date="2026-08-20")

    assert archive.ingestion_count() == 5, archive.ingestion_count()
    assert archive.publication_count() == 2, (
        "two publications were archived; the index should say so without counting reads")


def test_a_reread_is_not_counted_as_a_second_publication(archive, tmp_path):
    body = _gazette(tmp_path, "once")
    archive.record_ingest_bytes(body, "2026-09-24", event="first_ingest")
    archive.record_ingest_bytes(body, "2026-09-24", event="reread")
    assert archive.publication_count() == 1


# --- task 1.11: page bytes and PDF bytes move independently ------------------

def test_an_incrementing_hit_counter_does_not_look_like_a_page_change(archive, tmp_path):
    """The bug acceptance testing found, kept as a test.

    Comparing raw page bytes reports a change whenever the publisher's view counter ticks,
    so the check downloads the 1.9 MB PDF almost every week to learn nothing. Two fetches
    seconds apart match and two minutes apart do not, which makes the failure intermittent
    and easy to mistake for the publisher publishing something.
    """
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    net = _Net([_page(hitcount=153284), _page(hitcount=153285)], {PDF_URL: body})

    first = _poll(archive, net)
    second = _poll(archive, net)

    assert first.status == "reuploaded", first
    assert second.status == "unchanged", (
        "a view counter is not a publication; got %s" % second.status)
    assert net.pdf_fetches == 1, (
        "the counter ticked and cost a download (%d fetches)" % net.pdf_fetches)


def test_a_counter_tick_alongside_a_real_change_is_still_detected(archive, tmp_path):
    """Masking volatile bytes must not blind the check to a genuine new gazette."""
    held = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(held, "2026-09-24", published_date="2026-09-24")
    # same counter movement, but the page now carries a later 資料更新 and a new document
    net = _Net(
        [_page(stamp="115-09-29 13:55", hitcount=1),
         _page(stamp="115-10-20 09:00", hitcount=2)],
        {PDF_URL: held},
    )

    first = _poll(archive, net)
    net.pdfs[PDF_URL] = _gazette(tmp_path, "fresh")
    outcome = _poll(archive, net)

    assert first.status == "reuploaded", first
    assert outcome.status == "new_gazette", (
        "a real publication must survive the masking; got %s" % outcome.status)
    assert net.pdf_fetches == 2, "a real change must still be checked"


def test_a_changed_pdf_link_over_unchanged_page_bytes_downloads_nothing(archive, tmp_path):
    """The page is where the link and the stamp live, so it is what is compared."""
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    net = _Net([_page(), _page()], {PDF_URL: body})

    _poll(archive, net)
    outcome = _poll(archive, net)

    assert outcome.status == "unchanged"
    assert net.pdf_fetches == 1, "an unchanged page must not cost a download"


def test_changed_page_bytes_with_an_unchanged_pdf_is_a_reupload(archive, tmp_path):
    """The live page's real state: new stamp, same document."""
    body = _gazette(tmp_path, "held")
    archive.record_ingest_bytes(body, "2026-09-24", published_date="2026-09-24")
    net = _Net(
        [_page(stamp="115-09-24 13:55"), _page(stamp="115-09-29 13:55")],
        {PDF_URL: body},
    )

    first = _poll(archive, net)
    second = _poll(archive, net)

    assert first.status == "reuploaded"
    assert second.status == "reuploaded", (
        "changed page bytes are what trigger the check; the hash is what decides")
    assert len(archive.entries()) == 1


# --- the classifier, on its own ---------------------------------------------

@pytest.mark.parametrize("matches,expect", [(True, "reuploaded"), (False, "new_gazette")])
def test_classify_offer_depends_only_on_whether_the_hash_is_held(matches, expect):
    assert classify_offer(hash_matches_archive=matches).status == expect


def test_classify_offer_never_reads_a_timestamp():
    """The invariant, stated once more as a unit test rather than by inspection."""
    import inspect
    from urtpe import poller as poller_mod

    body = inspect.getsource(poller_mod.classify_offer)
    # strip the docstring: it discusses timestamps in order to forbid them
    code = re.sub(r'""".*?"""', "", body, flags=re.S)
    for banned in ("stamp", "mtime", "last_modified", "modified", "date"):
        assert banned not in code, (
            "classify_ofer must not consult %r; it decides on the hash alone" % banned)
    assert "hash_matches_archive" in code


# --- helpers ----------------------------------------------------------------

def _write(path: Path, body: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path