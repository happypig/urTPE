# Viewer UX improvements

A backlog of planned improvements to the static viewer (`viewer/app.js`, `viewer/app.css`).
Each entry records the problem, the evidence, the chosen design, its trade-offs, and the
spec and test impact. An entry is a candidate, not a change: start an openspec change
(`openspec/changes/<name>/`) before you implement it, and link the change here.

Append new entries at the bottom. Do not renumber entries; other documents may cite them
as `viewer-UX §N`.

| § | Title | Status | openspec change |
| --- | --- | --- | --- |
| 1 | Callout gutter: no-overlap implementation callouts | proposed | — |

---

## §1 Callout gutter: no-overlap implementation callouts

**Status:** proposed (2026-11-03). **Scope:** `viewer/app.js` callout placement
(`renderDetail`, the block after `// Callout placement`), `.impl-callout*` in
`viewer/app.css`, `scripts/viewer_smoke.js`.

### Problem

Implementation callouts (實施方式 / 基地面積 / 原戶數 / 使用分區) overlap the graph.
Seen on 大安區-通化段四小段-336地號等26筆 (3 records): the first callout covers the
label of its own node, "3 · 2022-08-02 擬訂 [施工中]".

The current placer tries 8 fixed spots around the node, takes the first one that does
not hit an obstacle, and extends the canvas downward when all 8 hit. Four gaps let
overlaps through:

1. The callout's own node is not an obstacle. `nodeRects` filters on
   `n.recno !== ownRecno`, so the placer never protects that node's label.
2. The clamp into the viewBox moves a candidate onto that node. For a node in the first
   row, the "above-left" spot has a negative `y`. The clamp moves it to `y = 4`, on top of
   the node, and gap 1 lets the spot pass.
3. The label width is estimated too small. `headLen * 6.5` sizes every character as
   Latin. CJK glyphs at 11px are about 11px wide, and `headLen` does not include
   `schedTxt` ("[施工中]") or the area suffix.
4. Lines are not obstacles. The track lines, the event edges, and the callout tails can
   cross a box, and nothing checks them.

Gaps 1–3 can be fixed one by one, but each fix removes candidate spots and sends more
callouts to the fallback at the bottom of the canvas. Gap 4 needs segment–rect tests and
tuned weights. This entry removes the cause instead: callouts move out of the graph area.

### Design

#### A. Dedicated callout gutter (was option 4)

- Reserve a fixed-width column (`CALLOUT_GUTTER`, about 160px) to the left of the
  leftmost track column. Draw only callouts in it. Shift all tracks, event columns and
  ghost anchors right by the gutter width. Reserve the gutter only when the project has
  at least one callout.
- Give each callout a target `y` equal to its node's `y` minus half the box height.
- Do one top-to-bottom sweep over the callouts in timeline order. If a box would overlap
  the box above it, move it down to `previous.y + previous.h + GAP`. Never move a box up.
  `GAP` is 2px: a 4-row box is 62px and the approval-row pitch is 64px, so unwrapped
  boxes on adjacent rows never drift. A 4px gap would need 66px and drift 2px per row.
- Extend `svgH` to the bottom of the last box.
- Replace the tail polygon with a leader from the right edge of the box to the node
  circle. Keep the `.callout-tail` color so the leader reads as part of the box.
- Remove the 8-spot search, the `hitsAny` tests against node, event and ghost rects, and
  the canvas-extension fallback. The gutter makes them unnecessary.
- Remove the stage-cluster band and its count chip (`bandHtml`, `.stage-band*`; from
  archived task 5.2.6 of `2026-09-02-viewer-enhancements-and-orphan-case-anchoring`).
  The chip is drawn at `x = PAD - 36`, inside the gutter. Keep the stage-key clustering
  itself: it still decides row order (base → splits → undated). Only the visual goes.

#### B. Size the box from its content (was option 5)

- Compute `w` from the longest row: label width + gap + value width + padding. Use the
  same per-character width helper as in C (CJK ≈ 10px at 10px font, ASCII ≈ 6px).
- Clamp `w` to `[CALLOUT_MIN_W, CALLOUT_GUTTER - margin]`. Set the gutter width from the
  widest box in the project, up to the clamp.
- Let a value wrap to at most 2 lines, then cut it with an ellipsis
  (`-webkit-line-clamp: 2`), and put the full value in a `title` attribute. Compute the
  box height from the wrapped line count, so a value never spills out of its box. The
  longest value in the 2026-11-03 dataset is 26 characters
  (敦化南北路特定專用區(A區)(原屬第四之一種住宅區), about 260px at 10px); 99% of
  implementation values have 14 characters or fewer.

#### C. Pairwise-intersection guard in the smoke test (was option 6)

