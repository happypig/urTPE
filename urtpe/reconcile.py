"""Reconcile a newly ingested gazette against its predecessor.

編號 is a coordinate in a mutable list, not a stable identity, and the mapping is not
even affine. Measured across the three gazettes:

    1150820 -> 1150827   every one of 1,421 matched records moved exactly +5
    1150827 -> 1151002   old#1 -> +8   old#100 -> +6   old#300 -> +5
                         old#1000 -> -13   (moved up past 13 records)
                         old#1420 -> +10

Date-order violations fell from 9 to 1 between those publications: the earlier export
was insertion-ordered, the newer one re-sorts the whole history by 核定日期.

Nor can records be matched on their content. Between 1150827 and 1151002, 59 land
cells differ in text and 43 historical approvals changed date, so an edit or a
re-dating is indistinguishable from a deletion. Three signals survive that:

    approvals newer than the previous maximum date   5      8      authoritative
    net change in total records                     +5     +9      authoritative
    calendar                                       same   changed  authoritative

So this module reports additions and net change authoritatively, reports historical
movement (re-dated, edited) as its own counted signal, and refuses the run only for the
conditions the data supports: the list shrinking, the previous newest cohort being
withdrawn, or a total re-keying. See design.md D6.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from urtpe.ledger import key_from_raw, normalize_land

# A record is "new" when its approval date is later than every date in the previous
# gazette. That boundary is a date the reader has already parsed, so it is trustworthy
# in a way that a content comparison of edited rows is not.
NEW_COHORT = "new"
HISTORICAL = "historical"


@dataclass
class ReconcileResult:
    """What changed between two publications."""

    previous_id: str | None = None
    current_id: str = ""
    comparable: bool = False
    note: str = ""

    previous_newest: str = ""
    new_approvals: int = 0
    previous_total: int = 0
    current_total: int = 0

    redated: list[tuple[str, str]] = field(default_factory=list)
    edited: list[tuple[str, str]] = field(default_factory=list)
    vanished: list[tuple[str, str]] = field(default_factory=list)
    accepted_removals: list[tuple[str, str]] = field(default_factory=list)
    withdrawn_recent: list[tuple[str, str]] = field(default_factory=list)

    moved_project_ids: list[tuple[str, str]] = field(default_factory=list)
    unchanged_project_ids: int = 0
    total_rekey: bool = False

    # The land labels of the approvals newer than the predecessor's newest. A count says
    # how many; a downstream consumer needs which, and cannot reconstruct it afterwards.
    new_approval_labels: list[str] = field(default_factory=list)

    calendar_previous: str = ""
    calendar_current: str = ""
    blocking: list[str] = field(default_factory=list)

    @property
    def net_change(self) -> int:
        return self.current_total - self.previous_total

    @property
    def ok(self) -> bool:
        return not self.blocking

    def report(self) -> str:
        lines = [f"reconcile: {self.previous_id or '(none)'} -> {self.current_id}"]
        if not self.comparable:
            lines.append(f"  {self.note or 'no comparison possible'}")
            return "\n".join(lines)

        lines.append(
            f"  previous newest approval: {self.previous_newest or '(none)'}")
        lines.append(
            f"  new approvals: {self.new_approvals}   "
            f"net change: {self.net_change:+d} "
            f"({self.previous_total} -> {self.current_total})")
        lines.append(
            f"  historical rows changed: re-dated {len(self.redated)}, "
            f"edited {len(self.edited)}, vanished {len(self.vanished)} "
            f"(accepted: {len(self.accepted_removals)})")
        lines.append(
            f"  project identities: moved {len(self.moved_project_ids)}, "
            f"unchanged {self.unchanged_project_ids}")
        if self.total_rekey:
            lines.append("  TOTAL RE-KEY: every project identity differs from the previous gazette")
        cal = "unchanged" if self.calendar_previous == self.calendar_current else "CHANGED"
        lines.append(f"  calendar: {self.calendar_previous} -> {self.calendar_current} ({cal})")

        for label, rows in (("re-dated", self.redated), ("edited", self.edited),
                            ("vanished", self.vanished), ("accepted removal", self.accepted_removals),
                            ("withdrawn recent approval", self.withdrawn_recent)):
            for item in rows[:10]:
                lines.append(f"  ~ {label}: {item[0]} @ {item[1]}")
            if len(rows) > 10:
                lines.append(f"  ~ ... and {len(rows) - 10} more {label}")
        lines += [f"  BLOCKING: {b}" for b in self.blocking]
        return "\n".join(lines)


def _calendar_of(records) -> str:
    from urtpe.extract import calendar_of

    kinds = {calendar_of(r.get("date", "")) for r in records}
    kinds.discard("unknown")
    if not kinds:
        return "unknown"
    if len(kinds) == 1:
        return kinds.pop()
    return "mixed:" + ",".join(sorted(kinds))


def _iso(record) -> str:
    from urtpe.extract import to_iso

    return to_iso(record.get("date", ""))[0] or ""


def _land_key(record) -> tuple[str, str]:
    """Identity ignoring date: district plus the normalized parcel description.

    A land cell that still matches after a date change means the city re-dated the
    row; one that does not means the text was edited or the row is gone.
    """
    return (record.get("district") or "?", normalize_land(record.get("land") or ""))


def _label(record) -> str:
    district = record.get("district") or "?"
    land = re.sub(r"\s+", "", record.get("land") or "")
    return f"{district} {land[:44]}"


def reconcile(previous: list[dict] | None, current: list[dict], *,
              previous_id: str | None = None, current_id: str = "",
              previous_projects: list[str] | None = None,
              current_projects: list[str] | None = None,
              accepted_removals: set[tuple[str, str]] | None = None,
              strict: bool = False) -> ReconcileResult:
    """Compare two publications and decide whether the ingest may proceed.

    ``strict`` promotes historical disappearance to blocking, which a ledger
    acceptance satisfies. ``previous_projects`` / ``current_projects`` enable the
    identity-move report; a total re-key is its own outcome because
    ``urtpe.coverage`` cannot express it.
    """
    accepted_removals = accepted_removals or set()
    result = ReconcileResult(previous_id=previous_id, current_id=current_id)
    result.calendar_current = _calendar_of(current)

    if previous is None:
        result.comparable = False
        result.note = "no previous gazette archived; nothing to compare against"
        return result

    result.comparable = True
    result.calendar_previous = _calendar_of(previous)
    result.previous_total = len(previous)
    result.current_total = len(current)

    prev_dates = sorted(d for d in (_iso(r) for r in previous) if d)
    cur_dates = sorted(d for d in (_iso(r) for r in current) if d)
    result.previous_newest = prev_dates[-1] if prev_dates else ""

    boundary = result.previous_newest
    if boundary:
        result.new_approvals = sum(1 for r in current if _iso(r) > boundary)
        result.new_approval_labels = sorted(
            {_label(r) for r in current if _iso(r) > boundary})
        # A previous newest-cohort row whose content is absent from the current
        # gazette altogether — deleted, or moved to a different date — is a
        # withdrawal worth refusing over. Rows merely re-dated stay in the
        # historical signal below.
        cur_keys = {key_from_raw(r) for r in current}
        result.withdrawn_recent = [
            (_label(r), _iso(r)) for r in previous
            if _iso(r) == boundary and key_from_raw(r) not in cur_keys
        ]
    else:
        newest_cohort = []

    # Historical comparison: match on land first so a re-dating is separated from an
    # edit or a disappearance, which content matching alone cannot do.
    prev_hist = [r for r in previous if _iso(r) <= boundary]
    cur_hist = [r for r in current if _iso(r) <= boundary]

    prev_by_land: dict[tuple[str, str], list[dict]] = {}
    for rec in prev_hist:
        prev_by_land.setdefault(_land_key(rec), []).append(rec)
    cur_by_land: dict[tuple[str, str], list[dict]] = {}
    for rec in cur_hist:
        cur_by_land.setdefault(_land_key(rec), []).append(rec)

    prev_full: Counter = Counter()
    cur_full: Counter = Counter()

    for land, prevs in prev_by_land.items():
        curs = cur_by_land.get(land)
        if not curs:
            for rec in prevs:
                key = key_from_raw(rec)
                entry = (_label(rec), key[1])
                if key in accepted_removals:
                    result.accepted_removals.append(entry)
                else:
                    result.vanished.append(entry)
            continue
        # The land cell survives, so any residual difference within this group is the
        # city moving the approval date. Counters are scoped to the group: a global
        # difference would report one unit's re-dating under another's label.
        prev_group = Counter(key_from_raw(r) for r in prevs)
        cur_group = Counter(key_from_raw(r) for r in curs)
        for key, n in (prev_group - cur_group).items():
            rec = next(r for r in prevs if key_from_raw(r) == key)
            result.redated.append((_label(rec), key[1]))

    # Rows present now whose land did not exist before are edits or additions inside
    # the historical window; count the net so the two effects can be told apart.
    for land, curs in cur_by_land.items():
        if land in prev_by_land:
            continue
        for rec in curs:
            result.edited.append((_label(rec), _iso(rec)))

    if result.net_change < 0:
        result.blocking.append(
            f"the list shrank: {result.previous_total} -> {result.current_total} records. "
            "Either the city removed approvals or the reader lost them.")

    if result.withdrawn_recent:
        names = ", ".join(f"{lbl} @ {d}" for lbl, d in result.withdrawn_recent[:5])
        result.blocking.append(
            f"{len(result.withdrawn_recent)} approval(s) from the previous newest cohort "
            f"({boundary}) are absent from the new one: {names}")

    unexplained = [v for v in result.vanished if v not in result.accepted_removals]
    if strict and unexplained:
        result.blocking.append(
            f"strict mode: {len(unexplained)} historical row(s) cannot be matched and no "
            "removal is recorded as accepted; record an acceptance in the ledger or "
            "re-run without --strict-reconcile")

    if previous_projects is not None and current_projects is not None:
        prev_set, cur_set = set(previous_projects), set(current_projects)
        result.moved_project_ids = [(pid, "") for pid in sorted(prev_set - cur_set)]
        result.unchanged_project_ids = len(prev_set & cur_set)
        result.total_rekey = bool(prev_set) and not (prev_set & cur_set)
        if result.total_rekey:
            result.blocking.append(
                "total re-key: every project identity differs from the previous gazette, "
                "so all cached per-project data is orphaned; confirm before proceeding")
    return result