## Context

See `proposal.md` for the motivation. This section holds only the state the design rests on.

**Actors and events.** The operator starts commands by hand today. The Windows Task Scheduler runs two tasks: `urtpe-poll` (Sundays 05:10: `poll_gazette.py`, `poll_p168.py`, `publish_release_diff.py`) and `urtpe-nightly-sweep` (daily 02:00, stops 05:00). The city publishes a gazette about once or twice a month, usually on a Tuesday around 13:45. The events that matter are: a gazette is archived; a gazette is ingested; the cache or the payload is rewritten; a person reviews and commits.

**Boundaries.**

```
poll_gazette / poll_p168  -> archive (outside the repo)        acquisition only, no lock
urtpe.cli <pdf> / --from-js -> data/*, viewer/projects.data.js  takes the lock over data/ (exit 5)
refresh_awaiting_caches   -> data/.link_cache/                   takes the lock (A1), none when idle
sweep                     -> data/.link_cache/ (+ rebuild)       takes the lock for the crawl (A8)
post_ingest_check         -> reports, docs, config sentence      no lock of its own
git                       -> a person (the emission); publish_release_diff (the report only)
                                                          the coordinator runs the latter after a finished ingest, and never runs git itself
```

**Facts the design depends on** (read 2026-11-23):
- The pollers print `--json` with a verified archived path (A3). A poll that archives a gazette updates `poll_state.json`, so the next poll reports the page `unchanged`: the `new_gazette` word is seen once, by whichever poll runs first.
- `SingleWriterLock(root)` writes `.pipeline.lock` into `root` and refuses a second holder with exit 5 in the CLI. It works over any directory.
- `post_ingest_check.py` regenerates `docs/etl_process.html`, `docs/domain-model.html`, `docs/release-diff.html`, `docs/coverage-report.html` and, through `sync_etl_process.py`, the current-dataset sentence in `openspec/config.yaml`.
- The board's U3 says the archive records acquisition, not a finished cycle, and that `ingested: false` in `poll_log.jsonl` is true only at acquisition.

## Goals / Non-Goals

**Goals:**
- One command, run daily, that takes a new archived gazette to a checked emission, publishes the generated report pages, and records every run.
- Stop at the first refusal. Never retry past one. Never pass a bypass flag.
- Add no gate and weaken none: the existing tripwire, reconcile, coverage and lock gates decide.
- Keep pure decision logic apart from the I/O adapters, so every U6 proof is a test with doubles.

**Non-Goals:**
- Committing or pushing the emission (A5). The cycle does publish the release-diff report (D13).
- A city-only cadence (A6), a diagnostic agent (A7), scheduling `refresh_whole_corpus.py` (U-D9).
- Moving the sweep into the coordinator (U-D8, decided against).
- Repairing a refused ingest, restoring files, or choosing among competing re-uploads of one date. A corrected re-upload with a different hash and the same date is left to the archive's `supersedes` path and a person.

## Decisions

**D1. Detection reads the archive, not a status word.** The coordinator's candidate is the newest archived gazette that (a) has a publication date later than the emitted dataset's `published_date`, (b) passes `assert_matches_entry`, and (c) is in neither the finished nor the stopped set of the cycle record. *Why:* any poll consumes `new_gazette`. The Sunday task would, and so would the hand-started polls that caught both real gazettes so far (11-06, 11-18). A coordinator that waited for that word would archive a gazette and never ingest it. Rule (a) also removes any need to seed the record: every older gazette is already not newer than the dataset. *Alternative rejected:* remove the pollers from every other caller. That fails the first time the operator runs `poll_gazette.py` by hand, which the runbook tells them to do. The dataset's date is read from `viewer/projects.data.js`, the state `--from-js` reads.

**D2. Pure logic in `urtpe/cycle.py`, adapters in `scripts/run_cycle.py`.** The module holds: the ordered step list as data (name, argv builder), candidate selection, the stop rule, the state transitions of the record, the exit-code mapping, and the shape of a record. It does no I/O. The script supplies the adapters: a subprocess runner, a `git status` reader, the record store, the clock, the archive. *Why:* the project rule (config.yaml) separates pure logic from I/O, and the twelve U6 proofs need a double for each adapter. Because the step list is data, one test asserts that no argv in any step contains `--allow-reconcile-block` or `--no-archive`.

