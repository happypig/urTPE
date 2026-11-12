# Proposal: dashboard-review-time

## Why

The dashboard's 審議量能與時程 section measures review time from the earliest
of three application dates (申請計畫日期, 申請概要日期, the national 事業計畫申請日期,
over every case of the project) to the gazette date of the project's earliest
node. The user re-stated the rule on 2026-11-13 after reading the figures: a
概要 application is an outline, not the plan under review; the national date
is a second witness of the city's own date; and the interval a policy reader
asks for ends at the approval that lets construction start, not at the first
gazette row. The page today also has no way to show the second interval, and
its 審議 card reads the first one. The data behind the rule was measured on
the 2026-10-28 payload (680 projects): every one of the 666 projects with a
plan approval carries the application and approval dates on the first
approval's own city case, so the rule can be anchored on that case instead
of on a scan over every case.

## What Changes

- The application date of a project is read from the city case bound to its
  first approval node: the earliest of that case's 申請計畫日期 and 申請權變日期.
  The first approval is the project's earliest 擬訂 node among its 事業計畫 and
  權利變換 approvals; when no 擬訂 node exists the earliest such node. 事業概要
  rows never count.
- The first-approval interval (line 1) ends at that case's 核定日期 or
  權變核定日期, earliest.
- A second interval (line 2) ends at the approval just before the project's
  building permit: the case 核定 date of the latest eligible node dated before
  the earliest 建照核發日期, or of the latest eligible node when no permit is
  recorded. It is absent when the permit precedes every node.
- The review chart draws both medians by year of first approval, each with its
  project count; the 審議時間中位數 card shows the line 2 median and names the
  line 1 median in its sub-line; the total-time figure keeps its meaning but
  starts from the new application date.
- Projects whose every node is a 事業概要 approval are left out of both lines,
  and the chart caption says how many in the scope.
- The definitions block restates review time under the new rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `policy-dashboard`: the requirement "Review time runs from the earliest
  application to the first approval, total time to completion" is replaced
  with the recno-anchored rule and the second interval. Every live scenario is
  carried; eight scenarios are added.

## Impact

- `viewer/dashboard.js`: the derivation loop (application, first approval,
  line 2), `reviewOf`, `reviewChart` (two series, legend), the 審議 card, the
  review caption, the definitions text in both languages.
- `scripts/dashboard_smoke.js`: prints the review caption so the 概要 notice
  is testable; the series extraction already reads every hover point.
- `tests/test_dashboard_rules.py`: the review tests follow the new rule; the
  dotted-ROC test moves to an idle-years assertion because the national
  application date is no longer a review source.
- Data: five split families and two swapped stage labels found while
  measuring this rule are fixed through the correction ledger and a PDF
  ingest, as their own `fix:` commit before this change is measured. That
  commit is not part of this change; the design records the seven entries.
- No pipeline code, no payload schema, no other page.
