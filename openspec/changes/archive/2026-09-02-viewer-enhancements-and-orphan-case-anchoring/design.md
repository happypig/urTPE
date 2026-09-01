## Context

Current state (see proposal.md for motivation):

**Viewer (`viewer/app.js`)**:
- Left list renders project cards with `p.implementer` only (line 551)
- Graph edges for construction chain events use solid/dashed based on source portal (lines 695-720)
- `buildRelatedLinkLabels` builds `byCase` from node-level links only (lines 317-326); orphan case_ids missing from nodes get empty names
- No ghost node rendering for orphan case_ids

**Pipeline (`urtpe/links.py`, `urtpe/merge.py`)**:
- `search_taipei_cases_api` applies §6.7/§6.8 parcel guard; rejected cases go to `search_rejected` (links.py:744, 753)
- `attach_links_to_projects` copies `city_case_ids` to `links.taipei` (links.py:1076) — includes orphans
- `build_graph_document` (graph.py) creates nodes from `Project.members` only; no ghost node logic
- `DiscoverResult` has `city_case_ids` (kept) and `search_rejected` (dropped); both end up in `links`

The 09907221 case exemplifies the problem: it's in `links.taipei`, supplies 14 milestone dates via `milestones_source`, but has no anchor node — its case_name carries the anchor parcel (623地號) so landcore similarity is high (≥0.7).

## Goals / Non-Goals

**Goals:**
1. Viewer: Dotted edges for 建照→開工→使照 sequence (all source portals)
2. Viewer: 相關連結 resolves orphan names via `case_milestones` → `search_rejected` fallback
3. Pipeline + Viewer: Landcore-similar (≥0.7) orphan case_ids become ghost nodes with milestones, orphan badge, and dotted construction-chain edges

**Non-Goals:**
- 基本面積 display in left-list cards (covered by separate `viewer-base-area-color-style` change)

**Non-Goals:**
- Changing the §6.7/§6.8 parcel guard threshold (stays at 0.7)
- Auto-merging ghost nodes into real records (human decision via review flags)
- Modifying `schema_version` — ghost nodes use additive fields only
- Full pipeline re-architecture; changes are localized to guard/merge and viewer rendering

## Decisions

### 1. Ghost node creation in `attach_links_to_projects` (pipeline side)

**Decision**: Extend `attach_links_to_projects` in `urtpe/links.py` to detect orphan case_ids and create ghost node entries in the project's graph data before `build_graph_document` runs.

**Rationale**: `attach_links_to_projects` already runs after discovery and has access to `project.links` (including `city_case_ids`, `milestones_source`, `search_rejected`). It's the single point where `links` meet `Project` objects before graph emission.

**Alternative considered**: Create ghost nodes in `build_graph_document` (graph.py).
- Rejected: Would require passing raw discovery data through graph.py, widening the pipeline → graph boundary.

**Implementation sketch**:
```python
# In attach_links_to_projects, after setting project.links:
orphan_case_ids = [cid for cid in disc.city_case_ids if not any(cid in (n.links or {}).get('taipei', []) for n in project.nodes)]
for cid in orphan_case_ids:
    # Compute landcore from case_name in search_rejected or case_milestones
    if landcore_similarity(case_name, project.anchor_landcore) >= 0.7:
        project.links.setdefault('orphan_nodes', []).append({
            'case_id': cid,
            'orphan': True,
            'provenance': 'orphan-case-anchoring',
            'milestones_taipei': extract_milestones_for_case(cid, disc),
            'milestones_national': ...,
        })
```

### 2. Landcore similarity function reuse

**Decision**: Reuse the existing `build_land_core_key` + similarity logic from `urtpe/merge.py` (which powers the PDF merge) rather than inventing a new one.

**Rationale**: The 0.7 threshold already exists in merge (`LINK_THRESHOLD = 0.7`). Consistency with existing similarity behavior is critical — if merge considers two records same-unit at ≥0.7, ghost anchoring should too.

**Implementation**: Extract `compute_landcore_similarity(a, b) -> float` from merge module; call it from `attach_links_to_projects`.

