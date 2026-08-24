## Context

Current state: 591 of 709 projects lack `twur` links and `milestones_national`. The bulk portal index crawl only captured ~110 recent entries before WAF blocked it. The existing per-project discovery (`discover_project_links`) already supports looking up view_ids via portal index, but the index is incomplete and the bulk crawl is unreliable. A targeted, time-bounded script that searches per-project via `?title=` and fetches view pages directly is the pragmatic path — reusing existing `fetch_url`, `extract_tuidui_history_from_view`, `extract_case_ids_from_view`, and `extract_view_id_from_search` primitives from `urtpe/links.py`.

## Goals / Non-Goals

**Goals:**
- Fetch twur links and 推導歷程 milestones for as many of the 591 missing projects as possible within a 06:30 deadline
- Prioritize recent projects first to maximize 使用核發日期 hits
- Polite sequential execution with 3-5 min intervals, retry logic, and failure logging
- Auto-regenerate viewer on completion
- Zero changes to existing discovery pipeline (`urtpe/links.py`, `urtpe/cli.py`)

**Non-Goals:**
- Fixing the bulk portal index crawl (WAF issue)
- Modifying the core `discover_project_links` or `build_portal_index` logic
- Parallel workers (WAF risk)
- Changing viewer schema or `projects.data.js` format
- Full re-discovery of Taipei case_ids (already done)

## Decisions

### 1. Standalone script, not CLI subcommand

**Decision**: Create `scripts/fetch_remaining_national_portal.py` as an executable script, not a new `--fetch-portal` flag in `cli.py`.

**Rationale**: Keeps the core CLI clean; the script is operational/tooling, not a pipeline stage. It reads `viewer/projects.data.js` directly and writes caches, then invokes the existing `--from-js --links` flow for regeneration.

**Alternative considered**: Add `--fetch-portal` to `cli.py`. Rejected — adds complexity to main entry point, mixes operational tooling with pipeline stages.

### 2. Sequential with 180-300s random interval

**Decision**: Single-threaded loop with `random.uniform(180, 300)` sleep between projects.

**Rationale**: The WAF killed the bulk crawl at ~110 requests. A deterministic or short interval would trigger the same block. Random 3-5 min mimics human browsing and distributes load unpredictably.

**Alternative considered**: Fixed 5 min interval. Rejected — predictable patterns are easier for WAF to fingerprint. Considered 10 min fixed; rejected — too slow, reduces throughput.

### 3. Retry with exponential backoff (2s, 4s, 8s), max 3 attempts

**Decision**: Reuse `fetch_url` which already implements 3 retries with 2s/4s/8s backoff on `ConnectionResetError`, `TimeoutError`, `URLError`, `OSError`.

**Rationale**: `fetch_url` in `urtpe/links.py` already implements this for all HTTP calls. The script just calls it; no new retry logic needed.

### 3. Candidate prioritization: recent 現況 date descending

**Decision**: Sort projects without `twur` by their anchor 現況 date (ISO date string) descending before the loop.

**Rationale**: Recent projects are more likely to be in the portal (even if not in the index) and more likely to have 使用核發日期 if they completed construction. The 10 PDF-last-records test showed 8/10 had 使用核發.

**Alternative considered**: Random shuffle. Rejected — wastes quota on unlikely-to-match old projects.

### 4. Time-bound: stop at 06:30

**Decision**: Check `datetime.now().time() >= time(6, 30)` at loop start; if past deadline, break and regenerate.

**Rationale**: Hard deadline ensures script exits before morning operations. In-progress fetch completes; remaining projects skipped.

### 4. Output: cache update + viewer regeneration

**Decision**: On each success, update `data/.link_cache/<project>/result.json` with `twur_view_id`, `twur_url`, `national_milestones`. On loop end (completion or timeout), invoke `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`.

**Rationale**: Regeneration via `--from-js --links` reads updated caches and emits fresh `viewer/projects.data.js` — same as existing workflow. No new emit logic.

### 5. Failure logging: JSON Lines + stderr

**Decision**: Append each failure to `data/.link_cache/fetch_failures.json` as a JSON object with `project_id`, `view_id`, `error`, `timestamp` (ISO), plus print to stderr.

**Rationale**: Structured log enables post-run analysis; stderr provides real-time visibility.

### 6. Isolated from core pipeline

**Decision**: Script imports `fetch_url`, `extract_tuidui_history_from_view`, `extract_case_ids_from_view`, `SEARCH_URL`, `BROWSER_HEADERS`, `_project_cache_dir` from `urtpe.links`. Does NOT import or call `discover_project_links`, `build_portal_index`, `attach_links_to_projects`, or `LinksDiscovery`.

**Rationale**: Guarantees zero impact on production pipeline. Caches written by this script are consumed by the next `--from-js --links` run exactly like any other discovery run.

### 6. Project ID safe cache path

**Decision**: Reuse `_project_cache_dir` from `urtpe.links` (sanitizes project_id with `re.sub(r"[^\w\-]", "_", project_id)`).

**Rationale**: Consistent with existing cache structure; avoids path traversal or encoding issues.

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WAF blocks even with 3-5 min intervals | Medium | Random interval + exponential backoff + graceful skip; log and continue |
| Search returns no view_id for old projects | High (older projects may not be on portal) | Log "no match", skip; expected for ~30-50% |
| View page markup changes break parser | Low | Parser handles both legacy (hidden) and current (visible) tables; log HTML snippet on parse failure |
| 06:30 deadline hits mid-fetch | Low | Loop checks deadline at top of loop; in-progress fetch completes before exit |
| Script crashes mid-run (OOM, SIGKILL) | Very low | Caches persist; re-run resumes from next project (idempotent) |
| Viewer regeneration fails | Low | CLI returns non-zero; script exits with error; caches already updated, manual re-run possible |

## Migration Plan

1. Run script: `python scripts/fetch_remaining_national_portal.py`
2. Script fetches until 06:30, updates caches, regenerates viewer
3. Verify: open `viewer/index.html` in browser, check 國 cards for new projects
4. Rollback (if needed): delete `data/.link_cache/<project>/view.html` and restore `result.json` from git, then re-run viewer regeneration

## Open Questions

None — all design decisions resolved.