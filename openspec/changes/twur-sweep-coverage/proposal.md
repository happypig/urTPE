## Why

The nightly national-portal sweep (`scripts/fetch_remaining_national_portal.py`, task `urtpe-nightly-sweep`) links a project to its twur view page. Measured on 2026-11-26 (`docs/inspections/optimization.md`, Part IV), 6 of the 12 construction-stage projects with no view id are twur pages the sweep could have linked:

- **Five 南港段一小段 projects** (366, 384, 412-2, 527, 560). The section search returns 18 results over two list pages of 10 and 8. `search_portal` reads page 1 only, and the probe limit of 8 fetches the first 8 results in returned order. Their pages are results 11 to 18. Re-checked 2026-11-26: reading both pages and screening the list titles for the parcel finds each of the five with exactly one hit. Reading pages alone finds none.
- **One 寶清段一小段 project** (51-13, view/239). Its title has no `等N筆`. `parse_name_id` returns an empty section, so `view_page_matches` rejects the page, although the spec already says an absent count is decided by section and parcel alone.

A miss costs a 14-day ledger entry and a project with no national link in the Viewer. The 2026-11-14 ledger entries expire about 2026-11-28, so the next real crawl will repeat the same misses until this lands.

Board decisions N-D1 (read every result page) and N-D2 (a countless title may match by section and parcel) are one change, not two. Both use one title test, "section and the whole parcel before 地號": N1 uses it to screen the list, N2 uses it to decide a countless title. N1 also lets more sibling pages reach the matcher, so N2's sibling cases only mean something with N1 in place.

## What Changes

- `search_portal` reads list pages 1, 2, … until a page adds no new view id, with a hard page cap, a 1.5 s delay between pages (the probes themselves have none; the sweep waits 60 to 180 s between projects), and a stop-time check between pages. It keeps its `(outcome, view_ids)` return shape. It also records each result's list title, for screening only.
- `find_matching_view_with_outcome` orders its probes: results whose list title names the candidate's section and whole parcel come first, then the rest in returned order. It still probes at most the probe limit (default 8) and still stops at the first strict match. No result that was probed before is dropped, so no project that matches today can stop matching.
- `view_page_matches` accepts a view page whose `<title>` has no `等N筆` form, when the title names the section and the whole parcel before 地號 and the page body names the parcel. A title that parses keeps today's strict rule.
- A later list page that fails after earlier pages worked is an error, not a miss, unless a match was already found.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fetch-remaining-portal`: "Targeted portal search by land core" (the search reads every list page; "returned order" becomes screened order), "Strict view-page identity match" (a countless title can match; a whole-parcel boundary rule), "Configurable view-probe breadth" (the limit counts probes after screening; page-read bound).

## Impact

- Code: `scripts/fetch_remaining_national_portal.py` (`search_portal`, `find_matching_view_with_outcome`, `view_page_matches`, one new title helper). No change to `urtpe/`, the ledger format, `data/` or the payload.
- Tests: new cases in `tests/test_fetch_remaining_portal.py` and `tests/test_search_failure_truth.py`; the existing failure-truth and sweep tests stay unchanged and green.
- Runtime: one extra list-page request per candidate whose search has 10 or more results, plus a 1.5 s wait. The stop time already bounds the crawl.
- Not changed: the 14-day TTL, the probe-limit default of 8, the no-match ledger schema, `twur_overrides.json` (board item N4), and the Class B count-drift rows (board item N3).
- Gate: the change is not archived, committed or pushed without the user's separate word.
