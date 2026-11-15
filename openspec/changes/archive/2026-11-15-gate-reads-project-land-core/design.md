## Context

See `proposal.md`. `refresh_project` loads the cache, then calls `verify_view_verified_ids(own_land_core=cached.land_core, …)` in two places: the re-decision of a recorded rejection and the view-verified gate. `urtpe/links.py` holds no derivation from the project id. `scripts/repair_land_cores.py` (F5 part A) has `expected_core` with the unit-id regex.

## Goals / Non-Goals

**Goals:** one derivation of the core from the id; the refresh never decides a case against a core that contradicts its id; the cache is corrected; the correction is named.

**Non-Goals:** discovery's core; the portal index; ids that are not unit ids; the payload (F5 part A already repaired the 3 caches).

## Decisions

**1. The derivation lives in `urtpe/links.py`** as `expected_land_core_of_project_id`, with the regex `^(.+?區)-([^-]+)-(\d[\d-]*地號等\d+筆)$`. The script imports it. *Alternative:* the refresh reads the payload. Rejected: six scripts call `refresh_project` and none passes the payload, the same shape as the `own_parcels` defect (F3).

**2. Heal at the top of the refresh**, next to the `own_parcels` block, before the re-decision step: if the derived core is non-empty and differs from `cached.land_core`, set it, record `report["land_core_healed"] = [old, new]` and set `changed`. Both later calls then read the corrected `cached.land_core`. One place, so both decisions agree.

**3. A twin or a non-unit id keeps the cache's core.** The derivation returns an empty string and the block does nothing. The `-2` twin of 市府220-2 holds the correct core and has no payload project.

**4. The report key is always present** (an empty list when nothing healed), as `view_gate_no_parcels` is.

## Risks / Trade-offs

- [A cache's core is right and the id is stale] → the id is the slug of the latest approval's core and the core in the cache comes from the same anchor at discovery time; they disagree only after a drift, and F5 measured 3 of 675. The report names each heal, so a wrong heal is visible.
- [The heal changes a cache outside a re-emit] → it runs only in a refresh, which already writes the cache; the report names it.

## Migration Plan

1. Land code and tests. The full suite stays green. No data run is needed: the 3 caches are repaired.
2. Roll back by reverting the commit; the field is the same one the cache already holds.
