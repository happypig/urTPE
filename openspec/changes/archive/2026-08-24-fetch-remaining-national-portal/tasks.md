> POC: This is an operational script reusing proven primitives (fetch_url, extract_* from urtpe.links). The core behavior (search→fetch→parse→cache) was already validated on 10 PDF-last-records + 109 index matches. No new domain logic to POC.

## 1. Test Writing (TDD Gate)

- [x] 1.1 Create test module `tests/test_fetch_remaining_portal.py` with pytest fixtures
- [x] 1.2 Test `search_portal` returns correct view_ids for mocked HTML (single match, multi-match, zero match)
- [x] 1.3 Test `fetch_and_parse_view` extracts milestones from live-type `type4_table` and ignores non-milestone tables
- [x] 1.4 Test `update_project_cache` merges twur_view_id, twur_url, national_milestones correctly (preserves existing fields, new wins on overlap)
- [x] 1.5 Test candidate prioritization sorts by 現況 date descending
- [x] 1.6 Test deadline logic stops at 06:30 and triggers regeneration
- [x] 1.7 Test failure logging writes JSON Lines with correct schema
- [x] 1.7 Test end-to-end: dry-run on 3 sample projects produces expected cache updates

## 2. Domain / Use-Case Tests (User-Visible Requirements)

- [x] 2.1 Acceptance test: script run on 3 known projects produces twur links + national milestones visible in viewer
- [x] 2.2 Acceptance test: 使用核發日期 from portal appears in 國 card in viewer
- [x] 2.3 Acceptance test: projects without portal match skip gracefully (no crash, logged)
- [x] 2.4 Acceptance test: viewer regeneration produces valid projects.data.js with new twur/milestones_national

## 3. Adapter / Infrastructure Tests

- [x] 3.1 Test `search_portal` parses `/view/(\d+)` from real portal HTML (fixture)
- [x] 3.2 Test `fetch_and_parse_view` handles both legacy (hidden) and current (visible type4_table) markup
- [x] 3.5 Test cache update preserves existing fields (city_case_ids, taipei_milestones, status, error)
- [x] 3.6 Test deadline check at 06:30 stops loop and triggers regeneration
- [x] 3.6 Test failure logging writes valid JSON Lines to fetch_failures.json

## 4. Script Scaffold & Imports

- [x] 4.1 Create `scripts/fetch_remaining_national_portal.py` with shebang, encoding, and imports
- [x] 4.2 Import from `urtpe.links`: `fetch_url`, `extract_tuidui_history_from_view`, `extract_case_ids_from_view`, `extract_view_id_from_search`, `SEARCH_URL`, `BROWSER_HEADERS`, `_project_cache_dir`
- [x] 4.3 Import stdlib: `json`, `random`, `sys`, `time`, `datetime`, `pathlib`, `urllib.parse`, `urllib.request`
- [x] 4.4 Add `sys.path.insert(0, repo_root)` for local imports

## 5. Candidate Selection & Prioritization

- [x] 5.1 Load `viewer/projects.data.js` and parse `window.PROJECTS.projects`
- [x] 5.2 Filter projects where `links.twur` is empty/falsy
- [x] 5.3 For each candidate, extract anchor 現況 node (is_current=True) and its ISO date
- [x] 5.4 Extract section and first parcel from anchor node for search keywords
- [x] 5.5 Sort candidates by 現況 date descending (newest first)
- [x] 5.6 Log candidate count and top 5 for sanity check

## 6. Portal Search & View Fetch

- [x] 6.1 Implement `search_portal(section, parcel)` — builds `?title={section}{parcel}` URL, fetches, extracts view_ids via regex `/view/(\d+)`
- [x] 6.2 Implement `fetch_and_parse_view(view_id)` — calls `fetch_url(view_url)`, extracts milestones via `extract_tuidui_history_from_view`, city ids via `extract_case_ids_from_view`
- [x] 6.3 Handle empty/no match cases gracefully (return empty dicts)
- [x] 6.4 Use existing `fetch_url` (3 retries, exponential backoff) — no custom retry wrapper needed

## 7. Cache Update Logic

- [x] 7.1 Implement `update_project_cache(project_id, view_id, milestones)` using `_project_cache_dir`
- [x] 7.2 Read existing `result.json`, merge `twur_view_id`, `twur_url`, `national_milestones` (new wins on overlap)
- [x] 7.3 Write updated JSON with `ensure_ascii=False, indent=2`
- [x] 7.4 Handle missing cache dir gracefully (skip with log)

## 7. Main Loop with Politeness & Deadline

- [x] 8.1 Define `DEADLINE = time(6, 30)` and check at loop start
- [x] 8.2 For each candidate:
  - Break if current time >= 06:30
  - Build search keyword from section + first parcel (handle sub-parcel e.g., "688" vs "688-1")
  - Call `search_portal`; if multiple view_ids, pick first and log warning
  - For each view_id (try up to 3): call `fetch_and_parse_view`, break on first success
  - If milestones or view_id found: call `update_project_cache`
  - Log outcome (success/empty/failed) with project_id, view_id, milestone count
  - On failure: append to `data/.link_cache/fetch_failures.json` with timestamp, error
- [x] 8.3 Sleep `random.uniform(180, 300)` between projects (not after last)
- [x] 8.4 On 06:30 deadline: break loop, log "deadline reached", proceed to regeneration

## 8. Failure Logging

- [x] 9.1 Open `data/.link_cache/fetch_failures.json` in append mode (JSON Lines)
- [x] 9.2 On any fetch failure (after retries): append `{"project_id", "view_id", "error", "timestamp": iso_now}`
- [x] 9.3 Also print to stderr for real-time visibility

## 9. Viewer Regeneration

- [x] 10.1 After loop ends (completion or deadline), run:
  `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`
- [x] 10.2 Wait for subprocess completion, check return code
- [x] 10.3 Log regeneration success/failure

## 9. CLI Entry & Config

- [x] 11.1 Add `if __name__ == "__main__":` block calling `main()`
- [x] 11.2 Add `DEADLINE_HOUR = 6`, `DEADLINE_MINUTE = 30` constants at top
- [x] 11.3 Add `--dry-run` argument for optional dry-run mode (optional, nice-to-have)

## 10. Testing & Validation (Verify TDD Gate Passed)

- [x] 12.1 Run pytest on `tests/test_fetch_remaining_portal.py` — all tests pass
- [x] 12.2 Run script with `--dry-run` on first 3 candidates — verify search + fetch + cache update
- [x] 12.3 Verify cache files updated: `twur_view_id`, `twur_url`, `national_milestones` present
- [x] 12.4 Run full pipeline once (short test run, early exit) to confirm viewer regeneration works
- [x] 12.5 Verify regenerated `viewer/projects.data.js` has new `twur` URLs and `milestones_national` for test projects

## 10. Documentation & Cleanup

- [x] 13.1 Add docstring to script explaining purpose, usage, and time-bound behavior
- [x] 13.2 Remove any temporary/debug scripts created during development
- [x] 13.3 Verify `pytest` still passes (no regressions in `urtpe/links.py` imports)