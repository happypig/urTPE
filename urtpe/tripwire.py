"""Completeness tripwire for gazette ingestion.

Refuses to emit a dataset it cannot prove is complete. The reader already raises
``TableStructureError`` for structural faults; this module covers the faults that
only show up *across* records — a gap in 編號, an unparsed date, a page that yielded
no table — and, critically, evaluates everything before any artifact is written.

That ordering is the whole point. ``urtpe.coverage`` diffs only
``set(before) & set(after)``, so when every ``project_id`` changes the intersection
is empty, ``regressions`` is empty, and the guard passes while all 709 caches are
orphaned. A check that runs after the damage, or that cannot see the failure, is
not a check.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tripwire:
    """Structural completeness gate.

    Thresholds are parameters rather than constants: they are calibrated against the
    gazettes measured so far and may need adjustment when the city publishes again.
    """

    # A defective export repeats one data row in the page header of every page after
    # the first. The reader discards those as duplicate 編號, so a small non-zero
    # count is expected and healthy; a large one means something else is wrong.
    max_duplicate_recnos: int = 400
    # 編� runs 1..N with no gaps in every gazette measured (1422 / 1427 / 1436).
    require_contiguous_recnos: bool = True

    # 編號 absent because the publisher truncated that record's cell; set by check().
    excluded_recnos: list[int] = field(default_factory=list)

    def check(self, records: list[dict], *, pages: int = 0, tables_found: int = 0,
              duplicate_recnos: int = 0,
              excluded_recnos: set[int] | None = None) -> list[str]:
        """Return every fault found; an empty list means the extraction is complete.

        ``excluded_recnos`` are the 編號 the reader deliberately dropped because the
        publisher truncated their cell (see :class:`urtpe.extract.CellFault`). They
        are absent from ``records`` on purpose, so they must not be reported as
        missing; any *other* gap still means a page or record went unread.
        """
        faults: list[str] = []
        excluded = {int(v) for v in (excluded_recnos or ())}
        self.excluded_recnos = []
        if not records:
            return ["no records extracted"]

        recnos = []
        for rec in records:
            try:
                recnos.append(int(rec["recno"]))
            except (KeyError, TypeError, ValueError):
                faults.append(f"record with a non-integer 編號: {rec.get('recno')!r}")
        if not recnos:
            return faults or ["no integer 編號 present"]

        unique = sorted(set(recnos))
        if self.require_contiguous_recnos:
            expected = set(range(1, max(unique) + 1))
            missing = sorted(expected - set(unique))
            unexplained = sorted(set(missing) - excluded)
            if unexplained:
                preview = ", ".join(str(v) for v in unexplained[:20])
                more = f" (+{len(unexplained) - 20} more)" if len(unexplained) > 20 else ""
                faults.append(
                    f"編號 not contiguous: {len(unexplained)} missing "
                    f"(expected 1..{max(unique)}): {preview}{more}")
            extra = sorted(set(unique) - expected)
            if extra:
                faults.append(f"編號 above the maximum: {extra[:10]}")
            # A gap that is entirely explained is still a shortfall in the gazette,
            # so it is surfaced as a note the caller reports rather than a pass.
            accounted = sorted(set(missing) & excluded)
            if accounted:
                self.excluded_recnos = accounted

        bad_dates = [r["recno"] for r in records
                     if not _parses(r.get("date", ""))]
        if bad_dates:
            faults.append(
                f"{len(bad_dates)} record(s) with an unparsed 核定日期: "
                f"{', '.join(str(v) for v in bad_dates[:20])}")

        if pages and tables_found != pages:
            faults.append(
                f"pages yielding a table: {tables_found} of {pages}; "
                "a page with no table would silently drop its records")

        if duplicate_recnos > self.max_duplicate_recnos:
            faults.append(
                f"duplicate 編號 count {duplicate_recnos} exceeds tolerance "
                f"{self.max_duplicate_recnos}")

        return faults


def _parses(date_str: str) -> bool:
    from urtpe.extract import to_iso

    return to_iso(date_str)[0] is not None


@dataclass
class TripwireResult:
    """Outcome of the gate, including what was observed for the run report."""

    ok: bool
    faults: list[str] = field(default_factory=list)
    calendar: str = "unknown"
    record_count: int = 0
    project_count: int = 0
    duplicate_recnos: int = 0

    def report(self) -> str:
        head = "tripwire: PASS" if self.ok else f"tripwire: FAIL ({len(self.faults)} fault(s))"
        lines = [
            head,
            f"  records: {self.record_count}  projects: {self.project_count}",
            f"  calendar: {self.calendar}  duplicate 編號: {self.duplicate_recnos}",
        ]
        lines += [f"  - {f}" for f in self.faults]
        return "\n".join(lines)


class TripwireFailure(RuntimeError):
    """The extraction was not provably complete; nothing was written."""

    def __init__(self, result: TripwireResult):
        self.result = result
        super().__init__(result.report())