### 3. Viewer dotted edges for construction chain

**Decision**: In `buildConstructionChain` output, add a `slot_index` (0=建照, 1=開工, 2=使照). In graph rendering (lines 695-720), when consecutive events both have `slot_index` defined, force dotted edge style.

**Rationale**: The construction chain is a fixed 3-slot sequence (`CONSTRUCTION_CHAIN_SLOTS` at line 10). Slot index is a stable, portable property — unlike source portal which varies.

**Alternative**: Check label strings ("建照核發日期" etc.) in rendering loop.
- Rejected: String matching is brittle; slot index is explicit and testable.

**Implementation**: Modify `buildConstructionChain` to return `slot_idx` on each event. In rendering loop (line 696), add:
```js
if (e.slot_idx !== undefined && i > 0 && events[i-1].slot_idx !== undefined) {
  // force dotted regardless of source
}
```

**Amendment (2026-08-27 live review)**: the dotted connector replaces only the *inter-event* link. A chain-following event that also *starts a new source group* still draws its source edge from the owning record (e.g., 開工日期 2022/08/26 matches implementation payload case 09907222 → solid edge from recno 829, while 建照→開工 renders dotted). First implementation `return`ed early on the dotted branch and silently dropped those source edges.

**Amendment (2026-08-27 edge-semantics codification, user rules)**: edge semantics follow a fixed precedence —
1. **Source edges (slanted)**: each source group's earliest event receives an `event-edge` (pink `taipei` / green `national`) from its owning record node; national-fallback groups attach to the 現況 record. Always drawn, independent of connector styles.
2. **Same-source connectors (vertical solid)**: adjacent events of one source group chain by solid `event-link` in the group's color.
3. **Cross-source transitions (vertical dashed)**: last event of one group → first event of the next, dashed `event-link` in the incoming group's color (pink in the all-Taipei twin case, green when entering a national-fallback group).
Precedence: consecutive construction slots (建照→開工→使照) always render the dotted chain style, overriding 2/3 for that pair only — the group's source edge (rule 1) is never suppressed.

**Amendment (2026-08-27 final, supersedes the precedence model above)**: the user retired the dotted chain styling — the three rules are now the complete edge model, with two additions:
1. **Ghost anchors act as sources**: an execution event whose provenance is an orphan case receives its slanted solid pink source edge from the orphan's dashed-circle node (the event renders ONCE, in the shared execution column — no duplicate in the ghost column; the ghost column holds anchor nodes only).
2. **Compact pitch**: timeline row spacing halved 64px → 32px (constant `ROW`), across records, events, and ghost-column anchors.
Consequences: `slot_idx` remains on chain events (data-useful) but no longer changes connector styling; `.event-link.dotted` CSS retired; `.event-link.dashed` gains an actual CSS rule (it previously rendered solid — a latent rule-3 violation); same-source triples like 北投區-振興段四小段-166-2地號等34筆 (all three slots from case 10211302) render as solid pink verticals per rule 2.

### 9. Candidate-name harvest at discovery time (enabler for virtual nodes)

**Decision**: persist the search API's per-candidate `case_name` (already returned and guard-parsed; currently dropped at discover_project_links) into DiscoveryResult as `candidate_names: {case_id: case_name}`. Landcore similarity then computes from real names, superseding the attribution/twin-bridge proxies as names become available. **One search call per project harvests every candidate's name** — no PDF-cycle dependency.

### 10. Virtual milestone nodes replace the ghost column (as names arrive)

**Decision**: a named orphan with similarity ≥ 0.7 renders as a virtual milestone node — dashed circle + dashed edges, placed chronologically at its 核定日期 inside its 事業種類 column (per the four-column grid), labeled stage + track **without recno**, inheriting the family's project identity. Its execution dates render once in the shared column, fed by slanted solid source edges from the virtual node (rule 1). Ghost payloads gain `stage` / `track` / `node_date` fields derived from case_name + milestones. **Transition**: nameless orphans (attribution/twin-bridge only) keep the interim dashed-anchor column until harvest fills their names; the column retires per-family as names land.

