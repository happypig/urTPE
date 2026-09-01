## Why

Planners reviewing urban-renewal case histories in the viewer encounter three usability gaps:

1. **Construction chain clarity**: The 建照/開工/使照 milestones (construction chain) are rendered as individual nodes but their logical grouping as a "construction phase sequence" is not visually distinct — all edges look the same.
2. **Incomplete 相關連結**: Orphan case_ids (e.g., 09907221) that were dropped by the §6.7/§6.8 parcel guard appear in project-level `links.taipei` but lack anchor records, so their case names don't appear in 相關連結 — users see raw IDs without context.
3. **Orphan cases absent from graph**: Case 09907221 supplies 14 milestone dates (`milestones_source` maps all to it) yet has no node in the graph because the merge/guard dropped it. When the orphan's landcore IS similar to the project anchor, it should be anchored as a ghost node; when not similar, it should stay out.

These are user-visible gaps that affect planning decisions. The fix spans both the viewer (1–2) and the pipeline merge/guard (3).

Note: 基本面積 display in left-list cards is now covered by the separate `viewer-base-area-color-style` change (archived).

## What Changes

- **Viewer**: Render dotted edges between consecutive construction-chain events (建照→開工→使照) regardless of source portal.
- **Viewer**: Fallback case names in 相關連結 by checking `project.links.case_milestones` keys and `project.links.search_rejected` when node-level links don't have the case_id.
- **Pipeline + Viewer**: During merge/guard, for each orphan case_id in `city_case_ids` that has NO anchor record, compute landcore similarity to the project anchor. If similarity ≥ 0.7 (matching the merge threshold), create a ghost node in the graph with the orphan's milestones; if < 0.7, skip (current behavior). The ghost node carries the case_id, its milestones, and a "orphan" flag for viewer rendering.

- **Pipeline (added 2026-08-27)**: Harvest candidate `case_name`s at discovery time — the platform search API already returns them per candidate; persist them into discovery results instead of discarding. Orphan landcore similarity then computes from real names (no PDF-cycle dependency).
- **Pipeline + Viewer (added)**: Landcore-similar orphans become **virtual milestone nodes** — dashed circle/edges, placed chronologically in their 事業種類 column at their 核定日期, labeled stage + track without recno, carrying the same 北 link and the family's project identity — replacing the ghost-anchor column as names arrive (nameless orphans keep the interim anchor column until then).
- **Viewer (added)**: Graph layout upgrades — content-addressed row pitch (normal height between consecutive nodes, half height for execution-date rows), the four-column grid codified (事業概要/事業計畫/都市計畫 | combined×權利變換 | 權利變換 | execution dates), horizontally centered graph viewport with pinch-zoom and drag, and RWD that caps the project list to leave more room for the detail below.

Note: 基本面積 display is implemented in `viewer-base-area-color-style`.

**Scope addition (2026-08-29, exploration §6.14/6.15 of the operations log — the 概要-track blind spot)**: the anchoring/ghost machinery was built for the 事業計畫/權利變換 tracks and silently fails on the 事業概要 track — `_match_case_by_date` doesn't know `概要核准日期` (延吉段727: exact date match missed, undated virtual node), `extract_landcore_from_case_name` rejects single-段 sections (民生段140-9: two 駁回/撤回 概要 orphans dropped). Additionally the search response's per-case `schedule` (已核准/已駁回/自行撤回/已失效/審查中/施工中) is discarded, hiding *why* units lack national-portal pages — exploration classified the 71 twur-less live: **15 never-approved** (permanent) · **50 recoverable** · 6 no-cases (data: `data/_twurless_classification.json`). Spec deltas added: `official-link-discovery` (概要核准 anchoring, ROC normalization, schedule capture), `orphan-case-anchoring` (single-段 extraction, ghost node_date fallback), `viewer-related-links` (status badge + never-approved reason), `fetch-remaining-portal` (ledger classification + liveness policy). Tasks in §7.

## Capabilities

### New Capabilities
- `orphan-case-anchoring`: Pipeline merges landcore-similar orphan case_ids as ghost nodes in the history graph; viewer renders them with an "orphan" badge and connects them with dotted construction-chain edges.
- `virtual-milestone-nodes`: Named orphans with landcore ≥ 0.7 render as virtual milestone nodes — dashed, chronological, in their track column, without recno — retiring the ghost-anchor column once names are harvested.
- `viewer-graph-layout`: Content-addressed row pitch, codified four-column grid, centered pinch-zoom graph viewport, and responsive list/detail balance.

### Modified Capabilities
- `viewer-milestone-timeline`: Construction-chain edges (建照/開工/使照) use dotted style to visually group them as a phase sequence.
- `viewer-related-links`: 相關連結 resolves case names for orphan case_ids via `case_milestones` and `search_rejected` fallbacks.

## Impact

- **Viewer (`viewer/app.js`)**: Graph edge logic for construction chain, `buildRelatedLinkLabels` fallback chain, ghost-node rendering for orphan cases.
- **Pipeline (`urtpe/merge.py` or `urtpe/links.py` guard)**: Landcore similarity check for orphan case_ids; emit ghost node entries into `projects.json` graph structure.
- **Data model (`projects.json`)**: New `orphan: true` flag on node objects; new `case_id` field on orphan nodes for portal linking.
- **No schema version change** — additive fields only, backward compatible.