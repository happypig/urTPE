# Proposal: sync-post-ingest-docs

## Why

A maintainer ingested the 2026-11-12 gazette without `--recover-truncated`.
The viewer initially omitted four recoverable records. The two documentation
pages still describe the 2026-10-28 payload. A maintainer must know which
checks to run and which measured facts to update. Readers can therefore see
current viewer data beside superseded documentation.

Actors: the maintainer operating an ingest or rebuild; the reader comparing
the ETL and domain-model pages with the viewer; the analyst reviewing the
release-diff and coverage reports.

## What Changes

- Add a command that synchronises dataset-derived figures and provenance in
  `docs/etl_process.html` and `docs/domain-model.html`. It preserves prose,
  bilingual pairings, layouts and historical examples. It refuses to guess
  when a required measurement cannot be produced.
- Add `scripts/post_ingest_check.py`. It validates emitted-file consistency,
  runs the viewer smoke harness and standing offline checks, and uses the
  existing recovery and rebuild commands for the failures those commands own.
  It rechecks after each repair. It never bypasses a refusal gate.
- Generate the two documentation pages, `docs/etl_process.html` and
  `docs/domain-model.html`, plus `docs/release-diff.html` and
  `docs/coverage-report.html` only after all local checks pass. Publication
  remains an explicit commit and push, not an implicit side effect.
- Refresh the 168-list input used by the coverage report from the latest
  archived poller snapshot. Keep the archived header scan separate; stale
  coverage is reported, not inferred away.
- Add `docs/etl_process.html` to the deployment artifact list. Document the
  recovery flag and the post-ingest command in the operating procedure.
- Reuse the existing measurement probes as maintained logic rather than
  copying their rules into another printer.

## Capabilities

### New Capabilities

- `post-ingest-verification`: validate a full ingest or rebuild, apply bounded
  existing repairs, and update dependent reports only after verification.
- `documentation-dataset-sync`: derive and update current-payload facts in
  the two bilingual documentation pages without rewriting their authored prose.

### Modified Capabilities

- `deployment-verification`: cover the ETL page in the published artifact
  list, so its served bytes cannot become silently stale.

## Impact

- New scripts, shared measurement/rendering logic, focused offline tests and
  a smoke harness for the new command.
- Existing commands reused: `urtpe.cli`, `scripts/viewer_smoke.js`,
  `scripts/baseline_silent_failures.py`, `scripts/release_diff_report.py`,
  `scripts/coverage_report.py`, and the two domain-measurement probes.
- Generated documentation and report HTML; `viewer/deploy.json`;
  `docs/etl_process.md` operating instructions.
- No changes to PDF parsing, merge scoring, identity rules, acquisition or
  scheduled-task behaviour. No new dependencies or CI.
