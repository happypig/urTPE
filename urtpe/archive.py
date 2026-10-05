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
READER_VERSION = "table-lines-v1"


@dataclass
class IndexEntry:
    """One append-only record of one ingest."""

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
              source_path: str = "") -> Path:
        """Retain a verbatim copy of ``pdf_path``, named by publication date.

        Re-storing the same publication date replaces the copy only when the content
        differs. A same-size collision is not treated as identity: ``verify`` compares
        digests, so a truncated or swapped member is detectable.
        """
        src = Path(pdf_path)
        if not src.exists():
            raise FileNotFoundError(src)
        dest = self.path_for(gazette_id)
        if dest.exists() and _sha256(dest) == _sha256(src):
            return dest
        tmp = dest.with_suffix(".pdf.part")
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)
        return dest

    def append_index(self, entry: IndexEntry) -> None:
        """Append one entry. Existing entries are never read back or rewritten."""
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def record_ingest(self, pdf_path: Path | str, gazette_id: str, **kwargs) -> tuple[Path, IndexEntry]:
        """Store the gazette and append its index entry."""
        dest = self.store(pdf_path, gazette_id, **kwargs)
        entry = IndexEntry(
            gazette_id=gazette_id,
            published_date=kwargs.get("published_date", gazette_id),
            ingested_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            record_count=kwargs.get("record_count", 0),
            project_count=kwargs.get("project_count", 0),
            reader_version=READER_VERSION,
            filename=dest.name,
            calendar=kwargs.get("calendar", ""),
            source_path=kwargs.get("source_path", str(pdf_path)),
            sha256=_sha256(dest),
        )
        self.append_index(entry)
        return dest, entry

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

    def index_ids_on_disk(self) -> set[str]:
        ids: set[str] = set()
        for path in self.root.glob("核定案件-*.pdf"):
            ids.add(path.stem.split("-", 1)[1])
        return ids

    def newest(self) -> str | None:
        ids = self.archived_ids()
        return ids[-1] if ids else None

    def predecessor_of(self, gazette_id: str) -> str | None:
        """The publication immediately before ``gazette_id`` in the archive."""
        ids = self.archived_ids()
        if gazette_id not in ids:
            return None
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
        """
        problems: list[str] = []
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
                    problems.append(
                        f"{entry.gazette_id}: content differs from the indexed digest "
                        f"(indexed {entry.sha256[:12]}, found {actual[:12]})")
        for gazette_id in sorted(self.index_ids_on_disk() - indexed_ids):
            problems.append(f"{gazette_id}: on disk but absent from the index")
        return problems