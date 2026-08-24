# Tasks — add-taipei-implementation-data

> Data-gathering POC equivalent already completed and captured: live probes of
> third/fourth.ashx for 6 projects (`scripts/probe_third_6projects.py`, facts
> §10.4–10.5) and the 86-field DOM label map from r_progress_detail.aspx —
> findings are folded into the spec/design; no further POC required.

## 1. Tests first (write before any implementation; all must be checked before implementation tasks are marked complete)

- [x] 1.1 Fixtures: sample third.ashx payload (completed case with 開工/使照 values, facts §10.5 case-141 values), all-empty payload, fourth.ashx payload
- [x] 1.2 Label-map test: lock STAGE_FIELD_MAP round-2 labels (comm_hold_date → 召開審議會日期, comm_hold_date2 → 權變召開審議會日期, outline_ok_date → 概要核准日期, jud_ok_date0 → 概要審議會通過日期, comm_hold_date0 → 概要召開審議會日期)
- [x] 1.3 Pure selection-logic tests (domain): best-populated payload pick, provenance case_id, conflict → review flag, no field-merging
- [x] 1.4 Emission acceptance tests (user-visible): project with completed case emits 開工日期/使照核發日期 milestones + `implementation`/`rewards` objects + `schema_version` 2; project without payloads emits none and stays v1-consumer-valid
- [x] 1.5 Viewer acceptance test: 執行階段/獎勵資料 cards render when objects exist, absent otherwise
- [x] 1.6 End-to-end discovery test (fixture-served): second+third+fourth fetched per case → cache round-trip → emitted graph, with one third-fetch failure recorded without aborting

## 2. Prerequisite map fix (makes 1.2 pass)

- [x] 2.1 Apply STAGE_FIELD_MAP round-2 corrections in `urtpe/links.py` per 1.2

## 3. Adapters: fetch + cache (I/O)

- [x] 3.1 Add `TAIPEI_THIRD_API` / `TAIPEI_FOURTH_API` constants
- [x] 3.2 Add `fetch_taipei_implementation_api(case_id)` / `fetch_taipei_rewards_api(case_id)` (empty dict on empty/malformed body, retry/backoff like existing fetches)
- [x] 3.3 Add per-case `implementation` / `rewards` dict fields to `DiscoveryResult` (default empty; old caches load with fields absent)
- [x] 3.4 Call both fetches per case in `discover_project_links` after the second.ashx fetch (existing `delay`), record per-case failures without aborting
- [x] 3.5 Verify `save_project_cache`/`load_project_cache` round-trip of the new fields

## 4. Core pipeline logic (pure, per D5/D9)

- [x] 4.1 Implement payload-selection function (best-populated payload, provenance case_id, review flag on conflicting values) — driven by 1.3
- [x] 4.2 Implement milestone extraction (開工日期 / 使照核發日期 / 成果報備日期 from the selected payload) — driven by 1.4

## 5. Emission + viewer (output adapters)

- [x] 5.1 Wire selection into emission: optional `implementation`/`rewards` project objects, milestone additions, `schema_version` 1 → 2 in both output files
- [x] 5.2 Viewer: add the captured field→label table to `viewer/app.js`; render 執行階段 / 獎勵資料 cards (only when populated), styled like milestone cards (`app.css`)
- [x] 5.3 Confirm 開工日期 / 使照核發日期 render in the existing milestone card without special handling

## 6. Suite + bulk pass (post-merge, sequenced per facts §12)

- [x] 6.1 Full suite green (`python -m pytest tests/ -q`), including 1.4–1.6 acceptance/e2e tests
- [x] 6.2 Back up `data/.link_cache/*/result.json`
- [x] 6.3 Bulk discovery refresh (delete per-project caches, re-run `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`); verify `schema_version` 2 and spot-check the 254 family shows 開工日期 2013/09/10 / 使照核發日期 2016/08/29
- [x] 6.4 Update facts doc §12.8 status and §7 file table
