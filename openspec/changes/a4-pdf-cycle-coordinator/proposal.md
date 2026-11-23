## Why

The operator learns of a new gazette only when the operator runs a command. The poll log shows it: the city stamped gazettes on Tuesday 11-03 and Tuesday 11-17, and both were caught by hand-started polls (11-06 and 11-18), while the scheduled Monday polls saw only re-uploads. After a catch, six more commands run by hand, each leaving a different layer current at a different time (optimization board, Part I, U1).

A1 to A3 and A8 made each step safe to chain: the refresh and the sweep take the lock, the pollers print a structured result with a verified archive path, and a failed check leaves a record. What is missing is the one component that runs them in a fixed order, stops at the first refusal, and records where it stopped.

## What Changes

- **Decisions this change records.** U-D1 (ratified 2026-11-22): a coordinator may start an ingest after hash acquisition, through this change and all existing gates. U-D2 (ratified 2026-11-22), amended on 2026-11-23 for the generated report pages only: the emission stays generate-and-stop, but the cycle publishes the four generated pages (the release-diff report, the coverage report, the domain model and the ETL page) after a finished ingest. U-D3 is settled as "supersede": the cycle is the report's single scheduled publisher. U-D7 (2026-11-23): the pollers and the cycle run daily, the cycle at 04:00 after a sweep window of 00:30 to 03:30. U-D8 (2026-11-23): the sweep stays its own task.
- **A coordinator.** A new script runs the existing commands in this order and adds no polling, ingest or refresh logic of its own: `poll_gazette.py --json`, `poll_p168.py --json`, detect a new gazette, ingest the archived PDF, `refresh_awaiting_caches.py`, the `--from-js` rebuild, `post_ingest_check.py`, the tests and `node scripts/viewer_smoke.js`. After the last check it records the hash as finished, then runs the existing `publish_release_diff.py`, which commits and pushes only the four generated pages (`docs/release-diff.html`, `docs/coverage-report.html`, `docs/domain-model.html` and `docs/etl_process.html`), and stops. The coordinator itself never stages or commits anything, and the emission (`data/`, `viewer/`, the other generated pages) stays uncommitted for a person to review and commit (A5).
- **The archive decides, not a status word.** An ingest starts only for an archived gazette that is newer than the emitted dataset, verifies against its archive entry, and that the coordinator has not recorded as finished or stopped. A poll's `new_gazette` status is consumed by any earlier poll, including a hand-started one (both real catches so far were), so waiting for that word would archive a gazette and never ingest it. A re-upload of a gazette the dataset already reflects never starts an ingest. A hash whose cycle finished is never ingested again.
- **Stop on the first refusal.** Any non-zero exit ends the cycle. The coordinator never passes `--allow-reconcile-block` or `--no-archive`. A failed cycle is resumable after diagnosis, and a later gazette cannot make a failed stage look successful.
- **No parent lock.** The coordinator does not hold `data/.pipeline.lock` across child commands (A8 showed that a parent-held lock makes the child CLI exit 5). Each child takes its own lock. A held lock stops the cycle with a recorded exit 5. The design says how the gaps between steps are handled.
- **Refuse a dirty tree.** Before any write, the coordinator checks `git status` for the paths a cycle owns. If another session has changes there, it stops, records why, and tries again on the next run.
- **A cycle record.** One structured line per run: the PDF hash, the stage reached, the exit code, the failed stage and the time. This is operational state, not identity (it never keys on 編號 or `project_id`).
- **A status page (new scope, requested 2026-11-23).** A read-only page generated locally from the cycle record, so the operator can see the last runs without reading JSON. It is not published to GitHub Pages by default. The design records that the operator may cut it; it has its own capability so it can be removed without touching the coordinator.
- **A schedule.** One new Windows task, `urtpe-cycle`, runs the coordinator daily at 04:00. The nightly sweep moves to start at 00:30 and stop at 03:30, so the two never overlap. The weekly `urtpe-poll` task is retired (disabled, not deleted): its pollers run daily inside the cycle, and its report publication moves into the cycle, so the report has one scheduled publisher.
- **A failed publication never undoes an ingest.** The hash is recorded as finished before the report is published. A failed push is its own outcome, `publication failed`, and a person retries it by hand.
- **The spec amendment.** `gazette-cadence` says "an unattended check never initiates" ingestion. The change modifies that requirement: the poller module still only acquires, and the coordinator is a third component that may start an ingest under the gates above. `AGENTS.md` rewrites the matching invariant in the same change.
- **Documentation, last.** After one real cycle has been observed, the ETL pages, `AGENTS.md` and the board are updated to match (tasks end with this group).

Not in this change: committing and pushing the emission (A5); a city-only cadence (A6); a diagnostic agent (A7); moving the sweep into the coordinator (U-D8, decided against for now); scheduling `refresh_whole_corpus.py` (U-D9); anything on Cloudflare.

Nothing here depends on a PDF-parsing or similarity-threshold POC: no reader, cleansing, merge or link rule changes, and the thresholds stay as they are. The one observation that gates later work is a real cycle on this machine. The documentation tasks wait for it.

## Capabilities

### New Capabilities
- `pdf-cycle-coordinator`: the fixed-order cycle, the gate that starts an ingest, the stop rules, the lock handling, the dirty-tree refusal, the processed-hash and cycle record, and the daily schedule.
- `cycle-status-page`: a read-only local page generated from the cycle record.

### Modified Capabilities
- `gazette-cadence`: the requirement "An unattended check cannot overwrite an emitted dataset" now allows the coordinator to start an ingest under named gates. The poller and the check still never ingest.

## Impact

- **New code:** the coordinator script, a small module for the cycle record and the dirty-tree check, and the status-page generator (names in `design.md`). Tests with doubles for the network, CLI refusals, locks and git. The offline suite stays offline.
- **Unchanged code:** `urtpe/cli.py`, `urtpe/poller.py`, the readers and the merge. The sweep script is not touched.
- **Scheduler:** one new task (`urtpe-cycle`, daily 04:00), one changed trigger and argument on `urtpe-nightly-sweep` (00:30, `--deadline 03:30`), and `urtpe-poll` disabled (not deleted).
- **Specs:** `gazette-cadence` (one modified requirement), two new specs.
- **Docs:** `docs/etl_process.html`, `docs/pipeline/etl_process.md`, `AGENTS.md`, `docs/inspections/optimization.md`.
- **Risk, publication:** the four pages are pushed to `main` unattended, as one set, when the release-diff report changed or the payload's project or record count changed. They describe the new payload while the served viewer still shows the old one, until the emission is committed and pushed. `docs/domain-model.html` and `docs/etl_process.html` also hold hand-written prose; the operator accepted that a commit of them could carry unfinished prose, and the cycle refuses to start when any of them has uncommitted changes. A push sends every commit that is ahead of `origin/main`, not only these pages.
- **Risk:** an unattended ingest can overwrite a good dataset. That is why the poller never ingested. The controls are the existing gates (tripwire, reconcile, coverage), the verified-hash trigger, the dirty-tree refusal and the stop before git. The coordinator adds no gate of its own and does not weaken any.
