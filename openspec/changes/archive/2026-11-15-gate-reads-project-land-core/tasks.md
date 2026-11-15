## 1. Tests first (offline; red before any implementation)

- [x] 1.1 In `tests/test_section8_anchor_parcel_drift.py`: a cache with the wrong district keeps `09609301` (not in `view_rejected`) and heals its core in one refresh
- [x] 1.2 Same file: the report names the project with `[old, new]` under `land_core_healed`; a cache with a correct core reports an empty list
- [x] 1.3 Same file: a `-2` twin id keeps the cache's core and heals nothing; a unit-id cache with an empty `land_core` is healed from the id
- [x] 1.4 Same file: `expected_land_core_of_project_id` is importable from `urtpe.links` and equals `repair_land_cores.expected_core` on every payload project id
- [x] 1.5 Confirm the tests are red for the right reason (missing key and function), not for a fixture error

## 2. Implementation

- [x] 2.1 Add `expected_land_core_of_project_id` to `urtpe/links.py`; make `scripts/repair_land_cores.py` import it
- [x] 2.2 Heal and report at the top of `refresh_project`, before the re-decision step, and add the always-present `land_core_healed` key

## 3. Close

- [x] 3.1 Run the full suite; refresh the counts in `AGENTS.md`
- [x] 3.2 `openspec validate gate-reads-project-land-core`; run the archive on a copy of `openspec/` first and compare the synced spec
- [x] 3.3 Mark F5 part B done on the board in `docs/inspection-batchF.md`; commit
