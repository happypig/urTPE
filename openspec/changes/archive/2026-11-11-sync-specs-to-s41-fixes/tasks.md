> POC: no new code is written — the behavior was shipped in commit `9d1eeaf` and
> verified (browser sweep of 681 projects, viewer_smoke, check_deploy all FRESH).
> The pinned tests already exist in `tests/test_viewer_labels.py`; this change
> only syncs the specs to that shipped behavior and archives the deltas.

## 1. Verify the deltas against the shipped code (evidence, no writes)

- [x] 1.1 Assert `tests/test_viewer_labels.py` still holds the three §41 pins:
  `test_callout_box_height_counts_wrapped_values_not_row_strings`,
  `test_callout_width_units_helper_exists_and_is_shared`, and
  `TestConstructionEdgeSemantics::test_undated_only_cluster_rows_interleave_by_their_own_event_key`
  — run that file and require green.
- [x] 1.2 Assert `viewer/index.html` carries `app.css?v=` (the stylesheet
  cache-bust) and `urtpe/viewer.py` rewrites it — the evidence for the
  `pdf-tsv-extraction` scenario.

## 2. Delta fidelity — MODIFIED requirements carry the live body

- [x] 2.1 Copy `openspec/` to a temp dir, apply the archive there
  (`openspec archive sync-specs-to-s41-fixes` on the copy), and confirm it
  reports the expected apply counts with no missing-scenario abort.
- [x] 2.2 Diff the two synced specs in the copy against the deltas: every
  pre-existing scenario of both MODIFIED requirements is present verbatim, and
  each delta adds exactly one scenario
  (`An undated approval row in a dated cluster interleaves by its own event key`;
  `Every cacheable reference carries the version`).

## 3. Validation and archive

- [x] 3.1 Run `openspec validate sync-specs-to-s41-fixes` — require zero errors.
- [ ] 3.2 Archive on the real tree and commit:
  `openspec: archive sync-specs-to-s41-fixes and sync its four spec deltas`.
- [ ] 3.3 Run the full suite (`python -m pytest`) and `node scripts/viewer_smoke.js`;
  both green before push. No viewer file changes, so no re-emit or cache write —
  no lock check needed, but confirm `data/.pipeline.lock` is absent anyway before
  committing.

## 4. Deploy check

- [ ] 4.1 Push `main` and run `python scripts/check_deploy.py` — all 5 artifacts
  FRESH (the spec files are not deployed artifacts; the check guards that the
  push itself landed).
