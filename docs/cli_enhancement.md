# CLI Enhancement — Portal Discovery Consolidation (design)

*Forward design doc for §12 #3 of `facts_2_portals.md` ("Portal discovery consolidation — library-first", decided; full sync-model context in `docs/sync_architecture.md` §4). Retire this file once the OpenSpec change lands and the spec takes over.*

---

## 1. Problem — capability spread across one-off scripts

Every portal capability was built where it was first needed; each 2026-08 incident (§17/§18/§6.10 of the reference + operations log) traced back to that split:

| Capability | Lives in | Reusable? |
|---|---|---|
| Taipei-first discovery (search + per-case timelines) | `urtpe/links.py` | yes |
| National targeted sweep (search → strict match → cache write) | `scripts/fetch_remaining_national_portal.py` | script-only |
| Strict matcher `view_page_matches` / `find_matching_view` | fetch script | script-only |
| No-match ledger (TTL, clear-on-match, run-start sweep) | fetch script | script-only |
| Deadline windows | `scripts/run_sweep_until.py` | wrapper |
| Name harvest (`candidate_names`) | `scripts/harvest_case_names.py` | script-only |
| Offline `view.html` recovery (twur + milestones) | `scripts/backfill_twur_from_view_html_20260829.py` | one-off |
| 相關連結 attach + per-case resolve | `scripts/resolve_via_view_links_20260829.py` | one-off |
| CASE_NAME backfill (`top.ashx`) | `scripts/backfill_names_from_top_api_20260829.py` | one-off |
| `--from-js` loader | duplicated in `run_links_from_js.py` vs `urtpe/cli.py` | drift risk |

Observed costs (evidence in `portal_operations_log.md`):

- **§18 + §6.10 wipes** — regen discarded what only scripts knew (targeted mappings lived only in deleted `result.json`); two full coverage collapses (292→109, 581→117).
- **Merge-semantics drift** — each one-off script hand-rolls its own field merge; one wrote a wrong key (`milestones_taipei`) and the type-swallowing loader silently re-crawled over the edit (§6.10 hazard).
- **Untelemetered runs** — a pasted-command sweep executed with no log redirect and was nearly invisible.

## 2. Target design — library-first, opt-in CLI

**Layer 1 — `urtpe/links.py` owns every capability** as importable functions (no I/O policy decisions inside; callers pass cache dir/flags):

```
search_portal() / view_page_matches() / find_matching_view()   # from fetch script
update_project_cache() / ledger API (load/save/filter/sweep/clear)
harvest_case_names()            # from harvest_case_names.py
backfill_from_view_html()       # offline view.html recovery
attach_view_links()             # 相關連結 per-case resolve
fetch_case_name_from_top()      # top.ashx CASE_NAME
```

**Layer 2 — scripts become thin wrappers** (arg parsing + interval/deadline loops only). `fetch_remaining_national_portal.py` keeps its unattended overnight role with the auto-regen hand-off.

**Layer 3 — one CLI surface** (`urtpe.cli`), all opt-in, composable:

```
python -m urtpe.cli --from-js viewer/projects.data.js --viewer viewer \
    --links \                     # Taipei-first discovery (existing)
    --links-targeted \            # national sweep (fetch_remaining)
    --harvest-names \             # candidate_names harvest
    --backfill-viewhtml \         # offline view.html recovery
    --resolve-view-links \        # 相關連結 attach
    --reprobe-days 14 --max-probe 8 --deadline 22:30 --dry-run --max-projects N
```

`--from-js` loading deduplicated into `urtpe.cli._load_projects_from_js` (scripts import it).

## 3. Incident lessons → guardrails as code

| Incident | Convention today | Code in the consolidation |
|---|---|---|
| §18/§6.10 coverage wipes | "back up + diff" prose rules (§18 rule 1/3) | **Coverage guard**: snapshot twur / national_milestones / 使用核發 / resolved before & after any write mode; any decrease aborts (§12 #1, build first) |
| §17 concurrency | "single-writer rule" prose (§17) | **Lockfile** on `data/.link_cache` — second writer refuses to start; the fetch script's deadline regen is the sanctioned hand-off |
| §18 mapping loss | "fold into index at write time" (§18 rule 2) | `update_project_cache` writes land-core→view_id into `portal_index.json` (or dedicated store) in the same transaction as `result.json` |
| Merge drift / poison keys | hand-rolled merges in each script | **One merge path** (field-level, monotonic, like the 08-29 merge-backs); writes validated against `DiscoveryResult(**data)`; loader logs instead of silently swallowing `TypeError` (links.py:986) |
| Ledger fragmentation | ledger lives in the fetch script only | Shared by every mode — no operation re-probes what another already rejected |

## 4. Scope & ordering (ties to §12 priorities)

1. **Coverage guard first** (§12 #1) — protects the consolidation's own bulk passes; small wrapper, no spec delta.
2. **Chimera emit-fix** (§12 #2) — independent, ready, no network; rides the same `graph.py` emission layer.
3. **This consolidation** (§12 #3, this doc) — needs an OpenSpec change (modifies `official-link-discovery`).
4. **Count normalization** (§12 #4) — rides with [3] (the matcher moves into links.py); enables the re-sweep over ledger negatives (~20-project recovery headroom to the 581 peak).
5. **Sync model** (§12 #5, `docs/sync_architecture.md`) — consumes [3]'s per-project functions as the orchestrator's portal lane.

## 5. Acceptance sketch (for the OpenSpec change)

- `--links-targeted` reproduces the fetch script's behavior 1:1 on a `--dry-run` diff of candidate queues.
- Coverage guard aborts a synthetic destructive job (test injects a cache wipe) and alerts.
- A cache written by any mode round-trips `DiscoveryResult(**data)` (poison-key test).
- Ledger is shared state across modes: a no-match recorded by the sweep suppresses `--backfill-viewhtml` re-probing of the same view_ids where applicable.
- All dated one-off scripts in `scripts/` either import from `urtpe.links` or are retired; no local re-implementations remain.
