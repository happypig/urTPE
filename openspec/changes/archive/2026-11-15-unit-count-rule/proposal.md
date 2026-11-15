## Why

The own-parcel rule of the §8 gate has no declared-count condition. It ran on 3 ids and all 3 were right, but it would admit up to 67 unproven pairs if it ran on them (`docs/inspection-batchF.md` F7). The user decided one rule for the gate, the sibling walk and the admission of held-by-no-project pairs (D1 and D2, 2026-11-15, on the advisor's recommendation).

The rule needs the unit's earlier counts as required input. A parcel list that was optional gave 華中247 its defect (F3), so the counts must not repeat it.

## What Changes

- **The count rule.** A name passes when its declared count (`等N筆`), or one of its `原N筆`, equals the unit's count at any approval. It guards the own-parcel form only; a matching land core needs no count test.
- **Required input.** A new cache field `own_counts` (sorted distinct integers), written by discovery on both paths and by the backfill. An empty list is a named report state, `view_gate_no_counts`. With no counts, only the land core's own count counts, so the narrower rule decides.
- **One predicate.** `unit_accepts_case_name` takes `own_counts`; the walk's provisional `require_equal_count` keyword goes. The gate and the walk both use the single rule.
- **Admission (D2).** A new command `scripts/admit_unit_cases.py` admits a `search_rejected` case that passes the rule and that no project holds. Measured offline: 7 cases (the 6 equal-count pairs in 潭美579-2, 光華508-6, 雙連197 ×2, 雙連407, 大安590, and 華興8's `09708111`, a withdrawn 2008 predecessor).
- The walk's join becomes one helper that the admission command also uses.

Not in scope: the search guard and the orphan branch keep their rules (F1 phase 2); the other 46 held-by-no-project pairs; the stem rule (F8).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cache-freshness`: the §8 gate requirement gains the count test; a new requirement for `own_counts` and its named empty state.
- `official-link-discovery`: the sibling walk uses the single rule; a new requirement for the admission command.

## Impact

- `urtpe/links.py`: `DiscoveryResult.own_counts`, `unit_accepts_case_name`, the gate, the walk, discovery's two paths, `refresh_project`.
- `scripts/backfill_own_parcels.py` (also writes `own_counts`), `scripts/admit_unit_cases.py` (new).
- Caches (the backfill, then 7 admitted cases with 14 read-only requests); `data/projects.json`, `viewer/projects.data.js` (one re-emit).
- Measured offline, not yet on the payload: of the guard-only pairs (86 when first measured; 84 after F5's land-core repair moved two 寶清51-13 cases to a land-core match), 24 then and 22 now pass the rule; 3 reach the gate and all 3 have an equal count, so no gate verdict changes. The payload effect of the 7 admissions is measured in the re-emit task.
