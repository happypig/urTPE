"""Append-only ledger of manual data corrections.

Replaces dated one-off scripts that patch emitted output in place. Those patches
are lost or silently reverted by the next rebuild, and keying them on 編號 makes
them position-dependent: 編號 is a coordinate within one publication, so a patch
written against 編號 621 lands on a different row once approvals are prepended.

Entries here are keyed on content — land core plus approval date — so a correction
travels with its case across publications. Entries are only ever appended; fixing a
wrong correction means appending one that supersedes it, which keeps the history.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Kept beside the gazette archive, outside the git working tree, for the same
# reason: it is operational history that must outlive any single checkout.
# Overridable by URTPE_LEDGER so a test run cannot append to the live ledger.
DEFAULT_LEDGER_PATH = Path(
    os.environ.get("URTPE_LEDGER")
    or Path(__file__).resolve().parents[2] / "urtpe-gazettes" / "corrections.jsonl"
)

# Fields a correction may set on a CleanRecord.
CORRECTABLE_FIELDS = (
    "track", "stage", "stage_index", "area_section", "implementer", "planner",
    "section", "first_parcel", "land_count", "named_anchor", "name",
    # ledger-date-correction: the ISO approval date. The entry is keyed on the
    # PRINTED day (so it keeps matching on every rebuild); the printed `date`
    # text is never touched, and `ymd` follows the corrected value in apply().
    # First use: recno 986 (德惠段813-1), printed 2017/5/10 for an approval the
    # city dates 2018/05/10.
    "iso_date",
)

_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Correction:
    """One manual correction."""

    match_land_core: str
    match_iso_date: str
    field: str
    to: object
    why: str
    by: str
    at: str = ""
    gazette_id: str = ""
    supersedes: str | None = None
    # Removal acceptances let reconciliation proceed when the city has genuinely
    # dropped a record, instead of aborting forever.
    accept_removal: bool = False
    # Merge confirmation (D5, ledger-confirm-merge): names a SECOND record by its
    # content key and states the two belong to one project family, whatever the
    # similarity score. Changes no field of either record — it answers a §6.8
    # merge-candidate flag, it does not invent data.
    confirm_merge: bool = False
    with_land_core: str = ""
    with_iso_date: str = ""

    def __post_init__(self) -> None:
        if not self.at:
            self.at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        if self.confirm_merge:
            if not self.with_land_core or not self.with_iso_date:
                raise ValueError(
                    "a confirm_merge entry must name the second record "
                    "(with_land_core + with_iso_date)")
            # A confirmation relates two records and sets nothing; its `field`
            # stays empty the way an accept_removal's does.
            return
        if self.field and self.field not in CORRECTABLE_FIELDS and not self.accept_removal:
            raise ValueError(
                f"{self.field!r} is not correctable; expected one of {CORRECTABLE_FIELDS}")
        if self.field == "iso_date":
            # Refuse a typo when the line is written, not on the next rebuild:
            # a calendar day in ISO form, nothing else (no slashes, no ROC form).
            value = self.to if isinstance(self.to, str) else ""
            try:
                if not _ISO_DAY.match(value):
                    raise ValueError
                dt.date.fromisoformat(value)
            except ValueError:
                raise ValueError(
                    f"iso_date correction must be a calendar day as YYYY-MM-DD, got {self.to!r}") from None

    @property
    def key(self) -> tuple[str, str]:
        return (self.match_land_core, self.match_iso_date)

    @property
    def with_key(self) -> tuple[str, str]:
        return (self.with_land_core, self.with_iso_date)

    def describe(self) -> str:
        if self.confirm_merge:
            return (f"confirm merge {self.match_land_core} @ {self.match_iso_date} "
                    f"with {self.with_land_core} @ {self.with_iso_date} ({self.why})")
        if self.accept_removal:
            return f"accept removal of {self.match_land_core} @ {self.match_iso_date} ({self.why})"
        return f"{self.match_land_core} @ {self.match_iso_date}: {self.field} -> {self.to!r} ({self.why})"


@dataclass
class LedgerOutcome:
    """What applying the ledger did, for the run report."""

    applied: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)
    # Recno pairs a confirmed merge resolved to (both keys matched exactly one
    # record each); merge() unions these before scoring (D5, ledger-confirm-merge).
    confirmed_pairs: list[tuple[int, int]] = field(default_factory=list)

    def report(self) -> str:
        lines = [f"manual corrections applied: {len(self.applied)}"]
        # Name every applied entry: a correction that turns out wrong affects
        # every run until superseded, so the report is where a person sees what
        # moved (and a confirmation names both of its keys).
        for a in self.applied:
            lines.append(f"  - applied: {a}")
        lines.append(f"unmatched corrections: {len(self.unmatched)}")
        for u in self.unmatched:
            lines.append(f"  - unmatched: {u}")
        for s in self.superseded:
            lines.append(f"  - superseded: {s}")
        return "\n".join(lines)


def normalize_land(land: str) -> str:
    """Collapse a 地號 cell to a comparable form.

    Line wrapping and punctuation vary between publications of the same parcel list;
    stripping whitespace and the list separators makes two prints of one cell
    comparable without altering either.
    """
    if not land:
        return ""
    text = re.sub(r"\s+", "", land)
    return re.sub(r"[、,，]", "", text)


class CorrectionLedger:
    """An append-only JSONL file of :class:`Correction` entries."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else DEFAULT_LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, correction: Correction) -> None:
        """Append one entry. Never reads or rewrites existing lines."""
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(correction), ensure_ascii=False) + "\n")

    def entries(self) -> list[Correction]:
        """Every entry, oldest first. Malformed lines are skipped, not fatal."""
        if not self.path.exists():
            return []
        out: list[Correction] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                data.pop("at", None) if data.get("at") is None else None
                out.append(Correction(**data))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return out

    def effective(self) -> list[Correction]:
        """Entries that are not superseded by a later one."""
        superseded = {e.supersedes for e in self.entries() if e.supersedes}
        return [e for e in self.entries() if e.describe() not in superseded]

    def accepted_removals(self) -> set[tuple[str, str]]:
        """Land-core/date pairs whose removal from the list has been verified."""
        return {e.key for e in self.effective() if e.accept_removal}

    def apply(self, records, *, key_of=None) -> LedgerOutcome:
        """Apply every effective entry to ``records`` in place.

        ``records`` are ``CleanRecord`` objects. ``key_of`` maps a record to its
        ``(land_core, iso_date)`` key; it defaults to the fields the cleansing step
        produces. Unmatched entries are reported, never fatal: a correction for a
        record that has not been republished yet is normal.

        A ``confirm_merge`` entry sets no field: each of its two keys must match
        exactly one record, and the recno pair lands on
        ``LedgerOutcome.confirmed_pairs`` for ``merge()`` to union (D5). A key
        matching no record, or two or more (a land cell + date printed twice),
        leaves the confirmation unmatched — reported, linking nothing, never
        guessed.
        """
        outcome = LedgerOutcome()
        if key_of is None:
            key_of = default_key

        entries = self.effective()
        if not entries:
            return outcome

        by_key: dict[tuple[str, str], list[Correction]] = {}
        for entry in entries:
            if entry.accept_removal:
                continue
            # Normalize the stored key the way default_key normalizes the record:
            # an operator copies the 地號 cell verbatim from the gazette, so the
            # entry may hold separators/wrapping the record key has already lost.
            by_key.setdefault(_norm_key(entry.key), []).append(entry)

        recs_by_key: dict[tuple[str, str], list] = {}
        for rec in records:
            recs_by_key.setdefault(key_of(rec), []).append(rec)

        matched_keys: set[tuple[str, str]] = set()
        for rec in records:
            key = key_of(rec)
            for entry in by_key.get(key, ()):
                if entry.confirm_merge:
                    continue  # set no field; resolved below from recs_by_key
                if not hasattr(rec, entry.field):
                    continue
                setattr(rec, entry.field, entry.to)
                if entry.field == "iso_date" and hasattr(rec, "ymd"):
                    # merge picks the anchor and graph orders members on ymd
                    # (urtpe/merge.py:185, urtpe/graph.py:12), so the tuple
                    # must follow the corrected day or the two views disagree.
                    rec.ymd = tuple(int(part) for part in entry.to.split("-"))
                matched_keys.add(key)
                outcome.applied.append(entry.describe())

        # Merge confirmations: both keys must resolve to exactly one record.
        for entry in entries:
            if not entry.confirm_merge:
                continue
            first = recs_by_key.get(_norm_key(entry.key), [])
            second = recs_by_key.get(_norm_key(entry.with_key), [])
            if len(first) == 1 and len(second) == 1:
                a, b = first[0].recno, second[0].recno
                outcome.confirmed_pairs.append((min(a, b), max(a, b)))
                matched_keys.add(_norm_key(entry.key))
                matched_keys.add(_norm_key(entry.with_key))
                outcome.applied.append(entry.describe())
            else:
                why = ("ambiguous: matches %d and %d records" % (len(first), len(second))
                       if (len(first) > 1 or len(second) > 1)
                       else "a named record matches no record in this gazette")
                outcome.unmatched.append(f"{entry.describe()} [{why}]")

        for entry in entries:
            if entry.accept_removal or entry.confirm_merge:
                continue
            if _norm_key(entry.key) not in matched_keys:
                outcome.unmatched.append(entry.describe())

        # Report the history: every entry a later one superseded (they are in
        # the file, but effective() dropped them — they applied nothing here).
        superseded_describes = {e.supersedes for e in self.entries() if e.supersedes}
        for entry in self.entries():
            if entry.describe() in superseded_describes:
                outcome.superseded.append(entry.describe())
        return outcome


def _norm_key(key: tuple[str, str]) -> tuple[str, str]:
    """Normalize a stored entry key to the record-key form.

    default_key normalizes a record's land cell (separators and whitespace
    stripped); the ledger entry may hold the cell as copied verbatim from the
    gazette. Matching compares like with like — see the D5 acceptance test that
    caught the 18-parcel cell (its 、 separators) never matching.
    """
    return (normalize_land(key[0]), key[1])


def default_key(record) -> tuple[str, str]:
    """Match key for a CleanRecord: normalized land cell plus ISO approval date."""
    return (normalize_land(getattr(record, "land", "")),
            getattr(record, "iso_date", "") or "")


def key_from_raw(record) -> tuple[str, str]:
    """Match key for a RawRecord or extracted dict."""
    from urtpe.extract import to_iso

    land = record.get("land", "") if isinstance(record, dict) else getattr(record, "land", "")
    date = record.get("date", "") if isinstance(record, dict) else getattr(record, "date", "")
    iso = to_iso(date)[0] or ""
    return (normalize_land(land), iso)