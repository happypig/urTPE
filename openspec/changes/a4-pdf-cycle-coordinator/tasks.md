## 1. Tests (test-first group — every task here is checked before any task in group 2)

The pure-logic tests use no adapter. The adapter tests use doubles for the network, the subprocess runner, the clock, locks and git. Nothing here reaches the network or writes the real `data/`. Proofs 7 and 8 of the board's U6 list are properties of the existing rebuild and the existing check; they are exercised in group 5, not re-implemented here.

- [x] 1.1 `tests/test_cycle.py` — the step list is data and its order is fixed: poll_gazette, poll_p168, detect, ingest, refresh, rebuild, post_ingest_check, tests, viewer smoke; it ends there and holds no git step
- [x] 1.2 `tests/test_cycle.py` — no step's argv, in any scenario, contains `--allow-reconcile-block` or `--no-archive` (U6 proof 5)
- [x] 1.3 `tests/test_cycle.py` — candidate selection: an archived gazette newer than the dataset, verified, and recorded neither finished nor stopped is chosen once (U6 proof 2); a gazette not newer than the dataset is never chosen, even with an empty record
- [x] 1.4 `tests/test_cycle.py` — a gazette archived by an earlier poll (this run's poll says `unchanged`) is still chosen; a `reuploaded` result for a gazette the dataset reflects chooses nothing (U6 proof 1); `failed` and `would_download` with nothing newer choose nothing
- [x] 1.5 `tests/test_cycle.py` — a newer archived gazette whose file does not match its archive entry is refused at the detection step, with the mismatch as the reason
- [x] 1.6 `tests/test_cycle.py` — a hash recorded as finished is not chosen again, however many runs start (U6 proof 11)
- [x] 1.7 `tests/test_cycle.py` — the stop rule: an ingest exit of 2, 3 or 4 stops the cycle, runs no later step, records the ingest as the failed stage, and does not record the hash as finished (U6 proof 5); a non-zero refresh is not followed by the rebuild (U6 proof 6)
- [x] 1.8 `tests/test_cycle.py` — a stopped hash makes later scheduled runs record "awaits diagnosis" and run none of its steps; an explicit resume restarts at the failed stage and not at the first step; a newer gazette does not make the earlier failed stage read as successful (U6 proof 12)
- [x] 1.9 `tests/test_cycle.py` — transient stops (a held lock, a dirty tree, another cycle running) leave the hash untouched, so the next run chooses it again
- [x] 1.10 `tests/test_cycle.py` — the exit-code map: 0 for finished, nothing to do and already done; 1 for a failed step or a hash awaiting diagnosis; 5 for a held lock or another cycle; 6 for a dirty tree; 2 for bad usage
- [x] 1.11 `tests/test_cycle.py` — a record holds the time, both poll outcomes, the hash, the last stage, the failed stage, the exit code and the outcome word; a run that found nothing is recorded as such; a gap longer than the expected interval is detectable from the records alone; no field keys on 編號, `recno` or `project_id`
- [x] 1.12 `tests/test_cycle.py` — the owned-path list: every path in it exists in the repository (so it cannot drift silently); an owned path dirty with a gazette ready refuses (U6 proof 9); an unrelated dirty path does not; a dirty owned path on a quiet day does not stop the run
- [x] 1.13 `tests/test_run_cycle.py` — with a fake runner and a recording git adapter, a new gazette runs every step once in order, and the only git command ever issued is a read-only status
- [x] 1.14 `tests/test_run_cycle.py` — locks, with real `SingleWriterLock` over temp directories: a lock held over `data/` at the start stops the cycle with exit 5 before any write step and writes nothing (U6 proof 4); a child exiting 5 mid-cycle stops with the stage recorded; between steps the `data/` lock is free; the cycle's own lock (over the archive root) does not block a child that takes the `data/` lock; a second cycle stops and records that one was running
- [x] 1.15 `tests/test_run_cycle.py` — `--dry-run` runs only the two polls with `--dry-run`, prints the steps it would take, and writes no record, no archive file and nothing under `data/`
- [x] 1.16 `tests/test_run_cycle.py` — the record store: append-only lines, a round trip of the state file, an atomic state write (a failed write leaves the old state), and `URTPE_ARCHIVE_ROOT` is honored
- [x] 1.17 `tests/test_run_cycle.py` — a step that times out counts as a failed step; the coordinator reads `--json` from the two polls and a malformed result is a failed step, not a "nothing new"
- [x] 1.18 `tests/test_cycle_status.py` — the page lists runs newest first with time, outcome word, last stage, failed stage and exit code; a stopped run is visibly different from a finished one and from a quiet one; the newest-record time is shown, with a warning when it is older than 36 hours
- [x] 1.19 `tests/test_cycle_status.py` — the generator reads only the record and writes only its own file; the page has no external script, stylesheet or request; the output path is outside the repository, so no committed or served path reaches it; a failing generator never changes the coordinator's exit code

## 2. Domain module — pure logic, no I/O (`urtpe/cycle.py`)

- [x] 2.1 The ordered step list as data: name, argv builder, timeout, whether it writes
- [x] 2.2 Candidate selection: newer than the dataset's date, verified, not finished, not stopped; newest first; the reason for each refusal
- [x] 2.3 The stop rule and the record transitions: finished, stopped (stage, exit code), transient stop, awaiting diagnosis, resume at a stage
- [x] 2.4 The exit-code map (D8)
- [x] 2.5 The record shape and the outcome words (D7)
- [x] 2.6 The owned-path list (D6) and the dirty-tree decision: refuse only when a gazette is ready

## 3. Adapters — I/O (`scripts/run_cycle.py`)

- [x] 3.1 The subprocess runner: `sys.executable`, repo root as the working directory, a timeout per step, stdout and stderr kept for the record
- [x] 3.2 The read-only git adapter: `git status --porcelain` over the owned paths; no other git command exists in the module
- [x] 3.3 The record store in the archive root: `cycle_log.jsonl` appended, `cycle_state.json` replaced atomically
- [x] 3.4 The cycle lock (`SingleWriterLock` over the archive root) and the `data/` probe that takes the lock and gives it back at once
- [x] 3.5 The command line: `--dry-run`, `--resume <hash>`, `--archive-root`; the exit codes of D8
- [x] 3.6 Wire the steps, call the status-page generator at the end of every run as best effort, and ensure no path writes git or the emitted tree outside the child commands

## 4. Status page (optional capability — cut by deleting `specs/cycle-status-page/` and this group)

- [x] 4.1 `scripts/cycle_status.py`: read `cycle_log.jsonl`, write `<archive root>/cycle_status.html`
- [x] 4.2 The page: runs newest first, the stopped, quiet and finished styles, the newest-record time, the 36-hour warning; self-contained, light-only, project cream tokens, zh-Hant labels with English technical names
- [x] 4.3 Confirm the output sits outside the repository, and that a failure to write it is swallowed by the coordinator

## 5. Observation — before any scheduler or documentation change

- [x] 5.1 Run the full suite and record the collected and passed counts
- [x] 5.2 Run `python scripts/run_cycle.py --dry-run` on the real tree. The plan must read "nothing to ingest" today, because the archive's newest gazette (2026-11-12) is not newer than the dataset's. Record the output
- [x] 5.3 Against a held lock on the real tree, run the coordinator on a temporary archive that holds a gazette newer than the dataset: it must stop with exit 5 and write nothing (the A1 check, repeated for the cycle)
- [x] 5.4 A live smoke on a temporary tree: copy the viewer payload and `data/.link_cache` (cache hits, so no request) to a temp directory and run the real rebuild and the real post-ingest check there. Confirm the recno partition and the project ids are preserved (U6 proof 7) and that the generated reports name the payload revision the viewer carries (U6 proof 8). The real `data/` and the real cache are not touched
- [x] 5.5 Run `python scripts/cycle_status.py` on the records from 5.2 to 5.3 and look at the page in a browser served on 127.0.0.1

**Observed 2026-11-23 (group 5).**
- 5.1: the full suite reports 1,679 passed, 1 skipped, 4 xfailed; 1,684 collected (121 new tests).
- 5.2: the dry run on the real tree reads: `poll_gazette` `would_download` (the page bytes changed; its stamp `115-11-17 13:44` is the stamp of the gazette already archived), `poll_p168` `unchanged`, detection "nothing to ingest". Exit 0. Nothing written.
- 5.3: the real adapters work: `git status` over the owned paths returned nothing, the dataset date read 2026-11-12, and a timed-out step returns 124. With the `data/` lock held, `--resume` of a stopped hash on a temporary archive exited 5, recorded `locked` at `refresh`, and kept the hash in progress at `refresh`. No network was used.
- 5.4: proof 7 holds: the real rebuild on a temporary copy of the viewer and the cache kept all 1,448 recnos and 676 project ids, and the real cache was untouched. Proof 8 is partly observed: `post_ingest_check.py --check-only` passed every local check, then failed only on `sync_etl_process.py --check` (the test count, stale because of the new tests; refreshed in 8.6). `sync_domain_model.py --check` is stale on three fields because `scripts/sync_domain_model.py:56` puts today's date inside compared fields. That is the flaw commit `53651bc` fixed in the ETL sync. This change did not cause it and does not fix it.
- 5.5: the status page looks right in a browser: four distinct row styles, no external request, no sideways overflow, and no warning for a fresh record.

## 6. Report publication (added 2026-11-23 — tests first, then code)

The user amended U-D2 for the release-diff report only (design D13). Tasks 6.1 to 6.9 are written and checked before 6.10 to 6.12. Editing existing tests is expected: the step order gains a last step, so the order tests in `test_cycle.py` and `test_run_cycle.py` change.

- [x] 6.1 `tests/test_cycle.py` — update the step-order tests: the order ends `viewer_smoke`, `publish_report`; `publish_report` is the last step and runs `scripts/publish_release_diff.py`; no argv holds a bypass flag; `next_step_after("viewer_smoke")` is `publish_report`
- [x] 6.2 `tests/test_cycle.py` — `publish_failed` is an outcome with exit code 1, and a publication exit of 1 or 2 maps to it
- [x] 6.3 `tests/test_run_cycle.py` — update the order tests: a finished cycle ends with `publish_report`, and the record names it as the last stage
- [x] 6.4 `tests/test_run_cycle.py` — publication never runs on `nothing_new`, `already_done`, `refused`, `stopped`, `locked`, `dirty_tree`, `awaiting_diagnosis`, or a resume that stopped again (parametrized)
- [x] 6.5 `tests/test_run_cycle.py` — the hash is recorded as finished before the publication step starts (the fake publisher reads the state file)
- [x] 6.6 `tests/test_run_cycle.py` — a failed publication (exit 1, and exit 2) is recorded as `publish_failed` with the step's own exit code, the coordinator returns 1, the hash stays finished, and the next run neither ingests nor publishes again
- [x] 6.7 `tests/test_run_cycle.py` — a resume that finishes reaches `publish_report`
- [x] 6.8 `tests/test_run_cycle.py` — the dry run's plan ends with the report publication when a gazette is ready, and still runs only the two polls
- [x] 6.9 `tests/test_cycle_status.py` — a `publish_failed` run is shown in the stopped style
- [x] 6.10 `urtpe/cycle.py` — add the `publish_report` step, the `publish_failed` outcome and its exit code
- [x] 6.11 `scripts/run_cycle.py` — mark the hash finished after the smoke step, then run the publication step; map its failure to `publish_failed`; the coordinator's own git use stays one read-only status
- [x] 6.12 `scripts/cycle_status.py` — the `publish_failed` style
- [x] 6.13 Run the three test files and the full suite; record the counts

**Found while doing group 6 (2026-11-23); the operator chose to fix `publish_release_diff.py` (option 1).** The cycle runs `post_ingest_check.py` before it publishes, and that command already regenerates `docs/release-diff.html`. `publish_release_diff.py` then regenerates the report again, compares it with its own copy from before that run (`regenerate()`), finds only the timestamp different, and answers "nothing to publish" without committing. A unit probe with a pre-regenerated report in a temporary file confirmed it: `regenerate()` returned False. So as designed the publication step would run, exit 0 and publish nothing, whenever a cycle has ingested. The same holds for a person who runs `post_ingest_check.py` and then the publisher by hand. Tasks 6.14 to 6.16 fix it; they change the existing script, so they wait for a decision.

- [x] 6.14 `tests/test_release_diff_publish.py` — the report counts as changed when it differs from the COMMITTED report, ignoring the generation stamp, not only from its own copy before this run: a report already regenerated by `post_ingest_check.py` is committed; a report equal to the committed one is not committed and is left byte-identical to it
- [x] 6.15 `scripts/publish_release_diff.py` — `regenerate()` compares with the committed version (`git show HEAD:docs/release-diff.html`); nothing else about the script changes
- [x] 6.16 Re-run the unit probe of 2026-11-23: with the report already regenerated and different from the committed one, `regenerate()` returns True

**Widened 2026-11-23 (the operator's choice): the publication step now publishes four generated pages as one set** (design D13; the new `gazette-cadence` requirement). The tests come first. Two guard tests of `test_release_diff_publish.py` are replaced, and the report names both.

- [x] 6.17 `tests/test_release_diff_publish.py` — in the temporary-repository sandbox, extended with the four pages and a payload file: the report changed, so the owned pages that differ are committed together, path-limited, and another session's staged file stays out; only the counts changed, so the three other pages are committed and the report stays byte-identical to HEAD; nothing changed, so there is no commit and the other three pages are untouched, a date-only diff included; a missing page is not an error; a dirty generator of another page gives exit 2; unreadable counts give exit 2; a payload absent from both gives no counts trigger; a retry after a failed push pushes the commit and exits 0; a dry run commits nothing and says which trigger fired; the counts parser
- [x] 6.18 Replace two guard tests, naming both in the report: `test_the_step_stages_only_the_paths_it_owns` (it pinned one path; it becomes the four `docs/` pages and still bans anything under `data/` or `viewer/`), and `test_the_step_writes_nothing_under_the_emitted_tree` (it banned the string `projects.data.js` from the source; reading the counts breaks that, so it becomes: every owned path is under `docs/`, and no write call targets the payload). The replacements are written before the old tests are relaxed
- [x] 6.19 `scripts/publish_release_diff.py` — own the four pages; stage only those that exist or are tracked; the counts trigger with the unreadable-counts error; extend `GENERATOR_PATHS`; push an unpushed commit that touches an owned page; the dry run names the trigger
- [x] 6.20 `urtpe/cycle.py` and `scripts/run_cycle.py` — update the comments and docstrings that say the step publishes only `docs/release-diff.html`
- [x] 6.21 Run the full suite and refresh the counts in `AGENTS.md` and the synced HTML count
- [x] 6.22 `scripts/sync_domain_model.py` — the `--check` read back the stored date instead of stamping today, as `sync_etl_process.py` does (found 2026-11-23: six fields STALE with no figure moved). Five tests in `tests/test_documentation_sync.py`, written first. Not part of the coordinator's own scope; the operator asked for it with group 6

## 7. Scheduler (only with the operator's approval at apply time)

- [x] 7.1 Save the XML of `urtpe-nightly-sweep` and of `urtpe-poll` to the archive root before any edit
- [x] 7.2 Change `urtpe-nightly-sweep`: trigger daily 00:30, action `--deadline 03:30`, 3-hour limit
- [x] 7.3 Create `urtpe-cycle`: daily 04:00, action `python scripts\run_cycle.py`, the principal and settings of the two existing tasks (user `jeffw`, interactive logon, limited), `StartWhenAvailable` on, `IgnoreNew`, 2-hour limit
- [x] 7.4 Disable `urtpe-poll` (do not delete it). Read back all three tasks: state, triggers, actions and next run times
- [ ] 7.5 After the first scheduled runs, read `sweep_runs.jsonl`, the cycle record and the status page: one line each, exit 0, nothing written outside the records. When the first new gazette arrives, observe the report publication (the first unattended push) and record whether it landed

## 8. Documentation — last, after groups 5 and 6 have been observed

- [x] 8.1 `docs/etl_process.html`: add the coordinator row and the status-page row to the "What runs, and who starts it" table; the two pollers and `publish_release_diff.py` move to the daily 04:00 cycle group; the `urtpe-poll` group is removed (the task is retired); the sweep row says daily 00:30, stops 03:30; the §1 stage rows and the after-stage-8 note mention the coordinator and the report publication. Every cell has its `en` and `zh` pair, and the counts stay equal
- [x] 8.2 `docs/pipeline/etl_process.md`: the same table, and §11 (the runbook says what the cycle does, what it leaves for a person, how to resume a stopped hash, and that a failed publication is retried by hand with `python scripts/publish_release_diff.py`, which also pushes a commit that is already ahead of the remote)
- [x] 8.3 `AGENTS.md`: rewrite the invariant "Acquisition is separate from ingestion … Don't wire polling into ingestion" (the poller module still never ingests; the coordinator is a third component that reads the archive); rewrite the `scripts/publish_release_diff.py` entry at line 190, which calls it "the third action of the `urtpe-poll` task"; describe `run_cycle.py` in the layout; refresh the test counts
- [x] 8.4 `scripts/publish_release_diff.py`: change the first lines of its docstring, which call it "the third action of the `urtpe-poll` scheduled task", to say that the cycle runs it after a finished ingest, which pages it owns and when it publishes them (a documentation edit only)
- [x] 8.5 `docs/inspections/optimization.md`: mark A4 done; record U-D2 as amended for the release-diff report only, U-D3 as settled "supersede", U-D7 (the cycle at 04:00, the sweep 00:30 to 03:30) and U-D8 as decided; say that A5 now covers only committing and pushing the emission; update the Part I "Current boundary" paragraph. Stage this file on its own, since the other session's ratification edits are still in the working tree
- [x] 8.6 Run `python scripts/sync_etl_process.py`, then `--check`, then the doc tests, then a browser pass of §1 at 1536 px and in a 390 px iframe, in both languages
- [x] 8.7 Before `openspec archive`, copy `openspec/` to a temporary directory and run the archive there. Confirm the report applies one modified requirement and keeps all five of its scenarios, and that `gazette-cadence` still reads correctly