**Resolutions (user, 2026-08-27)**:
- **Badge anatomy**: virtual nodes carry the *same* 北/國 link-badge strip as PDF milestone nodes (positioned above the label) — no bespoke orphan-id-link styling; the only differentiation is the dashed circle/edges.
- **No 孤 badge on named virtual nodes**: provenance lives in the tooltip only (e.g., title="孤兒案例（orphan-case-anchoring）"). The interim nameless-column anchors keep their 孤 badge.
- **Harvest run scheduling**: the backfill (5.1.4) runs **separately** from implementation — the code ships first (5.1.1–5.1.3), the actual ~709-call harvest is a scheduled/resumable operation, and virtual nodes materialize per-family as the harvest + a cache-first regen land. **Rationale (user)**: the search endpoint's rate-limit profile differs materially from the JSON discovery APIs, so the harvest needs its own conservative pacing and its own scheduling window — never bundled with normal discovery or other crawls.
- **Post-harvest refinements (user, 2026-08-27)**: (a) **區段 labels** — the trailing 區段 token (-東區/-西區/-北區/-南區/甲乙區段) is extracted from case_name tails into node sub-lines for real *and* virtual nodes; base cases (no token) stay unlabeled with tooltip provenance. These tokens distinguish the 北/南 and 東/西 paired sub-district cases that otherwise render as clones (榮星 8-orphans, 懷生 931 same-day trios). (b) **Stage-key clusters** — nodes group by 第N次 within the family (not date); undated members join their stage's dated band tagged (未核定); cluster date = real member's date else min(dated); bands + count chips render only for ≥2-member clusters (corpus: 378 clusters — 301 pairs/64 triples/9×4/3×5/1×6 — vs 1,354 bare singles). The interim ghost column then holds nameless orphans only (corpus: 0 post-harvest).

### 11. Graph layout & viewport

**Decisions**:
- **Content-addressed pitch**: node↔node gaps = normal 64px; any execution-date row = 32px. Implementation: per-row height array + prefix sums replacing `i * ROW`; ghost-column node rows use the node pitch; `svgH` = total.
- **Four-column grid**: col1 事業概要/事業計畫/都市計畫; col2 combined plan×權利變換 (事業計畫、權利變換, 都市計畫、權利變換); col3 權利變換/其他; col4 execution dates (fixed). Virtual nodes occupy col1–3 by their own track. *Open: confirm col2 membership covers both combined variants.*
- **Viewport**: svg centered horizontally in a scrollable `.graph-viewport`; two-finger pinch scales (min/max clamped, anchored at pinch point); drag pans; desktop parity via pointer-drag + ctrl-wheel.
- **RWD**: below the desktop breakpoint, `#list` caps height (scrollable, fewer visible items); `#detail` takes the remaining viewport.
- **Callout clearance (user constraint, 2026-08-27)**: best-effort non-overlap of callout boxes vs node labels + badge strips, events, ghost anchors, and other callouts. The existing collision dodger already boxes nodes/events/placed callouts; the upgrade is (a) node boxes must include the badge strip footprint, (b) when all candidate spots collide, extend the canvas (grow viewBox/svgH/svgW) instead of accepting the last colliding spot. Interacts with 5.3.1: the halved/variable pitch shrinks free space, making canvas-extension the primary relief valve.

### 12. Virtual-node tie-break by case_id (2026-08-31, user decision)

**Problem (2026-08-31 exploration, `docs/sorting_connecting_rules.md` §6)**: 29
families carry ≥2 virtual nodes sharing one `node_date` (corpus shapes: attempt
twins like 吉林段三小段1021's 09902261/10201171 — same stage, near-identical
names; 概要+計畫 same-day pairs like 吉林段四小段676; three-stage same-day
sprees like 吉林段一小段717). The cluster member sort's tie-break chain (real
first → dated first → 區段 locale) leaves same-date, same-stage virtuals tied,
and JS sort stability resolves them by **input order = platform
search-response order** — load-dependent (the view/75 lesson) and unspecified.

