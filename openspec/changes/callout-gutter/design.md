## Context

`docs/viewer-UX.md` §1 describes the problem: implementation callouts overlap graph content on the viewer.
The viewer pipeline flow is: `projects.json` -> `renderDetail` -> SVG with tracks (columns 1–3),
events (column 4), node labels, stage bands/chips, and callout boxes placed by an 8-spot dodging search
in `viewer/app.js`.

## Goals / Non-Goals

**Goals:**
- Callout boxes never overlap node labels, badge strips, event rows, other callouts, ghost anchors, or
  stage-band chips by construction.
- Callout leaders connect each box to its own node circle.
- Long callout values wrap to at most 2 lines, then cut with an ellipsis; full value in a tooltip.
- An overlap guard in `scripts/viewer_smoke.js` runs on every project that has a callout.

**Non-Goals:**
- No pipeline change; `projects.json` and `projects.data.js` are unchanged.
- `track` edges remain in `projects.json`; only their viewer drawing is removed (§6 bundled in this
  change).
- Stage clustering still orders rows and tags undated members; only the drawn band/chip is removed.

## Decisions

### A. Dedicated callout gutter

Reserve a column left of the leftmost track column; draw only callouts in it. Shift all tracks, event
columns, and ghost anchors right by the gutter width. One top-to-bottom sweep places boxes: each box
starts at its node's row, moves down only when it would overlap the box above, never up. Replace the tail
polygon with a leader from the box to the node circle.

Alternatives considered:
- 8-spot dodge + canvas extension (current): rejected — cannot protect the callout's own node, clamps
  onto the node, under-estimates CJK label width, never tests lines.
- Score every candidate spot (overlap area + line crossings + distance): rejected — more logic and tuned
  weights, still no guarantee on dense projects.

### B. Size box from content

`w` from the longest row, clamped `[CALLOUT_MIN_W, CALLOUT_GUTTER - margin]`. Gutter width = widest box
in the project, up to the clamp. Values wrap to at most 2 lines, then ellipsis; full value as tooltip.
`white-space: nowrap` is avoided — wrapping preserves text; ellipsis hides only overflow beyond 2 lines.

### C. Overlap guard in smoke test

Shared `layoutRects(p)` returns every placed rect (callout boxes, node label boxes, event rows, ghost
anchors, leader segments). `renderDetail` and `scripts/viewer_smoke.js` use the same helper. Smoke checks
1–3 run on every project that has a callout: no two rects intersect, every callout box inside the gutter,
no leader crosses a box or a node label.

## Risks / Trade-offs

- Each project with a callout gets up to ~160px wider; narrow screens zoom out more. Mitigation: gutter
  width is per-project, minimum when values are short.
- Wrapped boxes push boxes below them down; leaders get long and slanted when many callouts stack.
  Mitigation: 2px stack gap keeps 4-row boxes at the row pitch; only wrapped boxes drift.
- Removing stage bands loses the "N 案" count at a glance. Accepted per proposal.
