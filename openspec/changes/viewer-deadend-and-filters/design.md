## Context

Board D4b–d (`docs/inspection-batchD.md`), all rules decided by the user on
2026-11-05. Viewer-only change: no payload re-emit, no pipeline change.

## Goals / Non-Goals

**Goals:**
- No drawn edge starts at a dead-end node (chain or dotted).
- The list shows only what the current approval's own case states.
- The 計畫與執行 filter gives every project exactly one state.

**Non-Goals:**
- No removal of the 78 dotted edges that run up INTO a dead end (branch-off
  semantics stay).
- No change to the D12 case_id row order (D2b is a separate change).
- No 相關連結 per-case schedule badges change (kept as they are).

## Decisions

### D1 — dead-end definition: one helper, two consumers

`TERMINAL_SCHEDULES` semantics live in the pipeline; the viewer hard-codes the
three states. Add one viewer helper `const isDeadEnd = s => s === "已失效" ||
s === "自行撤回" || s === "已駁回";` used by the chain rule, the dotted-edge
rule, the badge and the filter. `familyScheds`/`NO_STATE_FAMILY` and
`neverApproved` are deleted with their chips.

### D2 — chain rule reads the upstream member's schedule

`virtualChainPairs` gains: `if (isDeadEnd(a.schedule ?? scheduleOf(a))) return;`
where the schedule of a virtual member is its own `schedule` field (orphan
payload) or `links.case_schedules[case_id]`. The board measured the shipped
scenario example (09902261 已失效 → 10201171) among the 36.

### D3 — dotted-edge rule: only the under-fallback is gated

In the §4 block, the fallback `nearestRecnoRowUnder` fires only when the
orphan's schedule is not a dead end. The primary branch (row above) is
untouched — that edge runs INTO the dead end (branch-off semantics, 78 edges
stay). Undated orphans have a schedule in the payload (`g.schedule`), so the
test is schedule-based, not date-based, and works for undated nodes.

### D4 — badge: current node's own case, after the construction chip

`statusChip` is replaced by a `deadEndChip(p)` reading
`case_schedules[first case of the is_current node]`. Render order:
`stageChip(p)` then `deadEndChip(p)`; `neverChip` is deleted. The board's
measured result: 龍泉534 已失效 (1 project), the 37 審查中 families lose their
chip, the 4 撤回/未核定 families lose theirs.

### D5 — 計畫與執行: one state per project, evaluated in order

`matches()` for the renamed dimension: if `constructionStage(p)` and its short
is selected → match; else if the dead-end chip state is selected → match; else
if the current node's exact track is selected → match; else no match. DIMS
options for 事業種類 drop 其他/都市更新計畫. The combined track matches only
itself (exact string compare, no `trackMatches`).

## Risks / Trade-offs

- [Dead-end orphans float with no edge] → Accepted by the user (board D4b):
  the schedule badge on the node's own row carries the state.
- [The 37 in-review families lose their only list signal] → Accepted: 審查中
  is a transient city state; the graph and 相關連結 still show it per case.
- [Combined-track exact match changes 186 projects' filter behaviour] →
  Intended (user decision); before, a combined-track current node could match
  事業計畫 via the any-member semantics — the 事業種類 dimension is unchanged
  (any member), only 計畫與執行 is exact.

## Migration Plan

Single viewer commit; tests first; smoke harness re-run. No data change.

## Open Questions

None.
