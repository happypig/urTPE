# Design: merge-across-count-shrink

## Context

Actors: `urtpe/merge.py` `score()` (the pure similarity function), `_clusters`
(union-find on links ≥ 0.7), `slug_for` / `pick_anchor` (the anchor rules),
`scripts/build_project_aliases.py` + `urtpe/links.py` `load_alias_table` (the
cache-dir migration), and the emitted payload (`viewer/projects.data.js`).

Flow: clean.tsv → `_candidates` (same district+section or shared named anchor)
→ `score` per pair → union-find at ≥ 0.7 → families → project_id from the
anchor's land core. A shrinking approval (`等4筆(原29筆)`) keeps the first
parcel but replaces the parcel set, so Jaccard collapses to ~0 and the pair
scores 0.639–0.690 — below the threshold. The family splits; both halves
carry the same national page and case ids.

## Decisions

### D1 — The bridge is a declared-history rule, not a threshold change

`score()` gains one branch after the section test:

```
if a.district == b.district and a.section == b.section \
        and a.first_parcel == b.first_parcel \
        and (a.orig_count and b.land_count and a.orig_count == b.land_count
             or b.orig_count and a.land_count and b.orig_count == a.land_count):
    # the gazette declares the continuity: (原N筆) names the other record's
    # count. The parcel set was replaced by the plan change, so the Jaccard
    # term measures the change, not the unit — drop it and normalise the
    # surviving components (the empty-parcel rule's redistribution).
    fp = 1.0 if a.first_parcel == b.first_parcel else <alias band>
    cnt = 1.0  # the bridge IS the count match
    return (0.35 * sec + 0.2 * fp + 0.1 * cnt) / (0.35 + 0.2 + 0.1)
```

The first-parcel test is exact. An alias match (0.95 band) under the bridge
normalises to 0.95 — still ≥ 0.7. The branch sits beside the existing
empty-parcel redistribution and reuses its shape, so the two special cases
read as one pattern: a term that measures the wrong thing is dropped, not
tuned.

### D2 — `cnt = 1.0` inside the bridge

The standing bridge (0.8) exists for pairs whose similarity still carries
Jaccard; inside the shrink bridge the gazette's own `(原N筆)` states the
continuity, so the count component is a match. Measured: all 11 pairs score
1.0 (exact first parcel) — comfortably above 0.7 and above the flag band.

### D3 — Cache migration through the standing alias mechanism

After the re-merge, the newer id (the shrink's project_id, e.g.
`信義區-吳興段二小段-790-6地號等4筆`) merges into the older family; the family's
project_id re-derives from the anchor (the newest approval — the shrink row
itself, so the id keeps `等4筆` and the OLD id `等29筆` retires).
`scripts/build_project_aliases.py` pairs the retired id on member content and
writes `data/project_aliases.json`; `load_alias_table` migrates the cache dir
at the next discovery. The script's ambiguous-pair refusal stands.

### D4 — Where the merge runs

The standing `merge(records)` path — no separate pass. The re-emit is the
ordinary `python -m urtpe.cli --from-js viewer/projects.data.js -o data
--links` (identity changes flow through `--from-js`'s project loading; the
TSVs re-derive from clean.tsv on a PDF run, and the payload regenerates from
the merged projects on both).

## Consequences

- 11 split pairs join; 10 duplicate national pages collapse to one project
  each. The viewer stops showing one development twice.
- The merged families gain the union of both halves' nodes; the twin orphan
  fold (C6) then applies to the combined case set.
- `docs/dataset_completeness_audit.md`'s "Watch, do not fix" list loses its
  14 under-merge cores' largest measured shape.
