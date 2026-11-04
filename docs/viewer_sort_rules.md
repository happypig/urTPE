# How the viewer sorts one project's timeline

This note explains the sort rules in `viewer/app.js`. Read it before you
touch the render path. Every rule has a reason. Change a rule only with a
test and a measurement.

## Background

One project can have many approval nodes. The gazette gives each approval a
row number (編號). The city's case platform gives each case an id, for
example `09506204`. A case id is a filing date plus a serial digit. The city
sorts its 相關連結 list by this id.

Some cases never bind to a gazette row. The viewer shows them as virtual
orphan nodes. They carry their own case id.

Each case also carries its own milestone dates: the city's platform records
the approvals and applications of that case (核定日期, 概要核准日期,
申請計畫日期, and so on). A real node reads them from
`links.case_milestones[case_id]`. A virtual orphan carries its dict in
`milestones_taipei_case`.

## Rule 1 — put each node in a swimlane column

The x-axis is the track (事業種類). Each track gets one column:

1. 事業概要, 事業計畫, 都市更新計畫 — left group.
2. 事業計畫、權利變換, 都市計畫、權利變換 — middle group.
3. 權利變換, 其他 — right group.

Sort the column keys by this group order. When two keys fall in one group,
sort them by plain string compare. Virtual orphans get a column from their
own track.

Code: `trackPosition` at `viewer/app.js:84`, column sort at
`viewer/app.js:936`.

## Rule 2 — sort the rows by the case's own event date

The y-axis is the row order. Put all members in one list: real nodes and
virtual orphans. Sort by three keys, in this order:

1. **The member's own event date, ascending.** Read the dates from the
   case's own milestones, in this order:
   - A 概要-track member: 概要核准日期 → 申請概要日期 → 申請計畫日期.
   - A plan-track member (事業計畫, 權利變換, combined): 核定日期 →
     權變核定日期 → 申請計畫日期 → 申請權變日期 → 申請概要日期.
   A member with a gazette date uses that date; the milestones only fill
   the members without one (today: virtual orphans).
2. **Case id, ascending.** This breaks equal dates and orders the members
   with no date at all. A real node uses its anchored case
   (`links.taipei[0]`). A virtual orphan uses its own case id. A node with
   no case gets `""`, which sorts first.
3. **Recno as text.** Last resort, when case ids are equal too.

Code: `ownEventDate` at `viewer/app.js:572`, `effectiveCaseKey` at
`viewer/app.js:562`, row sort at `viewer/app.js:1002`.

## Rule 2 — history: why case id came first, and why date took over

**The 2026-08-31 bug.** 29 families held two or more virtual orphans on one
date. The old sort left them tied. The browser then broke ties by input
order — the platform's search-response order. That order changed between
page loads. The same graph rendered in a different order each time.

**The D12 fix.** Sort by case id. A case id holds the filing year and a
serial digit, so ascending case id equals filing order. It never changes
between loads. Decision D12, `openspec/changes/archive/2026-09-02-viewer-enhancements-and-orphan-case-anchoring/design.md`.

**The measured cost.** Case id first reads 51 of 682 projects out of date
order (95 pairs). Three shapes: same-day serials, orphans whose case id is
late but approval early, and families whose filing order differs from their
approval order.

**The 2026-11-05 decision (board D2, `docs/inspection-batchD.md`).** Two
measurements removed the reasons against a date sort:

1. The city echoes the family's 概要核准日期 into every descendant case
   (吉林717's whole triple carried the 概要's 2007/01/30). That echo made
   plan cases read a sibling's approval as their own event. The pipeline
   now dates a ghost only from its own track (D2a), and the sort key never
   reads 概要核准日期 on a plan track (D2b).
2. The 29 tied families were mostly the echo, not genuine same-day events.
   After the D2a re-emit, only 7 same-date groups remain (all genuine
   serials), and case id still breaks them.

Date first with the own-event key reads **0 projects** out of date order.
The user decided the swap on 2026-11-05; the change is
`openspec/changes/archive/2026-11-05-track-aware-ghost-dates-and-date-sort`.

**Your rule:** the own-event date decides the row; case id breaks ties. Do
not read 概要核准日期 from a plan-track case — the platform echoes it. If
you change the rule, count the non-chronological projects again and record
both numbers on the inspection board.

## Rule 3 — interleave execution events by date

Execution events are 建照, 開工, and 使照. They do not get rows from rule 2.
Insert each event before the first member whose date is later than the
event date. Put events with no later member at the end.

First normalise every event date to ISO. National portal dates arrive as
ROC dots (`110.10.25`); taipei milestones arrive as slashes
(`2023/04/27`). A slash sorts after every ISO date of the same year in
ASCII, so un-normalised events landed at the newest end. Both formats must
become `YYYY-MM-DD`.

Code: date normalisation at `viewer/app.js:384`, event interleave at
`viewer/app.js:1013`.

## Rule 4 — draw stage clusters as bands

Members group by stage: 擬訂, 變更, 變更(第二次), and so on. Each group
draws a band. The band is visual only. Rule 2 still decides the row
sequence.

Inside one band, the same three keys as rule 2: own-event date, then case
id, then the 區段 token.

The band's date is the real member's date. With no real member, take the
oldest member date. With no date at all, the band reads `(未核定)` and
sorts to the bottom.

Code: `compareClusterMembers` at `viewer/app.js:588`, cluster date at
`viewer/app.js:963`.

## Rule 5 — place orphan nodes

An orphan node's own date is often empty. Its band then lends the band
date to the event interleave. This stops an undated orphan from colliding
with events.

Draw a dotted edge from the orphan to the nearest real row above it. When
no real row sits above, draw it to the nearest row below — but only when
the orphan's schedule is not a dead end (已失效/自行撤回/已駁回): no edge
may point out of a closed case (board D4b).

Read the rendered rows, not dates — an undated orphan has no date of its
own, so a date test can never fire.

Shift an orphan 32px right when its row sits between two real rows of the
same swimlane. Measured on the whole corpus: this never fires for 概要
orphans. Keep the test anyway; the corpus can change.

Code: row neighbours at `viewer/app.js:1062`, shift test at `viewer/app.js:1075`.

## Checks before you merge

1. Run `python -m pytest`. All tests must pass.
2. Run `node scripts\viewer_smoke.js`. The render must finish with no
   error.
3. Open a project from each shape above in the viewer: 逸仙段三小段-34
   (orphan at its date position), 寶清段二小段-375 (undated orphan last),
   關渡段二小段-303 (same-case date tie-break), 吉林段一小段-717 (the echo
   shape: dead plan cases undated). The order must match this note.