**D3. Steps run as subprocesses of `sys.executable`, from the repo root, one at a time.** The coordinator reads the exit code, and for the two polls it reads `--json` from stdout. It never imports a step's `main`. *Why:* each step keeps its own exit-code contract and lock, exactly as when a person runs it; the coordinator cannot accidentally change them. Each step has a timeout (ingest 15 min, tests 30 min, others 5 min), and a timeout counts as a failed step.

**D4. Two kinds of stop.** *Refusal stops* (ingest exit 2, 3, 4; any other non-zero step; a gazette that does not verify) record the hash as **stopped**. Later scheduled runs record "awaits diagnosis" and run nothing for it. A person restarts it with `run_cycle.py --resume <hash>`, which restarts at the failed stage. *Transient stops* (exit 5 from a held lock; a dirty tree; another cycle running) leave the hash untouched, so the next daily run tries again. *Why:* AGENTS.md says a non-zero exit is a refusal and must not be retried past; but a held lock is not a refusal of the data, only of the moment.

**D5. Lock handling.** The coordinator holds no lock over `data/` (the A8 lesson: a parent-held lock makes the child exit 5). Before its first write step it probes `data/`: it takes the lock and gives it back at once. If that raises `LockHeld`, the cycle stops with exit 5 recorded. Each child then takes its own lock; an exit 5 mid-cycle stops with the stage recorded. The gap between two steps is accepted, and closed by three things: the 04:00 slot starts 30 minutes after the sweep's 03:30 stop (the sweep checks its deadline before each sleep, so an overrun is minutes: one probe and its rebuild), the probe, and the child locks. A writer that slips in a gap can at worst stop the cycle at the next step, which resumes later. *Alternative rejected:* a marker file the sweep must read. It would change the sweep (A8, just proven) for a window of minutes. *Cycle against cycle:* the coordinator takes a `SingleWriterLock` over the **archive root**, a different directory from `data/`, for the whole cycle. The children never take that one, so the A8 problem cannot occur, and a second cycle (a hand-started one beside the task) stops with a record.

**D6. Owned paths for the dirty-tree check.** A fixed list in `urtpe/cycle.py`: the tracked files under `data/` that an ingest rewrites (`projects.json`, `raw.tsv`, `clean.tsv`, `merged.tsv`, `review_report.txt`), `viewer/projects.data.js`, `viewer/index.html`, the four generated pages (`docs/etl_process.html`, `docs/domain-model.html`, `docs/release-diff.html`, `docs/coverage-report.html`) and `openspec/config.yaml` (its current-dataset sentence). The check is `git status --porcelain -- <list>`; any output means dirty. It runs once, after detection finds a gazette and before the first write step. A quiet day is never stopped by it. *Consequence worth knowing:* a cycle that finishes leaves its output uncommitted for review (generate and stop), so the next new gazette is refused until the operator commits it. That is intended: it keeps two unreviewed emissions from stacking. A test asserts every path in the list exists in the repository, so the list cannot drift silently.

**D7. The record.** `cycle_log.jsonl`, one line per run, and `cycle_state.json`, a map from gazette hash to `finished` or `stopped` with stage, exit code and time. Both live in the archive root beside `poll_log.jsonl`, so they sit outside the repo, are shared by every process, and honor `URTPE_ARCHIVE_ROOT` (the test conftest already points that at a temp dir). A line holds: time, the two poll outcomes, hash, last stage, failed stage, exit code, outcome word. No rotation: a line is about 300 bytes, so a year is about 110 KB, and the poller logs do not rotate either. The record never keys on 編號, `recno` or `project_id`.

**D8. Exit codes of `run_cycle.py`.** 0: finished, or nothing to do, or already done. 1: a step failed, a hash awaits diagnosis, or the report publication failed. 5: a lock was held or another cycle was running. 6: refused for a dirty tree. 2: bad usage. `Last Result` in the scheduler then says something, and the record says the rest.

**D9. Dry run.** `--dry-run` runs `poll_gazette.py --dry-run --json` and `poll_p168.py --dry-run --json` (read-only: one page GET and the list requests), evaluates detection, prints the steps it would take, and writes nothing, not even a record. This is the observation the documentation tasks wait for. A real cycle on a new gazette cannot be forced, so the evidence before the docs is: a dry run, a test run against a temporary archive and output tree (the U6 live smoke), and the first scheduled run.

**D10. The status page is a separate, optional capability.** `scripts/cycle_status.py` reads `cycle_log.jsonl` and writes `<archive root>/cycle_status.html`: outside the repo, so it cannot be committed or served by Pages. The coordinator calls it at the end of every run, best effort; a failure to write the page never changes the cycle's exit code. The page is self-contained (no CDN), light-only with the project's cream tokens, with Traditional Chinese labels and English technical names, and a warning when the newest record is older than 36 hours. A failed publication is shown in the stopped style. **You may cut it:** delete `specs/cycle-status-page/` and task group 4. The coordinator does not depend on it.

