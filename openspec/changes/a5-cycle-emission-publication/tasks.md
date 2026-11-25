## 1. Tests (test-first group — every task here is checked before any task in group 2)

New tests:

- [x] 1.1 `tests/test_publish_emission.py` (new) — with a recording git double: the commit is path-limited to the eight emission paths and names them on the commit command itself; another session's staged file is neither committed nor discarded; the push is followed by a remote check that asks for the commit; a push that did not land exits 1 naming what did not land; a retry after a failed push pushes the commit that is already ahead and exits 0
- [x] 1.2 `tests/test_publish_emission.py` — the no-drop guard: a new record count below the committed one commits and pushes nothing and exits non-zero naming the guard; equal and higher counts proceed; an unreadable count exits 2
- [x] 1.3 `tests/test_publish_emission.py` — the code-clean check: an uncommitted tracked file under `urtpe/` or `scripts/` exits 2 and commits nothing; an untracked file does not
- [x] 1.4 `tests/test_publish_emission.py` — every git command carries the no-prompt environment; a push or remote check over its time limit is a failure; `--dry-run` writes and commits nothing
- [x] 1.5 `tests/test_run_cycle.py` — a finished cycle runs the emission publisher then the report publisher, both after the hash is recorded finished; a failed emission publisher is recorded `publish_failed` with the step named, the hash stays finished, the ingest does not run again, and the report publisher is not run after it; neither child runs on any other outcome (nothing new, already done, refused, stopped, locked, dirty tree, awaiting diagnosis)
- [x] 1.6 `tests/test_cycle.py` — `classify_exit` treats the emission publisher like the report publisher (`publish_failed` on any non-zero or timeout, never `refusal` or `transient`); `OWNED_PATHS` holds `viewer/dashboard.html`, and the existing test that every owned path exists still passes
- [x] 1.7 `tests/test_post_ingest_check.py` — a payload that moves the record count passes the initial check and continues to generation; a generation that leaves the config sentence stale fails the final check; `--check-only` runs every test and fails on a stale sentence; every name in the left-out list exists as a test
- [x] 1.8 `tests/test_documentation_sync.py` — the mechanical pins derive their expected date and counts from the payload (before: the test fails on a count change; after: it passes on any payload). The test renders the pages in memory, so it checks that the renderer follows the payload; a companion test renders from another publication date to prove the expectation is not vacuous. A committed page that lags the payload is caught by `sync_etl_process.py --check`, which `post_ingest_check.py --check-only` runs — this task does not claim the derived test catches it

Existing tests that encode the A4 contract and must change (listed so the red-to-green record shows changed contracts, not deleted guards):

- [x] 1.9 `tests/test_cycle.py` task 1.1 — the step order now holds `emit` and `publish_report` after `viewer_smoke`; "it ends there and holds no git step" becomes "no step the coordinator itself runs is git; the two publishers are child commands"
- [x] 1.10 `tests/test_run_cycle.py` task 1.13 — "the only git command ever issued is a read-only status" stays true of the coordinator; add that the emission publisher is the only other child that commits
- [x] 1.11 `tests/test_run_cycle.py` harness — `_name_of` gains a branch for `publish_emission.py`; a harness default for it exits 0
- [x] 1.12 `tests/test_run_cycle.py` — the `--dry-run` assertion on the printed steps and its sentence "the emission stays uncommitted for you to review" are updated to the new sentence and the new step list

## 2. Implementation

- [ ] 2.1 `scripts/publish_emission.py` (new): modelled on `publish_release_diff.py`; exit 0/1/2; path-limited commit of the eight paths; verified push; `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, 120 s limits; the code-clean check and the no-drop guard; `--dry-run`; reuses that script's git helpers where they fit
- [ ] 2.2 `urtpe/cycle.py`: `STEP_ORDER` gains `publish_emission` before `publish_report`; `build_steps` gains the step (timeout 600, writes False); `classify_exit` treats it like `publish_report`; `OWNED_PATHS` gains `viewer/dashboard.html`
- [ ] 2.3 `scripts/run_cycle.py`: run the emission publisher in the post-finished block, before `publish_report`, and skip it on a failure of the other; exclude it from the progress marks the way `publish_report` is; map its failure to `publish_failed` with the failed stage named; the dry run and the status page name the step
- [ ] 2.4 `scripts/post_ingest_check.py`: the left-out list for the initial check and the strict final check (design D9)
- [ ] 2.5 `tests/test_documentation_sync.py`: convert the mechanical pins to payload-derived expectations (design D7), keeping the historical-prose pins
- [ ] 2.6 Full suite green; `sync_etl_process.py --check` and `sync_domain_model.py --check` current

## 3. Documentation

- [ ] 3.1 `AGENTS.md`: rewrite the coordinator invariant ("never commits the emission (U-D2) … runs git read-only") to say the coordinator's own git stays read-only and the cycle's two children commit and push; rewrite the `scripts/publish_release_diff.py` entry; add `scripts/publish_emission.py`; refresh the test counts
- [ ] 3.2 Docstrings of `scripts/run_cycle.py` and `urtpe/cycle.py`: the "stays uncommitted for a person to review (A5)" sentences
- [ ] 3.3 `docs/pipeline/etl_process.md` §11 and `docs/etl_process.html`: the person gate becomes diagnosis only; the emission commit and push are the cycle's; the rollback is `git revert`; the retry of a failed publication is `python scripts/publish_emission.py`
- [ ] 3.4 `docs/inspections/optimization.md`: A5 implemented with the U-D2 reversal in force; the seven open points named as decided (design D1–D9); the measured rate of tests stops stated as one observation (design D7), not as a promise of unattended runs
- [ ] 3.5 Confirm the 04:00 task still runs `run_cycle.py` from the working tree; no scheduler change

## 4. Observation (before archive; not reachable on the day of implementation)

- [ ] 4.1 A cycle with nothing new ends `already_done` or `nothing_new`, exit 0, no emission commit (the 04:00 run after implementation)
- [ ] 4.2 The first new-gazette cycle runs the full unattended path: emission committed and pushed, then the pages, `check_deploy.py` fresh; the record and the status page say so. Do not hand-run a cycle to satisfy this task