- Move the rect geometry into one helper, `layoutRects(p)`, that returns every placed
  rect: callout boxes, node label boxes (circle + title + sub line + badge strip), event
  rows, and ghost anchors. `renderDetail` and `scripts/viewer_smoke.js` use the same
  helper, so the test checks the geometry the renderer uses.
- Add a smoke check: for every project in the dataset, assert that no two rects
  intersect. Name the project and the two rects on failure.
- Add a second check: every callout box lies fully inside the gutter.
- Add a third check: no leader crosses a box or a label. A leader may cross a track line
  or an edge — a leader from a node in column 2 or later must cross the column-1 track.
- Run these checks on every project in `viewer/projects.data.js` (676 projects carry
  implementation data on 2026-11-03), not on the existing 12-project sample. Look at
  大安區-通化段四小段-336地號等26筆 and 內湖區-潭美段四小段-579-2地號等21筆 (7 records with
  implementation data, the most in the dataset) by name.

### Pros and cons

| | Pros | Cons |
| --- | --- | --- |
| A. Gutter | Overlap cannot happen by construction: nothing else is drawn in the gutter. Predictable: all boxes on one side, in time order. Simpler code (one sweep replaces the search and the fallback). Easy to test. | Each project with a callout gets about 160px wider, so narrow screens zoom out more. When many callouts stack, the sweep pushes boxes away from their node and the leaders get long and slanted. Visible layout change, so it needs a spec delta. |
| B. Content width | Values cannot spill out of a box. Short boxes keep the gutter narrow. | Widths are estimates; the real width depends on the font. A value longer than 2 lines is cut with an ellipsis, so its end is visible only in the tooltip. Wrapped boxes are taller and can push later boxes down. |
| C. Smoke guard | Turns "no overlap" into a rule a script can check. Catches regressions from later viewer entries too. | Checks estimated rects, not real rendering. `node scripts\viewer_smoke.js` runs by hand only (no CI), so it protects nothing unless someone runs it after a viewer change. |

### Alternatives not chosen

- **Make the own node an obstacle, and measure label width per character.** Small, and it
  fixes the screenshot. Rejected as the main fix because every extra obstacle removes
  candidate spots and sends more callouts to the bottom-of-canvas fallback, far from
  their node.
- **Score every candidate spot (overlap area + line crossings + distance).** Better
  results than first-fit, but more logic, tuned weights, and still no guarantee on dense
  projects.

### Decisions (2026-11-03)

1. Long values wrap to at most 2 lines, then cut with an ellipsis and a full-value tooltip.
2. The stage-cluster band and its count chip are removed. Clustering stays for row order.
3. The overlap guard checks boxes, labels, badges and events against each other. Leaders
   may cross lines, but not a box or a label.
4. The gap between stacked boxes is 2px.
5. The new smoke checks are the test-writing group for the test-first gate. Write them
   first and confirm they fail on the current layout (the 336 project must fail). No
   pytest wrapper, no `> POC:`.
6. The deploy check (acceptance 4) runs only after the user pushes the change.

The change touches only `viewer/` and `scripts/viewer_smoke.js`. It needs no pipeline
run, so `data/` and `viewer/projects.data.js` stay unchanged.

### Spec impact

`openspec/specs/viewer-graph-layout/spec.md`, requirement *Callout placement keeps
clearance from nodes and labels*, describes best-effort placement around the node with a
canvas-extension fallback (from archived task 5.3.6 in
`2026-09-02-viewer-enhancements-and-orphan-case-anchoring`). The change must replace
that requirement with a gutter requirement. Proposed scenarios:

- **WHEN** a project has at least one implementation callout **THEN** the graph reserves
  a callout gutter left of the leftmost track, and every callout box lies inside it.
- **WHEN** two callouts would overlap in the gutter **THEN** the later one moves down,
  never up, and its leader still connects to its own node.
- **WHEN** a callout value is wider than the box clamp **THEN** the value wraps to at most
  2 lines, is cut with an ellipsis after that, and the full value is available as a tooltip.
- **WHEN** a stage cluster has 2 or more members **THEN** the graph draws no band and no
  count chip; the cluster still decides row order.
- **WHEN** the smoke harness lays out every project **THEN** no two layout rects
  intersect.

### Acceptance

1. 大安區-通化段四小段-336地號等26筆 shows three callouts in the gutter, and none
   covers a node, a label, a badge, an edge, or an event.
2. `node scripts\viewer_smoke.js` passes the new intersection and in-gutter checks
   across the full dataset.
3. `python -m pytest` still passes (the change touches only the viewer).
4. After the user pushes the change, the published page at
   `https://happypig.github.io/urTPE` shows the new layout, confirmed with
   `python scripts\check_deploy.py`.
