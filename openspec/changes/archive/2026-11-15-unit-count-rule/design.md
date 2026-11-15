## Context

See `proposal.md`. Today `unit_accepts_case_name(own_land_core, case_name, own_parcels, *, require_equal_count=False)` is the one predicate. The gate calls it with the default (no count test). The walk passes `require_equal_count=True`, a provisional hold-back that F7's rule replaces. `DiscoveryResult.own_parcels` is the model for a required, persisted unit input: set by discovery on both paths, backfilled, pinned live, with a named empty state (`view_gate_no_parcels`).

## Goals / Non-Goals

**Goals:** one count rule in one predicate; the counts are required, persisted and pinned; an empty list is named; the 7 measured pairs are admitted by a command with a dry run.

**Non-Goals:** the search guard (S1) and the orphan branch (S5) keep their rules; the stem rule; the 46 other pairs; changing any gate verdict on today's payload.

## Decisions

**1. `unit_accepts_case_name(own_land_core, case_name, own_parcels, own_counts=())`.** The land-core branch is unchanged and needs no count. The own-parcel branch also requires the count test: the unit's counts are `set(own_counts) ∪ {the land core's count}`; the name passes when its `等N筆` (the first count in its land core) or any `(原N筆)` is in that set. The keyword `require_equal_count` is removed. *Why the land core's count is always included:* it is one of the unit's counts, and it makes an empty `own_counts` mean the equal-count rule, the narrower of the two, never a silent widening.

**2. `own_counts_of(project)` and the field.** `DiscoveryResult.own_counts: list[int]`, sorted distinct, from every member record's `land_count` and `orig_count` (positive ints). Discovery sets it on a fresh result and, on the cached path, writes it only when it differs (as it does for `own_parcels`). `scripts/backfill_own_parcels.py` also writes it from the payload nodes' `land_count` and `orig_count`, with the same backup and lock. A live pin keeps every payload project's cache equal to the payload's counts.

**3. The gate and the walk pass `own_counts`.** `refresh_project` reads `cached.own_counts`; when it is empty and the gate decided any id, it reports `view_gate_no_counts` (the ids), as it does for parcels. The walk reads `disc.own_counts`.

**4. One join helper.** The walk's in-place join (city ids, `candidate_names`, `case_case_names`, `case_milestones`, `case_headers`) becomes `_join_unit_case(disc, cid, name, row, milestones)`. The admission command calls the same helper, so a case joins the same way by either route.

**5. The admission command.** For each payload project it takes each `search_rejected` id whose name passes the predicate with `own_counts`, that no payload project holds and that `view_rejected` does not record. A dry run lists the ids and issues no request. `--apply` takes the lock, backs up each changed `result.json`, reads the header and the milestones (2 read-only requests per admitted case), joins, and removes nothing from `search_rejected`. *Alternative:* delete the id from `search_rejected` on admission. Rejected: the dict is the discovery's record of what the guard dropped; the cache then holds the id both ways, which the live pin allows (`city_case_ids` is the held list).

**6. The 09012312 record.** It is `other_unit` in `sibling_probed`. Under the rule its count 69 is not among 長春559-5's counts, so the walk would refuse it again and the record stays valid. The live check in the tasks confirms this.

## Risks / Trade-offs

- [The rule is weaker for a unit with many approvals and many counts] → the numbers are pinned (22 guard-only pairs pass, 62 are refused, 3 reach the gate, 7 are admitted); a later widening fails the pin and names the pair.
- [An admitted case is another unit's] → only 7 pairs pass, each equal-count or an earlier count of the same unit; 華興8's case was read live (same implementer, same 13 parcels). The report names each admitted case.
- [`search_rejected` keeps an admitted id] → by design, see decision 5.

## Migration Plan

1. Land code and tests. Run the backfill (all caches get `own_counts`; backup first).
2. Dry-run the admission command; compare with the 7 measured pairs.
3. `--apply`; re-emit; measure and re-pin.
4. Roll back by restoring the backups and re-emitting; older code ignores `own_counts` (loaded with `.get`).
