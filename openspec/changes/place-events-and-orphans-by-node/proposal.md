## Why

Viewer UX entries §3 and §4 (docs/viewer-UX.md) need layout changes to the history graph:

§3 — Execution events currently sit a full 64px node row under the preceding approval, because each approval row adds NODE_ROW=64px below itself. Per §3 decision 1, an event that follows an approval starts ½ node row (32px) under it; event-to-event pitch stays 32px; event→approval keeps full 64px clearance.

§4 — Named orphans currently sit on their track line without a dotted edge to the recno node they relate to. Nameless 孤 anchors sit in a separate right-most ghost column at list order, not date order. Per §4 decisions 1–4, every orphan takes its own timeline row by date, shifts 32px right when in a track column, and gets a dotted edge to the nearest recno node; the ghost column is removed.

Both changes affect row geometry and the column model in viewer-graph-layout, and both need the wave 2 overlap guard to prove they add no collision. Wave 2 is done (guard passes on all 676 callout projects).

## What Changes

- viewer/app.js `renderDetail`: row pitch uses NODE_ROW/2 between an approval and a following event; named orphans shift 32px right in track columns and get dotted edges to nearest recno node; nameless orphans join the timeline by date in the nearest recno node's column shifted 32px right with a dotted edge; the interim ghost column (ghostColX, ghostPosRaw, ghostRows) is removed.
- viewer/app.css: add `.edge.orphan` dotted style.
- scripts/viewer_smoke.js: extend overlap guard to include orphan (virtual + nameless) label rects and orphan dotted edges; run on every project with callouts or orphans.
- openspec/specs/viewer-graph-layout/spec.md + orphan-case-anchoring/spec.md: delta specs.

## Capabilities

Modified: viewer-graph-layout (row pitch, column model), orphan-case-anchoring (dotted edges, placement by date).

## Impact

Viewer only; no pipeline run, no data change. Projects with orphans: 593 named + 3 nameless at current data.