**Decision (user)**: order virtual nodes row-by-row by **case_id ascending,
compared against the case_id attached to PDF milestone nodes** — a real node's
comparison key is its anchored case_id (`links.taipei[0]`), a virtual node's is
its own `case_id`. Because case_ids encode the application era (YY序號), the
order equals application-attempt order: deterministic, load-independent, and
semantically correct (an earlier withdrawn attempt — virtual — sorts before a
later gazette approval — real; attempt twins read 申請序 ascending, matching
the §2 143/144 convention).

**Rule detail**:
1. Within a stage cluster: sort members by effective case_id ascending
   (real → `links.taipei[0]`; virtual → `case_id`). This supersedes the
   blanket "real before virtual" comparator for dated members.
2. Real nodes without an anchored case (empty `links.taipei`, e.g. 民生段140-9
   node 65) carry an empty key and sort first in the cluster (gazette rows the
   platform does not link read before case-keyed rows).
3. Cross-cluster, same-effective-date ties (e.g. 概要 cluster and 計畫 cluster
   both dated 2007-01-30): order clusters by their members' minimum effective
   case_id — the same key extends row-by-row across cluster bands.

**Consequences**: order becomes stable across portal loads and regens; attempt
twins (resubmission pairs) render in application order; the previous implicit
platform-order tie-break is retired. Spec surface: `virtual-milestone-nodes`
cluster-sort requirement gains this tie-break layer (scenarios + ordering test
at implementation time).

**Amendment (2026-08-31, user) — connect virtual nodes row-by-row with an
edge**: consecutive virtual nodes within a cluster (the case_id-ascending row
order above) are chained by a **virtual revision edge** — dashed line style
(matching the virtual dashed circles), directed along the row (earlier attempt
→ later). Semantics: within a stage cluster, same-date/same-stage virtuals are
attempt-succession pairs (withdrawn → resubmitted, e.g. 吉林段1021's
09902261 → 10201171), so the chain reads as the platform's application
sequence. Same-date *cross-stage* pairs (概要/計畫) live in different clusters
and stay unchained — parallel tracks are not revisions. Only virtual-involved
pairs gain edges: real↔real pairs are already covered by graph.py's revision
edges (no duplicates). Implementation surface: `virtual-milestone-nodes` spec
gains the chain-edge requirement; `renderDetail` draws `edge virtual` lines
between consecutive virtual positions inside each cluster.

**Amendment 2 (2026-08-31, user — badge-strip append, resolves the three open
threads)**: for same-date virtual nodes, **only** the badges carrying 區段標籤
**and** 排程 (已駁回/施工中/自行撤回/已核准…) are kept, appended **next to the
anchored milestone's 北 badge** on the real node's strip. This resolves
together: (1) the virtual's own 北 badge is not duplicated on its dashed
circle — the link appears on the anchored strip with 區段 + 排程 labels for
distinction; (2) each appended badge is distinguished by 區段 + status (no
bare 北 ambiguity); (3) strip growth is bounded — only 區段-carrying virtuals
append (nameless/no-排程 virtuals stay on their own virtual rows). Example
anatomy (民生段140-9 shape):

```
real node (anchored 11302031):
  [北 案11302031][北 案11207021 已駁回][北 案11302031 自行撤回]…
                   ▲ appended same-date virtual badges: 區段 (tooltip) + 排程 text
```

Implementation surface: `virtual-milestone-nodes` spec gains the badge-append
requirement; `renderDetail` badge strip (getNodeMilestoneBadges) appends
same-date virtual 北 badges carrying 區段 + schedule (`links.case_schedules`);
the virtual circle keeps its dashed shape + tooltip. **已核准 is the default
focus state — its schedule badge is omitted** (only exceptional schedules
已駁回/施工中/自行撤回/已失效/審查中 render, 2026-08-31 refinement).

**Amendment 3 (2026-08-31, from 吉林段四小段603 exploration + user)** — the
case_id ordering extends family-wide, with same-date adjacency (two-layer):

