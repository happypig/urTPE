# Tasks: merge-across-count-shrink

## 1. Tests (test-first — all checked before any implementation task)

- [ ] 1.1 Unit test: the shrink pair (等4筆(原29筆) vs 等29筆, same section +
      first parcel, disjoint parcel sets) scores ≥ 0.7 —
      `tests/test_merge_count_shrink.py::TestShrinkBridge`
- [ ] 1.2 Unit test: the 11 measured recno pairs from clean.tsv all link
      (978/1157 吳興790-6, 699/952 中山202, 485/949 中正44, 506/817 犁和89,
      1237/1336 桃源251, 656/1013 立農513, 359/1063 南港566, 336/730 玉成545,
      807/1024 芝蘭130, 875/1099 玉泉91, 81/880 金華719) —
      `TestMeasuredPairs` (marked skip when clean.tsv is absent)
- [ ] 1.3 Unit test: a coincidental same-first-parcel pair with no `(原N筆)`
      bridge keeps the standing score (no over-merge) —
      `TestNoBridgeWithoutShrink`
- [ ] 1.4 Unit test: the alias-band first parcel under the bridge still
      normalises ≥ 0.7 — `TestAliasUnderBridge`
- [ ] 1.5 Unit test: the empty-parcel rule and the shrink bridge compose (a
      shrink with unparseable parcels links) — `TestBridgeWithEmptyParcels`

## 2. Implementation

- [ ] 2.1 `urtpe/merge.py` `score()`: the shrink-bridge branch after the
      section test, normalising over the surviving weights (design D1/D2)
- [ ] 2.2 Re-merge: `python -m urtpe.cli --from-js viewer/projects.data.js -o
      data --links` (no merge change reaches the payload without a run)
- [ ] 2.3 `scripts/build_project_aliases.py`: regenerate
      `data/project_aliases.json` for the displaced project_ids; cache dirs
      migrate at the next discovery

## 3. Verification

- [ ] 3.1 `python -m pytest` full suite green
- [ ] 3.2 The re-emitted payload: the 11 pairs read as one project each; the
      national-page duplicates are gone; smoke + baseline pass
- [ ] 3.3 `openspec validate --all` green; archive the change and sync the
      delta
