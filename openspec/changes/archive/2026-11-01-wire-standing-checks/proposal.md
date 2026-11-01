## Why

Two checks that the project's own audit calls for exist but never run in the
pipeline, and a run that skips them reports success — the same shape as the
2026-08-24 incident, where checks existed on paper while the damage shipped:

1. **The emission gate is dead code.** `urtpe/emission.py` (`emission_faults`)
   exists precisely to catch a rebuild without `--links` emitting a dataset with
   no link data — the spec `official-link-discovery` requires the report
   (`Report link data that a run failed to attach`). The module is imported at
   `urtpe/cli.py:15` and called from nowhere. A no-`--links` run today produces
   `links: {}` on every project and exits 0; the check only runs if a person
   executes `scripts/baseline_silent_failures.py` by hand. The dead import shows
   the wiring was intended and lost.
2. **No gate enforces the audit's own completeness assertions.** The
   dataset-completeness audit (Appendix A) verifies, for every gazette, that the
   record→project partition is total and disjoint — the property whose violation
   silently loses or double-counts records. The tripwire checks contiguity,
   dates, and empty pages; `cli` only *prints* counts. The partition assertion is
   three lines and runs nowhere.

The maintainers affected: anyone re-running the pipeline without `--links`
(the default path, advisory by design D5), and any reviewer trusting the emitted
dataset's record counts. Both gaps are closed by wiring checks that already
exist in writing.

## What Changes

- Call `emission_faults(doc["projects"])` in `_run_locked` after
  `build_graph_document` and before `write_json`; report faults in
  `review_report.txt` and print them. **Warning, not refusal** — `--links` stays
  advisory by design (D5), and partial coverage is the expected state per the
  spec.
- Add a census gate to the ingestion: after merge, assert the merge partition is
  total and disjoint over the cleansed records (every clean recno in exactly one
  family; family members sum to the clean count), and that the emitted record
  count equals the cleansed count minus named exclusions. Wire it beside the
  tripwire so it evaluates before any artifact is written.
- Both checks report through the existing run-report machinery; neither adds a
  CLI flag.

## Capabilities

### New Capabilities

(none — both checks pin behaviour existing specs already require)

### Modified Capabilities

- `official-link-discovery`: the emission-report requirement gains its wiring —
  the report SHALL be produced by every emission path in `cli`, not only by the
  manual baseline script. (Requirement text unchanged in substance; the delta
  makes the production path normative.)
- `history-graph`: the emitted document SHALL carry a record→project partition
  that is total and disjoint over the cleansed records; a partition violation
  SHALL be reported before any artifact is written, with the violating records
  named.

## Impact

- `urtpe/cli.py` — `_run_locked` gains the emission-fault call; `_ingest_pdf`
  gains the census gate beside the tripwire.
- `urtpe/emission.py` — no change (already correct).
- `urtpe/tripwire.py` or a small new module — the census check, kept pure.
- `review_report.txt` gains the emission-fault lines.
- No emission-format change: the flag-less bytes are unaffected when links data
  is present; the new report lines are additive text.