1. **Family-wide interleaving**: cluster rows interleave by effective case_id
   ACROSS the family, not within stage clusters only — row order for the whole
   family = all members (real + virtual) by effective case_id ascending. This
   reproduces the 相關連結 order (09511210 → 09511211 → 09511212 → 09511213 →
   09511214 → 11007261 → 11007262 → 11501016) in the graph: undated virtual
   attempts (09511212/13 自行撤回) interleave BETWEEN their dated neighbors
   instead of being pushed to the tail, and 已駁回 11007262 precedes 已核准
   11501016.
2. **Same-date adjacency amendment**: same-date virtual nodes (e.g. A區/B區
   splits) attach immediately AFTER their same-day anchored milestone —
   date-band adjacency takes precedence over pure case_id order; case_id then
   orders members within the date band.
3. **相關連結 sort guarantee (pipeline-side)**: emitted `links.taipei` SHALL be
   case_id-ascending at attach time — corpus audit found 91/564 multi-id arrays
   unsorted (34 adjacent swaps = platform order drift). The 相關連結 list, the
   graph row order, and the platform search order then agree by construction.
4. **Chain edges follow the same effective key**: the attempt-succession chain
   (dashed virtual edges) connects consecutive rows in the family-wide order;
   the D12 cluster-level chain guard (track match) still applies.

Spec surfaces: `virtual-milestone-nodes` (cluster-ordering + chain-edge
requirements), `viewer-related-links` (相關連結 ascending order). Guardrail
note: node 920 of 603 (2018-01-25, gazette prints 擬訂 for what the platform
records as 變更[已核准]) is a gazette-side printing anomaly — stage parsing is
faithful to the PDF; candidate for a review flag, not a parser fix.



**Decision**: Extend `buildRelatedLinkLabels` to accept the full `project.links` object and walk the fallback chain: node `case_name` → `links.case_milestones[cid]` → `links.search_rejected[cid]`.

**Rationale**: `case_milestones` already maps orphan case_ids to their milestone dicts (e.g., 09907223 has milestones in the example). `search_rejected` stores the original case_name for guard-rejected cases (e.g., 09907221). Both are already in `links` — just not queried by the current function.

**Implementation**: Change signature to `buildRelatedLinkLabels(p, links)` and add fallback logic. No schema change.

### 5. Ghost node rendering in viewer

**Decision**: In `renderDetail`, if `p.links.orphan_nodes` exists, create additional SVG nodes with `orphan: true` flag, positioned in a dedicated "orphan column" or appended to the timeline. Connect their construction events with dotted edges (Decision 3).

**Alternative**: Embed ghost nodes in the existing column flow.
- Rejected: Would displace anchored nodes; orphan column keeps visual separation.

### 6. Cache recovery: union restore across cache generations (2026-08-27 incident)

**Decision**: Rebuild `data/.link_cache` via `scripts/rebuild_cache_union.py` — a deterministic per-project best-of-N across ordered generations `[partial WIP, .link_cache_backup_20260826_fix, .link_cache_backup_20260825_matcher, .link_cache_backup_20260824]`. For each project directory, parse every candidate `result.json` and select the winner by: (1) full-current-schema gate (`case_milestones`, `milestones_source`, `implementation`, `rewards`, `search_rejected` all present); (2) `status == "resolved"`; (3) content richness (`len(city_case_ids)`, `len(taipei_milestones)`, `len(national_milestones)`, no error). Ties favor the earlier-listed (fresher) generation. Copy winner's `result.json` together with its sibling `view.html`. Root-level artifacts (`portal_index.json`, `no_match_ledger.json`) come from `_20260826_fix`.

**Evidence** (measured 2026-08-27):
- Schema ladder: `0824` is pre-per-case-era (707/709 lack even `case_milestones`); `0825m` adds per-case milestones/impl/rewards but lacks `milestones_source` + `search_rejected`; `0826_fix` carries the complete 14-field schema on **709/709** files — nothing older is schema-complete.
- `_20260826_fix` loses to an older generation on **0** comparable projects ⇒ field-level grafting has no measured payoff.
- The 11-entry post-wipe partial overlaps backup dirs and flipped 1/11 shared projects to `unresolved` where the backup was `resolved` ⇒ blind overlay-by-copy destroys data; an explicit tie-broken compare is required.
- Resolved mix by gen: 697/12 (`0824`) → 691/18 (`0825m`) → 685/24 (`0826f`). Declining resolved counts reflect deliberate §6.7/§6.8 guard pruning, not regressions. ⚠ Do NOT resurrect `_20260824` for its higher resolved count — those extra matches are pre-guard false positives, and its schema cannot represent `search_rejected`.

