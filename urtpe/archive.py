"""Gazette archive: retain every ingested publication outside the git working tree.

The city's download URL is version-specific
(``www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/<uuid>.pdf``), so it serves
one version at a time and older gazettes become unreachable once republished. An
archive is therefore the only way a past publication can be re-read — and re-reading
it matters: when the reader changes, historical records must be regenerated under the
new rules rather than left holding whatever a past reader produced.

The PDFs live outside the repository (about 2 MB each, roughly 100 MB/year) so the
repo does not grow with upstream artifacts. An append-only index records what each
archived publication yielded, which makes a missing or altered member detectable
rather than silent.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

# Default archive location: a sibling of the repository, so it is unambiguously
# outside the working tree and survives git operations. Overridable by
# URTPE_ARCHIVE_ROOT so that a test run can never write into the live archive —
# fixture PDFs can legitimately carry a real publication's 統計至 date, and
# defaulting them to the production directory silently corrupts it.
DEFAULT_ARCHIVE_ROOT = Path(
    os.environ.get("URTPE_ARCHIVE_ROOT")
    or Path(__file__).resolve().parents[2] / "urtpe-gazettes"
)

INDEX_NAME = "index.jsonl"
RECORD_NAME = "poll_log.jsonl"

# Three reader identities, not two. `table-lines-v1` absorbed a page-number footer into a
# 地號 cell and truncated long cells at the printed row height, so an entry stamped with
# it cannot be treated as equivalent to one stamped `v2`: cell content differs between
# them, and a comparison across the two would attribute reader differences to the
# publisher. Entries predating this distinction keep their original string and are
# reported as unverified rather than being rewritten.
#
# `table-lines-v3` drops the positional skip of grid row 0. `v2` located the header band
# by position, which was correct only while every publication after page 1 repeated a
# record inside that band; from 1151006 (2026-10-01) the band is absent and row 0 holds
# a record of its own, so `v2` silently deleted one approval per page (230 of 1,439).
# `v2` stays verified rather than becoming legacy: on every publication it actually read,
# whose pages carry the repeated band, `v2` and `v3` emit the same records. It is `v3`
# that is required to read the newer export shape.
READER_VERSION = "table-lines-v3"
LEGACY_READER_VERSIONS = frozenset({"table-lines-v1"})


@dataclass
class IndexEntry:
    """One append-only record of one ingest or re-read."""

    gazette_id: str
    published_date: str
    ingested_at: str
    record_count: int
    project_count: int
    reader_version: str
    filename: str
    calendar: str = ""
    source_path: str = ""
    sha256: str = ""
    # `first_ingest` is the ingest that produced the archived data; `reread` is a later
    # read of the same publication. Recording them separately is what lets a reader tell
    # how many publications are archived from how many ingestions ran — twelve entries
    # previously described three publications, and the index could not say which.
    event: str = "first_ingest"
    # How the gazette reached the archive. `fetched` carries the publisher's reported
    # timestamp, which is provenance: the publisher re-uploads unchanged content under a
    # later stamp, so it is never evidence that a gazette is new.
    acquisition: str = ""
    publisher_stamp: str = ""
    # The URL the document was served from, when it was fetched. The publisher
    # serves one PDF link at a time and repoints it on every publication, so the
    # live link names "whatever is newest" rather than "this document". The
    # version-specific URL stays a durable address for that document afterwards
    # (measured 2026-11-06: the URL that served the 2026-10-15 gazette still
    # serves the 2026-10-15 document, a different digest from the current one,
    # while a fabricated path answers 404), so it is recorded at the time.
    #
    # Additive: an entry written before this field existed carries none, and
    # that publication is reported as having no recorded URL rather than being
    # treated as having one.
    publisher_url: str = ""
    # Departures from descending approval date, with the count of records a date could be
    # read from. Both are stored because a zero-violation result over too few dated
    # records means the date parser failed, not that the publication is well ordered.
    date_order_violations: int = -1
    dated_records: int = -1
    # The digest this entry's content replaced. Set only on a re-store of a publication
    # whose held bytes differed: a corrected re-upload is then traceable, and verify()
    # can distinguish a documented replacement from an undocumented substitution.
    supersedes: str = ""
    # Where a restored member came from: the quarantine path it was re-filed out of.
    # The quarantine itself is never deleted, so the pair of paths is the audit trail.
    restored_from: str = ""

    def is_verified(self) -> bool:
        """True only when a digest was recorded *and* the reader is precisely identified."""
        return bool(self.sha256) and self.reader_verified

    @property
    def reader_verified(self) -> bool:
        return self.reader_version not in LEGACY_READER_VERSIONS and bool(self.reader_version)


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class GazetteArchive:
    """A directory of retained gazettes plus an append-only index."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root is not None else DEFAULT_ARCHIVE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def index_path(self) -> Path:
        return self.root / INDEX_NAME

    def path_for(self, gazette_id: str) -> Path:
        return self.root / f"核定案件-{gazette_id}.pdf"

    def store(self, pdf_path: Path | str, gazette_id: str, *, published_date: str = "",
              record_count: int = 0, project_count: int = 0, calendar: str = "",
              source_path: str = "", acquisition: str = "", publisher_stamp: str = "",
              publisher_url: str = "", **_ignored) -> Path:
        """Retain a verbatim copy of ``pdf_path``, named by publication date.

        Re-storing the same publication date replaces the copy only when the content
        differs, and the replacement is recorded: an append-only re-store entry names
        the digest it supersedes and the digest now held, so a corrected re-upload is
        traceable and ``verify`` does not report the documented replacement as damage.
        A same-size collision is not treated as identity: ``verify`` compares
        digests, so a truncated or swapped member is detectable.
        """
        src = Path(pdf_path)
        if not src.exists():
            raise FileNotFoundError(src)
        dest = self.path_for(gazette_id)
        if dest.exists() and _sha256(dest) == _sha256(src):
            return dest
        superseded = _sha256(dest) if dest.exists() else ""
        tmp = dest.with_suffix(".pdf.part")
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)
        if superseded:
            self.append_index(IndexEntry(
                gazette_id=gazette_id,
                published_date=published_date or gazette_id,
                ingested_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                record_count=record_count,
                project_count=project_count,
                reader_version=READER_VERSION,
                filename=dest.name,
                calendar=calendar,
                source_path=source_path or str(src),
                sha256=_sha256(dest),
                event="re-store",
                supersedes=superseded,
                publisher_url=publisher_url,
            ))
        return dest

    def append_index(self, entry: IndexEntry) -> None:
        """Append one entry. Existing entries are never read back or rewritten."""
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def record_publisher_url(self, gazette_id: str, url: str, sha256: str,
                             publisher_stamp: str = "") -> IndexEntry:
        """Record the publisher URL that serves a publication, verified by digest.

        The publisher serves one PDF link at a time and repoints it on every
        publication, so the live link names "whatever is newest". A
        version-specific URL names one document and stays a durable address for
        it (measured 2026-11-06: the URL that served the 2026-10-15 gazette
        still serves the 2026-10-15 document, a different digest from the
        current one, while a fabricated path answers 404).

        A URL learned after the fact — recovered from the repository's own
        history, for instance — is worth recording too, and this is where it
        goes. The digest is the proof: the URL is accepted only when the
        document it serves hashes to the digest the archive already holds for
        that publication. A URL that serves a different document is refused
        rather than recorded, because a link to the wrong gazette looks
        correct.

        ``publisher_stamp`` is the publisher's 資料更新 timestamp for the
        document that URL serves. It is recorded with the URL because the two
        belong together: a date beside a link dates the document the link
        serves, and a release must not inherit another release's date.

        Appended as its own entry. The index is append-only, so an entry
        written before the field existed keeps its shape and this one adds the
        address without rewriting anything.
        """
        if not url:
            raise ValueError("no URL to record")
        if not sha256:
            raise ValueError("no digest to verify the URL against")
        known = {e.sha256 for e in self.entries() if e.sha256}
        if sha256 not in known:
            raise ValueError(
                "%s is not a digest the archive holds; refusing to record a URL "
                "for a document this archive does not have" % sha256[:12])
        entry = IndexEntry(
            gazette_id=gazette_id,
            published_date=gazette_id,
            ingested_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            record_count=0,
            project_count=0,
            reader_version=READER_VERSION,
            filename=self.path_for(gazette_id).name,
            sha256=sha256,
            event="publisher-url",
            publisher_url=url,
            publisher_stamp=publisher_stamp,
        )
        self.append_index(entry)
        return entry

    def record_ingest(self, pdf_path: Path | str, gazette_id: str, **kwargs) -> tuple[Path, IndexEntry]:
        """Store the gazette and append its index entry."""
        dest = self.store(pdf_path, gazette_id, **kwargs)
        entry = IndexEntry(
            gazette_id=gazette_id,
            published_date=kwargs.get("published_date", gazette_id),
            ingested_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            record_count=kwargs.get("record_count", 0),
            project_count=kwargs.get("project_count", 0),
            reader_version=kwargs.get("reader_version", READER_VERSION),
            filename=dest.name,
            calendar=kwargs.get("calendar", ""),
            source_path=kwargs.get("source_path", str(pdf_path)),
            sha256=kwargs.get("sha256") or _sha256(dest),
            event=kwargs.get("event", "first_ingest"),
            acquisition=kwargs.get("acquisition", ""),
            publisher_stamp=kwargs.get("publisher_stamp", ""),
            date_order_violations=kwargs.get("date_order_violations", -1),
            dated_records=kwargs.get("dated_records", -1),
            supersedes=kwargs.get("supersedes", ""),
            restored_from=kwargs.get("restored_from", ""),
            publisher_url=kwargs.get("publisher_url", ""),
        )
        self.append_index(entry)
        return dest, entry

    def record_ingest_bytes(self, body: bytes, gazette_id: str, **kwargs) -> IndexEntry:
        """Archive an in-memory document and index it.

        Used by the poller, which receives the publisher's bytes rather than a path.
        """
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="urtpe-archive-")) / "gazette.pdf"
        tmp.write_bytes(body)
        _, entry = self.record_ingest(tmp, gazette_id, **kwargs)
        return entry

    def refile_from_quarantine(self, quarantine_path: Path | str, gazette_id: str, **kwargs):
        """Copy a quarantined candidate into the archive under its publication name.

        Identity is established by digest: the candidate must hash to a digest some
        earlier record ties to this ``gazette_id``. Records consulted, in order:
        the current index, the pre-rebuild index backup (``index.jsonl.pre-*`` —
        the 2026-10-07 rebuild dropped 09-24's entries outright, so the current
        index alone cannot prove a quarantined candidate the rebuild lost), and
        the poll log (``poll_log.jsonl``), whose hash record is the acquisition
        evidence. A candidate matching nothing is refused rather than guessed at.
        The quarantine file is never deleted: the quarantine directory is evidence
        of the old reader's failure, and this entry's ``restored_from`` provenance
        is the audit trail's other half.
        """
        src = Path(quarantine_path)
        if not src.exists():
            raise FileNotFoundError(src)
        digest = _sha256(src)
        known = {e.sha256 for e in self.entries()
                 if e.gazette_id == gazette_id and e.sha256}
        # Pre-rebuild index backups: entries the rebuild dropped still speak.
        for backup in sorted(self.root.glob("index.jsonl.pre-*")):
            try:
                for line in backup.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = IndexEntry(**json.loads(line))
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if e.gazette_id == gazette_id and e.sha256:
                        known.add(e.sha256)
            except OSError:
                continue  # an unreadable backup is not proof either way
        # The poll log: acquisition evidence keyed by content hash (design D1).
        poll_log = self.root / "poll_log.jsonl"
        if poll_log.exists():
            try:
                poll_lines = poll_log.read_text(encoding="utf-8").splitlines()
            except OSError:
                poll_lines = []  # an unreadable log is not proof either way
            for line in poll_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (record.get("gazette_id") == gazette_id
                        and record.get("sha256")):
                    known.add(record["sha256"])
        if not known or digest not in known:
            raise ValueError(
                "%s does not match any digest previously recorded for gazette %s; "
                "refusing to re-file an unidentified file" % (src.name, gazette_id))
        dest, entry = self.record_ingest(
            src, gazette_id,
            event="restored",
            source_path=str(src),
            restored_from=str(src),
            sha256=digest,
            **kwargs)
        return dest, entry

    def has_hash(self, digest: str) -> bool:
        """Whether a document with this content hash is already archived."""
        if not digest:
            return False
        return any(e.sha256 == digest for e in self.entries())

    def gazette_id_for_hash(self, digest: str) -> str | None:
        for e in self.entries():
            if e.sha256 == digest:
                return e.gazette_id
        return None

    def assert_matches_entry(self, pdf_path: Path | str, gazette_id: str) -> None:
        """Raise unless ``pdf_path`` is the document the index says it archived.

        Provenance has to be provable. An entry with no digest cannot prove anything, so
        it refuses rather than waving the document through.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(path)
        entries = [e for e in self.entries() if e.gazette_id == gazette_id]
        if not entries:
            raise KeyError("no index entry for gazette %s" % gazette_id)
        hashed = [e for e in entries if e.sha256]
        if not hashed:
            raise ValueError(
                "gazette %s has no recorded digest; provenance cannot be established" % gazette_id)
        actual = _sha256(path)
        known = {e.sha256 for e in hashed}
        if actual not in known:
            raise ValueError(
                "content of %s does not match any recorded digest for %s "
                "(found %s, index holds %s)"
                % (path.name, gazette_id, actual[:12], ", ".join(sorted(h[:12] for h in known))))

    def unverified_members(self) -> list[str]:
        """Publications whose provenance cannot be established from the index.

        A member with no digest, or one stamped with a reader too coarse to distinguish
        from the reader it replaced. Both are reported rather than assumed sound.
        """
        out = []
        for e in self.entries():
            if e.event == "reread":
                continue
            if not e.is_verified():
                out.append(e.gazette_id)
        return sorted(set(out))

    def publication_count(self) -> int:
        """Distinct publications archived, counting each once however often it was read."""
        return len(self.index_ids_on_disk())

    def ingestion_count(self) -> int:
        """Every ingest and re-read recorded. Diverges from publication_count by design."""
        return len(self.entries())

    def record_ordering(self, gazette_id: str, violations: int, dated_records: int,
                        **kwargs) -> None:
        """Append the publication's date-ordering result to its own entry.

        Appended rather than mutated in place: the index is append-only, so correcting a
        measurement is a new record and the earlier one stays readable. An entry whose
        ``date_order_violations`` is -1 was recorded before this measurement existed,
        which is different from a measurement of zero.
        """
        target = None
        for entry in reversed(self.entries()):
            if entry.gazette_id == gazette_id and entry.event != "reread":
                target = entry
                break
        if target is None:
            return
        self.append_index(IndexEntry(**{**asdict(target),
                                        "ingested_at": dt.datetime.now().astimezone().isoformat(
                                            timespec="seconds"),
                                        "event": "ordering",
                                        "date_order_violations": violations,
                                        "dated_records": dated_records,
                                        **kwargs}))

    def entries(self) -> list[IndexEntry]:
        """Every index entry, oldest first. Malformed lines are skipped, not fatal."""
        if not self.index_path.exists():
            return []
        out: list[IndexEntry] = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(IndexEntry(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    def archived_ids(self) -> list[str]:
        """Publication dates present on disk, oldest first."""
        return sorted(self.index_ids_on_disk())

    def recorded_ids(self) -> list[str]:
        """Publications the index says were ingested, oldest first.

        History, not presence. `index_ids_on_disk()` answers "what files are here right
        now"; this answers "what was ingested", and the two are not the same question.
        Measured 2026-10-07: with 核定案件-2026-09-24.pdf deleted, the disk-glob answer
        promoted 2026-08-27 into 09-24's slot, so reconciling 10-01 reported 19 re-dated,
        16 edited and 41 vanished rows plus a `roc -> gregorian` calendar change that all
        belonged to 09-24's own transition. A publication that was ingested keeps its
        position whether or not the document is still here.
        """
        return sorted({e.gazette_id for e in self.entries()})

    def index_ids_on_disk(self) -> set[str]:
        ids: set[str] = set()
        for path in self.root.glob("核定案件-*.pdf"):
            ids.add(path.stem.split("-", 1)[1])
        return ids

    def newest(self) -> str | None:
        ids = self.archived_ids()
        return ids[-1] if ids else None

    def predecessor_of(self, gazette_id: str) -> str | None:
        """The publication immediately before ``gazette_id``.

        The gazette itself need not be archived yet. It is archived *after* reconciliation
        runs, so requiring it to be present made this return None on every ingestion and
        left reconciliation reporting "no comparison possible" against a populated archive —
        which is why the parked portal cascade's trigger ("a reliable change set across two
        consecutive ingestions") could never be met.

        Resolved from `recorded_ids()`, not from the directory listing, because this is a
        question about what was ingested. A predecessor whose document has since been
        deleted still occupies its position: the caller asks `path_of()` separately and
        reports the absence, rather than this silently naming an earlier publication and
        letting an interval spanning two publications read as though they were adjacent.
        """
        ids = self.recorded_ids()
        if gazette_id not in ids:
            # the incoming gazette: compare against whatever precedes it
            earlier = [i for i in ids if i < gazette_id]
            return earlier[-1] if earlier else None
        i = ids.index(gazette_id)
        return ids[i - 1] if i > 0 else None

    def path_of(self, gazette_id: str) -> Path | None:
        p = self.path_for(gazette_id)
        return p if p.exists() else None

    def verify(self) -> list[str]:
        """Report archive members that are missing, unindexed, or altered.

        A digest is compared where the index recorded one, so a member replaced by
        different content is reported rather than assumed intact. Entries written
        before digests were recorded fall back to existence only.

        A mismatch is *not* reported when the index itself documents the replacement:
        a re-store entry naming an older digest as superseded makes that older entry's
        mismatch the expected consequence of a recorded replacement, not damage. An
        undocumented substitution — bytes changed with no re-store entry — is still
        reported, naming both digests.
        """
        problems: list[str] = []
        superseded: set[tuple[str, str]] = set()
        for entry in self.entries():
            if entry.supersedes:
                superseded.add((entry.gazette_id, entry.supersedes))
        indexed_ids = set()
        for entry in self.entries():
            indexed_ids.add(entry.gazette_id)
            path = self.root / entry.filename
            if not path.exists():
                problems.append(f"{entry.gazette_id}: indexed but missing from the archive")
                continue
            if entry.sha256:
                actual = _sha256(path)
                if actual != entry.sha256:
                    if (entry.gazette_id, entry.sha256) in superseded:
                        continue  # documented replacement: the re-store entry owns it
                    problems.append(
                        f"{entry.gazette_id}: content differs from the indexed digest "
                        f"(indexed {entry.sha256[:12]}, found {actual[:12]})")
        for gazette_id in sorted(self.index_ids_on_disk() - indexed_ids):
            problems.append(f"{gazette_id}: on disk but absent from the index")
        return problems