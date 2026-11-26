## Context

See `proposal.md` for the measurements. The sweep is one script, `scripts/fetch_remaining_national_portal.py`, run nightly by the task `urtpe-nightly-sweep`. Three of its functions change: `search_portal`, `find_matching_view_with_outcome` and `view_page_matches`. The task runs the script from the working tree, so an uncommitted edit runs at the next 02:00 start.

Facts measured on 2026-11-26 (read-only, live):

- A twur list page holds **10** results. 南港段一小段 has 18: page 1 holds 10, page 2 holds 8, page 3 holds none.
- Each result's anchor carries its title in a `title='…'` attribute, in single quotes: `<a href='…/view/93' title='擬訂臺北市南港區南港段一小段412-2地號等48筆…'>`. Some titles end early (view/58 ends "…權利變換計", view/38 ends "…權利變換計畫").
- Screening the 18 titles for "section + parcel + 地號" gives exactly one hit for each of 366, 384, 412-2, 527, 560 and 520-2, all on page 2.
- `parse_name_id` already parses `…51-17地號1筆…` (count 1) and `…561地號1筆(原5筆)…` (count 1). It returns an empty section only for a title with no count at all, such as view/239: `…寶清段一小段51-13地號土地都市更新事業計畫案…`.
- The sweep's probe loop makes its requests back to back. Only `main`'s loop waits, 60 to 180 s between projects.
- Tests replace `search_portal` with fakes of the form `lambda *a, **k: ("miss", [ids])` and `lambda section: ("miss", vids)` (`tests/test_sweep_failure_truth.py`, `tests/test_fetch_remaining_portal.py`). They also replace `fetch_url` under the real `search_portal` (`tests/test_search_failure_truth.py`). Both must keep working unchanged.

## Goals / Non-Goals

**Goals:**

- The five Class A projects and the 寶清 51-13 project reach their view ids with the default probe limit of 8.
- No project that matches today stops matching.
- A search that did not read all its pages never records a 14-day negative.

**Non-Goals:**

- No change to the probe limit default, the TTL, the ledger schema, or `data/` and the payload.
- No count-drift rule (board item N3) and no override entry (board item N4).
- No parsing of a count from a list title.

## Decisions

**D1. One change for N-D1 and N-D2.** Both edit one title test and one spec. N1 needs the screen to reach page 2 under a limit of 8; N2 needs the same "section + whole parcel before 地號" test for a countless title. N1 also sends more sibling pages (51-3, 51-13, 51-17 are three units) to the matcher, so N2's sibling cases mean something only with N1 in place. Alternative considered: two changes. Rejected: both would edit the same helper and the same three requirements, and neither golden table would test the combination.

**D2. The screen reorders; it never filters.** Probe order is: title hits in returned order, then the rest in returned order, cut at the probe limit. Every result that was probed before is still probed unless a title hit displaces it past the limit, and a displaced result was a miss before only by position. Alternative: probe title hits only. Rejected: a title cut short or worded oddly would hide a real page, and a recorded miss would then claim more than was probed. With reordering, `view_ids_checked` in the ledger still lists exactly the pages that were fetched.

**D3. One helper, `title_names_parcel(title, section, parcel)`.** It normalizes the text like `view_page_matches` does (full-width digits to ASCII, `之` to `-`), and tests, with a plain regex: the section is directly preceded by `區`, `市` or the start; the parcel is directly preceded by neither a digit nor `-`; `地號` directly follows the parcel. The screen calls it on each list title. The countless fallback calls it on the view page's `<title>`. One definition keeps the screen and the decision from drifting apart. Alternative: a looser substring test for the screen. Rejected: a loose screen would put sibling pages first and spend the probe limit on them (parcel `1-13` inside `51-13`).

**D4. The countless fallback is narrow.** It runs only when `parse_name_id` returns an empty section on the normalized title. Then it accepts only when `title_names_parcel` holds on the title, and the text right after 地號 is not `等` or a digit. The body check that `view_page_matches` already runs first stays, but it runs on the whole page, so a page's own `<title>` satisfies it (found while writing the tests, 2026-11-26). The countless branch therefore adds its own check: the parcel must also appear in the page text outside `<title>` and the meta tags (the `og:title` meta repeats the title). view/239 names `51-13地號` 7 times there. The evidence is weak, because the page heading repeats the case name, but it is the condition N-D2 asked for and now it is a real one. A title that parses, with any count form, keeps today's rule exactly. Alternative: drop the parse and use only the helper. Rejected: it would loosen every counted title, including the count check that separates 444等7筆 from 444等17筆.

**D5. `search_portal` keeps its signature and return shape and does the paging.** It returns `(outcome, ids)`, where `ids` is a small `list` subclass with a `titles` mapping (view id to list title). A plain list means "no titles", and `find_matching_view_with_outcome` reads `getattr(ids, "titles", {})`. So every existing fake keeps working and no title means returned order. Alternatives: a new function returning pairs (rejected: `find_matching_view_with_outcome` would stop calling `search_portal`, and the existing fakes that inject an error or a miss would go quietly dead); an extra keyword argument (rejected: `lambda section:` fakes would raise `TypeError`).

**D6. Paging rules.** Page 1 is always read. Page `n+1` is read only when page `n` was full (10 or more results, `LIST_PAGE_SIZE_HINT`), added at least one new id, and fewer than `MAX_LIST_PAGES` (10) pages have been read. Between pages the script waits `LIST_PAGE_DELAY_S` (1.5 s) and checks the stop time. The full-page test saves a request for the common section with fewer than 10 results, and keeps existing tests fast. The "adds no new id" stop guards against a portal that repeats a page. Alternative: always read until an empty page. Rejected: one extra request per search, and a repeated-page portal would loop to the cap.

**D7. A partial search is an error unless something matched.** If page 1 failed, the outcome is an error with no ids, as today. If a later page fails, or the stop time passes between pages, `search_portal` returns an error with the ids read so far. `find_matching_view_with_outcome` then probes those ids, returns a match if one is found, and otherwise returns an error: the ledger spec already says a failed search is not a negative. Alternative: treat a failed page 2 as the end of the list. Rejected: it would record a 14-day negative for a result the sweep never saw.

## Risks / Trade-offs

- [Portal page size changes below 10] → The full-page test would stop at page 1. Mitigation: the constant is one line, and a run note prints when the page cap ends the reading.
- [A sibling whose title names the same parcel] → Whole-parcel boundaries and the golden table (51-3, 51-13, 51-17, 1-13, 13, 51-130). The strict match on the view page, not the list title, always decides.
- [More requests per search] → At most `MAX_LIST_PAGES` extra requests, and in practice one for a section with 11 to 20 results. The stop time already bounds the crawl, and the ledger writes each negative at once.
- [Screening spends the probe limit on title hits that fail] → Each hit is a distinct parcel, so at most a few exist. A hit that fails the match does not end the probing.
- [The script runs from the working tree] → Finish the edit and the tests in one session. Do not leave the file half-edited. A rollback is `git revert` of the commit; the ledger and caches need no repair, because the change adds no field.
