## Why

A unit's cases sit in the 7-digit id stems it already holds, but the pipeline finds a
case only through the parcel search or the national view page. When neither names a
sibling, the unit never holds it. The step-2 id walk could reach it, but it runs only for
an unplaced node and accepts only on that node's 案名 and date. A sibling has neither.

Measured 2026-11-15 (`docs/inspection-batchF.md` F4): 63 interior-gap ids probed read-only
in 52 projects. 15 are no case, 40 belong to another unit, and **8 are the unit's own**
(懷生16, 萬隆463, 百齡342, 雙園505, 長春559-5). Seven match the unit's land core;
`09012312` passes only by the own-parcel rule with unequal counts (`等69筆` against
`等80筆`) and is unproven. The 8 is a lower bound. The user decided D3 = A and D4 = A.

## What Changes

- Add `walk_unit_siblings` in `urtpe/links.py`. For every held id's 7-digit stem it
  probes each digit between the lowest and the highest held digit that the cache
  does not hold, that no other project holds, and that an earlier run did not
  already probe. It reads the case header and accepts a case on positive evidence.
- Add one predicate, `unit_accepts_case_name(own_land_core, case_name,
  own_parcels)`: a parseable land core that scores at least `LINK_THRESHOLD`, or a
  name that declares the unit's district+section and one of its own parcels. The
  walk accepts the own-parcel form only when the name's declared count equals the
  unit's (a provisional keyword that F7's single count rule replaces; it keeps
  `09012312` out). The §8 gate's `city_ok` calls the same predicate with that
  keyword off, so the gate's verdicts do not change. A missing or
  parcel-less name is **not** accepted by the walk, because the gate keeps those on
  no-evidence grounds and a walk that did the same would admit every neighbour.
- An accepted case joins the cache in place and append-only (`city_case_ids`,
  `candidate_names`, `case_case_names`, `case_milestones`, `case_headers`).
- A probed id that is not accepted is remembered in a new cache field
  `sibling_probed` (`none` or `other_unit`), so no later run repeats the request.
  The field round-trips; an older cache loads with `{}`. An adapter failure is not
  remembered.
- Add `scripts/walk_unit_siblings.py`: dry-run by default; `--apply` takes the
  single-writer lock, backs up every `result.json` it changes, paces 1 s per request
  and stops at a request cap. The emission side issues no request (the design rule
  of `resolve_node_cases`).
- Re-emit once and pin the payload effect: the 7 land-core ids are held, no id is held by two
  projects through this path, and the badge and callout counts are re-pinned.

Not in scope: ids beyond a stem's lowest or highest held digit; other stems of the
same filing day; the declared-count condition for the gate and the held-by-no-project
pairs (F7, which also decides `09012312`); the stem rule that cross-lists
larger units' cases (F8).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-link-discovery`: adds two requirements — a unit-level id-stem sibling
  walk with its acceptance predicate, and the persisted probe memo that keeps it
  from repeating a request.

## Impact

- `urtpe/links.py`: `walk_unit_siblings`, `unit_accepts_case_name`, the gate's
  `city_ok`, `DiscoveryResult.sibling_probed`.
- `scripts/walk_unit_siblings.py` (new); a live run of at most 63 read-only header
  requests, plus up to 8 milestone fetches.
- `data/.link_cache/*/result.json` for the projects that gain a case or a probe
  memo; `viewer/projects.data.js`, `data/projects.json` (the normal ~24 MB re-emit).
- Tests: new offline tests, live pins, and re-pinned badge/callout counts
  (`tests/test_national_badge.py`, `tests/test_joined_node_callouts.py`).
- Depends on F3 (done, `91f7088`): the walk reads `own_parcels` from the cache.
- Scope is provisional where measured: the 7 ids rest on one probe pass; the
  payload effect is measured in the re-emit task, not claimed here.
