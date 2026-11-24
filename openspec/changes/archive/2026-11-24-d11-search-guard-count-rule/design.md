# Design: d11-search-guard-count-rule

## Context

Actors: the search guard S1 (`urtpe/links.py` `_search_taipei_raw`, called through
`membership_verdict(…, "search_guard")`), the §8 gate S2 (`_unit_membership_reason`),
the two production callers of the parcel search (`discover_project_links`,
`refresh_project`), and the person who ratified D11 = A on 2026-11-15.

Flow: PDF → payload → discovery/refresh → `search_taipei_cases_api` → the guard →
city cases → caches → emission. The guard filters search results before the resolver
sees them; a case it drops never binds.

The gate's count rule (F7, decided 2026-11-15, in
`_unit_membership_reason`): the name's declared count (`等N筆`) or one of its
`原N筆` equals the unit's count at ANY approval — a member of `own_counts` or the
unit's own land-core count. With no `own_counts`, the land-core count is the only
count (the narrower rule, named by the caller).

## Measurements taken before this design (2026-11-24, offline, read-only)

| Fact | Figure | Source |
|---|---|---|
| The 62 pinned pairs by parcel-rule form | 54 `own_parcel`, 8 `stem`, 0 `exact` | probe over `tests/fixtures/s1_accepts_count_rule_refuses.json` + live caches |
| The 8 stem pairs' status | all `held_here` (cross-listings: 大龍265-7 ×6, 興安628-1, 玉成253-1) | same probe |
| The one held-here own-parcel pair | 臨沂412's `10205151` (413地號等3筆; counts 3 vs 11/12) | same probe |
| Tier-1 hand-checked units under the post-D11 guard | 0 refusals of 24 held cases | probe over `membership_tier1.json` |
| Golden table S1 verdicts that move | 65 of 3,094, all accept→refuse (54 pinned + 11 cross-section golden-only names) | probe over `membership_golden.json` |
| 臨沂412's kept case `10305021` | stays accepted (exact form when searched under 412; own-parcel form under 414 with counts 11/12 matching) | probe |
| Live caches whose core count is not in `own_counts` | 48 of 725 | probe over `data/.link_cache` |
| Live pin set today | still 62 (no fresh discovery since F3) | probe |

## Decisions

### D1 — scope: the own-parcel form only

`_parcel_rule` returns `exact`, `stem`, or `own_parcel`. The count test applies to
`own_parcel` only. `exact` (the searched parcel — the pre-F3 rule) and `stem`
(the legacy pre-subdivision form, F8) keep their behaviour.

Why: the decision's words are "S1's own-parcel form adopts the count rule". The
stem rule is F8's named rule; F8 option C (remove the cross-listed cases) waits
for D11 and the S3/S5 choice by the user's own decision of 2026-11-15. Refusing
the 8 stem pairs at the guard would decide F8-C by the back door: on a fresh
discovery from an empty cache those held-here cases would never be re-added.
The 8 pairs stay pinned as admitted, awaiting F8-C. The 54 own-parcel pairs are
the population the count rule refuses.

### D2 — one count rule, two sites

The gate's count test moves into a shared helper (`_count_rule_passes(name,
own_counts, land_core)`); the gate's `_unit_membership_reason` and the guard's
`search_guard` branch both call it. No test in `tests/test_unit_count_rule.py`
may move: the gate's behaviour is pinned there.

A count-refused name in the guard gets `Verdict(False, "count_refused")` — a
distinct reason, so the audit trail names why the parcel form matched and the
case still dropped. The drop lands in `dropped_out`/`search_rejected` as before.

### D3 — the guard's Unit needs counts and the land core

The guard call site builds `Unit("", own_parcels, (), anchor_name)` today. It
becomes `Unit(land_core, own_parcels, own_counts, anchor_name)`. The land core is
required by the 48-cache fact: the gate's rule includes the land-core count, and
48 live caches hold an `own_counts` that lacks it (the 地號 cell's count and the
案名's count can disagree). Dropping the fallback would make the guard narrower
than the gate on a real shape.

Plumbing:
- `search_taipei_cases_api` and `_search_taipei_raw` gain `own_counts=None` and
  `land_core=""` parameters (after the existing ones; the `TypeError` fallback
  chain in `refresh_project` already handles adapters that take fewer).
- `discover_project_links` passes `land_core=land_core` and
  `own_counts=own_counts_of(project)`.
- `refresh_project` passes `land_core=cached.land_core` (the healed core) and
  `own_counts=cached.own_counts`. The search key keeps its 5 elements — the
  counts come from the cache in hand, not from the key.
- `scripts/harvest_case_names.py` passes no `own_parcels`, so the own-parcel
  form never fires there; no change.

### D4 — the empty-counts state stays narrow

A caller that passes `own_parcels` without counts gets the narrower rule (the
guard's Unit land core empty → no core-count fallback → the count test refuses).
This matches the gate's documented narrower rule; the production callers always
pass counts after this change. A test pins the narrow state so it is a named
behaviour, not a silent widening in reverse.

### D5 — the golden fixture is re-captured, not hand-edited

Batch F's method: the characterization table is replayed after each sanctioned
site move. The `s1` column is re-captured from the post-change code over the
same frozen inputs. The regeneration asserts: exactly 65 moves, all
accept→refuse; the S2/S3/S5 columns and the node pairs unchanged; the tier-1
table unchanged (S1 already accepted every tier-1 case). History lives in git.

### D6 — the 62-pair fixture stays frozen at 62

The pin test measures the form-versus-rule population (the raw parcel predicate
against `unit_accepts_case_name`), which D11 does not change — it changes the
guard's adoption of the rule. The fixture is not shrunk. A companion assertion
pins the new guard behaviour: 54 refused, 8 admitted (the stem pairs, named).

### D7 — nothing moves in the data today

No fresh discovery has run since F3; the 2026-11-15 admission of 7 cases stands
(they pass the gate, and the guard is not re-read for held cases). The change
binds only future fresh discoveries and refreshes. No cache or payload rewrite
is part of this change; `refresh appends and never removes` keeps the held-here
pair 臨沂412 `10205151` in its cache even though the guard would now refuse it
at search time.

## Risks

- A fresh discovery after this change refuses 54 search results the old guard
  admitted. Measured: all 54 are cases the count rule refuses; none is held by
  its project except 臨沂412 `10205151`, which the cache keeps regardless.
- The `TypeError` fallback in `refresh_project` calls the adapter with fewer
  arguments for test doubles; doubles that accept `own_parcels` but not
  `own_counts` fall to the 3-arg call and keep old behaviour. No production
  caller sits on that path.
