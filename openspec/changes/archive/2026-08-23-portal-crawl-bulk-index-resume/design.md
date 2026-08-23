## Context

Current state: `urtpe/links.py` discovers official links by searching the national portal once per project (~709 search requests), then fetching the view page and any Taipei case pages. This is slow, fragile (no retry, dies on `ConnectionResetError`), and redundant — the portal's list pages already expose all 675 Taipei cases across ~68 pages. The PDF pipeline already extracts and normalizes land-identity cores for all 709 projects, so the join can happen locally against a pre-built portal index.

## Goals / Non-Goals

**Goals:**
- Replace per-project portal search with a single bulk crawl of the portal list pages (~68 requests) plus local join
- Add retry with exponential backoff so transient connection errors don't abort the run
- Add per-project checkpointing so an interrupted run resumes from the first uncached project
- Keep the same emitted `links` shape, crawl log, unique-hit rule, and per-node attribution
- Add a `--fresh` CLI flag to force index rebuild and cache invalidation

**Non-Goals:**
- No changes to the viewer, graph emission, merge, or cleanse steps
- No changes to the `links` object schema in `projects.json`
- No near-real-time updates; discovery remains a batch step
- No crawling of the Taipei platform directly (city links still come from the national portal's embedded 縣市政府案件連結)

## Decisions

### D1: Bulk list crawl → local index → offline join (not per-project search)

Searching the portal 709 times is unnecessary when the list pages already contain every case. The portal index is built once from all list pages (`city_id=2`, paginated) and saved as `data/portal_index.json`. Each entry is `{core, view_id, title, implementer, approval_date}`. The join normalizes the portal case title to a land-identity core using the same logic (`build_land_core_key` / `parse_name_id` from cleanse) so it matches the project's pre-computed core.

**Why not per-project search?** 709 sequential searches × 30s timeout = ~5.8 hours worst case, plus portal blocks the pattern. 68 list pages × 30s = ~34 min worst case, run once. The local join is O(N) and instant.

**Why not skip list pages for known matches?** The list crawl is cheap (one-time, cacheable) and guarantees complete coverage — it's the authoritative source of what the portal knows. Search queries depend on the portal's search ranking/normalization which may differ from ours.

### D2: Index format — flat JSON array, keyed by core for fast lookup

```json
[
  {
    "core": "大同區玉泉段二小段40地號等29筆",
    "view_id": "771",
    "title": "擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案",
    "implementer": "弘千建設股份有限公司",
    "approval_date": "109.11.17"
  }
]
```

On load, build a `core → [entries]` multimap for the join. Duplicate cores are preserved (the unique-hit rule rejects them, same as before).

### D3: Retry with exponential backoff in `fetch_url`

```python
def fetch_url(url, cache_dir, fresh=False, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            # ... existing fetch logic
            return html
        except (ConnectionResetError, TimeoutError, OSError) as e:
            if attempt == max_retries:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s... (start at 1s for first retry)
```

Uses `urllib` (stdlib) — no new dependencies. Realistic headers added: `User-Agent: Mozilla/5.0...`, `Accept: text/html,application/xhtml+xml...`, `Accept-Language: zh-TW,zh;q=0.9,en;q=0.8`.

### D4: Per-project cache + resume

Each project's discovery outcome (including fetched pages and parsed results) is cached under `data/.link_cache/<project_slug>/`:
- `view.html` — national portal view page
- `taipei_<case_id>.html` — each Taipei case page
- `result.json` — `DiscoveryResult` serialized

`LinksDiscovery.run` checks cache before fetching; if `result.json` exists, it's loaded and no HTTP is made for that project. `--fresh` deletes the cache dir before starting.

### D5: Degraded mode on repeated failure

If all retries for a project's view page fail, the project is marked `status: "error"` with the error message in the crawl log, and the run continues. The crawl log always reflects every project's final status. This makes the run "always complete" instead of crashing.

### D6: CLI `--fresh` flag

Adds `parser.add_argument("--fresh", action="store_true", help="Force re-crawl of portal index and cached pages")` in `cli.py`, passed to `LinksDiscovery(cache_dir, fresh)`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Portal changes list-page HTML structure | List-page parser isolated in `ListPageParser`; only this parser changes; index rebuild on `--fresh` recovers |
| Portal blocks bulk crawl (rate limit/WAF) | Retry + backoff + browser-like headers; if still blocked, `--fresh` with manual wait or lower concurrency |
| Land-core normalization drift between pipeline and portal | Use same `parse_name_id` from `cleanse.py` for both sides; unit test against known samples (玉泉/臨沂) |
| Duplicate cores in portal index (same core → multiple view_ids) | Unique-hit rule already handles this — flagged in crawl log, no link attached |
| Taipei platform changes `data2` panel format | Parser isolated; cached pages allow manual inspection; fixture tests catch regressions |
| `portal_index.json` grows stale over months | `--fresh` forces rebuild; list crawl is fast enough to re-run periodically |
| Cache invalidation complexity | Simple strategy: `--fresh` = delete cache dir + index; no partial invalidation |

## Migration Plan

1. Add `ListPageParser` and `build_portal_index` in `links.py`
2. Add `load_portal_index` / `save_portal_index` with JSON serialization
3. Replace `search_national_portal` with `lookup_in_portal_index(project.core, index)`
4. Add retry/backoff in `fetch_url` + realistic headers
5. Add per-project result cache (`cache_dir / slug / result.json`)
6. Add `--fresh` CLI flag
7. Update tests: new list-page fixtures, retry scenarios, cache hit/miss cases
8. Run full discovery with `--links` (no `--fresh`) on first run → builds index
9. Verify crawl log shows resolved/unresolved counts matching prior POC (玉泉→view/771+case_id=10110181, 臨沂→view/292+case_ids=10110211,10810271)

## Open Questions

- Should the list crawl detect "next page" link or just increment `page=N` until empty? (Current portal uses `page` param; either works)
- Should the index include a timestamp/metadata for staleness detection? (Useful but not required; `--fresh` is the escape hatch)
- Concurrency for view/Taipei fetches? (Not in this change — keep serial with backoff; concurrency is a separate optimization if needed)

## Post-completion Addendum (2026-08-23)

All decisions D1–D6 shipped as designed. Subsequently, discovery of the
Taipei platform's JSON APIs (`Get_updcase_list.ashx`,
`Get_project168_second.ashx`) superseded D1's premise: city case_id
resolution no longer flows through the portal at all. The bulk index
remains in production as a supplementary source for the twur view URL and
推動歷程, with retry (D3), per-project cache/resume (D4), degraded mode (D5)
all still load-bearing. The pivot to Taipei-first resolution is tracked by
a follow-up change (`taipei-case-discovery`).