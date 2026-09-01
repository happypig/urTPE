> POC: Validate landcore similarity computation for orphan case_ids against known clusters (e.g., 09907221 similarity to 文山區木柵段三小段623地號等39筆 anchor) before implementing ghost node logic.

## 1. Test Writing & Validation

### 1.1 Landcore Similarity POC
- [x] 1.1.1 Extract `compute_landcore_similarity` from `urtpe/merge.py` and verify it returns ≥0.7 for 09907221 vs anchor "文山區木柵段三小段623地號等39筆" (verified: 0.85)
- [x] 1.1.2 Verify it returns <0.7 for a known dissimilar orphan (e.g., different district/section) (verified: 0.0 for different district)
- [x] 1.1.3 Document threshold edge cases and confirm 0.7 matches `LINK_THRESHOLD` in merge

### 1.2 Viewer Unit Tests
- [x] 1.2.1 Add test for `constructionStage` derivation (already exists) — ensure slot_idx mapping works
- [x] 1.2.2 Add test for `buildRelatedLinkLabels` fallback chain: node → case_milestones → search_rejected
- [x] 1.2.3 Add test for construction-chain edge style: slot_idx consecutive → dotted

### 1.3 Pipeline Unit Tests
- [x] 1.3.1 Add test for `attach_links_to_projects` orphan detection: case_id in city_case_ids but not in any node.links.taipei
- [x] 1.3.2 Add test for landcore similarity computation on orphan case_name vs anchor
- [x] 1.3.3 Add test for ghost node creation: `orphan: true`, `provenance: "orphan-case-anchoring"`, milestones populated from milestones_source
- [x] 1.3.4 Add test for threshold: similarity <0.7 → no ghost node

## 2. Viewer Implementation (`viewer/app.js`)

### 2.1 Construction Chain: Dotted Edges
- [x] 2.2.1 Update `buildConstructionChain` (line ~227) to include `slot_idx` (0/1/2) on each event
- [x] 2.2.2 In graph rendering (lines 695-720), add slot_idx consecutive check before group-transition logic
- [x] 2.2.3 Force dotted style (`stroke-dasharray: 4,4`) when both current and previous event have slot_idx
- [x] 2.2.4 Verify anchored nodes: 建照→開工→使照 edges are dotted
- [x] 2.2.5 Verify orphan ghost nodes (when rendered): same dotted style

### 2.3 相關連結: Fallback Chain
- [x] 2.3.1 Extend `buildRelatedLinkLabels(p)` to accept full `project.links` and walk fallback: node.case_name → links.case_milestones[cid] → links.search_rejected[cid]
- [x] 2.3.2 For case_milestones fallback: render case_id with "(milestones available)" or similar context
- [x] 2.3.3 For search_rejected fallback: render the stored case_name verbatim
- [x] 2.3.4 Verify 09907221 shows "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案" from search_rejected
- [x] 2.3.5 Verify 09907223 shows context from case_milestones
- [x] 2.3.6 Precedence fix (2026-08-28): consult `orphan_nodes` real case names BEFORE the `case_milestones` label — the 里程碑 N 筆 branch ran first, so harvested names (e.g. 吉林段603 09511210/12/13, 11007262; 學府段125 10611122) never replaced the generic label; structural regression test in test_viewer_labels.py
- [x] 2.3.7 candidate_names emission + fallback (2026-08-29): `attach_links_to_projects` emits `links.candidate_names` (harvested names never reached the viewer before), `buildRelatedLinkLabels` consults it before the milestone label (spec chain updated; structural test extended; fixes 長安段454 09112120 label)

### 2.4 Ghost Node Rendering
- [x] 2.4.1 In `renderDetail`, detect `p.links.orphan_nodes` array and create SVG ghost nodes
- [x] 2.4.2 Position ghost nodes in a dedicated rightmost column (after track columns)
- [x] 2.4.3 Add "orphan" badge (e.g., 👻 or "孤" label) on ghost nodes
- [x] 2.4.4 Connect ghost node's construction events with dotted edges (reuse 2.2 logic)
- [x] 2.4.5 Ghost node click → open Taipei case page via `case_id` field
- [x] 2.4.6 Verify 09907221 ghost node appears with 14 milestones and orphan badge

