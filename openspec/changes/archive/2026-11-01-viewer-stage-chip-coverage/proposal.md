## Why

Three viewer findings, one test group, one file — bundled because they share the
render path and the spec they touch:

- **V3 (needs a spec delta).** 195 of 694 cards show no stage chip, which reads
  as "not started" while the data says 審查中 (59) or 自行撤回 (130). The spec
  currently says "Projects with none of the three construction dates SHALL show
  no badge" — written when silence meant "no data"; the payload's
  `case_schedules` now distinguishes genuinely-not-started from in-review or
  withdrawn. The badge logic itself (未核定) is verified correct and untouched.
- **V2.** The 20-column record table prints `地號清單` as raw JSON
  (`["336","336-1",…]`), `地號別名` as `{}`, and `原地號數` as `null`. The table
  is the "say what was read" surface; raw encodings undercut it.
- **V4.** Three date formats appear in one detail pane (node dates ISO,
  Taipei milestones `2011/11/27`, national milestones ROC `100.12.20`). The
  pane's whole job is comparing across sources; mixed formats defeat it.

The maintainers affected: every viewer user reading the list (V3) and the detail
pane (V2, V4).

## What Changes

- V3: a grey `審查中`/`撤回` chip for projects with no construction stage but a
  known `case_schedules` state; the spec scenario updated to name the chip.
  Silent cards (no schedule at all) keep showing nothing — documented.
- V2: `地號清單` renders as `、`-joined prose; empty dict/list cells render as an
  em dash; `null` renders as an em dash.
- V4: all dates render ISO at display time (source strings stay verbatim in the
  data); the ROC `100.12.20` and Taipei `2011/11/27` forms convert on render.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `history-graph`: the construction-stage badge requirement gains the
  in-review/withdrawn chip (the spec delta rewrites the "no badge" clause).
- `viewer-filtering`: the record table renders human-readable cell text (parcel
  lists as prose, empty/absent as an em dash), and dates render ISO.

## Impact

- `viewer/app.js` — the chip derivation, the table cell formatters, the date
  formatter.
- `openspec/specs/history-graph/spec.md` + `openspec/specs/viewer-filtering/spec.md`
  — the deltas.
- No data change: all three are render-time rules; the payload stays verbatim.
