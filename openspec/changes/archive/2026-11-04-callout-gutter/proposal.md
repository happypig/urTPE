## Why

Implementation callouts (實施方式 / 基地面積 / 原戶數 / 使用分區) overlap the graph they annotate.
Seen on 大安區-通化段四小段-336地號等26筆 (3 records): the first callout covers its own node label,
"3 · 2022-08-02 擬訂 [施工中]".

The placer tries 8 fixed spots around each node, takes the first one clear of obstacles, and extends the
canvas downward when all 8 hit. Four gaps let overlaps through: (1) the callout's own node is not an
obstacle, so the placer never protects that node's label; (2) clamping into the viewBox pushes an
"above" candidate down onto the node, and gap (1) lets the spot pass; (3) label width is estimated with
Latin-width characters, so CJK labels are under-protected; (4) track lines, event edges and callout tails
cross boxes without any check. Fixing gaps 1–3 one by one removes candidate spots and sends more callouts
to the bottom-of-canvas fallback; gap 4 needs segment–rect tests with tuned weights. The reliable fix is
to move callouts out of the graph area entirely into a reserved gutter column.

Related cleanup in the same viewer change: §6 removes the green 事業種類 legend item and the drawn
`track` edges (revision and section edges stay; `track` edges remain in `projects.json` as data).

## What Changes

- Add a reserved callout gutter column left of the leftmost track column; every callout box lies inside it.
- Place callouts with one top-to-bottom sweep: each box starts at its node's row, moves down only when it
  would overlap the box above, never up. Replace the tail polygon with a leader from the box to the node
  circle.
- Size each callout box from its content (longest row value), clamped to the gutter width; long values
  wrap to at most 2 lines, then cut with an ellipsis; the full value shows as a tooltip.
- Add an overlap guard to `scripts/viewer_smoke.js`: no two placed rectangles intersect, every callout box
  lies inside the gutter, and no leader crosses a callout box or a node label. Run on every project that
  has a callout, not a 12-project sample.
- Remove the stage bands and their count chips from the graph (clash with the gutter); stage clustering
  still orders rows and tags undated members as before.
- Remove the 事業種類 legend item and the drawn `track` edges from the viewer; `track` edges remain in
  `projects.json` data.

## Capabilities

### Modified Capabilities
- `viewer-graph-layout`: Callout placement requirement changes — callouts move to a reserved gutter instead
  of dodging around nodes in the graph area; stage bands/count chips are removed from rendering. This
  changes requirements *Callout placement keeps clearance from nodes and labels* (viewer-graph-layout)
  and the *soft band + count chip* description (virtual-milestone-nodes).

### New Capabilities
None.

## Impact

- Viewer (`viewer/app.js`, `viewer/app.css`): callout placement block, stage-band block, legend item,
  `track`-edge loop, `.impl-callout*` and `.stage-band*` CSS.
- Test harness (`scripts/viewer_smoke.js`): new overlap-guard checks on every project with a callout.
- `openspec/specs/viewer-graph-layout/spec.md` and `openspec/specs/virtual-milestone-nodes/spec.md` delta
  specs describe the requirement changes.
- `projects.json` is unchanged; `track` edges remain in the payload. No pipeline run is needed.
