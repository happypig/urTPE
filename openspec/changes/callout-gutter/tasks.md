## 1. Test writing (overlap guard) — must be fully checked before any implementation task

- [x] 1.1 Add `layoutRects(p)` helper to `scripts/viewer_smoke.js`: returns callout boxes, node label
  boxes (circle + title + sub line + badge strip), event rows, ghost anchors, and leader segments.
- [x] 1.2 Add smoke check 1: no two placed rectangles intersect, naming project and rects on failure.
- [x] 1.3 Add smoke check 2: every callout box lies fully inside the gutter.
- [x] 1.4 Add smoke check 3: no leader segment crosses a callout box other than its own, or any node
  label box.
- [x] 1.5 Run checks 1–3 on every project with a callout, naming
  大安區-通化段四小段-336地號等26筆 and
  內湖區-潭美段四小段-579-2地號等21筆 (7 carrying records).
- [x] 1.6 Confirm checks fail on 大安區-通化段四小段-336地號等26筆 with the current (pre-fix)
  layout.

## 2. Viewer implementation — callout gutter

- [x] 2.1 Add reserved callout gutter column left of the leftmost track column; shift tracks/event
  columns/ghost anchors right by gutter width; reserve gutter only when a project has a callout.
- [x] 2.2 Add content-sized callout box: width from longest row, clamped to gutter; height from line
  count (max 2 lines), ellipsis + tooltip for overflow values.
- [x] 2.3 Add top-to-bottom placement sweep: each box starts at its node's row, moves down only when
  overlapping the box above (2px gap), never up; leader from box to node circle.
- [x] 2.4 Remove 8-spot dodging search, `hitsAny` obstacle tests, and canvas-extension fallback.
- [x] 2.5 Remove stage bands and count chips from rendering; keep clustering order and (未核定) tagging.

## 3. Viewer implementation — §6 track cleanup

- [x] 3.1 Skip `kind === "track"` edges in the viewer edge loop; remove the 事業種類 legend item and
  `.legend .trk` CSS. `track` edges remain in `projects.json` data.

## 4. Verification

- [x] 4.1 `node scripts/viewer_smoke.js` passes checks 1–3 on every project with a callout.
- [x] 4.2 `python -m pytest` passes (viewer-only change).
- [x] 4.3 Manually confirmed 大安區-通化段四小段-336地號等26筆 shows callouts in the gutter,
  none covering a node label/badge/edge/event; no stage band or count chip.
