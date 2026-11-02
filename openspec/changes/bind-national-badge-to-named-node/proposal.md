## Why

The 國 badge (national-portal view page) binds to the wrong nodes today.
`getNodeMilestoneBadges` gives 國 to the 現況 node (`node.is_current`) **and**
to each node whose anchored case is in `links.view_verified_case_ids`. Measured at
`30612dd`: 632 of 693 projects have a `twur` link, and 492 of those 632 have an empty
`view_verified_case_ids`. Example: 大安區-通化段四小段-336地號等26筆
(`view/900`, `view_verified_case_ids: []`) shows 國 on node 1 only because of the 現況
rule, even though its national page names recno 3 (擬訂 事業計畫) and recno 370
(變更 事業計畫).

Every national approval label names its own stage and track:
事業計畫核定日期 632, 權利變換計畫核定日期 377, 第一次變更事業計畫核定日期
280, … So a label can be matched to the recno node carrying the same stage and track,
which is the node the national view page really asserts.

## What Changes

- `getNodeMilestoneBadges`: a node gets 國 when a national approval label binds to it
  (same stage + track, date tie-break when multiple nodes match), **or** when the
  `view_verified_case_ids` rule applies. The `node.is_current` branch is removed.
- A new pure helper `nationalLabelKey(label)` → `{stage, track}` or `null`.
- National execution events (使用核發日期) keep their place in the event chain; a
  source edge starts from the latest bound node, or no edge when no node is bound.
- The first-national-event source edge no longer always starts at the 現況 node.

## Capabilities

### Modified Capabilities
- `history-graph`: the 現況 node's 國 badge rule is replaced with label-to-node
  binding by stage+track; `view_verified_case_ids` stays as a second source.

### New Capabilities
None.

## Impact

- Viewer (`viewer/app.js`): `getNodeMilestoneBadges`, the national event source-edge
  branch, the new `nationalLabelKey` helper.
- `openspec/specs/history-graph/spec.md` delta: replace the 現況 國 badge rules with
  the binding rule.
- `projects.json` unchanged. No pipeline run needed.
