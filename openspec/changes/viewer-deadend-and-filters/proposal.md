## Why

The Batch D board (D4b–d, `docs/inspection-batchD.md`, measured 2026-11-05)
found that the viewer draws edges **out of** dead-end nodes (36 chain edges, 160
dotted edges), keeps three family-level chips whose signal the gazette already
refutes (審查中 on 37 projects, 撤回 and 未核定 on 4 — all 4 have an approved
current node), and offers filter options that match nothing (其他, 都市更新計畫)
while the dead-end states cannot be filtered at all. The user decided each rule
on the board; this change implements them.

## What Changes

- **Chain edges** (`virtual-milestone-nodes`): no dashed chain edge starts at a
  virtual node whose schedule is 已失效 / 自行撤回 / 已駁回 (36 of 48 removed;
  the shipped scenario's own example 09902261 已失效 → 10201171 is one).
- **Dotted edges** (`orphan-case-anchoring`): the "row directly under" fallback
  no longer fires when the orphan's schedule is a dead end — those 160 orphans
  render with no edge. Edges up to the branch-off row stay.
- **List badges** (`history-graph`): the grey 審查中 / 撤回 chips and the
  未核定 (`neverApproved`) badge are removed, including the 相關連結
  "未曾核定… 無國土管理署入口網頁" note. A new dead-end badge shows the current
  recno node's own case state (已失效 / 自行撤回 / 已駁回) after the
  construction chip — 1 project today (龍泉534, 已失效).
- **Filters** (`viewer-filtering`): 事業種類 drops 其他 and 都市更新計畫 (0
  nodes each). 施工階段 is renamed 計畫與執行 and gains the dead-end states
  (same definition as the badge) plus the 計畫 options. Each project matches at
  most one 計畫與執行 state: construction first, then dead end, then the exact
  current-node track (事業計畫、權利變換 matches only its own option).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `virtual-milestone-nodes`: the chain-edge requirement gains the terminal-start
  exclusion; its "Attempt pair is chained" scenario changes.
- `orphan-case-anchoring`: the dotted-edge requirement's under-fallback gains
  the dead-end exclusion.
- `history-graph`: the status-chip requirement is rewritten (dead-end badge on
  the current node; no family-level 審查中/撤回 chips).
- `viewer-filtering`: the 事業種類 option list loses two entries; the
  construction-stage dimension becomes 計畫與執行 with the new options.
- `viewer-related-links`: the never-approved note is removed.
- `official-link-discovery`: the never-approved family classification's list
  consequence is removed.

## Impact

- Code: `viewer/app.js` (`virtualChainPairs`, the §4 dotted-edge fallback,
  `statusChip`, `neverApproved`, `constructionStage`/`matches`, the DIMS
  options, the 相關連結 note) — viewer only, no re-emit.
- Specs: six deltas as above (five edited requirements, one scenario).
- Tests: `tests/test_viewer_labels.py` (chips, badges, chain/edge rules,
  filter options); `node scripts\viewer_smoke.js` re-run.
- The dead-end badge and the 自行撤回/已駁回 filter options match 0 projects
  today; they exist for future cases (measured, board D4c/D4d).
