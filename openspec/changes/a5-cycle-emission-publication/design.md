# Design — A5: the cycle commits and pushes the emission

## Context

The decision is the board's "A5 decision" (2026-11-23): after a finished cycle the coordinator commits and pushes the emission, no review step. The 2026-11-25 cycle showed the current shape end to end: the cycle published the four pages (`3ed2f53`), the person reviewed and committed the emission (`f65e8eb`), and the same push carried both. The mechanisms A5 needs already exist and are proven — `publish_release_diff.py`'s path-limited commit, verified push, credential-fail-fast — and are the template, not new code.

## Goals / Non-Goals

Goals:

- One unattended path from a verified gazette to a served viewer *and* served pages, with no person git gate.
- The emission and the four pages leave in one push, in payload-then-pages order, so the pages never describe data the viewer does not hold.
- A defect guard before anything is pushed: a record-count drop stops for diagnosis.

Non-goals:

- No change to acquisition, ingest, refresh, rebuild, checks or tests. The dirty-tree gate, the refusal rules, the record and the resume path keep their semantics.
- No automatic repair, no agent, no bypass of any refusal.
- No change to the four-pages publisher's own rules (when it commits, what it owns).

## Decisions

**D1 — The emission publisher is its own script, `scripts/publish_emission.py`, a child of the coordinator.**
Modelled on `publish_release_diff.py`: exit 0 published, 1 the push failed, 2 not in a state to publish from; path-limited commit; verified push; no-prompt environment; `--dry-run`. It reuses that script's git helpers where they fit. Three reasons it is a child and not code inside `run_cycle.py`:

1. The coordinator's own git use stays read-only (one `git status`). The A4 scenario keeps its meaning: the child commits, not the coordinator.
2. In `_cycle`, a step in `run_steps` that exits non-zero goes to `mark_stopped`. A publication step must not: the hash is finished, and a failed publication never undoes the ingest. The emission publisher therefore runs in the post-finished block with `publish_report`, is classified like it (`classify_exit` → `publish_failed`), and is excluded from the progress marks.
3. A script is what lets a person retry a failed publication by hand, as the spec requires.

The pages publisher keeps its own commit rule (publish only when the report or counts changed); the emission rule is unconditional after the gates. One rule per script. Alternative considered: fold both into one script — rejected.

**D2 — Order: the emission publisher, then the report publisher; the counts trigger becomes unreachable, and that is accepted.**
Both push; the second carries any commit still ahead, so the cycle's two children make the pages land on top of the emission they describe. A failure of the pages publisher then leaves emission-pushed/pages-stale, which `check_deploy.py` reports as stale — visible, and the ingest is not undone.

A side effect, accepted: once the emission is committed first, `HEAD`'s payload counts equal the new ones, so the pages publisher's "only the counts changed" trigger can no longer fire. The publisher then publishes only when `release-diff.html` differs from the committed copy. For any new gazette it does (the report lists the new release), so no real cycle is affected. The unreachable path stays in the publisher for a hand run after a hand-committed emission.

**D3 — Path-limited commit of the emission paths.**
The paths: `data/projects.json`, `data/raw.tsv`, `data/clean.tsv`, `data/merged.tsv`, `data/review_report.txt`, `viewer/projects.data.js`, `viewer/index.html`, `viewer/dashboard.html`. The commit command names the paths itself (the A4 hazard, closed for the pages publisher, applies equally): another session's staged file is neither committed nor discarded. `viewer/dashboard.html` rides the emission: the 2026-11-25 ingest rewrote it, and the deploy check watches it. It is **not** in the A4 `OWNED_PATHS` today, so the dirty-tree gate would not see another session's edit to it, and an unattended commit would sweep that edit in. A5 adds it to `OWNED_PATHS`; the existing test that every owned path exists covers it.

**D4 — The no-drop count guard, measured from the payload, before the commit.**
Read `counts.records` from the new `viewer/projects.data.js` and from the committed `HEAD:viewer/projects.data.js`. A new count **below** the committed one stops the publication (recorded as a failed publication naming the guard; the hash stays finished; a person diagnoses). Equal or higher proceeds. The dataset's measured trajectory only grows (1,444 → 1,448 → 1,450 over 2026-10-15 → 11-12 → 11-19); a drop has always named a defect (a truncated gazette accepted, a reconcile-block missed). This is the "one more check before the push" the board left open — the drop direction only, deliberately narrow, so a legitimate near-equal gazette is never blocked. A project-count guard was considered and rejected: projects can legitimately shrink when families merge, and the record count already gates the catastrophic cases.

**D5 — The code-clean check, immediately before the commit.**
The dirty-tree gate runs before the ingest, so `urtpe/`/`scripts/` were clean then; a check *inside* the publication step re-verifies just those two directories and refuses (exit 2, nothing committed) if the code that produced the emission has since changed. A commit that does not explain its own code is exactly the "emission no commit explains" the 6.24 board note warned about. Cheap: one `git status --porcelain --untracked-files=no -- urtpe scripts`.