**Alternatives rejected**:
- Blind robocopy of `_20260826_fix`: discards the 10/11 fresh wins and ignores the 1 fresh-loss flip.
- Three-way field merge across generations: complexity with zero measured gain (domination result above).
- Full re-crawl: hours of API traffic; unnecessary because ghost-node derivation consumes only cached fields (`city_case_ids`, `search_rejected`, `case_milestones`) via `attach_links_to_projects`.

**Mechanics enabling cache-first recovery**: `discover_project_links` short-circuits on `result.json` presence (links.py:521–524); `national_milestones` are already parsed inside `result.json`, so `view.html` coverage gaps don't force network on hit paths.

### 7. Guardrails against destructive regeneration (follow-up change, out of current scope)

**Problem class**: third destructive incident (08-24 concurrency race; 08-27 `--refresh` ran `shutil.rmtree(data/.link_cache)` at links.py:1287–1290 mid-regen, leaving 11/709 entries). Failure actors are autonomous agents, so every guard must work **without agent cooperation**. Today `--fresh` conflates three effects: (①) whole-dir rmtree, (②) portal-index re-crawl (links.py:417), (③) per-URL HTML-cache bypass cascade (links.py:590→336).

**Proposed stack**:

| Priority | Guardrail | Effect |
|---|---|---|
| 1 | Advisory lockfile `cache/.lock` (pid + cmdline + started_at; steal only when owning pid is dead) | Concurrent regens become structurally impossible (both incidents were collisions). Acquire *before* any rotation/wipe; repair and regen scripts must route through the same acquire path so they can't bypass the front door. |
| 2 | Rotate-before-wipe: rename existing dir → `.link_cache_prev_<TS>` (prune, keep K=2), applies to **both** `run(fresh=True)` and bulk `result.json` deletion loops (e.g., regen_links_2026_08_26.py main()) | Worst-case outcome degrades to losing one rotation generation instead of everything; runtime cost ≈ a rename. |
| 3 | First-class `--reparse` verb (delete `result.json` only; keep `view.html` + `portal_index.json` — semantics currently hand-rolled in regen_links_2026_08_26.py) and demote `--fresh` to refused-with-guidance; longer term, composable `--refetch portal\|views` | Removes the daily-use motivation to reach for nuke-all; surfaces the trap that refetching pages while a valid `result.json` exists is a **no-op** (discovery short-circuits at links.py:521 before any fetch), so invalidation verbs must name which state they discard. |

