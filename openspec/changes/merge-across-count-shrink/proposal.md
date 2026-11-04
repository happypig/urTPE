# Proposal: merge-across-count-shrink (S13 — C9)

## Why

A plan change that shrinks the site (`等4筆(原29筆)`) keeps the first parcel
and earns the count bridge (`orig_count == land_count` → 0.8), but its new
parcel set barely overlaps the old one, so `urtpe/merge.py:40`'s score stays
near 0.64 and the merge splits one 更新單元 into two projects. The second
project then carries the same national page, the same case ids and the same
construction dates as the first, so the viewer shows one development twice.

Measured over the corpus (2026-11-04): **11 split pairs**, 10 of which share
one national page — 吳興790-6 (view/118, recno 978 等4筆(原29筆) vs recno 1157
等29筆, score 0.639), 中山202 (view/319), 中正44 (view/321), 犁和89 (view/637),
桃源251 (view/84), 立農513 (view/281), 南港566, 玉成545 (view/718),
芝蘭130 (view/276), 玉泉91 (view/231), 金華719 (view/358). Every pair scores
0.639–0.690 — below the 0.7 link threshold by the Jaccard term alone.
`docs/dataset_completeness_audit.md:184` already listed 吳興790-6's land core
as an under-merge ("second row says `(原29筆)`") and classed the 14 such cores
as "Watch, do not fix"; C9 is that watch item, now measured.

## What changes

- `urtpe/merge.py` `score()`: when district + section + first parcel match
  **and** the declared history bridges the pair (one record's `orig_count`
  equals the other's `land_count`), the similarity SHALL be computed without
  the parcel-Jaccard term — the surviving components (section .35, first
  parcel .2, count bridge .1) are normalised over their sum, exactly the way
  the empty-parcel rule at `merge.py:73` already redistributes weight. The
  bridge counts as a full count match (`cnt = 1.0`) in the normalisation
  because the gazette itself declares the continuity (`(原29筆)` names the
  older approval's count). Score for the measured pairs: (0.35 + 0.2 + 0.1)
  / 0.65 = **1.0** for a full match; a renumbering first-parcel alias scores
  0.95 · the same normalisation.
- The borderline band (0.5–0.7) is unchanged for every other pair shape.
- Re-merge, then `scripts/build_project_aliases.py`: the newer id merges into
  the older family; the displaced project_id's cache dir migrates through
  `data/project_aliases.json` (the standing mechanism, refuses ambiguous
  pairs).

## What does not change

- The similarity weights (0.35/0.2/0.3/0.1) for every pair the bridge does
  not describe.
- `slug_for` / `pick_anchor`: the merged family re-anchors on its newest
  approval by the standing rule.
- The fragment-family detection (§6.8) and the orphan gate.

## Capabilities

### Modifications

- `case-merging`: MODIFIED — the "Link records by similarity" requirement
  gains the count-shrink bridge scenario; the existing scenarios stand.

## Risks

- Over-merging a coincidental same-section/same-first-parcel pair whose
  `orig_count` equals the other's count by chance: the gazette prints
  `(原N筆)` only on the shrinking approval of the same unit, and the
  first-parcel requirement is exact (not an alias), so the shape is the
  publisher's own statement of continuity. The 11 measured pairs are all
  true units; no over-merge appeared in a dry simulation over the corpus.