**D6 — Credential fail-fast and verified push, as in the pages publisher.**
`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, 120 s limits on `push` and `ls-remote`; after the push, ask the remote whether it holds the commit; a push that did not land is a failed publication. A retry after a failed push pushes the commit already ahead.

**D7 — The pinned-fact tests split by kind (added at the user's word, 2026-11-25).**
The 2026-11-25 cycle stopped twice at `tests` on pins. Two kinds of pin, two treatments:

- *Mechanical pins* — values that **must** equal the current payload's facts (the doc-sync test's date and counts). These stop every ingest that moves the counts, which would break A5's unattended publication on day one. A5 converts them to derive the expected strings from the payload itself. The test keeps its real job — the committed pages must carry the current payload's facts — without pinning literals that the next gazette invalidates. The historical-prose assertions (`"2026-10-15 payload"`, `"83b7b2e"`) stay pinned: they are history, not current facts.
- *Judgment pins* — populations whose movement requires a person's re-measurement and decision (the national-badge 1197/809, the joined-node 39/36/32). Deriving their expected values from the same logic they test would make them tautologies. They stay as they are: on drift they stop the cycle, the person re-measures, updates the pins with the drift named, and resumes. After A5 this is the one remaining designed stop, and it is a feature, not a defect: it is the person gate that A5 keeps.

**Measured rate (2026-11-25, `git log` of the three test files against the payload's emission commits).** The sample is one. The pinned-fact tests were written between 2026-11-13 and 2026-11-19, so only one gazette (2026-11-19) has been ingested since they all existed; it moved the doc-sync pins and two judgment pins. The judgment pins also changed on events that were not a gazette: the 2026-11-15 membership work and the 2026-11-20 city refresh. So the rate at which a gazette stops the cycle at `tests` is **unmeasured, with one observation of "stopped"**. A5 delivers the *mechanism* of an unattended publication; whether a given gazette completes it without a person is for task 4.2 to observe, and the board must not claim otherwise.

**D9 — `post_ingest_check.py` must not stop on facts that its own generation step will update.**
The 2026-11-25 first stop was an ordering bug. `run()` validates first, and `run_local_checks` runs `tests/test_deploy_target.py`, whose config-count test compares `openspec/config.yaml`'s sentence with the new payload. The same script's `generate_reports` is what rewrites that sentence, after the validation. So any ingest that moves the record count exits 1 at `post_ingest_check`, before the tests step is reached. D7 does not cover this: it concerns a different test and a different step. The fix, test-first: the **initial** validation deselects the tests that compare a generated fact with the payload (a named constant list, today the one config-count test in `tests/test_deploy_target.py`); the **post-generation** validation (the second `validator(root)` call) runs everything and stays strict, so a generation that left a fact stale still fails. `--check-only` stays strict too: it generates nothing, so nothing can be stale on purpose. A test asserts that each deselected node id exists, so the list cannot drift silently when a test moves. The `post-ingest-verification` spec gets a MODIFIED delta, because its first requirement says the consistency tests run "before any report generation" and its third says generation updates the config count: for a count-moving payload those two cannot both hold.

Alternative considered and rejected: run the generation (the sync of `openspec/config.yaml`, `docs/etl_process.html`, `docs/domain-model.html`) before the initial validation. That writes documentation from a payload the check has not yet accepted, which breaks "dependent reports update only after a successful recheck".

**D8 — Repository growth is accepted.**
About 23 MB per ingest lands in git history permanently. GitHub's practical limits and this repo's cadence (weekly) make this sustainable for years. No pruning, no LFS — both would break the `file://` viewer and the deploy check.

## Risks / Trade-offs

- [A bad emission is served with no review] → The no-drop guard (D4) plus every existing gate (tripwire, reconcile, post-ingest check, tests, smoke) run before it; rollback is a person's `git revert` of the emission commit (D-rollback below); the previous payload stays reachable in history.
- [The pages publisher fails after the emission pushed] → Visible (stale pages), recorded as publish_failed, hash stays finished; the person reruns the publisher by hand. The emission is not un-pushed.
- [Another session edits code mid-cycle] → D5's re-check refuses the commit; the record names it.
- [The tests drift on a gazette] → Mechanical pins no longer drift (D7) and the check no longer stops on the config sentence (D9); judgment pins stop the cycle by design, and the record shows `tests` as the failed stage, the same drill as 2026-11-25. The rate is unmeasured (D7).
- [A publication child fails after the hash is finished] → Classified `publish_failed`, not `stopped` (D1): the hash stays finished and the ingest never runs again.

## Migration Plan

1. Test-first tasks (group 1), then implementation (group 2).
2. The first cycle after A5 lands runs with no scheduled-task change: the 04:00 task already runs `run_cycle.py` from the working tree.
3. Rollback: `git revert` the emission commit, push by hand, fix the cause, and let the cycle re-ingest (the hash's cycle is finished, so a re-ingest needs the person to clear the record or a newer gazette to supersede; the cycle itself never rewrites history or re-ingests a finished hash).

## Open Questions

None. The board's seven open points are decided above (D3, D2, D6, D8, D4, rollback, D2). The pinned-fact split is decided at D7, at the user's word. The check-ordering bug is decided at D9.
