## Why

The version graph draws its timeline in the wrong order, in two compounding ways
measured live in Chrome on 通化段四小段-336 (and dataset-wide on 316 of 490
construction-bearing projects):

1. **Execution events (建照/開工/使照) land at the newest end of the timeline**
   instead of between the approval nodes they chronologically follow. Root cause:
   `buildConstructionChain` emits execution dates in slash form (`2023/04/27`)
   while approval nodes carry ISO dates (`2023-03-21`), and the timeline
   interleave at `viewer/app.js:838` compares them as strings — `"2023/04/27" <
   "2023-03-21"` is **false** in ASCII (`/` > `-`), so the events skip past every
   earlier-dated node and flush only before the newest one. The rendered
   top-to-bottom was 建照(2023/04) → 開工(2023/07) → node(2026) → node(2023-03) →
   node(2022-08): both 2023 execution dates drawn above the 2026 approval.
2. **The timeline is drawn newest-at-top.** The SVG y-order is node 1
   (2026-10-15) at top, node 453 (2022-08-02) at bottom — the reverse of the
   date-ascending order the record table and the reader's own output use. A user
   reading top-to-bottom reads history backwards.

The maintainers affected: every viewer user reading the version graph — the
construction chain's whole purpose is showing 建照→開工→使照 in sequence relative
to the approvals, and both defects defeat that.

(The stale provenance anchors measured in the same session — 案10011271·編號1 on
2023-dated execution events — are the 669-stale-bindings finding recorded in
`docs/inspection.md`; re-emission fixes those, not this change.)

## What Changes

- `buildConstructionChain` normalises execution-event dates to ISO at data-build
  time (the client-side ROC/slash rule from Wave 6's `fmtDate`), so the timeline
  sort is chronological. Display converts back from ISO.
- The SVG draws the timeline array in ascending order — oldest row at top,
  newest at bottom — matching the record table's convention.
- The smoke harness gains a fixture whose execution dates fall between two
  approvals, pinning the interleave.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `viewer-graph-layout`: the version graph's vertical order — approval nodes and
  execution events SHALL interleave chronologically (date-ascending,
  top-to-bottom), with execution events placed between the approvals they
  follow; the ROC/slash date forms SHALL be normalised before any ordering
  comparison.

## Impact

- `viewer/app.js` — `buildConstructionChain` (ISO dates), the timeline assembly
  (`sortedEvents` comparison and the splice loop), the y-pitch mapping direction.
- No payload change; no pipeline change; `viewer-graph-layout` spec delta only.
