## Context

The pipeline is PDF → positional parse → raw.tsv → cleanse → clean.tsv → similarity merge → merged.tsv → projects.json → viewer. `cleanse.py` derives structured fields per record (section, first parcel, parcel set, counts, aliases, anchor, stage, track); `merge.py` scores candidate pairs with `score()` (weights: section .35, first-parcel .2, parcel-set Jaccard .3, land-count .1; named anchor short-circuits to 1.0) and clusters via union-find at a link threshold of 0.7, flagging 0.5–0.7 pairs as borderline. Implementer is already absent from the score.

The observed failure: some source 地號 cells omit the 地號 separator (e.g. `臺北市中山區中山段二小段1251筆土地`). Cleansing then yields an empty parcel set and a `缺少地號清單` flag, so the `if s1 and s2` guard drops the entire .3 Jaccard weight and a perfect land-key match scores 0.65 — under the 0.7 link threshold. See proposal.md - Why for the affected families (125/302/531).

## Goals / Non-Goals

**Goals:**
- Recover a record's parcel identity from the 案名 when the 地號 cell is malformed.
- Let identical land keys link even when both parcel sets are empty, across implementer changes.
- Keep implementer out of the score and keep ambiguous cases in the review pipeline.

**Non-Goals:**
- No change to the link/flag thresholds (0.7 / 0.5–0.7) or the other feature weights.
- No change to anchor selection, slugging, or project_id stability.
- No full rework of `_parse_land`; the fallback is additive to the existing derivation.

## Decisions

**D1 — Name-derived parcel fallback in cleansing (`cleanse.py`).**
`parse_name_id()` already extracts section, first parcel, and land count from the 案名 (name is the stable identity — the 地號 cell can wrap or be malformed). Extend the derivation: when the 地號 cell yields no parcel list, parse the 案名's land fragment (`…二小段125地號1筆…` → parcels `{125}`, count 1; `…531地號等2筆…` → first_parcel `531`, count 2) and populate `parcels` where recoverable. When the count is 1 and the name names the single parcel, the set is exact; when the count is >1 and the name names only the first parcel, the set stays `{first}` (partial but non-empty) — Jaccard is then computable between any two records of the same unit that both carry `{531}`.
*Alternative considered:* leave parcels empty and only rebalance merge weights. Rejected — rebalancing alone still leaves the record without any parcel set, weakening the Jaccard signal between a malformed record and a well-formed one.

**D2 — Weight rebalancing when both parcel sets are empty (`merge.py`).**
In `score()`, when both records have empty parcel sets but share district + section + first_parcel + land_count, treat the land key as full agreement: renormalize the Jaccard weight into the surviving components so the score reflects the agreement. Concretely: the .3 Jaccard weight is redistributed proportionally to the present components (section, first parcel, count), so a full land-key match scores 1.0 and links. If the land key does not fully agree, the existing components (with Jaccard still 0) keep the pair at or below the old value — no over-merging.
*Alternative considered:* hard-link rule ("same land key ⇒ merge") independent of score. Rejected — bypasses the borderline/flag path and could over-merge when first-parcel/count match but the true parcel sets differ.
*Alternative considered:* lower LINK_THRESHOLD to 0.6. Rejected — this is a structural weight bug, not a threshold calibration issue; lowering would also loosen every non-empty-parcel pair.

**D3 — Implementer stays out of the score (unchanged).**
The proposal and specs already state land is the sole identity. This change only removes the accidental coupling where a malformed cell silently promoted the .3 weight to 0. No code uses implementer in `score()` today; none will.

**D4 — Keep the `缺少地號清單` flag on records whose parcels came from the name fallback.**
The source cell is still malformed; the flag keeps the data-quality signal visible in the review report and viewer, even though the fallback now supplies identity.

## Risks / Trade-offs

- [Name-derived parcels are partial for count > 1] → Jaccard between two `{531}` sets is 1.0 and between `{531}` and a full set is lower but computable — monotone with real overlap; the rebalance in D2 handles the both-empty case.
- [Renormalizing weights changes the meaning of scores] → Only when both sets are empty; pairs that were correctly at 0.65 (borderline) and genuinely distinct will not gain points unless the land key fully agrees.
- [Regression risk on 718 projects] → Existing 41-test suite plus new cases for 125/302/531 families; re-run the full pipeline and diff project counts against the archived baseline (718 projects today; expect fewer singleton splits).
- [Name fallback may mis-parse an unusual 案名 form] → The fallback only fires when the 地號 cell is already unparseable; a wrong guess is still flagged for review rather than silently merged.

## Migration Plan

1. Implement D1 + D2 with tests.
2. Re-run the pipeline end-to-end (`python -m urtpe.cli source.pdf -o data --viewer viewer`).
3. Diff `data/merged.tsv` project count and the specific families (125/302/531) against the archived baseline.
4. Re-verify ground-truth clusters (永昌159, 中華工程, 逸仙151, 東星) still merge correctly — the rebalance must not disturb them.