**D11. The schedule** (the operator's choices of 2026-11-23). Three tasks, one new, one changed and one retired:
- `urtpe-nightly-sweep` moves from 02:00 to **00:30**, and its argument changes from `--deadline 05:00` to **`--deadline 03:30`**: a 3-hour window. *Why:* the sweep holds the lock for the whole crawl, which can take about 2.5 to 3 hours on a night with real candidates (the first is about 11-28). At the old deadline it would still run at 04:00 and stop the cycle with exit 5. A crawl that does not finish continues the next night, because the 14-day ledger records what was probed. Its execution limit becomes 3 hours.
- `urtpe-cycle` (new): daily at **04:00**, action `C:\Python314\python.exe D:\project\urTPE\scripts\run_cycle.py`, the sweep's logon and battery settings, `StartWhenAvailable` on (a missed 04:00 runs when the machine wakes; the probe, the lock and the dirty-tree check make a late start safe), `MultipleInstancesPolicy` IgnoreNew, a 2-hour limit.
- `urtpe-poll` is **retired**: disabled, not deleted, so its XML and history stay. Its two pollers now run daily inside the cycle, and its report publication moves into the cycle (D13).

`urtpe-cycle` copies the principal and the settings of the two existing tasks (user `jeffw`, interactive logon, limited, no wake), so it runs where they run and uses the same git credentials. D13 says what that does not prove. Before any edit, the XML of the tasks to change is saved to the archive root. Editing the scheduler happens only with the operator's approval at apply time.

**D12. The test step is the full suite plus the viewer smoke run.** The board's U1 step 8 names both. `post_ingest_check.py` already runs a focused subset, so the full run is the one thing the cycle adds that no step before it does. It runs only on a day with a gazette, never on a quiet day, so the four minutes are rare.

**D13. The cycle publishes the generated report pages, and only those.** The operator decided this on 2026-11-23, against the advice to keep generate-and-stop, and then widened it from the release-diff report to four generated pages. It amends U-D2 for those pages. The emission stays generate-and-stop: the coordinator never stages or commits `data/`, `viewer/` or `openspec/config.yaml`, and a person reviews and commits them (A5). It also settles U-D3 as "supersede": the cycle is the single scheduled owner of the report pages, and retiring `urtpe-poll` removes the second publisher. A5 shrinks to committing and pushing the emission.
- *The step.* After `viewer_smoke` succeeds, the coordinator records the hash as finished, then runs `scripts/publish_release_diff.py` with no flag. The script keeps its name, which AGENTS.md, the tests and the task cite. It owns `docs/release-diff.html`, `docs/coverage-report.html`, `docs/domain-model.html` and `docs/etl_process.html`, stages only those that exist or are tracked, commits them in one path-limited commit, and verifies the push against the remote. It runs only after a finished ingest. The coordinator's own git use stays one read-only `git status`.
- *The trigger* (the operator's rule): the four pages publish as one set when the release-diff report differs from the committed report (ignoring its stamp), or when the payload's `counts` (projects, records) differ from the committed payload's. If neither, nothing is committed and the other pages are left alone, because a date-only difference in the domain model or the ETL page may belong to an emission still waiting for review. A payload absent from both HEAD and the working tree does not trigger; a payload that is present but has no readable counts is an error (exit 2), never a guess. The rule lives in the script, so it holds for a hand run too, and a hand retry (below) publishes the same set.
- *Generators.* The script already refuses (exit 2) when the report generator's source is uncommitted. It now does the same for the generators of the other pages (`coverage_report.py`, `coverage_checks.py`, `sync_domain_model.py`, `sync_etl_process.py`, `doc_measurements.py`), so no page is published from an uncommitted generator.
- *Exit codes of the publisher* (from its docstring, 2026-11-23): 0 published or nothing to publish; 1 the push failed; 2 the tree is not fit to publish from. The coordinator maps 1 and 2 to one outcome, `publish_failed`, records the child's own exit code, returns 1, and leaves the hash finished. The next run finds the hash done and does not publish again. *Why finished first:* a failed push must never bring the ingest back.
- *A retry must land.* After a failed push the commit already exists, so a naive retry would find nothing to commit and exit 0 without pushing. The script therefore also pushes when a commit that touches an owned page is ahead of `origin/main`. The runbook says: retry with `python scripts/publish_release_diff.py`. A push sends every commit that is ahead of `origin/main`, not only the pages.
- *Fixed on the way.* Before this change the script compared the regenerated report with its own copy from before the run, which `post_ingest_check.py` had already regenerated, so it said "nothing to publish" (measured 2026-11-23, commit `fd2a0b5`).
- *Risks the operator accepted.* (1) The four pages describe the new payload while the served viewer still shows the old one, until the emission is committed and pushed. The release-diff report reads the working-tree payload only for its gap note, but the coverage report and the domain model describe the payload throughout. (2) `docs/domain-model.html` and `docs/etl_process.html` hold hand-written prose, so a commit of them could carry someone's unfinished prose. The cycle refuses to start when any owned page has uncommitted changes, which covers the unattended case; it does not cover a hand run.
- *What retiring `urtpe-poll` loses.* The Sunday run republished the report after a reader or code change even with no new PDF. After this change that happens only with the next gazette, or by hand. The task is disabled, not deleted.
- *What is not proven.* The push credentials. `urtpe-poll` and `urtpe-nightly-sweep` run as the same user with the same logon type, and `urtpe-cycle` copies them. But no unattended push has been observed: the scheduled runs of 11-09 and 11-16 found nothing to publish (exit 0), and the last report commit (`9877821`, 11-18) followed a hand-started poll. The first unattended push is therefore observed, not assumed (task 7.5), and a hand run of the script is the first check.
- *Alternative rejected.* An opt-in flag so that the default stays report-only. It would override the operator's choice and make the documented hand retry publish only the report.

## Risks / Trade-offs

- **An unattended ingest can replace a good dataset.** → The existing gates decide; the trigger needs a verified archived file newer than the dataset; the cycle stops before git, so nothing is published and the previous files stay in git history; a refusal is never retried by itself.
- **A stalled review blocks later gazettes.** → By design (D6). The record and the page say "waiting for review of the previous output" every day, so it is visible, not silent.
- **Another session is editing an owned path.** → The cycle refuses and tries again; the cost is a skipped day, shown on the page.
- **A lock gap lets the sweep write between two steps.** → D5: the slot, the probe and the child locks. The failure mode is a stopped, resumable cycle, not a corrupted cache.
- **The first unattended push is untested.** → D13: same principal and settings as the task that was meant to push; the first real publication is observed in task 7.5, and a failed push is recorded, not hidden.
- **The published pages describe the new payload while the served viewer shows the old one.** → D13: the operator accepted it; it lasts until the emission is committed and pushed.
- **A commit of `domain-model.html` or `etl_process.html` could carry unfinished prose.** → D13: accepted; the cycle refuses to start when any owned page is dirty.
- **The weekly republish after a reader or code change is gone.** → D13: do it by hand; the task is disabled, not deleted.
- **The daily run needs the machine awake and the user logged on.** → Same limit as the sweep. `StartWhenAvailable` helps after a sleep. A missed day shows as a gap in the record (spec: gaps are detectable).
- **A candidate rule based on dates misses a corrected re-upload of an already-ingested date.** → Declared a non-goal; the archive's `supersedes` path and a person handle it.
- **The status page adds scope the user asked for late.** → It is isolated (D10) and removable.

## Migration Plan

1. Write the tests first, then the pure module, then the script, then the status page (task groups 1 to 4, then the report publication in group 6).
2. Observe (group 5): a dry run on the real tree, a stop against a held lock, and a live smoke on a temporary tree. All three come before any scheduler or documentation change.
3. With the operator's approval (group 7): save the XML of the tasks to change, move `urtpe-nightly-sweep` to 00:30 with `--deadline 03:30`, create `urtpe-cycle` at 04:00, disable `urtpe-poll`.
4. Update the ETL pages, `AGENTS.md` and the board (group 8); run `sync_etl_process.py` and its check.
5. Watch the first scheduled runs through the record and the page.

**Rollback:** disable `urtpe-cycle`, re-enable `urtpe-poll`, restore `urtpe-nightly-sweep` from the saved XML, and revert the commit. The record files are outside the repo and harmless to leave.

## Open Questions

- Should the status page get an English switch? It starts zh-Hant only, which keeps it small. Adding the switch later changes no spec.
- Should `urtpe-poll` be renamed once it only publishes a report? Deferred to A5, which owns that report.
- Should the test step shrink to a focused subset if the four minutes become a problem? It starts as the full suite; the spec says only "runs the test suite", so narrowing it later changes no requirement.
