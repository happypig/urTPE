## Why

The §8 gate and the re-decision step compare a city case name with the land core stored in the cache's `result.json`. 市府220-2's cache held the district 中正區 (the unit is 大同區) for more than two months, so the gate refused `09609301`, a correct case. Three of 675 caches disagreed with their project id. F5 part A (`f9b779c`) repaired them. Nothing stops the next wrong copy from deciding a case.

A unit's project id is the slug of its land core, so the id already spells the core. `docs/inspection-batchF.md` F5 and the user's decision D5 = C ask the gate to read that core.

## What Changes

- Add `expected_land_core_of_project_id(project_id)` in `urtpe/links.py`: the id's three parts joined, or an empty string when the id is not a unit id (a `-N` twin, `未解析-N`, `地號等?筆`). `scripts/repair_land_cores.py` imports it, so one definition serves both.
- `refresh_project` uses that core, when it exists and differs from the cache's, for the re-decision step and the §8 gate. It writes the core into the cache and names the project in a new report key `land_core_healed` (`[old, new]`).
- With no unit-id shape, or an equal core, nothing changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cache-freshness`: the view-verified verification decides against the unit's land core (the id's core when the id is a unit id) and not the cache's copy; a new requirement heals and reports a core that disagrees with the id.

## Impact

- `urtpe/links.py` (`refresh_project`, one new helper); `scripts/repair_land_cores.py` (imports the helper).
- No payload change expected: F5 part A already repaired the 3 caches. The live pin of part A stays.
- Tests: new offline tests in `tests/test_section8_anchor_parcel_drift.py`.
- Not in scope: discovery's own core (built from the anchor record), the portal-index lookup, non-unit ids.
