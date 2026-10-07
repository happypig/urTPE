"""Gate behaviour: a refused ingestion must leave the working tree untouched.

Tasks 1.5 and 2.2 of robust-gazette-ingestion — both require that a failure writes
nothing, not merely that it is reported.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

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


def test_previous_projects_is_readable_so_identity_moves_can_be_reported(tmp_path):
    """`--previous-projects-from` must reach the reconciler, not die on the way.

    `main()` carried a redundant function-local `import json`, which made `json` a
    local name for the whole body, so the only read of the previous dataset raised
    UnboundLocalError — the flag aborted before the lock was taken and before any
    gate ran. It is the flag that supplies the *before* half of the identity-move
    comparison, so losing it silently reduces reconciliation to a record-level diff
    and reports no moves at all.

    Found 2026-10-07 while ingesting 1151006.
    """
    pdf = _good_pdf(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out)]) == 0

    prev = tmp_path / "previous.json"
    prev.write_text(json.dumps({"projects": [{"project_id": "北投區測試段一小段1地號等1筆"}]}),
                    encoding="utf-8")

    # Same publication again, with the previous dataset supplied. It must complete
    # normally; the reconciler compares it and finds no movement.
    assert cli.main([pdf, "-o", str(out), "--previous-projects-from", str(prev)]) == 0


# --- change archive-recorded-vs-held: a predecessor that is recorded, not held ----
#
# 2026-10-07. `核定案件-2026-09-24.pdf` was deleted from the archive. The next ingestion
# reconciled 10-01 against 08-27 instead and persisted 19 re-dated, 16 edited and 41
# vanished rows plus a `roc -> gregorian` calendar change that were all 09-24's own
# transition, with `blocking: []`. These pin the two states apart.
#
# These need a private archive: the session archive is shared (conftest points it at one
# temp dir for the whole run), so what `predecessor_of` finds depends on which tests ran
# first. The root is created *inside* the session directory so conftest's escape guard
# still holds.

@pytest.fixture
def iso_archive(request):
    from urtpe.archive import GazetteArchive

    root = Path(GazetteArchive().root) / ("iso-%s" % request.node.name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _archive_member(gazette_id: str, archive_root=None):
    from urtpe.archive import GazetteArchive

    path = GazetteArchive(archive_root).path_of(gazette_id)
    assert path is not None and path.exists(), "%s must be held to set this up" % gazette_id
    return path


def _ingest(pdf, out, archive_root, **kw):
    return cli._ingest_pdf(str(pdf), str(out), archive_root=str(archive_root), **kw)


def test_a_recorded_but_absent_predecessor_is_named_in_the_report(tmp_path, iso_archive):
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    newer = tmp_path / "newer.pdf"
    write_gazette(str(newer), ROC_ROWS, published="統計至115年8月27日")

    out = tmp_path / "out"
    out.mkdir()
    _ingest(older, out, iso_archive)
    _archive_member("2026-08-11", iso_archive).unlink()

    rec = _ingest(newer, out, iso_archive)["reconciliation"]

    assert rec.comparable is False, (
        "a predecessor whose document is gone cannot be compared against")
    assert "2026-08-11" in rec.note, (
        "the report must name the publication it cannot reach, or an operator cannot "
        "tell which archive member to restore: %r" % rec.note)
    assert "not held" in rec.note, (
        "the reason must be that the document is absent, not that it was never "
        "ingested: %r" % rec.note)


def test_it_does_not_substitute_an_earlier_publication_for_the_missing_one(tmp_path, iso_archive):
    """The 41 phantom vanished rows, prevented."""
    oldest = _good_pdf(tmp_path, published="統計至115年8月11日")
    middle = tmp_path / "middle.pdf"
    write_gazette(str(middle), ROC_ROWS, published="統計至115年8月18日")
    newest = tmp_path / "newest.pdf"
    write_gazette(str(newest), ROC_ROWS, published="統計至115年8月27日")

    out = tmp_path / "out"
    out.mkdir()
    _ingest(oldest, out, iso_archive)
    _ingest(middle, out, iso_archive)
    _archive_member("2026-08-18", iso_archive).unlink()

    rec = _ingest(newest, out, iso_archive)["reconciliation"]

    assert rec.previous_id == "2026-08-18", (
        "the recorded predecessor must still be named even though its document is gone")
    assert rec.previous_total == 0, (
        "no total may be reported for a publication that was not read; reporting "
        "08-11's total here is what produced the phantom movement")
    assert rec.net_change == 0 and rec.new_approvals == 0
    assert rec.calendar_previous == "", (
        "the calendar must not be compared against a publication that was not read")
    assert not (rec.redated or rec.edited or rec.vanished), (
        "historical movement cannot be attributed across an unread publication")


def test_the_two_no_comparison_states_are_distinguishable(tmp_path, iso_archive):
    """A reader must be able to tell 'nothing earlier' from 'recorded and lost'."""
    newest = tmp_path / "newest.pdf"
    write_gazette(str(newest), ROC_ROWS, published="統計至115年8月27日")
    older = tmp_path / "older.pdf"
    write_gazette(str(older), ROC_ROWS, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()

    never = _ingest(newest, out, iso_archive)["reconciliation"]
    assert never.comparable is False
    assert "2026-08-11" not in never.note, (
        "nothing was ever recorded before this one, so no publication may be named: %r"
        % never.note)

    _ingest(older, out, iso_archive)
    _archive_member("2026-08-11", iso_archive).unlink()
    lost = _ingest(newest, out, iso_archive)["reconciliation"]

    assert lost.comparable is False
    assert lost.note != never.note, (
        "two different situations must not read identically, or a lost archive member "
        "is indistinguishable from an empty archive")
    assert "2026-08-11" in lost.note


def test_the_absence_reaches_the_persisted_change_set(tmp_path, iso_archive):
    """It must outlive the terminal, like every other reconciliation conclusion."""
    import json as _json

    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    newest = tmp_path / "newest.pdf"
    write_gazette(str(newest), ROC_ROWS, published="統計至115年8月27日")
    out = tmp_path / "out"
    out.mkdir()
    _ingest(older, out, iso_archive)
    _archive_member("2026-08-11", iso_archive).unlink()

    _ingest(newest, out, iso_archive)

    stored = _json.loads((iso_archive / "change_sets" / "2026-08-27.json").read_text(encoding="utf-8"))
    assert stored["comparable"] is False
    assert "2026-08-11" in stored["note"], (
        "the persisted note must carry the reason, or a later run reading it back "
        "cannot tell a lost member from an empty archive: %r" % stored.get("note"))
    assert not stored.get("blocking")


# --- change archive-recorded-vs-held: archive damage is surfaced, not fatal -------

def test_an_ingestion_reports_a_missing_member_and_still_writes_output(
        tmp_path, iso_archive, capsys):
    """Damage is reported, never fatal: the gate cannot repair the archive."""
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    newer = tmp_path / "newer.pdf"
    write_gazette(str(newer), ROC_ROWS, published="統計至115年8月27日")

    out = tmp_path / "out"
    out.mkdir()
    _ingest(older, out, iso_archive)
    capsys.readouterr()
    _archive_member("2026-08-11", iso_archive).unlink()

    assert cli.main([str(newer), "-o", str(out),
                     "--archive-root", str(iso_archive)]) == 0, (
        "a missing older member must not stop an unrelated publication being ingested")

    text = capsys.readouterr().out + capsys.readouterr().err
    assert "2026-08-11" in text and "missing" in text.lower(), (
        "the run must say which member is missing: %r" % text[-400:])
    assert (out / "projects.json").exists(), "output must still be written"


def test_an_ingestion_reports_a_member_whose_bytes_were_replaced(
        tmp_path, iso_archive, capsys):
    """`store()` permits re-storing a publication when content differs, so a swapped
    PDF is possible by design; only a digest comparison notices."""
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    out = tmp_path / "out"
    out.mkdir()
    _ingest(older, out, iso_archive)

    _archive_member("2026-08-11", iso_archive).write_bytes(
        b"%PDF-1.7 not the gazette that was indexed")
    capsys.readouterr()

    assert cli.main([str(older), "-o", str(out),
                     "--archive-root", str(iso_archive)]) == 0
    text = capsys.readouterr().out + capsys.readouterr().err
    assert "2026-08-11" in text, "the substituted member must be named: %r" % text[-400:]
    assert "digest" in text.lower(), (
        "the report must say the content differs from the indexed digest, which is the "
        "only evidence that distinguishes a substitution from a re-read: %r" % text[-400:])


def test_an_intact_archive_reports_nothing(tmp_path, iso_archive, capsys):
    """Absence of a report is the ordinary case, not a skipped check."""
    pdf = _good_pdf(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out),
                     "--archive-root", str(iso_archive)]) == 0

    text = capsys.readouterr().out + capsys.readouterr().err
    assert "missing from the archive" not in text
    assert "absent from the index" not in text


def test_an_ingestion_reports_a_document_with_no_index_entry(tmp_path, iso_archive, capsys):
    """A gazette present on disk that the index never recorded has no provenance: no
    reader identity, no digest, so nothing can establish where it came from."""
    from urtpe.archive import GazetteArchive

    pdf = _good_pdf(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([pdf, "-o", str(out),
                     "--archive-root", str(iso_archive)]) == 0

    stranger = tmp_path / "stranger.pdf"
    write_gazette(str(stranger), ROC_ROWS, published="統計至115年9月1日")
    GazetteArchive(str(iso_archive)).store(str(stranger), "2026-09-01")
    capsys.readouterr()

    assert cli.main([pdf, "-o", str(out),
                     "--archive-root", str(iso_archive)]) == 0
    text = capsys.readouterr().out + capsys.readouterr().err
    assert "2026-09-01" in text, "the unindexed member must be named: %r" % text[-400:]
    assert "index" in text.lower(), (
        "the report must say it is absent from the index, which is what makes it "
        "unverifiable rather than merely unknown: %r" % text[-400:])


def test_an_ordinary_adjacent_comparison_is_unaffected(tmp_path, iso_archive, capsys):
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    newer = tmp_path / "newer.pdf"
    write_gazette(str(newer), ROC_ROWS, published="統計至115年8月27日")
    out = tmp_path / "out"
    out.mkdir()
    _ingest(older, out, iso_archive)
    capsys.readouterr()

    rec = _ingest(newer, out, iso_archive)["reconciliation"]

    assert rec.comparable is True
    assert rec.previous_id == "2026-08-11" and rec.previous_total == len(ROC_ROWS)
    text = capsys.readouterr().out + capsys.readouterr().err
    assert "not held" not in text, (
        "absence language must not appear when the predecessor is recorded and held")


def test_an_ordinary_adjacent_comparison_is_unaffected(tmp_path, capsys):
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    newer = tmp_path / "newer.pdf"
    write_gazette(str(newer), ROC_ROWS, published="統計至115年8月27日")
    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([older, "-o", str(out)]) == 0

    rec = cli._ingest_pdf(str(newer), str(out))["reconciliation"]

    assert rec.comparable is True
    assert rec.previous_id == "2026-08-11" and rec.previous_total == len(ROC_ROWS)
    text = capsys.readouterr().out + capsys.readouterr().err
    assert "not held" not in text, (
        "absence language must not appear when the predecessor is recorded and held")
#
# Measured on 1151006 (2026-10-07). The current publication is read with a completion
# corpus and its predecessor without one, so the comparison is not like-for-like:
# net change read +18 where the two sides read alike give +4, and 13 historical rows
# were reported as "edited" that were never edited — the predecessor's truncated 地號
# cells, completed on the current side only. A number persisted as a publication's
# conclusion cannot be a mixture of the publisher's change and this reader's
# asymmetry.


def test_reconciliation_compares_two_publication_reads_built_the_same_way(tmp_path, monkeypatch):
    """Both sides of the comparison are read through the same seam, or the diff lies.

    A 地號 cell the publisher truncated is completed by borrowing the whole list from
    another approval of the same unit elsewhere in the archive. That corpus must be
    available on *both* sides of a reconciliation: the incoming publication's read
    had one and its predecessor's did not, so the predecessor lost records to
    exclusions the current side did not suffer.

    Measured on 1151006, 2026-10-07. Read unequally the reconciler published net
    change +18 where the two sides read alike give +4, and named 13 historical rows
    as "edited" that the city never edited — they were the predecessor's truncated
    cells, completed on one side only. Each side is therefore completed by every
    *other* archived publication, which is the only reading under which the totals
    describe the publisher rather than this reader.
    """
    older = _good_pdf(tmp_path, published="統計至115年8月11日")
    middle = tmp_path / "middle.pdf"
    write_gazette(str(middle), ROC_ROWS, published="統計至115年8月18日")
    newer = tmp_path / "newer.pdf"
    write_gazette(str(newer), ROC_ROWS, published="統計至115年8月27日")

    out = tmp_path / "out"
    out.mkdir()
    assert cli.main([older, "-o", str(out)]) == 0
    assert cli.main([str(middle), "-o", str(out)]) == 0

    seen: list[tuple[str, int]] = []
    real_extract = E.extract_pdf_with_meta

    def _spy(path, *, strict=True, corpus=None):
        seen.append((str(path), len(corpus or [])))
        return real_extract(path, strict=strict, corpus=corpus)

    monkeypatch.setattr(E, "extract_pdf_with_meta", _spy)
    cli._ingest_pdf(str(newer), str(out))

    reads = {Path(p).name: n for p, n in seen}
    assert reads, "nothing was read, so nothing was compared"
    assert len(reads) >= 2, (
        "a reconciliation must read both the incoming publication and its "
        "predecessor, each through the completion seam: %r" % reads)
    for name, candidates in sorted(reads.items()):
        assert candidates > 0, (
            "%s was read with no completion corpus, so a record the publisher "
            "truncated is excluded on this side and completed on the other, and the "
            "difference is published as the publisher's change" % name)