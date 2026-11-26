## 1. Tests first (write, run, watch each fail for the stated reason)

- [x] 1.1 `title_names_parcel` table in the new `tests/test_sweep_coverage.py` (all of group 1 lives there; the four older test files stay unchanged): 51-13 in the real view/239 title is true; 51-3, 51-17, 51-1 against a 51-13 title are false; candidate `1-13` and `13` against a `51-13地號` title are false; `51-13` against a `51-130地號` title is false; `之` and full-width digits are normalized; a title under another section is false; section preceded by 區, 市 or the start is true.
- [x] 1.2 `view_page_matches` countless cases: the view/239 title is accepted for 寶清段一小段 `51-13` with and without a candidate count; the view/170 (`51-3地號等1筆`) and view/204 (`51-17地號1筆`) titles are rejected for `51-13`; the view/239 title is rejected for candidates `51-3`, `51-17`, `51-1`, `1-13`; a countless title under another section is rejected; a countless title whose parcel is named only in the `<title>` is rejected (page text outside the title and meta tags must name it); a counted title with a different parcel is rejected; the view/1169 title (`561地號1筆(原5筆)`) keeps its old verdict.
- [x] 1.3 `search_portal` paging with a fake `fetch_url`: a full page 1 (10 ids) and a page 2 (8 ids) give 18 ids; a page 2 that repeats page 1 stops without a page 3; a page 1 of fewer than 10 ids makes exactly one request; the page cap stops a portal that always returns new ids; the list titles are read from single-quoted `title='…'` attributes; a plain-list fake and a titleless page give no titles. No test sleeps: patch `time.sleep` and assert it is called between pages only.
- [x] 1.4 Error truth for paging (the pattern of `tests/test_search_failure_truth.py`, whose cases stay unchanged): page 1 fails gives an error with no ids; page 2 fails after page 1 answered gives an error carrying the page-1 ids; `find_matching_view_with_outcome` on that error probes the page-1 ids, returns the match if one satisfies the strict rule, and returns an error (not a miss) if none does; a stop time that passes between pages behaves like a failed page.
- [x] 1.5 Probe order in `find_matching_view_with_outcome`: 18 results with the only title hit at position 15 and a matching page probes that one first and no other (limit 8); with no title hit the order and the unprobed count note are unchanged (the existing `_run_find` cases stay as they are); a title hit that fails the strict match is followed by the rest in order up to the limit; a cut-short list title does not change acceptance; `view_ids_checked` lists exactly the probed ids.
- [x] 1.6 Golden rows from the 2026-11-26 measurement, as fixtures built from the real titles: the five Class A candidates (366, 384, 412-2, 527, 560 of 南港段一小段) each reach their view id (81, 82, 93, 69, 38) under the default limit; 寶清段一小段 `51-13` reaches view/239 while `51-3` and `51-17` reach view/170 and view/204, never each other's.
- [x] 1.7 Run the new tests and confirm each fails on the current code for the stated reason (paging, ordering, countless title), not on a typo.

## 2. Pure logic (no I/O)

- [x] 2.1 Add `title_names_parcel(title, section, parcel)` with the rule of design D3.
- [x] 2.2 Add the countless fallback to `view_page_matches` with the rule of design D4; leave the body check and the strict path as they are.
- [x] 2.3 Add the probe-order function: title hits first, the rest after, each in returned order; no result is dropped.

## 3. Adapter (list reading and probing)

- [x] 3.1 Add `LIST_PAGE_SIZE_HINT`, `MAX_LIST_PAGES` and `LIST_PAGE_DELAY_S`; extend `search_portal` with the paging rules of design D6, the `titles` mapping of D5, the stop-time check between pages and the partial-error result of D7.
- [x] 3.2 Make `find_matching_view_with_outcome` read `titles`, apply the probe order, probe the ids of a partial search, and return an error rather than a miss when the search was partial and nothing matched.
- [x] 3.3 Print one note when the page cap ends a search, and keep the "unprobed results remain" note.

## 4. Verification

- [x] 4.1 Run `python -m pytest tests/test_fetch_remaining_portal.py tests/test_search_failure_truth.py tests/test_sweep_failure_truth.py tests/test_sweep_lock.py -q` and confirm the old cases pass unchanged.
- [x] 4.2 Run the full suite (`python -m pytest`) and compare the pass, skip and xfail counts with the baseline in `AGENTS.md`, adjusted for the new tests.
- [x] 4.3 Live read-only check, by a scratch script that calls `find_matching_view_with_outcome` directly with `max_probe` 8 and writes no ledger or cache: the five Class A tuples reach view 81, 82, 93, 69, 38, and 寶清 `51-13` reaches 239 while `51-3` and `51-17` reach 170 and 204. This check runs before any N4 override entry exists for those rows.
- [x] 4.4 Run `openspec validate twur-sweep-coverage --strict`.

## 5. Board and docs

- [x] 5.1 In `docs/inspections/optimization.md`: record N-D1 and N-D2 as decided on 2026-11-26 by the user's word; mark steps 7a and 7b as one change `twur-sweep-coverage` (the step ids stay); correct N1 (the list-title screen is required: paging alone fixes 0 of 5 under a limit of 8, paging with the screen fixes 5 of 5; the probes have no 1.5 s delay, the sweep waits 60 to 180 s between projects); write the live-check result.
- [ ] 5.2 Do not archive, commit or push. These wait for the user's word.
