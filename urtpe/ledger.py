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
)


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

    def __post_init__(self) -> None:
        if not self.at:
            self.at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        if self.field and self.field not in CORRECTABLE_FIELDS and not self.accept_removal:
            raise ValueError(
                f"{self.field!r} is not correctable; expected one of {CORRECTABLE_FIELDS}")

    @property
    def key(self) -> tuple[str, str]:
        return (self.match_land_core, self.match_iso_date)

    def describe(self) -> str:
        if self.accept_removal:
            return f"accept removal of {self.match_land_core} @ {self.match_iso_date} ({self.why})"
        return f"{self.match_land_core} @ {self.match_iso_date}: {self.field} -> {self.to!r} ({self.why})"


@dataclass
class LedgerOutcome:
    """What applying the ledger did, for the run report."""

    applied: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)

    def report(self) -> str:
        lines = [f"manual corrections applied: {len(self.applied)}"]
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
            by_key.setdefault(entry.key, []).append(entry)

        matched_keys: set[tuple[str, str]] = set()
        for rec in records:
            key = key_of(rec)
            for entry in by_key.get(key, ()):
                if not hasattr(rec, entry.field):
                    continue
                setattr(rec, entry.field, entry.to)
                matched_keys.add(key)
                outcome.applied.append(entry.describe())

        for entry in entries:
            if entry.accept_removal:
                continue
            if entry.key not in matched_keys:
                outcome.unmatched.append(entry.describe())

        all_describes = {e.describe() for e in self.entries()}
        for entry in entries:
            if entry.describe() in all_describes:
                continue
            outcome.superseded.append(entry.describe())
        return outcome


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