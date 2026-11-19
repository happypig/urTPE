# Tasks: sync-post-ingest-docs

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_documentation_sync.py`: marked-region replacement,
  duplicate/missing-marker refusal, bilingual consistency, historical-content
  preservation, deterministic generation, and stale check-mode detection.
- [x] 1.2 `tests/test_documentation_sync.py`: whole-payload ETL measurements,
  `probe_tab2_numbers.measure_payload()` over all nodes and virtual cases,
  and the Node measurement adapter's required-field/error handling with a
  local fixture rather than network access.
- [x] 1.3 `tests/test_documentation_sync.py`: the two real documentation
  pages contain every required marker, current publication/count fields,
  and no current-looking 2026-10-28 payload count after generation.
- [x] 1.4 `tests/test_post_ingest_check.py`: total/disjoint recno checks over
  all five emitted layers; raw 編號 mapping; graph/viewer equivalence;
  malformed/missing-file failure; named truncation versus unexplained gaps.
- [x] 1.5 `tests/test_post_ingest_check.py`: command-order fakes prove that
  reports follow a passing recheck, recovery runs at most once without
  bypass flags, residual/refusal outcomes stop, `--check-only` writes
  nothing, and no git command runs.
- [x] 1.6 `tests/test_post_ingest_check.py` and
  `tests/test_deploy_target.py`: newest valid archived 168 snapshot
  selection, hash mismatch refusal, bounded header-scan evidence, and the
  ETL page in the deployment artifact list.
- [x] 1.7 Run the new tests before implementation and record the expected
  failures. The pre-existing configured-count failure is separately recorded:
  `tests/test_deploy_target.py` says 1,444 while the payload holds 1,448.

## 2. Pure measurement and rendering

- [x] 2.1 Refactor `scripts/probe_tab2_numbers.py` into a reusable
  whole-payload measurement function plus its existing printer; correct the
  known 事業換計畫 lane typo and return every domain §2/§4/§5 current fact.
- [x] 2.2 Add `--json` output to `scripts/probe_tab1_numbers.js`, preserving
  its real `buildConstructionChain` call and human-readable mode.
- [x] 2.3 Add `scripts/doc_measurements.py`: payload/artifact measurement,
  strict Node JSON parsing, marked HTML rendering, stable write/check
  behavior, and the configured current-dataset update.
- [x] 2.4 Extract the existing partition/coverage checks into a reusable
  read-only adapter. Preserve `probe_three_coverage_proofs.py` behavior and
  make badge/flag disagreement fail its verdict instead of printing success.

## 3. Documentation adapters

- [x] 3.1 Add `scripts/sync_etl_process.py` and marked regions to
  `docs/etl_process.html`; render the current payload, local artifact facts,
  measurement provenance, recovery procedure, and post-ingest command.
- [x] 3.2 Add `scripts/sync_domain_model.py` and marked regions to
  `docs/domain-model.html`; render §2/§4/§5 current facts from both probes
  while preserving the dated historical table and examples.
- [x] 3.3 Synchronise the prose source notes in `docs/etl_process.md` and
  `docs/domain_model.md` so they identify the generated regions and do not
  direct maintainers to hand-edit generated numbers.
- [x] 3.4 Update `openspec/config.yaml`'s marked current-dataset sentence,
  `viewer/deploy.json`, and the operating commands, including
  `--recover-truncated` and `python scripts/post_ingest_check.py`.

## 4. Post-ingest orchestration and coverage evidence

- [x] 4.1 Add `scripts/post_ingest_check.py`: layered validation, bounded
  recovery/rebuild, final recheck, two doc generators, then release/coverage
  generation. Implement `--check-only`, per-check output, non-zero failures,
  and no implicit git operation.
- [x] 4.2 Refresh `data/p168_all.json` from the newest valid archived poller
  snapshot before coverage generation; never enumerate new portal cases in
  this command.
- [x] 4.3 Update `scripts/coverage_report.py` so snapshot/header-scan
  provenance is visible and unmeasured cases remain unclassified rather
  than contributing to unsupported approval/revocation arithmetic.

## 5. End-to-end verification and publication hand-off

- [x] 5.1 Run the focused new and existing tests; generate both documents;
  inspect their diffs and run both `--check` modes. Confirm historical
  examples, bilingual switching, layouts and self-contained rendering.
- [x] 5.2 Run `node scripts/viewer_smoke.js`,
  `python scripts/baseline_silent_failures.py`, and the full offline pytest
  suite. Run `node scripts/probe_fence_mask_diff.js` only if the archive
  probes changed; they are outside this change's scope.
- [x] 5.3 Run `python scripts/post_ingest_check.py` on the real dataset.
  Confirm any repair uses an existing gate-respecting command, then confirm
  `docs/etl_process.html`, `docs/domain-model.html`,
  `docs/release-diff.html`, and `docs/coverage-report.html` regenerate
  successfully. Re-run `--check-only` to verify a clean result.
- [ ] 5.4 Review `git diff` and report owned paths separately from other
  sessions' files. Commit only reviewed owned paths, push `main`, and verify
  all 12 artifacts with `python scripts/check_deploy.py`.
- [ ] 5.5 Validate the OpenSpec change strictly; archive it on a temporary
  copy first, compare synced specs, then archive the real change and run the
  final test/deploy checks. Report the test-first gate result.
