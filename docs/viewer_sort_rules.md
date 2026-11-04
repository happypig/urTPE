# How the viewer sorts one project's timeline

This note explains the sort rules in `viewer/app.js`. Read it before you
touch the render path. Every rule has a reason. Change a rule only with a
test and a measurement.

## Background

One project can have many approval nodes. The gazette gives each approval a
row number (編號). The city's case platform gives each case an id, for
example `09506204`. A case id is a filing date plus a serial digit. The city
sorts its 相關連結 list by this id. The viewer copies that order.

Some cases never bind to a gazette row. The viewer shows them as virtual
orphan nodes. They carry their own case id.

## Rule 1 — put each node in a swimlane column

The x-axis is the track (事業種類). Each track gets one column:

1. 事業概要, 事業計畫, 都市更新計畫 — left group.
2. 事業計畫、權利變換, 都市計畫、權利變換 — middle group.
3. 權利變換, 其他 — right group.

Sort the column keys by this group order. When two keys fall in one group,
sort them by plain string compare. Virtual orphans get a column from their
own track.

Code: `trackPosition` at `viewer/app.js:84`, column sort at
`viewer/app.js:920`.

## Rule 2 — sort the rows by case id

The y-axis is the row order. Put all members in one list: real nodes and
virtual orphans. Sort by three keys, in this order:

1. **Case id, ascending.** A real node uses its anchored case
   (`links.taipei[0]`). A virtual orphan uses its own case id. A node with
   no case gets `""`, which sorts first. This copies the city's
   相關連結 order. It does not change when the city re-issues the gazette.
2. **Node date, ascending.** This decides only between members that share
   one case id. Before 2026-11, equal case ids tied on recno. 編號 is a
   newest-first coordinate, so the newer gazette row rendered above the
   older one in 30 of 39 same-case groups. The date tie-break fixed that.
3. **Recno as text.** Last resort, when dates are equal or absent.

Code: `effectiveCaseKey` at `viewer/app.js:550`, row sort at
`viewer/app.js:964`.

## Rule 2 — why case id beats date

This is not a style choice. It replaced a measured bug.

**The bug (2026-08-31).** 29 families held two or more virtual orphans on
one date. The old sort left them tied. The browser then broke ties by
input order — the platform's search-response order. That order changed
between page loads. The same graph rendered in a different order each
time.

**The fix (decision D12, `openspec/changes/archive/2026-09-02-viewer-enhancements-and-orphan-case-anchoring/design.md`).**
Sort by case id. A case id holds the filing year and a serial digit, so
ascending case id equals filing order. It never changes between loads, and
it never changes when the city re-issues the gazette. Amendment 3 made the
order family-wide, so the graph reads in the same order as the city's own
相關連結 list.

**Five reasons date order loses:**

1. Dates are outcomes. Case ids are filings. Two cases filed the same day
   can win approval months apart. Date order splits these attempt twins
   and mixes other families' cases between them. Case id keeps the twins
   together, like the city's own 相關連結 list.
2. A dead track would lead the story. 逸仙段三小段-34's orphan 概要 holds
   the earliest date in its project — but the track is dead (已失效). Date
   order renders that dead 概要 as the project's start. The real start is
   the plan filing.
3. 30 corpus orphans carry no date at all. Date order drops them to the
   tail. The family-wide interleave needs them between their case id
   neighbours.
4. Date ties still need case id. 29 families share one date. A date sort
   falls back to case id for exactly those pairs. It gains nothing.
5. The city re-dates historical rows. A case id never changes. Case id
   order survives a re-issue; date order can flip.

**Your rule:** keep case id first. Do not reach for a date sort when a
project looks non-chronological — see the cost note below. Re-count the 51
projects if you must change the rule.

## Rule 3 — interleave execution events by date

Execution events are 建照, 開工, and 使照. They do not get rows from rule 2.
Insert each event before the first member whose date is later than the
event date. Put events with no later member at the end.

First normalise every event date to ISO. National portal dates arrive as
ROC dots (`110.10.25`); taipei milestones arrive as slashes
(`2023/04/27`). A slash sorts after every ISO date of the same year in
ASCII, so un-normalised events landed at the newest end. Both formats must
become `YYYY-MM-DD`.

Code: date normalisation at `viewer/app.js:368`, event interleave at
`viewer/app.js:975`.

## Rule 4 — draw stage clusters as bands

Members group by stage: 擬訂, 變更, 變更(第二次), and so on. Each group
draws a band. The band is visual only. Rule 2 still decides the row
sequence.

Inside one band:

1. Members with a date sort before members without one.
2. Then case id ascending.
3. Then 區段 token compare.

The band's date is the real member's date. With no real member, take the
oldest member date. With no date at all, the band reads `(未核定)` and
sorts to the bottom.

Code: `compareClusterMembers` at `viewer/app.js:558`, cluster date at
`viewer/app.js:947`.

## Rule 5 — place orphan nodes

An orphan node's own date is often empty. Its band then lends the band
date to the event interleave. This stops an undated orphan from colliding
with events.

Draw a dotted edge from the orphan to the nearest real row above it. When
no real row sits above, draw it to the nearest row below. Read the
rendered rows, not dates — an undated orphan has no date of its own, so a
date test can never fire.

Shift an orphan 32px right when its row sits between two real rows of the
same swimlane. Measured on the whole corpus: this never fires for 概要
orphans. Keep the test anyway; the corpus can change.

Code: row neighbours at `viewer/app.js:1024`, shift test at
`viewer/app.js:1037`.

## Known cost — 51 projects read out of date order

Rule 2 puts case id above date. In 51 of 682 projects, some pairs of rows
disagree with date order (95 pairs in total). Three shapes cause this:

1. Same-day serial cases. Two cases filed the same day differ only in the
   last digit. Their approval lag differs.
2. Orphans. A dead 概要 case has a late case id but an early approval
   date.
3. Interleaved families. Two renewal attempts whose filing order and
   approval order do not match.

The board accepted this. Do not fix it with a date sort. If you change
the order rule, count the 51 projects again before and after, and record
both numbers on the inspection board.

## Checks before you merge

1. Run `python -m pytest`. All tests must pass.
2. Run `node scripts\viewer_smoke.js`. The render must finish with no
   error.
3. Open a project from each shape above in the viewer: 逸仙段三小段-34
   (orphan between rows), 寶清段二小段-375 (undated orphan last),
   關渡段二小段-303 (same-case date tie-break). The order must match this
   note.
