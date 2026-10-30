# -*- coding: utf-8 -*-
"""How a publication orders itself, as a countable property.

The city's list is published newest-first, but not perfectly so: a small number of rows
sit against the order. This module counts those departures per publication so the
question of whether the publisher sorts by date *permanently* can be answered by
observation rather than by re-deriving figures by hand.

Two properties of the published data make the naive implementation wrong in ways that
look like answers:

- **編號 1 is repeated as a running page head.** 1151002 does this on all 246 pages, so
  a row count without deduplicating reads 1681 instead of 1436 and the departure count
  inflates from 1 to 246 — the metric manufacturing the anomaly it exists to detect.
- **The calendar changes.** 1151002 publishes Gregorian dates (`2026/9/24`) where earlier
  publications use ROC (`115/8/27`). An ROC-only parser returns no dated records at all,
  which reports as *zero departures*: a broken metric indistinguishable from a healthy one.

So the report carries its own dated-record count, and `unmeasurable` is set whenever the
denominator is too small for the numerator to mean anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Below this share of dated records, a zero-departure result describes the parser
# rather than the publication. Chosen because the real publications date every row;
# a genuine publication that leaves a third of its dates blank is a different finding.
MIN_DATED_SHARE = 0.9


@dataclass
class DateOrderReport:
    """Departures from descending approval date, with the count that gives them meaning."""

    violations: int = 0
    dated_records: int = 0
    total_records: int = 0
    max_inversion_days: int = 0

    @property
    def is_sorted(self) -> bool:
        """Whether the publication descends by approval date.

        False below two dated records: one record is not evidence of an ordering in
        either direction, and reporting it as sorted is how an unreadable publication
        comes to look perfectly ordered.
        """
        return self.violations == 0 and self.dated_records >= 2

    @property
    def unmeasurable(self) -> bool:
        """True when the dated count is too small for the violation count to mean anything."""
        if self.total_records == 0 or self.dated_records == 0:
            return True
        return (self.dated_records / self.total_records) < MIN_DATED_SHARE

    def describe(self) -> str:
        if self.unmeasurable:
            return (
                "UNMEASURABLE: %d of %d records carried a readable approval date. "
                "A departure count over this many records describes the parser, "
                "not the publication."
                % (self.dated_records, self.total_records)
            )
        worst = (", largest inversion %d days" % self.max_inversion_days
                 if self.max_inversion_days else "")
        return "%d departure%s from descending approval date across %d dated records (%s)" % (
            self.violations, "" if self.violations == 1 else "s",
            self.dated_records, worst or "strictly descending")


def departures_from_descending(
    dates: list[str | None],
) -> tuple[int, int, bool]:
    """Count positions where a record is dated earlier than the one before it.

    Returns ``(violations, max_inversion_days, is_sorted)``. A record with no readable
    date is skipped rather than compared: an undated cell between two dated ones is a
    gap in the data, not an inversion in the ordering.

    ``is_sorted`` is False when fewer than two records carry a date, because a single date
    establishes no ordering at all — claiming otherwise is how an unreadable publication
    comes to look perfectly ordered.

    The caller owns deduplication: ``urtpe.extract._dedupe_by_recno`` already ran on the
    records these dates came from (first occurrence wins, extract.py), which is where the
    repeated-page-head guarantee lives since 2026-10-06. ``date_order_report`` — the
    PDF-level wrapper that deduplicated here — was deleted as dead code (2026-10-30
    cleanup, docs/inspection.md F3): no live spec cites it and nothing in production
    called it.
    """
    parsed = [(i, date.fromisoformat(d)) for i, d in enumerate(dates)
              if d and _is_iso(d)]
    violations = 0
    worst = 0
    for (_, prev), (_, cur) in zip(parsed, parsed[1:]):
        if cur > prev:
            violations += 1
            worst = max(worst, (cur - prev).days)
    return violations, worst, violations == 0 and len(parsed) >= 2


def _is_iso(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True