## 3. Pipeline Implementation (`urtpe/links.py`)

### 3.1 Landcore Similarity Utility
- [x] 3.1.1 Extract `compute_landcore_similarity(a: str, b: str) -> float` into `urtpe/links.py`
- [x] 3.1.2 Ensure it uses same normalization (`normalize_parcel_token`, full-width digits, 之→-) as merge

### 3.2 Ghost Node Logic in `attach_links_to_projects`
- [x] 3.2.1 After setting `project.links`, compute anchored case_ids from `project.nodes` (union of node.links.taipei)
- [x] 3.2.2 Identify orphan case_ids: `set(disc.city_case_ids) - anchored_case_ids`
- [x] 3.2.3 For each orphan, get case_name from `disc.search_rejected.get(cid)` or infer from `disc.case_milestones[cid]`
- [x] 3.2.4 Compute landcore similarity between orphan case_name and project anchor landcore
- [x] 3.2.4 If similarity ≥ 0.7, build ghost node dict with: `case_id`, `orphan: true`, `provenance: "orphan-case-anchoring"`, `milestones_taipei` (from `disc.milestones_source` filtered by case_id), `milestones_national` (from `disc.national_milestones` if mapped)
- [x] 3.2.5 Append ghost node to `project.links.orphan_nodes` list
- [x] 3.2.6 Verify 09907221 creates ghost node with 14 milestones
- [x] 3.2.7 Verify dissimilar orphan (e.g., different section) does NOT create ghost node

### 3.3 Propagate Ghost Nodes to `projects.json`
- [x] 3.3.1 Ensure `build_graph_document` (graph.py) includes `orphan_nodes` from `project.links` in the emitted graph structure
- [x] 3.3.2 Verify `projects.json` contains `orphan_nodes` array with correct fields

## 4. End-to-End Verification

### 4.1 Cache Recovery, Regeneration & Spot Check

> 2026-08-27: a concurrent `--fresh` regen triggered `shutil.rmtree(data/.link_cache)`
> (links.py:1289), wiping ~700 cached discoveries mid-run (11 survived). Do NOT pass
> `--fresh` in this section — recovery path restores caches first per design.md
> Decision 6; permanent hardening is Decision 7 (follow-up change).

