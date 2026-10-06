# Design — idempotent-link-flags

## Context

`urtpe/links.py:1494`, reached from `discover_project_links` when a record's published stage
disagrees with the stage of the platform case it anchored to:

```python
member.review_flags = list(member.review_flags) + [
    f"階段與平台案件狀態不一致(公報{member.stage}/平台{m_case.group(1)})"
]
```

Unconditional append. `member.review_flags` arrives from the ingested TSV, and `--from-js`
reads `clean.tsv` back as its input, so the previous run's flags are already there.

Measured 2026-10-06 on the live dataset:

| | |
|---|---|
| nodes carrying a duplicated flag | **282** |
| occurrences of `階段與平台案件狀態不一致(公報變更(第二次)/平台變更)` | **1162** |
| growth per `--links` run | ~280 |
| identical flag on one record, run A / run B | 5 / 6 |

## Decisions

### D1 — Add only when absent, at the raise site

The narrow fix is at line 1494: append only if the string is not already present. Fixing it
here rather than at emission means the model in memory is correct, so anything reading
`review_flags` before write — the run summary, `report.py`, the graph builder — sees the
truth rather than a tally.

### D2 — Also dedupe at emission, because the data is already dirty

D1 alone fixes future runs but leaves 1162 existing copies in the tracked dataset. Two
reasons to collapse on write as well:

- The duplicate strings are identical, so collapsing loses nothing. The distinct set per
  record is unchanged by definition.
- Emission is the last point where every path is caught, including any future flag source
  that forgets the guard at D1.

Order is preserved as first-appearance, so the review report still reads in the order the
conditions were met.

### D3 — Do not renumber, recount, or "fix" the existing rows in place

The 282 affected nodes keep their flag. Their data is correct; only the multiplicity is
wrong. A one-off script that edited `clean.tsv` would be obsolete the next ingest, and
`data/projects.json` is derived — the correction belongs in the code that produced it.

## The misdiagnosis, recorded so it is not repeated

This was initially reported as **nondeterministic emission**, and that was wrong in a way
worth preserving:

| claim | how it was disproved |
|---|---|
| set/dict iteration order | pinning `PYTHONHASHSEED=12345` still gave ~250 differences |
| slow convergence | counts went 253 → 261, i.e. **up** |
| the emission is unstable | `--from-js` **alone** is byte-stable across two runs |

The discriminator is cheap and worth stating as a habit: **run it twice and compare.** If the
second run is identical the problem is idempotence, not determinism; if it differs, check
whether a value *grew* or *moved*. Growth means append-without-dedupe. Movement means ordering.
Here it grew by exactly one copy of exactly one flag per run, which is why every ordering
hypothesis fit the surface observation and none survived the check.

## Risks

- **A 880-string deletion in the diff.** Large, and unrelated to whatever else is in the
  same commit. The diff is real and is the point of the change, but it should be its own
  commit so it is not mistaken for churn.
- **D2 could mask a genuine repeat.** If some future condition were legitimately expected to
  fire twice with the same text, deduplication would hide that. No such condition exists
  today; the stage/platform disagreement is a property of the pair, not an event.

## Migration

None. One `--links` run after the fix collapses the existing duplicates and produces the
stable file that later runs then reproduce exactly.