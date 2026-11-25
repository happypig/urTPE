## Why

The user decided on 2026-11-23 (optimization board, "A5 decision") that after a finished cycle the coordinator commits and pushes the emission (`data/`, `viewer/` and the tracked TSVs) to `main`, with no review step. This reverses U-D2 ("generate and stop") for the emission. Today that reversal is only a board decision: after the 2026-11-25 cycle, a person reviewed and committed the emission by hand (`f65e8eb`), and the Pages site showed the new gazette only after that push. Until A5 lands, every gazette leaves two person gates (review the emission, commit and push it), and the four generated pages can describe a payload the served viewer does not hold yet. A5 makes the whole publication unattended and one-consistent: the viewer's data and the pages that describe it go out together.

Actors: the coordinator (`scripts/run_cycle.py`, logic in `urtpe/cycle.py`), which gains one publication step; the person, who keeps the diagnosis role when a guard stops the cycle; and GitHub Pages, which serves from `main`.

## What Changes

- A new script, `scripts/publish_emission.py`, modelled on `publish_release_diff.py`, commits the emission paths only (the five tracked `data/` files, `viewer/projects.data.js`, `viewer/index.html`, `viewer/dashboard.html`) in one path-limited commit and pushes `main`, verified against the remote. The coordinator runs it as a child, after the hash is recorded finished and before the report publisher. The coordinator's own git use stays read-only.
- The publisher commits only when the new payload's record count does not drop below the committed payload's, and only when the code directories are clean (a drop stops it for diagnosis before anything is pushed).
- One push carries the emission and the four generated pages, in that order, so the site never serves pages describing a newer payload than the viewer holds.
- `viewer/dashboard.html` joins the dirty-tree gate's owned paths, because the ingest rewrites it and the unattended commit takes it.
- `post_ingest_check.py` stops failing its initial check on the config count sentence that its own generation step updates (the ordering bug behind the 2026-11-25 first stop). The check after generation stays strict.
- The documentation test that pins the payload's date and counts as literals derives them from the payload. The judgment pins (national-badge, joined-node populations) stay: a person re-measures them.

## Capabilities

### New Capabilities

### Modified Capabilities

- `pdf-cycle-coordinator`: the requirement "The cycle runs the existing steps in a fixed order and commits only the report" is amended: the emission is committed and pushed after a finished, verified cycle, by a child publisher the coordinator runs before the report publisher; the coordinator's own git use stays read-only. The requirement "Every run is recorded, including the ones that find nothing" is amended to name the emission publisher in the record and the dry run. Every existing scenario of both requirements is carried forward, reworded only where the amendment changes it.
- `post-ingest-verification`: the requirement "The emitted dataset is checked across every output layer" is amended: the initial check leaves out the named tests that compare a generated fact with the payload; the check after generation and `--check-only` run every test. Every existing scenario is carried forward.

## Impact

- `scripts/publish_emission.py` (new): the path-limited commit, the verified push, the no-drop guard, the code-clean check.
- `urtpe/cycle.py`: the step list gains `publish_emission`; `OWNED_PATHS` gains `viewer/dashboard.html`; `classify_exit` treats the new step like `publish_report`.
- `scripts/run_cycle.py`: runs the new child in the post-finished block; the dry run and the status page name it.
- `scripts/post_ingest_check.py`: the initial check leaves out the named generated-fact tests.
- `tests/test_publish_emission.py` (new), `tests/test_cycle.py`, `tests/test_run_cycle.py`, `tests/test_post_ingest_check.py`, `tests/test_documentation_sync.py`: the new scenarios (test-first), and four existing A4 assertions that encode the old contract.
- `AGENTS.md`, `docs/pipeline/etl_process.md` §11, `docs/etl_process.html`: the "never commits the emission" sentences.
- Repository growth: about 23 MB of diff per ingest is accepted and documented.
- Rollback of a bad served emission: `git revert` of the emission commit by a person; the cycle never rewrites history.
