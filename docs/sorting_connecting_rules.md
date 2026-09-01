# Graph Sorting & Connecting Rules — Nodes, Virtual Nodes, Execution Dates

*Reference for the history-graph SVG built by `viewer/app.js` `renderDetail` (per-project) from `viewer/projects.data.js`. Source of truth: the spec deltas in `openspec/changes/viewer-enhancements-and-orphan-case-anchoring/specs/` (synced to `openspec/specs/` on archive) + the main specs `history-graph` / `viewer-milestone-timeline`. Code pointers given as `app.js:<line>` (2026-08-30 layout, post §8 chimera fix).*

---

## 1. Node taxonomy

| Class | Identity | Column | Render |
|---|---|---|---|
| **PDF node** | `recno` (gazette 編號), family = project_id | col 1–3 by track | solid circle; 北/國 badges; schedule badge `[已駁回]`-style from its anchored case |
| **Virtual node** (named orphan) | `case_id` only (`recno: "v"+case_id`) | its track column at `node_date` | dashed circle; stage label (+`(未核定)` if undated); schedule badge; tooltip 案`<case_id>` |
| **Interim orphan** (nameless) | `case_id` only | rightmost ghost column | dashed circle, no name |
| **Execution event** | `label` (建照核發日期/開工日期/使照核發日期) | col 4 (shared execution column) | black dot; hyperlink to source portal; renders **exactly once** |

Gate rules for becoming a virtual node (`orphan-case-anchoring` spec): orphan = in `links.taipei` minus node-anchored; named (candidate_names) AND (landcore similarity ≥ 0.7 **or** in `view_verified_case_ids` **or** attributed **or** twin-bridge ≥3 shared dates).

## 2. Sorting rules

### 2.1 Columns (four-column grid)
- `trackPosition(track)` (app.js:61): 事業概要/事業計畫/都市更新計畫 → col 1; 事業計畫、權利變換 / 都市計畫、權利變換 → col 2; 權利變換/其他 → col 3; execution dates → col 4.
- 區段 splits create their own sub-column: column key = `track（X區段）` (app.js:646-653).
- Column order: by `trackPosition`, then key name (app.js:667-673).

### 2.2 Timeline rows (stage-key clusters, §5.2.6 — D12 Amendment 3: family-wide case_id interleave)
> **2026-08-31 update (Amendment 3, 603 exploration)**: the case_id ordering is
> family-wide — undated virtual attempts interleave between their case_id
> neighbors (09511212/13 between 09511211 and 09511214), 已駁回 11007262 before
> 已核准 11501016, matching the 相關連結 order; same-date virtuals (A區/B區
> splits) attach immediately after their same-day anchored milestone (date-band
> adjacency before pure case_id). Spec: virtual-milestone-nodes (603 scenarios).

1. Nodes and virtual nodes group by **stage** (擬訂/變更/變更(第N次)…) into clusters (app.js:687-688).
2. Within a cluster, members sort (app.js:691-694): real before virtual → dated before undated → by 區段 token (zh-Hant locale).
3. Cluster date = the real member's date, else the earliest dated member, else `(未核定)` (app.js:696-699).
4. Clusters sort chronologically by effective date (app.js:702).
5. Execution events interleave by date: each event lands **before** the first cluster member whose effective date is later (app.js:706-717); remaining events append at the end.
6. Row pitch (§5.3.1): approval rows `NODE_ROW` (64px), execution rows `EVENT_ROW` (32px) (app.js:719-725).
7. Virtual placement: chronologically by `node_date` (fallback chain 核定日期 → 權變核定日期 → 概要核准日期, links.py `_ghost_node_date`); undated virtuals join their stage cluster tagged `(未核定)`.

## 3. Connecting rules (edges)

### 3.1 PDF node ↔ PDF node (`p.edges`, built by `urtpe/graph.py`)
- **revision** (blue solid, 版本/核定時序): chains each record toward the family anchor; direction points toward the anchor (history-graph spec "Revision edges point toward the anchor").
- **track** (teal dashed, 事業種類): groups records sharing the 事業種類 cluster.
- **section** (orange dotted, 區段): section branches within the family.

