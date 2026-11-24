# Proposal: d11-search-guard-count-rule

## Why

The search guard (S1, `urtpe/links.py` `_search_taipei_raw` via
`membership_verdict(…, "search_guard")`) keeps a case whose name declares any of
the unit's own parcels, with no count test. F3 made discovery pass `own_parcels`
to the guard; a fresh discovery, or a refresh with a 5-part search key, would
re-accept the 46 held-by-no-project pairs that D2 had left out, because nothing
holding counts guards that form. Batch F measured the pair set at 62
(46 held by no project, 9 held here, 7 held elsewhere), frozen in
`tests/fixtures/s1_accepts_count_rule_refuses.json`. The user decided on
2026-11-15 (D11 = A, recorded in `docs/inspections/inspection-batchF.md` and the
optimization board, Part II): S1's own-parcel form adopts the count rule — the
first F1 phase-2 unification, moving the guard from "declares any own parcel" to
"declares any own parcel AND a count the unit declared at some approval".

A fresh discovery has not run since F3, so nothing moves today; the change
closes the door before a future discovery or refresh opens it.

## What Changes

- The `search_guard` policy's own-parcel form adopts the count rule: a name
  admitted because it declares an own parcel must also declare a count (`等N筆`,
  or one of its `原N筆`) equal to the unit's count at ANY approval — a member of
  `own_counts` or the unit's land-core count.
- The count test reuses the gate's rule (`_unit_membership_reason`, F7),
  so S1 and S2 agree on the same evidence.
- The legacy **stem form is out of scope**: of the 62 pinned pairs, 8 sit in the
  stem form (all held-here cross-listings, e.g. 大龍段265-7's 10908271–274);
  removing them is F8 option C, which the user decided waits for D11 and the
  S3/S5 choice. The stem form keeps its current behaviour.
- The `exact` form keeps its current behaviour (the searched parcel itself needs
  no count test; 臨沂412's kept case 10305021 is an exact hit).
- `corroborated_area` (parcel-less names) keeps its current behaviour.
- The guard needs the unit's counts on the call path: `search_taipei_cases_api`
  gains an `own_counts` parameter, `discover_project_links` passes
  `own_counts_of(project)`, and `refresh_project` passes the cached counts
  alongside `own_parcels` in its search key.
- The pin fixture stays frozen at 62 pairs (it records the form-versus-rule
  measurement, which D11 does not change); its test is reinterpreted: after the
  change the guard refuses the 54 own-parcel pairs and still admits the 8 stem
  pairs (F8-C's territory). The set may shrink, never grow.
- No verdict changes today: no fresh discovery has run since F3, so the 54
  refusals change no cache and no payload; they bind only future fresh runs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `taipei-case-discovery`: the name guard keeps a case naming any of the unit's
  own parcels only when its declared count passes the count rule. (The own-parcel
  form lives in this spec alone; `official-link-discovery` states only the
  searched-parcel rule and the corroboration rule, which D11 does not touch, and
  its walk and admission requirements already carry the count rule since F7.)

## Impact

- `urtpe/links.py`: `membership_verdict` (`search_guard` branch),
  `search_taipei_cases_api`, `_search_taipei_raw` (new `own_counts` parameter),
  `discover_project_links`, `refresh_project`.
- Tests: `tests/test_membership_verdict.py` (golden table regenerates: 65 S1
  verdicts move accept→refuse, measured 2026-11-24), `tests/test_links.py`
  (§6.7 guard), `tests/test_bind_unplaced_by_cell_section.py`,
  `tests/test_unit_count_rule.py` (the 62-pair pin shrinks to 8),
  `tests/test_gaiyao_track.py`, `tests/test_named_area_cases.py`.
- Fixture: `tests/fixtures/s1_accepts_count_rule_refuses.json` shrinks (62 → 8
  stem pairs) once, in the same change, with a regeneration command recorded.
- Fixture: `tests/fixtures/membership_golden.json` regenerates (65 S1 pairs).
- No payload change: the guard runs at discovery/refresh time, not emission, and
  no fresh discovery has run since F3.
- Windows task `urtpe-cycle` (04:00 daily) runs the suite in its gate; the
  change must land green before the next 04:00.
