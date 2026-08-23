## 1. Taipei Search API (shipped — mark with verification notes)

- [x] 1.1 Implement `_post_taipei_api(url, params)` — POST form-encoded params to ashx endpoints, gzip magic-byte decompression, retry with exponential backoff on connection errors
- [x] 1.2 Implement `search_taipei_cases_api(section, parcel)` — split parcel into 母號/子號, POST `Get_updcase_list.ashx`, extract numeric case_ids from each entry's `details` URL, filter to `r_progress_detail.aspx` cases, dedupe
- [x] 1.3 Verify search returns expected cases for POC anchors: 玉泉段二小段40 → 4 numeric ids incl. 10110181; 河堤段四小段263-19 → 101208 / 10204032 / 10707031

## 2. Milestone API (shipped)

- [x] 2.1 Define `STAGE_FIELD_MAP` (30 field→label entries covering 計畫/權變/概要 tracks) and `TAIPEI_STAGE_API` constant
- [x] 2.2 Implement `fetch_taipei_milestones_api(case_id)` — POST case_id, parse JSON rows, map non-empty fields through `STAGE_FIELD_MAP`, normalise ISO datetimes (`2020-11-17T00:00:00` → `2020-11-17`)
- [x] 2.3 Verify milestone fetch: case 10110181 returns 29 milestones including 核定日期 2020/11/17, 計畫公聽會日期 2012/10/18

## 3. Discovery Flow Rewrite (shipped)

- [x] 3.1 Rewrite `discover_project_links`: Step 1 Taipei parcel search → city_case_ids; Step 2 per-case milestone fetch merged into one dict; Step 3 supplementary national portal (bulk index lookup → fallback view_id → view page 推動歷程)
- [x] 3.2 Status derivation from actual results: `resolved` = case_ids + milestones; `resolved_no_city` = case_ids only; `unresolved` otherwise
- [x] 3.3 Per-project checkpoint cache (`data/.link_cache/<project>/result.json`) with resume; caches cleared when discovery logic changes
- [x] 3.4 Gzip handling in `fetch_url` shared by all fetches (magic-byte detection + decompress before decode)

## 4. CLI & Data Fixes Folded In (shipped)

- [x] 4.1 Fix `--from-js` round trip: recognise already-ISO dates (`YYYY-MM-DD`) in node.date instead of re-parsing as ROC — dates no longer wiped on every load-from-JS run
- [x] 4.2 Regenerate dataset: 1,419/1,419 node dates preserved AND 697 projects carry links/milestones simultaneously
- [x] 4.3 Keep `--playwright` flag wiring `urtpe/taipei_playwright.py` as a manual fallback tool

## 5. Validation & Docs (done)

- [x] 5.1 Full run: `python -m urtpe.cli -o data --viewer viewer --links --from-js viewer/projects.data.js` → **697 resolved, 12 unresolved, 0 errors**
- [x] 5.2 Verified emitted data: 697 projects with `links.taipei`, 697 with `milestones_taipei`; sample 玉泉段二小段40 → twur view/771, 4 case_ids, 核定日期 2020/11/17
- [x] 5.3 Document endpoints, gotchas (details-URL id extraction, gzip), and results in `docs/final_results_json_api.md`
- [x] 5.4 Browser verification via wmux: 階段辦理過程 cards render 29-row and 26-row timelines for sample projects; expand/collapse works