- [x] 4.1.0 Confirm no link-discovery process is running; move partial `data/.link_cache` (11 entries) → `data/.link_cache_wip_20260827` (keep it, don't delete)
- [x] 4.1.0b Add `scripts/rebuild_cache_union.py`: per-project best-of-N restore — winner selection = full-schema gate (`search_rejected`/`case_milestones`/`milestones_source`/`implementation`/`rewards`) → `resolved` status → city-id/milestone richness; ties favor earlier-listed (fresher) generation; carry sibling `view.html`; root `portal_index.json` + `no_match_ledger.json` from `_20260826_fix`
- [x] 4.1.0c Restore `data/.link_cache` via union over `[data/.link_cache_wip_20260827, data/.link_cache_backup_20260826_fix]` (older gens optional); expect ~709 full-schema result.json and a printed per-generation status-mix report
- [x] 4.1.1 Run `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links` (cache-first resumable: ~700 cache hits, minutes — never with `--fresh`)
- [x] 4.1.2 Open viewer, filter to 文山區-木柵段三小段-623地號等39筆
- [x] 4.1.3 Verify graph shows ghost node for 09907221 with orphan badge
- [x] 4.1.4 Verify 建照→開工→使照 edges are dotted (both anchored and ghost)
- [x] 4.1.5 Enable 相關連結 debug toggle, verify 09907221 and 09907223 show case names (live data: real names arrive after the deferred search-API harvest; both currently show "里程碑 15 筆" via the case_milestones fallback branch per spec)

### 4.2 Regression Check
- [x] 4.2.1 Verify projects without orphans render identically (no visual regressions)
- [x] 4.2.2 Verify projects with low-similarity orphans don't show ghost nodes
- [x] 4.2.3 Verify construction-chain dotted edges don't affect non-construction edges

### 4.3 Acceptance Test: User Scenarios
- [x] 4.3.1 Scenario: Planner opens detail, construction chain visually grouped ✓
- [x] 4.3.2 Scenario: Planner enables 相關連結, sees full case names for all links ✓
- [x] 4.3.3 Scenario: Planner sees ghost node with orphan badge, understands it's a guard-dropped case ✓

### 4.4 Post-acceptance corrections (2026-08-27, live review)
- [x] 4.4.1 Left-list label 基本面積 → 基地面積 (matches implementation callout)
- [x] 4.4.2 Dotted construction edge no longer suppresses the group's source edge (開工 reconnects to recno 829 / 案09907222 via impl Eng_Start_Date match)
- [x] 4.4.3 Ghost node renders as dashed circle (no PDF record) labelled 北<case_id> with 孤 badge, edge to its 建照核發日期 event; eventless ghosts still render

### 4.5 Twin-bridge anchoring + edge-semantics codification (2026-08-27)
- [x] 4.5.1 Twin-bridge gate: zero-attribution orphans anchor via ≥3 shared (label,date) pairs with anchored cases; payload carries the shared pairs only (spec + design Decision 8 updated; shadowed twin 09907223 now anchors)
- [x] 4.5.2 Spec: viewer-milestone-timeline gains "Source-colored edge semantics" requirement (slanted source edges / same-source solid / cross-source dashed, chain-dots precedence)
- [x] 4.5.3 TDD: structural tests pinning the three edge rules + chain precedence in app.js (test first, then confirm implementation complies)
- [x] 4.5.4 Final edge model: retire dotted chain styling; execution dates render once (ghost column = anchor nodes only); orphan-sourced events get slanted solid pink edges from their ghost anchor; fix missing `.event-link.dashed` CSS; same-source triples render solid (166-2 case) — spec rewritten, tests first, then app.js
- [x] 4.5.5 Compact pitch: timeline row spacing 64px → 32px (`ROW` constant) for records, events, and ghost anchors

## 5. Virtual milestone nodes + graph layout (added 2026-08-27, same change per user)

> Design Decisions 9–11; specs `virtual-milestone-nodes` + `viewer-graph-layout`.
> Execution order: harvest enables virtual nodes; layout work is independent.

### 5.1 Name harvest (pipeline)
- [x] 5.1.1 Extend DiscoveryResult with `candidate_names: {case_id: case_name}`; persist kept-case names at discover_project_links (search API already returns them)
- [x] 5.1.2 Emit names into ghost payloads (`case_name`); attach computes landcore similarity from harvested names, superseding attribution/twin-bridge when present
- [x] 5.1.3 Derive `stage` / `track` / `node_date` (核定日期) per ghost payload from name + milestones; unit tests for all derivations
- [x] 5.1.4 Targeted harvest run: one search-API call per project (resumable, cache-first style, NO --fresh) to backfill names into the cache — **scheduled as a separate operation with its own conservative pacing (search endpoint's rate limits differ from the discovery JSON APIs); never bundled with discovery runs or other crawls**
- [x] 5.1.5 Regen (cache-first, no --fresh) after the harvest run so payloads gain names/stage/track/node_date
- [x] 5.1.6 Portal-verified ghost bypass (2026-08-29): new `DiscoveryResult.view_verified_case_ids` — cases extracted from the project's own national view page 相關連結 are portal-verified and exempt from the landcore-similarity gate (parcel-less case names score 0.0, e.g. 崇仁新村); `resolve_via_view_links…` writes the field; spec delta updated (orphan-case-anchoring "Portal-verified orphans bypass the landcore gate"); regression test `test_view_verified_orphan_bypasses_similarity_gate`; enables 崇仁新村 virtual nodes (§6.11/6.12 of operations log)

### 5.2 Virtual milestone nodes (pipeline + viewer)
- [x] 5.2.1 Named \+ similar orphans render as virtual nodes: dashed circle/edges, chronological placement at node_date, own 事業種類 column, stage+track label without recno, **standard 北/國 badge strip identical to PDF nodes**, family identity; named virtual nodes carry **no 孤 badge** (tooltip provenance only)
- [x] 5.2.2 Virtual-node execution dates stay single-render in the execution column with slanted solid source edges from the virtual node
- [x] 5.2.3 Nameless orphans keep the interim dashed-anchor column (孤 badge retained there); column retires per-family once names land
- [x] 5.2.4 Tests: placement, labeling, single-render, transition behavior
- [x] 5.2.5 區段 labels: extract trailing 區段 token (-東區/-西區/-北區/-南區/甲乙區段…) from case_name into the node sub-line for REAL and virtual nodes (e.g., 事業計畫（西區）); base (no token) provenance in tooltip
- [x] 5.2.6 Stage-key clusters: group graph nodes by 第N次 within the family — undated members join their stage's dated cluster tagged (未核定); cluster date = real member's date else min(dated); band + count chip (e.g., 變更(第四次) · 4 案 · 1 未核定) for clusters ≥2, singles bare; members ordered base(real) → splits(by 區段) → undated. Corpus: 378 multi-clusters (301 pairs/64 triples/9×4/3×5/1×6), 959 singles unaffected

### 5.3 Graph layout & viewport (viewer)
- [x] 5.3.1 Content-addressed pitch: node↔node 64px, execution-date rows 32px (per-row height array + prefix sums; svgH = total)
- [x] 5.3.2 Four-column grid codified (col1 概要/事業/都市計畫; col2 combined×權利變換; col3 權利變換/其他; col4 execution dates)
- [x] 5.3.3 `.graph-viewport`: horizontal centering, two-finger pinch zoom (clamped, pinch-anchored), drag pan; desktop pointer parity (drag + ctrl-wheel)
- [x] 5.3.4 RWD: cap `#list` height on narrow viewports (scrollable); `#detail` keeps the majority space
- [x] 5.3.5 E2E: 623 family (virtual 09907221 beside recno 829 at 2019/01/31), 166-2 solid chain, pinch/center behavior, narrow-viewport balance
- [x] 5.3.6 Callout clearance: node boxes include badge-strip footprint; canvas-extension fallback when all candidate spots collide (never accept overlap while canvas can grow)
- [x] 5.3.7 Left list: append (+N) orphan-node count after the record count when present (e.g., 2(+2) 筆)

## 6. Coverage regression guard (facts §12 #1 / §18 rule 3; added 2026-08-29)

> Two unguarded wipes (§18, §6.10) made this the standing "do first" item. Operational
> guard — no capability-spec delta; protected by BDD tests.

- [x] 6.1 `urtpe/coverage.py`: `snapshot(root, project_ids)` → per-project flags (resolved / twur / national / 使用核發) read from sanitized-id caches; `diff(before, after)` → regressions (flag True→False on the pid intersection), lost, gained; `coverage_guard(root, project_ids, strict=True)` context manager appending an alert line to `data/.link_cache/coverage_alerts.jsonl` on any regression and raising `CoverageRegression` when strict
- [x] 6.2 Wire into `urtpe.cli._run` discovery lane: guard wraps `discovery.run` so a cache-wiping job aborts BEFORE the viewer is emitted (the §17/§18 viewers-emitted-regressed-state failure mode)
- [x] 6.3 BDD tests: snapshot counting; monotonic job passes; injected wipe raises with pid+flag; family-merge (lost pid, equal flags) is reported not raised; strict=False collects without raising; alert trail only on regression

## 7. 概要-track support + schedule/status visibility + never-approved classification (added 2026-08-29, exploration §6.14/6.15)

> Exploration baseline: 71 twur-less classified live via `top.ashx` outcome — **15 never-approved** (lapsed 概要, permanent) · **17 has-approved + 33 mixed/other recoverable** · 6 no-cases. Data: `data/_twurless_classification.json`; spec deltas: official-link-discovery (概要核准 anchoring, schedule capture), orphan-case-anchoring (single-段 extraction, ghost node_date), viewer-related-links (status badge + no-twur reason), fetch-remaining-portal (ledger classification).

### 7.1 E1 — 概要-track support (pipeline)
- [x] 7.1.1 Tests first: single-段 extraction (民生段140-9地號等3筆); 概要核准日期 anchoring (延吉段727, incl. ROC 115/3/31 form); ghost node_date fallback chain — red before fix (tests/test_gaiyao_track.py, 9 scenarios)
- [x] 7.1.2 `extract_landcore_from_case_name`: accept single-段 sections (previously required the 段…段 double shape — 民生段140-9's two 概要 orphans were silently dropped)
- [x] 7.1.3 `_match_case_by_date`: add `概要核准日期` to the anchor label set (延吉段727: 概要核准 2026/03/31 = node date, exact match missed)
- [x] 7.1.4 Ghost `node_date` fallback chain: 核定日期 → 權變核定日期 → 概要核准日期 (undated virtual node fix)

### 7.2 E2 — schedule/status capture + display
- [x] 7.2.1 Tests first: schedule round-trip via search rows; attach emission via the dict shim; ghost payload carries schedule; `schedule_from_top` mapping; structural badge/reason assertions (tests/test_gaiyao_track.py, test_viewer_labels.py)
- [x] 7.2.2 Pipeline capture: search rows keep `schedule` → `DiscoveryResult.case_schedules` (was discarded)
- [x] 7.2.3 Pipeline emission: attach emits `links.case_schedules`; `schedule_from_top` maps `top.ashx` phase/NAME; ghost payload carries the schedule
- [x] 7.2.4 Viewer (adapter): 相關連結 schedule badge; virtual-node label badge; real-node anchored-case badge; left-list 未核定 chip; never-approved reason line (never-approved — no national-portal page)
- [x] 7.2.5 Infrastructure: schedule top-up sweep — `top.ashx` per case for every cache with city_case_ids lacking `case_schedules`, paced 0.8 s + logged + resumable (`scripts/schedule_topup_20260829.py`; done: 623 caches · 1,923 calls · 0 errors → 641/708 emit case_schedules, 21 未核定 chips live)
- [x] 7.2.6 Acceptance: live verification on 民生段140-9 — 未核定 chip in the list, [已駁回]/[自行撤回] badges + reason line in 相關連結, [已駁回]/[自行撤回] on the virtual nodes (emitted viewer, post top-up §6.15)
- [x] 7.2.7 已核准 default-state filter (2026-08-31): schedule badges render only for exceptional states (已駁回/施工中/自行撤回/已失效/審查中) — 已核准 nodes are the default focus, badge skipped in graph labels + 相關連結 (structural test added)

### 7.3 E3 — never-approved classification (ledger liveness)
- [x] 7.3.1 Tests first: `classify_case_outcome` mapping (lapsed/withdrawn/rejected → never-approved; 核定 → approved; 審查/施工 → in-progress); `project_twur_class` aggregation; `filter_candidates` excludes never-approved beyond TTL; `annotate_class` preserves probe history (tests/test_ledger_classification.py, test_fetch_remaining_portal.py)
- [x] 7.3.2 Classification implemented: `classify_case_outcome` + `project_twur_class` (top.ashx phase/NAME → outcome), `annotate_class` ledger annotation
- [x] 7.3.3 Liveness applied: ledger annotated from the live baseline (15 never-approved excluded from re-probes, 50 recoverable re-enter) — `data/_twurless_classification.json`

## 8. Chimera emit fix — per-node milestones from the anchored case (added 2026-08-30, exploration; facts §12 #2 / §5)

> Spec delta: `viewer-milestone-timeline` — "Per-node milestone attribution" MODIFIED. Exploration baseline: **319 families** carry multiple distinct 核定日期 across cases; the merged `milestones_taipei` is last-write-wins (newest fetched case wins), so every node renders the newest case's dates. Per-case truth exists in every cache (`case_milestones`), and every node already knows its case (date-anchored, §6.13).

- [x] 8.1 Tests first: node emits its anchored case's own 核定日期 (254-shape: node 1219 emits 2012/08/27, not the merged 2016/08/23); legacy cache without `case_milestones` falls back to the merged dict; project-level merged dict + `milestones_source` unchanged
- [x] 8.2 `attach_links_to_projects`: after date-anchoring, fill `node_links["milestones_taipei"]` from `disc.case_milestones[anchored_cid]` when present (merged project-level dict stays as the fallback; merged dict emission at project level unchanged)
- [x] 8.3 Regen + viewer verification: 254's three nodes each show their own approval dates; construction-chain provenance unchanged

## 9. 吉林段四小段603 exploration follow-ups (added 2026-08-31, D12 Amendment 3)

> Exploration: 603 family graph vs 相關連結 order mismatch (user screenshot); corpus audit
> found 91/564 `links.taipei` arrays unsorted (34 adjacent swaps = platform order drift);
> node 920's gazette 擬訂 vs platform 變更[已核准] is a gazette printing anomaly. Spec deltas
> updated: virtual-milestone-nodes (family-wide interleave + date-band adjacency),
> viewer-related-links (相關連結 ascending + gazette-anomaly review flag).

- [x] 9.1 Tests first: `attach_links_to_projects` emits `links.taipei` case_id-ascending; 相關連結 renders ascending; 603 family-wide interleave scenario; same-date virtual adjacency (date band before case_id); gazette-anomaly review flag
- [x] 9.2 Pipeline: sort `city_case_ids` ascending before emission in `attach_links_to_projects` (anchored assignments unaffected)
- [x] 9.3 Viewer: family-wide case_id interleave in the cluster/timeline build (replace cluster-local ordering per D12 Amendment 3); chain edges follow the same effective key
- [x] 9.4 Pipeline: gazette-stage-anomaly review flag (printed 擬訂 vs platform 變更+approved on the anchored case)
- [x] 9.5 Acceptance: 603 graph row order == 相關連結 order (09511210→…→11501016); node 920 flagged; suite green
## 10. Per-track stage derivation for combined-track nodes (added 2026-08-31, 507 exploration)

> Model: 事業計畫 (bonus floor area) and 權利變換 (builder/owner share) progress independently —
> both go through 擬訂/變更/變更(第N次) and can apply together or separately, so a combined
> node may carry TWO stage ordinals. Baseline: 中正區-臨沂段一小段-507 recno 1 (2026-08-11)
> 案名 `變更…事業計畫及變更(第二次)權利變換計畫案` renders `變更` only. Corpus: 69 combined
> 案名 fully parseable → **47 split-stage** (stage1 ≠ stage2) + 22 uniform; 454 other shapes
> unchanged. Spec deltas: data-cleansing (per-track derivation, ADDED),
> viewer-milestone-timeline (combined-track label render, ADDED).

- [x] 10.1 Tests first: split-stage derivation (507 fixture → stage_事業計畫=變更, stage_權利變換=變更(第二次)); uniform-ordinal keeps shared stage; single stage field unchanged
- [x] 10.2 Pipeline (cleanse derive): per-track stages `stage_事業計畫` / `stage_權利變換` parsed from the dual-ordinal 案名 (`[stage1]…事業計畫及[stage2]權利變換計畫案`), emitted as additive record fields
- [x] 10.3 Viewer (adapter): combined-track node label renders `stage1/stage2` when the ordinals differ (single form when uniform); 階段 column likewise
- [x] 10.4 Acceptance: 507 node 1 shows `變更/變更(第二次)` in graph + table; corpus count re-run (47 split-stage baseline)

