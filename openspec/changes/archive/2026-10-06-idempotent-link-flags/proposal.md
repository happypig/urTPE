# A `--links` run must not accumulate review flags

## Why

Found while verifying a one-project link override, and it is the easiest property in this
pipeline to miss because **every run succeeds**.

`--from-js` alone is deterministic: two consecutive runs produce byte-identical output, 0
differing projects.

`--from-js --links` is deterministic but **not idempotent**: two runs produce ~250 differing
project payloads. The mechanism is append-without-deduplicate at `urtpe/links.py:1494`:

```python
member.review_flags = list(member.review_flags) + [
    f"階段與平台案件狀態不一致(公報{member.stage}/平台{m_case.group(1)})"
]
```

Because `--from-js` round-trips through `clean.tsv`, the next run inherits the previous run's
copies and adds another:

```
run A: 階段與平台案件狀態不一致(公報變更(第二次)/平台變更)   × 5
run B: the same flag                                            × 6
```

Measured on the 2026-10-06 dataset: **282 nodes carrying a duplicated flag**, one flag string
appearing **1162 times**, growing by roughly 280 per run.

This is not incidental. `regenerate_viewer()` in the portal sweep calls exactly
`--from-js … --links`, so **every sweep regenerates the viewer and adds a round of
duplicates** — twice on 2026-10-06.

The emission is the project's primary artifact and is tracked in git, so this also means a
regenerated dataset carries a counter of how many times the pipeline has been run, and no
reviewer can tell that from a real change.

## What Changes

- **Review flags are a set, not a tally.** A flag already present is not added again, so a
  second `--links` run over the same input produces byte-identical output.
- **Existing duplicates collapse.** One run over the current dataset reduces 1162 copies to
  one per affected node; no information is lost, because the copies were identical.
- **Order of first appearance is preserved**, so the review output still reads in the order
  the conditions were met.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-link-discovery`: a stage/platform disagreement is flagged once, and re-running
  discovery over unchanged input does not add the flag again.
- `data-cleansing`: emitted review flags carry no duplicates.

## Impact

- **Changed:** `urtpe/links.py` — the flag is added only when absent.
- **Data:** one `--links` run rewrites `data/projects.json` and `viewer/projects.data.js`,
  removing 880 duplicate flag strings. That is a large diff and a real correction, which is
  why the data files were held back from the previous commit rather than committed with the
  duplication baked in.
- **Unchanged:** the set of flagged nodes, the flag text, discovery outcomes, and every
  other field.