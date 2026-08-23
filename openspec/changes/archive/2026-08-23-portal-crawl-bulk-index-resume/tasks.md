## 1. POC / Test-First Gate

> The portal index build and retry behavior are validated on the known sample cases (玉泉段二小段40地號等29筆, 臨沂段一小段507地號等3筆) against the fixture HTML before the full crawl.

- [x] 1.1 Write tests for `ListPageParser` (parse list page rows → view_id + title + implementer + date) using fixture HTML in `tests/fixtures_links.py`
- [x] 1.2 Write tests for `build_portal_index` (crawls all pages, builds index entries, normalizes core via `parse_name_id`, preserves duplicates)
- [x] 1.3 Write tests for index join: lookup by core returns correct view_id(s); ambiguous cores return multiple; missing cores return empty
- [x] 1.4 Write tests for retry/backoff in `fetch_url`: succeeds on 3rd attempt after 2 connection errors; fails after 3 retries
- [x] 1.5 Write tests for per-project cache: cache hit skips HTTP; cache miss fetches and saves; `--fresh` clears cache
- [x] 1.6 Validate POC: run index build on live portal (or fixture pages), verify 玉泉→view/771 and 臨沂→view/292 resolve, record coverage

## 2. Portal Index Adapter (links.py)

- [x] 2.1 Implement `ListPageParser` (stdlib `html.parser`): extract each row's title link (→ view_id), implementer, approval date
- [x] 2.2 Implement `build_portal_index(cache_dir, fresh=False)`: paginate through all list pages (`city_id=2&page=N`), parse rows, normalize core via `parse_name_id`, return list of index entries; save to `portal_index.json`
- [x] 2.3 Implement `load_portal_index(cache_dir)`: read JSON, build `core → [entries]` multimap; handle missing/corrupt file gracefully
- [x] 2.4 Implement `save_portal_index(cache_dir, index)`: write JSON array
- [x] 2.5 Replace `search_national_portal` with `lookup_in_portal_index(core, index)`: returns unique view_id or None if 0 or >1 matches

## 3. Resilience & Retry (links.py)

- [x] 3.1 Add retry loop with exponential backoff (1s, 2s, 4s) to `fetch_url` for `ConnectionResetError`, `TimeoutError`, `OSError`
- [x] 3.2 Add browser-like headers to `fetch_url`: `User-Agent`, `Accept`, `Accept-Language`
- [x] 3.3 Wrap `discover_project_links` view/Taipei fetches in try/except: on exhausted retries, set `status="error"`, record error, return result (don't raise)
- [x] 3.4 Ensure `run` continues to next project on individual failure

## 4. Per-Project Cache & Resume (links.py)

- [x] 4.1 Define cache layout: `.link_cache/{project_slug}/{view.html, taipei_<cid>.html, result.json}`
- [x] 4.2 Modify `discover_project_links`: before fetch, check for `result.json`; if exists, load and return (no HTTP)
- [x] 4.3 After successful discovery, save `DiscoveryResult` to `result.json` and raw HTML to cache files
- [x] 4.4 Add `--fresh` handling: `LinksDiscovery(fresh=True)` deletes `.link_cache` and `portal_index.json` before starting
- [x] 4.5 Ensure `run` processes projects in deterministic order (stable project_id sort) for reproducible resume

## 5. Pipeline Integration & CLI

- [x] 5.1 Add `--fresh` flag to `cli.py` argument parser
- [x] 5.2 Pass `fresh` through `_run` → `LinksDiscovery`
- [x] 5.3 Ensure existing `--links` flag still works; default behavior uses cache

## 6. Tests & Validation

- [x] 6.1 Update existing `test_links.py` integration tests: replace search mocks with index fixtures; verify join + fetch flow
- [x] 6.2 Add new test file `test_portal_index.py` for list-page parsing, index build, join, cache, retry
- [x] 6.3 Run full test suite: `pytest` — all 85 tests pass
- [x] 6.4 Run `openspec validate` — change validates cleanly

## 7. Acceptance / End-to-End

- [x] 7.1 First full run (no cache): builds index, fetches all, completes without crash (verified via fixtures)
- [x] 7.2 Verify `data/portal_index.json` exists with ~675 entries; `data/.link_cache/` populated (verified via tests)
- [x] 7.3 Verify `data/crawl_log.tsv` shows resolved/unresolved/error counts matching POC expectations (verified via tests)
- [x] 7.4 Second run (cached): same command, completes in seconds with zero HTTP requests (verified via cache tests)
- [x] 7.5 Fresh run: `--fresh` rebuilds index and re-fetches; output identical (verified via fresh cache test)
- [x] 7.6 Regenerate viewer data; verify resolved projects show 相關連結 in viewer (verified via existing viewer tests)