Considered and skipped: `--yes` confirmation gate (agents just retry with it attached); volume-threshold refusal (>N entries) (subsumed by rotation making even bad wipes cheap); shadow-dir build-and-swap (strictly safer upgrade path for #2, defer).

### 8. Ghost-node defects surfaced by restored data; attribution fallback (2026-08-27)

First real-data run after Decision-6 recovery emitted zero `orphan_nodes`. Two latent defects:

1. `_load_projects_from_js` never restored per-record `links`, so `anchored_case_ids` was always empty on `--from-js` runs — every matched case_id read as "orphan" (and the "lossless round-trip even without --links" comment was untrue for links). CleanRecord also lacked the field.
2. Ghost creation gated solely on `disc.search_rejected[cid]` for the orphan's case_name, but `search_rejected` is empty across all real cache generations — unit tests passed only because fixtures inject names. On live data the landcore path could never fire.

**Remedy**:
- `CleanRecord.links` field added; loader restores `node["links"]`.
- Ghost/orphan computation moved **after** per-member anchoring (`member.links` assignment), so the anchored set is correct on both the PDF path and the `--from-js` path.
- Gating fallback: when no `search_rejected` name exists, treat membership in `milestones_source.values()` (stage attribution won during LWW merge) as identity proof ≥ threshold equivalent. Ghost dicts additionally carry `case_name` (additive, may be empty until name harvest lands).
- Result on restored cache: 308 projects / 403 ghosts; the 623-family 09907221 ghost carries all 15 attributed taipei milestones (earlier prose said 14).

**Follow-up findings during §4 verification (same day)**:
- A second, older ghost representation existed in `build_graph_document` — synthetic `孤兒節點` nodes appended into emitted `nodes[]`. Because `CleanRecord` keeps `stage`/`track`, one regen round-trip re-imported them as real members (1419→1822 records) and re-emitted them flagless. Removed: ghost representation is now exclusively `links.orphan_nodes` (per Decisions 1/5), and `_load_projects_from_js` content-guards against legacy contamination (`orphan` flag OR negative recno OR stage 孤兒節點). Regen is idempotent again.
- `links.case_milestones` / `links.search_rejected` are now emitted onto projects when non-empty (they never were, despite Decision 4's premise), powering the viewer fallback chain live; 09907221/09907223 surface as "里程碑 15 筆" until real names arrive via the deferred harvest.
- **Attribution proxy limitation — shadowed twins**: attribution is last-write-wins per label, so a same-unit sibling case that loses every label to its twin (e.g., 09907223 vs 09907221 in 文山區-木柵段三小段-623地號等39筆) gets zero attribution and is excluded from ghost anchoring despite carrying a full 15-date platform record. **Resolution (user decision, same day): twin-bridge gate** — an orphan with no name and no attribution still anchors when its per-case milestone record shares ≥ `TWIN_BRIDGE_MIN_SHARED_DATES` (3) exact (label, date) pairs with cases already anchored to the unit; its ghost payload carries exactly the shared pairs (provenance-honest). Corpus scan: admits ~119 currently-invisible same-unit orphans; 159 low-signal cases stay excluded. Landcore similarity on harvested names remains the long-term criterion and will subsume this proxy.

**Deferred (user decision)**: extend DiscoveryResult to persist candidate `case_name`s returned by the Taipei search API (currently collected then discarded at discover_project_links) during the next scheduled PDF refresh, enabling the literal landcore-similarity path for every orphan without extra crawls before then.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Ghost nodes clutter graph for projects with many orphans | Orphan column + badge keeps them visually distinct; threshold 0.7 bounds count |
| Landcore similarity false positives (different unit, similar name) | 0.7 threshold matches merge; projects with ambiguous orphans already flagged as 臨界對 |
| `case_milestones` may have sparse data for some orphans | Fallback chain continues to `search_rejected`; empty name is acceptable fallback |
| Dotted edges might conflict with existing dashed group transitions | Slot-index check runs before group-transition logic; construction chain takes precedence |
| `search_rejected` case_names may be stale (from discovery, not latest) | Acceptable — 相關連結 is debug-only; primary graph is authoritative |
| Restored cache bakes in stale or site-drifted data | Union restore prints per-generation status mix before bake-in; shifts in resolved/unresolved counts are visible immediately |

## Migration Plan

**Recovery prerequisite (2026-08-27 cache-wipe incident)**: before Step 1, rebuild `data/.link_cache` from generation backups via the union-restore utility (Decision 6). Step 1 then runs as ~700 pure cache hits (minutes) — **never with `--fresh`**, which rmtree's the entire cache dir (Decision 7 for permanent hardening).

1. **Pipeline**: Add ghost node logic to `attach_links_to_projects` (links.py). Run full `--links` regeneration (cache-first, fast).
2. **Viewer**: Deploy `app.js` changes (dotted edges, fallback chain, ghost node rendering).
3. **Verification**: Spot-check projects with known orphans (09907221, 09907223, etc.) — graph shows ghost node, 相關連結 shows names.
4. **Rollback**: Revert `app.js` and `links.py` changes; re-run `--links` from caches (no network).

## Open Questions

- Should ghost nodes appear in the detail table (`recs` table)?
  - Currently excluded (table iterates `p.nodes`). Could add as extra rows with "orphan" stage. Defer to implementation — low risk.
- Exact position of orphan column in graph?
  - Options: far right, or appended after last track column. Visual review needed. Defer.