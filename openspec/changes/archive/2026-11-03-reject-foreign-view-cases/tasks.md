## 1. Test writing — fully checked before any implementation task

- [x] 1.1 pytest: the decision-1 table — all four rows (accept/accept, reject/reject →
  shape A reason, accept-label/reject-city → shape B reason, reject-label/accept-city →
  accept + label error logged), on a two-project fixture where the rejected id's city
  name matches the other project.
- [x] 1.2 pytest: the parcel-less city name (崇仁新村 shape, no 地號 in CASE_NAME) does
  not reject a view-verified id, and the label-not-confirmed report path.
- [x] 1.3 pytest: a missing city name (header fetch failed / no CASE_NAME) keeps the id
  view-verified and never rejects for missing data.
- [x] 1.4 pytest: the offer — a rejected id whose city-name land core matches exactly one
  other cache is appended to that cache's `city_case_ids` (never re-ordered), recorded
  `adopted_from_view` on the target and `view_rejected` on the source; zero matches and
  multiple matches move nothing (ambiguous owner reason); an id the target already holds
  is not duplicated.
- [x] 1.5 pytest: both new fields (`view_rejected`, `adopted_from_view`) round-trip
  through the `--from-js` payload reader, and the payload emits them at project level
  beside `case_schedules` (legacy caches without them emit without the key).
- [x] 1.6 pytest: the refresh re-checks view-verified ids on a fully-approved cache (the
  awaiting-approval selector would skip it) and the run report names every rejected id,
  every offered id, and every label error with counts.
- [x] 1.7 pytest: CASE_NAME persists into the refreshed cache (`case_case_names[cid]`),
  surviving a reload like `case_headers` does.
- [x] 1.8 Confirm the new tests fail on the current code (the id stays view-verified and
  no field exists). — confirmed: `tests/test_view_case_ownership.py` = 5 failed,
  1 passed (the legacy no-key case passes by construction), 11 skipped on the
  unimplemented pure helpers, at `4ca6cc2`.

## 2. Pipeline implementation

- [x] 2.1 Add `DiscoveryResult.case_case_names: dict[str, str]` and
  `DiscoveryResult.view_rejected: dict[str, dict]` + `adopted_from_view: dict[str, str]`;
  persist all three in `save_project_cache`/`load_project_cache` and the `--from-js`
  payload reader (field-by-field, legacy-safe, like `superseded_by`).
- [x] 2.2 `refresh_project`: persist `CASE_NAME` into `case_case_names[cid]` during the
  per-case loop.
- [x] 2.3 `refresh_project`: the view-verified decision pass — decide each id by the
  decision-1 table (`extract_landcore_from_case_name` + `compute_landcore_similarity` at
  `LINK_THRESHOLD` against the cache's own `land_core`; parcel-less → not decidable),
  mutate `view_verified_case_ids` / `view_rejected`, fill the report buckets
  (`view_rejected_ids`, `view_label_errors`, `view_not_confirmed`), and keep a missing
  city name as no evidence.
- [x] 2.4 The driver offer step (in the refresh script): match each rejected id's
  city-name land core against every cache's `land_core`; exactly one match → append to
  that cache's `city_case_ids` (append-only), fetch milestones if absent, record
  `adopted_from_view`; zero/multiple → no move (ambiguous owner). Pure helper
  (`offer_rejected_ids`), unit tested, driven under the lock.
- [x] 2.5 `attach_links_to_projects`: emit `links.view_rejected` and
  `links.adopted_from_view` at project level.

## 3. Cache refresh + re-emit (under the single-writer lock)

- [x] 3.1 Back up the cache dir (`data/.link_cache_backup_<stamp>_viewgate`).
- [x] 3.2 Run the §8 pass on the 146 view-verified caches; the report must name 10202065,
  09511211, 09807161, 09608220 as rejected (each with its shape) and 10906092 as accepted
  with a label error; the offers land on 辛亥163 / 吉林603 / 康寧262 / 犁和165.
  — done: 4 rejections (10202065 A, 09608220 A, 09511211 B, 09807161 A), 4 offers,
  1 label error (10906092), 3 not confirmed (09112120/09112121), 0 failures.
- [x] 3.3 Re-emit `data/` + `viewer/projects.data.js` as a separate `chore:` commit
  (~23 MB diff). Acceptance: the 3 nameless 孤 anchors are gone from
  `links.orphan_nodes`; 09112120 stays view-verified; the viewer smoke passes.
  — done (`f961f6a`): orphan nodes 596 → 592, nameless 3 → 0; 09112120 kept
  ("not confirmed"); smoke passes.

## 4. Verification

- [x] 4.1 `python -m pytest` passes (853+ new cases included). — 870 passed, 1 skipped.
- [x] 4.2 `node scripts/viewer_smoke.js` passes all checks (orphan guard now runs on the
  named-orphan-only corpus).
- [x] 4.3 The run report (stdout) names every rejected id and every offered id with its
  reason — §8 acceptance 4. — `data/viewgate_run_20261104.log`.
- [x] 4.4 Payload spot-check: 10202065 / 09511211 / 09807161 absent from their wrong
  holders' `view_verified_case_ids` + `orphan_nodes`, present in each `view_rejected`
  with its reason, and present on the owning project (city_case_ids / case_milestones)
  — §8 acceptance 1–2.

## 5. Docs + archive

- [x] 5.1 Update `docs/viewer-UX.md` §8 status → done (wave 3b), and the inspection
  board's B7/B8 rows → done.
- [x] 5.2 Append the live-run record to `docs/portal_operations_log.md` (§39).
- [x] 5.3 `openspec: archive reject-foreign-view-cases` and sync the three spec deltas.
