## Why

On 2026-10-07 an operator deleted `核定案件-2026-09-24.pdf` from the archive after its consequence was measured and stated twice. The next ingestion produced a reconciliation that looked entirely normal and was wrong in every field: `2026-10-01.json` recorded **08-27 → 10-01** and therefore carried what was 09-24's own transition — 19 re-dated rows, 16 edited rows, **41 vanished rows**, and the `roc → gregorian` calendar change — none of which belong to 10-01. `blocking: []`, so it persisted without objection.

Two properties made that possible, and neither is a data problem:

- **`predecessor_of()` asked the filesystem.** It resolved the publication chain from `index_ids_on_disk()` — a directory glob of `核定案件-*.pdf` — so a publication the index still recorded simply ceased to exist as far as the chain was concerned, and the earlier publication was silently promoted into its slot. A record of what happened was answered with a snapshot of what exists right now.
- **`archive.verify()` was never called.** It exists to report members that are missing, unindexed, or altered — including a member whose bytes were *replaced*, since `store()` permits re-storing a publication when content differs. It had two callers, both in `tests/`.

Nothing in the pipeline noticed the deletion. It was found by running `git grep` and thinking to check, which is not a detection mechanism.

## What Changes

- **The publication chain is derived from the index, not the directory.** `predecessor_of()` answers a historical question — *what was ingested before this* — and must read the append-only record of ingestions. A new `recorded_ids()` accessor exposes that, and is used in exactly one place.
- **`index_ids_on_disk()` is kept, and keeps its meaning.** It answers a present-tense question and `verify()` needs both sides to compare them. `publication_count()`'s contract is "publications **archived**", which is honestly present-tense, and is left alone. The original defect was conflating the two questions behind one accessor.
- **A predecessor that is recorded but not held is reported, never skipped.** Today `if prev_path is not None:` falls through silently and reconciliation proceeds against whatever the chain yields. Three cases become explicit: no predecessor recorded, predecessor recorded but its document absent, predecessor readable.
- **`verify()` runs during ingestion** and reports members that are missing, unindexed, or whose content no longer matches the indexed digest. It reports and does not block: a missing older gazette does not invalidate the one being ingested.
- **No ingestion is blocked by an absent member.** Refusing would mean a filesystem accident permanently prevents ingestion, which punishes the operator for something the gate cannot repair.

This change is **preventive**. It cannot undo the misattribution already persisted: 09-24's document is gone, and the correct 09-24 → 10-01 conclusion survives only in `2026-10-01.superseded-with-09-24.json`. Reconstructing the chain position from the index to make the comparison look adjacent would fabricate the provenance the archive exists to hold, so it is explicitly out of scope.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gazette-archival`: the archive SHALL distinguish a publication it has **recorded** from one it **holds**, and SHALL surface members that are missing, unindexed, or altered during ingestion.
- `gazette-reconciliation`: when the predecessor is recorded but its document is not held, the reconciliation SHALL report that no comparison was possible and SHALL NOT silently compare against an earlier publication.

## Impact

- `urtpe/archive.py` — add `recorded_ids()`; change `predecessor_of()` to use it; `verify()` gains a production caller. `index_ids_on_disk()`, `archived_ids()`, `publication_count()` and `newest()` keep their current contracts.
- `urtpe/cli.py` — the reconcile block distinguishes the three predecessor states; `verify()` invoked at ingestion.
- Behaviour visible to an operator: a previously impossible sentence ("recorded but not held") appears in the reconcile report and in the persisted change set; `verify()` output appears in the run log.
- `openspec/specs/gazette-reconciliation/spec.md` gains an outcome that today cannot be produced, so `change_sets/*.json` gains a `note` value that is currently reserved for "no previous gazette archived".
- Blast radius is one live call site: `predecessor_of()` is called only from `cli.py:253`. `newest()` and `publication_count()` have no production callers.