### 3.2 Execution events (col 4) — source-colored edges
Render each event once. Edges per `buildConstructionChain` + app.js:886-915:
1. **Group start** (source changes, or first event): a **slanted solid source edge** from the owner to the group's earliest event —
   - anchored record → from that record's node position (pink `taipei`),
   - national-mapped (使用核發) → from the 現況 node (green `national`),
   - orphan-sourced → from the virtual/ghost anchor position (pink).
2. **Within a source group**: vertical **solid** `event-link` chain (same-source semantics).
3. **Source transition**: vertical **dashed** `event-link` in the incoming group's color.
Source identity = `national` or `case:<case_id>`; provenance chain: implementation exact-match → `milestones_source` map → national-only (app.js:289-297).

### 3.3 Virtual nodes
- **No revision/track/section edges** (no recno — they never join `p.edges`).
- Their construction events connect via the **slanted solid pink source edge** from the virtual node's own grid position (app.js:756-758, 902-905).
- **Virtual chain edges (decided 2026-08-31, design.md D12 amendment)**: consecutive virtual nodes within a stage cluster (case_id-ascending row order) are chained by a dashed **virtual revision edge** (attempt succession, earlier attempt → later). Cross-stage same-date pairs sit in different clusters and stay unchained. *(Implementation pending — spec surface: `virtual-milestone-nodes` chain-edge requirement.)*
- Cross-family caveat: a sibling family's real node and this family's virtual node may render the same case (double-display, §6.8) — resolved only by family merge.

### 3.4 Interim orphans
- Source edges originate from the rightmost ghost column positions (app.js:737-745, 902-905); nameless ghosts render bare when they carry no construction dates.

## 4. Per-node content attribution (what each node "carries")

| Node | `links.taipei` | `links.milestones_taipei` |
|---|---|---|
| PDF node | its date-anchored case_id (§6.13 ROC/ISO matcher) | **its anchored case's own timeline** (`case_milestones[case_id]`, §8 chimera fix); fallback = project-level merged dict when the case has no per-case data |
| Virtual node | its own case_id | (payload on `orphan_nodes`: milestones_taipei/national, node_date, schedule badge) |

Project-level `links.milestones_taipei` (last-write-wins merged dict) is **unchanged** — it feeds the 階段辦理過程 card and construction-chain provenance (`milestones_source`).

## 5. Where each rule is spec'd

| Rule | Artifact |
|---|---|
| Four-column grid / row pitch / callout clearance / viewport | change delta `viewer-graph-layout/spec.md` |
| Virtual placement / stage clusters / 區段 / nameless interim column | change delta `virtual-milestone-nodes/spec.md` |
| Execution events render once / source-colored edge semantics / compact pitch | change delta `viewer-milestone-timeline/spec.md` |
| Ghost gate (similarity / portal-verified bypass / twin-bridge) | change delta `orphan-case-anchoring/spec.md` |
| Revision/track/section edges toward anchor; construction chain | main spec `openspec/specs/history-graph/spec.md` |
| Per-node milestone attribution (chimera fix, merged fallback) | main spec `viewer-milestone-timeline` (MODIFIED via change delta, 2026-08-30) |

## 6. Known gaps / notes

- **Virtual–virtual same-date order**: ~~underspecified~~ → **decided 2026-08-31 (design.md D12)**: row-by-row by case_id ascending (real via anchored case_id, virtual via own; case-less real first) + dashed virtual chain edges between consecutive virtuals in a cluster. Spec delta + tasks pending at implementation.
- **Virtual vs real on the same date**: cluster rule puts the real member first — correct by design (real record outranks a sibling-family case reference).
- **Delta sync**: the change deltas above live under `openspec/changes/viewer-enhancements-and-orphan-case-anchoring/specs/` until archive; `openspec/specs/` holds the pre-change baselines (history-graph, viewer-milestone-timeline base requirements).
- Cross-family double-display (same case as real node in one family, virtual in another) is inherent until fragment-family merges land (§6.8/§12).
