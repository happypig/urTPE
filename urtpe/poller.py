# -*- coding: utf-8 -*-
"""Unattended detection of a newly published gazette.

The publisher re-uploads the same PDF and advances its timestamp, so detection is by
content hash and a timestamp is provenance only. Measured against the live page on
2026-10-05: the page advertised 資料更新 115-09-29 while the newest gazette held is
2026-09-24, and the served PDF was byte-identical to the archived copy.

Design D1: hash decides, timestamp never does.
Design D2: compare page bytes first; download the 1.9 MB PDF only when they differ.
Design D3: a check that finds nothing writes a dated record, so a missed publication is
           distinguishable from a quiet week.
Design D4: acquisition is separate from ingestion. Nothing here reads or writes the
           emitted dataset, and no code path in this module ingests.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

PAGE_URL = "https://uro.gov.taipei/cp.aspx?n=963B15B39CADB94E"
STATE_NAME = "poll_state.json"
RECORD_NAME = "poll_log.jsonl"
CADENCE_DAYS = 7

# 資料更新：115-09-29 13:55 — the publisher's own stamp, kept as provenance.
_STAMP_RE = re.compile(r"資料更新[：:]\s*</?[^>]*>?\s*([0-9]{2,4}-[0-9]{1,2}-[0-9]{1,2}[^<]*)")
_PDF_HREF_RE = re.compile(r'href="([^"]*\.pdf)"', re.IGNORECASE)

# Bytes that change without a publication. The live page carries a view counter
# (`id="hitcount"`, measured 153284 -> 153285 between two checks minutes apart) and a
# timestamped AJAX endpoint, neither of which says anything about whether a gazette was
# published. Comparing raw page bytes therefore reports a change almost every check and
# spends the 1.9 MB download to learn nothing. Masked before hashing, not ignored: a real
# publication still moves the stamp or the link, and both are compared.
_VOLATILE_RE = re.compile(
    r'(<[^>]*\bid="hitcount"[^>]*>)[^<]*(</)'          # view counter
    r'|(GetCPHitcount\.ashx[^"\']*)'                  # per-request nonce
    r'|([?&](?:_|t|cachebust|timestamp)=[^"\'&\s]*)'  # cache-busting query
    , re.IGNORECASE)


def _page_fingerprint(page: bytes) -> str:
    """Hash the page with volatile spans masked out."""
    text = page.decode("utf-8", "replace")

    def _mask(m: re.Match) -> str:
        if m.group(1):
            return m.group(1) + m.group(2)
        return ""

    masked = _VOLATILE_RE.sub(_mask, text)
    return hashlib.sha256(masked.encode("utf-8")).hexdigest()


class PollerError(RuntimeError):
    """The publisher could not be reached, or served something unusable."""


@dataclass
class PollOutcome:
    status: str                      # new_gazette | reuploaded | unchanged | failed
    gazette_id: str = ""
    publisher_stamp: str = ""
    sha256: str = ""
    detail: str = ""
    ingested: bool = False           # always False; acquisition is not ingestion (D4)
    pending_gazette_id: str = ""      # what a later, explicit ingestion would take
    dry_run: bool = False

    @property
    def changed(self) -> bool:
        return self.status == "new_gazette"


@dataclass
class _State:
    """What the previous check saw. Enough to skip a download, nothing more."""

    page_sha256: str = ""
    page_bytes: int = 0
    last_checked: str = ""
    last_gazette_id: str = ""
    known_hashes: dict = field(default_factory=dict)


def classify_offer(*, hash_matches_archive: bool) -> PollOutcome:
    """Decide an offered PDF on its hash alone.

    Deliberately takes no timestamp argument: the re-upload case is exactly one where a
    newer stamp accompanies unchanged content, and a parameter here would invite its use.
    """
    if hash_matches_archive:
        return PollOutcome(status="reuploaded", detail="content already archived")
    return PollOutcome(status="new_gazette", detail="content not previously archived")


class _Net:
    """Default network. Injectable so a check can be exercised without the publisher."""

    def fetch_page(self, url: str) -> bytes:
        return self._get(url)

    def fetch_pdf(self, url: str) -> bytes:
        return self._get(url)

    @staticmethod
    def _get(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "urTPE-gazette-poller"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - any transport failure is one condition
            raise PollerError("%s: %s" % (type(exc).__name__, exc)) from exc


class Poller:
    """Checks whether a new gazette exists. Never ingests one (design D4)."""

    def __init__(self, archive, *, page_url: str = PAGE_URL, net: _Net | None = None,
                 state_path: Path | str | None = None, log_path: Path | str | None = None,
                 cadence_days: int = CADENCE_DAYS, dry_run: bool = False,
                 emitted_dir: Path | str | None = None):
        self.archive = archive
        self.page_url = page_url
        self.net = net or _Net()
        self.state_path = Path(state_path) if state_path else archive.root / STATE_NAME
        self.log_path = Path(log_path) if log_path else archive.root / RECORD_NAME
        self.cadence_days = cadence_days
        self.dry_run = dry_run
        # Recorded only so a caller can assert the emitted tree was untouched.
        self.emitted_dir = Path(emitted_dir) if emitted_dir else None

    # --- state -------------------------------------------------------------

    def _read_state(self) -> _State:
        if not self.state_path.exists():
            return _State()
        try:
            return _State(**json.loads(self.state_path.read_text(encoding="utf-8")))
        except (ValueError, TypeError):
            return _State()

    def _write_state(self, state: _State) -> None:
        if self.dry_run:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def read_records(archive) -> list[dict]:
        """Every check ever performed, oldest first. A check that found nothing counts."""
        path = archive.root / RECORD_NAME
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    @staticmethod
    def max_gap_days(records: list[dict], *, cadence_days: int = CADENCE_DAYS,
                     now: str | dt.datetime | None = None) -> float | None:
        """Longest interval between checks, and since the last one.

        ``None`` when there is no history at all — missing history is not a gap in
        existing history, and conflating them hides a poller that never ran.
        """
        times = []
        for r in records:
            try:
                times.append(dt.datetime.fromisoformat(r["checked_at"]))
            except (KeyError, ValueError):
                continue
        if not times:
            return None
        times.sort()
        gaps = [(b - a).total_seconds() / 86400.0 for a, b in zip(times, times[1:])]
        end = now if isinstance(now, dt.datetime) else (
            dt.datetime.fromisoformat(now) if now else dt.datetime.now(times[-1].tzinfo))
        gaps.append((end - times[-1]).total_seconds() / 86400.0)
        return max(gaps)

    # --- the check ---------------------------------------------------------

    def poll(self) -> PollOutcome:
        now = dt.datetime.now().astimezone().isoformat()
        try:
            page = self.net.fetch_page(self.page_url)
        except PollerError as exc:
            outcome = PollOutcome(status="failed", detail=str(exc), dry_run=self.dry_run)
            self._record(outcome, now)
            return outcome

        page_hash = _page_fingerprint(page)
        stamp = self._extract_stamp(page)
        state = self._read_state()

        # Design D2: page bytes first. The PDF costs 1.9 MB; the page costs 86 KB.
        if state.page_sha256 and state.page_sha256 == page_hash:
            outcome = PollOutcome(status="unchanged", gazette_id=state.last_gazette_id,
                                  publisher_stamp=stamp, dry_run=self.dry_run,
                                  detail="page bytes unchanged since the last check")
            state.last_checked = now
            self._write_state(state)
            self._record(outcome, now)
            return outcome

        href = self._extract_pdf_href(page)
        if not href:
            outcome = PollOutcome(status="failed", publisher_stamp=stamp,
                                  detail="page carried no PDF link", dry_run=self.dry_run)
            self._record(outcome, now)
            return outcome

        if self.dry_run:
            # A dry run answers "would this download?", not "what is in the document",
            # so it stops before the 1.9 MB transfer. It reports the page as changed
            # without claiming to have classified content it never retrieved.
            outcome = PollOutcome(
                status="would_download", publisher_stamp=stamp, dry_run=True,
                detail="page bytes changed since the last check; PDF not retrieved",
            )
            self._record(outcome, now)
            return outcome

        try:
            body = self.net.fetch_pdf(href)
        except PollerError as exc:
            outcome = PollOutcome(status="failed", publisher_stamp=stamp,
                                  detail=str(exc), dry_run=self.dry_run)
            self._record(outcome, now)
            return outcome

        digest = hashlib.sha256(body).hexdigest()
        held = self.archive.has_hash(digest)
        outcome = classify_offer(hash_matches_archive=held)
        outcome.publisher_stamp = stamp
        outcome.sha256 = digest

        if outcome.status == "reuploaded":
            outcome.gazette_id = state.known_hashes.get(digest, "")
            if not outcome.gazette_id:
                found = self.archive.gazette_id_for_hash(digest)
                outcome.gazette_id = found or ""
            outcome.detail = (
                "publisher re-uploaded identical content%s"
                % (" (gazette %s)" % outcome.gazette_id if outcome.gazette_id else "")
            )
            outcome.pending_gazette_id = outcome.gazette_id
        else:
            if self.dry_run:
                outcome.gazette_id = "dry-run"
                outcome.detail = "new content; not archived because this was a dry run"
            else:
                gazette_id = self._gazette_id_for(body, stamp)
                self._archive(body, gazette_id, digest, stamp)
                outcome.gazette_id = gazette_id
                outcome.detail = "archived as a new gazette; awaiting explicit ingestion"
                state.known_hashes[digest] = gazette_id
            outcome.pending_gazette_id = outcome.gazette_id

        state.page_sha256 = page_hash
        state.page_bytes = len(page)
        state.last_checked = now
        state.last_gazette_id = outcome.gazette_id or state.last_gazette_id
        self._write_state(state)
        self._record(outcome, now)
        return outcome

    # --- helpers -----------------------------------------------------------

    def _record(self, outcome: PollOutcome, now: str) -> None:
        """Write the outcome of every check, including the ones that find nothing."""
        if self.dry_run:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        row = asdict(outcome)
        row["checked_at"] = now
        # `error` is what a consumer reads to tell a failed check from a quiet week;
        # `detail` is prose for a human. Both exist so the two never get conflated.
        if outcome.status == "failed":
            row["error"] = outcome.detail or "check failed with no reason recorded"
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _extract_stamp(page: bytes) -> str:
        text = page.decode("utf-8", "replace")
        m = _STAMP_RE.search(text)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r"資料更新[：:][^<]*?([0-9]{3}-[0-9]{1,2}-[0-9]{1,2}[^<]*)", text)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    @staticmethod
    def _extract_pdf_href(page: bytes) -> str:
        text = page.decode("utf-8", "replace")
        m = _PDF_HREF_RE.search(text)
        return m.group(1) if m else ""

    @staticmethod
    def _gazette_id_for(body: bytes, stamp: str) -> str:
        """Prefer the PDF's own 統計至 line; fall back to the page's stamp.

        The stamp is a publication *timestamp*, not a gazette id, so it is the last
        resort — using it first would file a re-upload under a new date.
        """
        import io

        import pymupdf

        with pymupdf.open(stream=body, filetype="pdf") as doc:
            first = doc[0].get_text()
        m = re.search(r"([0-9]{2,4})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日", first)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            y = y + 1911 if y < 1911 else y
            try:
                return dt.date(y, mo, d).isoformat()
            except ValueError:
                pass
        m = re.search(r"([0-9]{3})-([0-9]{1,2})-([0-9]{1,2})", stamp)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            return dt.date(y + 1911, mo, d).isoformat()
        raise PollerError("could not determine a gazette id from the document or stamp")

    def _archive(self, body: bytes, gazette_id: str, digest: str, stamp: str) -> None:
        """Retain the document and index it as fetched.

        Archive only. Nothing here reads or writes the emitted dataset: an unattended run
        that could ingest is one that could overwrite a good dataset with a bad one
        (design D4).
        """
        self.archive.record_ingest_bytes(
            body, gazette_id, published_date=gazette_id,
            acquisition="fetched", publisher_stamp=stamp, sha256=digest)