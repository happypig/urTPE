## 1. Tests first (offline; red before any implementation)

- [x] 1.1 `tests/test_unit_sibling_walk.py`: predicate tests for `unit_accepts_case_name` — land core at the threshold accepts; an own-parcel name in the own section accepts only with `require_equal_count=True` and an equal count; the same name with an unequal count is refused by the walk's form and accepted by the gate's form; a nameless or parcel-less name is refused; a name of another section is refused
- [x] 1.2 Same file: gate parity — `verify_view_verified_ids` gives the same kept/rejected set as before the refactor on the 華中247, 吳興163-2 and foreign-id fixtures, and on every held case name of the live payload (pair by pair against the old inline expression)
- [x] 1.3 Same file: walk tests with injected header and milestone adapters — the 懷生16 shape (three interior ids join), a foreign id is refused and recorded `other_unit`, a header with no name is recorded `none`, an id held by another project is skipped without a request, no id outside a stem's held minimum and maximum is probed, a second run issues zero requests, an adapter failure is not recorded and is retried, `max_requests` stops the walk and reports it, a joined case carries name, header and milestones
- [x] 1.4 Same file: `sibling_probed` round-trips through `save_project_cache` and `load_project_cache`; a cache without the field loads with `{}`
- [x] 1.5 `tests/test_walk_unit_siblings_script.py`: the driver's dry run issues no request and writes nothing; `--apply` backs up each changed `result.json` first, writes, and a second `--apply` changes nothing; the lock refuses a second writer
- [x] 1.6 Confirm the new tests are red for the right reason (missing function, field and script), not for a fixture error

## 2. Domain: the predicate and the field

- [x] 2.1 Add `unit_accepts_case_name` to `urtpe/links.py` and make the gate's `city_ok` call it with the default keyword; the early `not city_lc` branch stays in the gate
- [x] 2.2 Add `DiscoveryResult.sibling_probed` and load it with `.get`; check that `save_project_cache` writes it
- [x] 2.3 Add `walk_unit_siblings` per the design (candidates, header, decision, in-place join, report, cap); adapters default to the live ones and are injected in tests

## 3. Adapter: the driver

- [x] 3.1 Add `scripts/walk_unit_siblings.py` (dry run by default, `--apply`, lock, backup `…_siblingwalk`, 1 s pacing, `--max-requests`, a report that names every refused id once with its name)
- [x] 3.2 Dry run on the live caches; compare the candidate list with the F4 probe list (63 interior ids); report any difference

## 4. Live run and re-emit

- [x] 4.1 `--apply` on the live caches; check the report (7 land-core ids added in 4 projects; `09012312` not added; the rest recorded)
- [x] 4.2 Re-emit (`python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`); count nodes, badges, callouts and orphan flags before and after; record the numbers in `docs/inspection-batchF.md` F4
- [x] 4.3 Add live pins: the 7 ids are held by their projects; no id is held by two projects through the walk; `sibling_probed` and `city_case_ids` do not overlap; re-pin `tests/test_national_badge.py` and `tests/test_joined_node_callouts.py` to the new counts with the existing drift-naming messages
- [x] 4.4 Run the viewer smoke (`node scripts/viewer_smoke.js`) on the new payload

## 5. Close

- [x] 5.1 Run the full suite; refresh the counts in `AGENTS.md`
- [x] 5.2 `openspec validate unit-sibling-id-walk`; run the archive on a copy of `openspec/` first and compare the synced spec
- [x] 5.3 Mark the F4 row of the Order table done in `docs/inspection-batchF.md`; commit
