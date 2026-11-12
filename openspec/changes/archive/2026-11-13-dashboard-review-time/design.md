# Design: dashboard-review-time

## Context

The rule is the user's, stated 2026-11-13 and settled point by point in the
same conversation. The measurements below are on the 2026-10-28 payload at
`5c81270` (680 projects, 1,444 records), before the ledger fix described in
D5.

| Population | Count |
| --- | --- |
| projects with at least one non-概要 node | 680 |
| of those, the first node carries both an application and a 核定 date on its case | 666 (all) |
| projects whose every node is a 事業概要 row | 14 |
| first nodes bound to more than one city case | 13, all area splits (A區/B區, 北區/南區, 東區/西區); dates identical, only 建照核發日期 differs |
| projects whose earliest node is a 變更 | 7 — five are split families (D5), one a swapped stage label (D5), one a gazette year typo (D4) |
| projects with a 建照核發日期 | 535 |
| permit earlier than every node | 1 (萬大段519-2, resolved by D5) |
| line 1 median, earliest-node variant (Python pre-measure) | 3.0 years (n 666); the page before this change showed 3.67 (n 679) |
| line 2 median, earliest-node variant (Python pre-measure) | 3.77 years (n 665) |

Measured through the harness on the changed page (task 3.2, payload at
`5c81270`, 680 projects, before the D5 ingest):

| Figure on the page | Value |
| --- | --- |
| 審議時間中位數 card (line 2) | 3.8 years |
| line 1 median, named in the card's sub-line | 3.0 years, n 666 over 25 years |
| line 2 median | 3.8 years, n 664 over 25 years |
| total to use permit, completed projects | 7.1 years (was 8.0: the application date no longer reaches back to the 概要 date) |
| outline-only projects named in the caption | 14 |

Each gazette node already carries its own case binding (`links.taipei`, the
case ids, and `links.milestones_taipei`, that case's milestones), and the
project carries `links.case_milestones` keyed by case id. So "from the first
approval recno" is a lookup, not a date match.

## Decisions

### D1 — Anchor on the node's case, read the project's case table

The derivation takes the first approval node's `links.taipei` ids and reads
each from the project's `links.case_milestones`; when a node names no case it
falls back to the node's own `links.milestones_taipei`. The project table is
the one the rest of the page reads (stage, idle time), so the two stay one
source. Across joined cases the earliest application and the earliest 核定
are taken; the 13 live cases agree on both, so the choice is only a tie rule.

### D2 — 擬訂 first, else the earliest eligible node

Measured: with the D5 data fix applied, the two rules agree on every project
but 德惠段813-1, whose 變更 row prints 2017-05-10 for an approval the city
records on 2018/05/10 (a gazette year typo the ledger cannot correct — it has
no date field). Preferring the 擬訂 node sidesteps that one row. The fallback
covers projects whose 擬訂 predates the data.

### D3 — Line 2 orders nodes by gazette date, ends on the case 核定 date

"The recno just before the permit" is read on the gazette dates, because
that is what a recno is: a gazette row. The interval's end is that row's case
核定 date (or the gazette date when the case has none), the same end rule
line 1 uses, so the two lines differ only in which node they end on.

### D4 — What is not fixed

- 德惠段813-1 recno 986: gazette year typo, not correctable by the ledger
  (CORRECTABLE_FIELDS has no date). D2 absorbs it. A ledger date field would
  be its own change.
- 1393's per-track stage fields (`stage_事業計畫`, `stage_權利變換`) are
  derived from the printed name at cleanse time and are not ledger-correctable,
  so the viewer's per-track chip on that one node keeps the printed 擬訂 while
  `stage` reads 變更. Recorded in the notes; the dashboard reads `stage`.

### D5 — The data fix is a separate `fix:` commit that precedes measurement

Seven ledger entries, verified offline against `data/clean.tsv` (each key
matches exactly one record; the five pairs resolve to (851,1345), (1287,1387),
(339,970), (854,1119), (404,993); the two stage corrections apply to 1423 and
1393): five `confirm_merge` for 犁和段102/165, 萬隆段461/468, 萬隆段623/519,
華江段274/215-2, 萬大段519-2/萬華段519-2; `stage`+`stage_index` on 景美段501's
recnos 1423 (→擬訂, 0) and 1393 (→變更, 1). A ledger entry applies only on a PDF
ingest, so the fix needs one run on 核定案件-2026-10-28.pdf, which rewrites
the tracked data files and the payload (680 → 675 projects). The dashboard
tests use fixtures, so this change's tests do not depend on that run; its
measured figures (task 3.2) do.

### D6 — The harness grows one field

`scripts/dashboard_smoke.js` prints the review chart's caption (`reviewCap`)
so the 概要 notice can be asserted. Nothing else in the harness changes: the
series extraction already fires every hover handler, so a second series
appears as more points, distinguishable by the tooltip's second line.

### D7 — The dotted-ROC scenario keeps its text, the test moves its probe

The dates requirement's "A dotted ROC date" scenario is unchanged. Its test
asserted through the review card using a national application date, which is
no longer a review source; it now asserts through idle years using a national
核定 date, the same read path.

## Risks

- The 審議 card's figure moves from 3.67 to the line 2 median. Readers who
  bookmarked the old figure see a different number; the sub-line names both.
- The review chart gains a legend; on narrow screens the two lines may cross.
  Point-to-point drawing is kept; colours follow the approvals chart's pair.
