## Why

The 國 badge binding scores each node on its own (`nationalBoundTo`,
viewer/app.js:130): it asks "does any national label match this node?" per node,
never "which node does this label choose?" per label. A label whose stage+track
matches 2–3 nodes therefore badges all of them. Measured with the shipped
helpers over the payload (Batch C, C1): 19 multi-candidate labels, 41 badged
nodes, 16 nodes wear a 國 that neither the spec nor `view_verified_case_ids`
gives (文林64 recnos 1086+693; 潭美579-2 recnos 673, 627, 618).

## What Changes

- Binding becomes per label at project level: each label chooses at most one
  node — exact date first, then ±1 day (the 公告-vs-committee offset the 北
  matcher already allows), then nothing. A label with 0 or 2+ qualifying nodes
  after the tie-breaks binds nothing.
- `getNodeMilestoneBadges` reads the per-project binding map instead of scoring
  the node itself. `view_verified_case_ids` stays as the second source.
- Viewer only; no payload change, no re-emit.

## Capabilities

### Modified Capabilities
- `history-graph`: a label SHALL bind at most one node (exact date, then ±1
  day); multi-match labels bind nothing.

## Impact

- `viewer/app.js`: new `bindNationalLabels(project)` (label → node recno),
  `nationalBoundTo` replaced.
- `scripts/viewer_smoke.js`: per-label binding assertions.
