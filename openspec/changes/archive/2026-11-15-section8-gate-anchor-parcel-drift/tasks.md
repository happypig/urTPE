## 1. Tests first (all red before any implementation)

- [x] 1.1 Gate unit tests in `tests/test_view_case_ownership.py`: a drifted name (land core `201-2`, own core `247`, own parcels include `201-2`) is kept; a same-section name with none of the unit's parcels (09608220 shape) is rejected shape A; a name carrying an own parcel in another district or section is rejected; no parcel list leaves the land-core rule alone (the old results hold); a parcel-less name still does not reject; the token boundary `220` against `2201` and `220-3` against `220-31`.
- [x] 1.2 Re-decision tests: a cache whose `view_rejected` holds a drifted id has it lifted and re-absorbed with its milestones fetched (injected fetcher, no network); an id the rule still rejects keeps its record and triggers no fetch; a record with no held city name stands; a second run lifts nothing.
- [x] 1.3 Persistence tests: discovery writes `own_parcels` beside `land_core`; a `--fresh` discovery carries it forward; `refresh_project` with a five-part key overwrites it; a cache without the field loads with an empty list; the gate reads the cache field when no key carries parcels (a call with no `search_key` gives the same answer as one with it).
- [x] 1.4 Anchoring test in `tests/test_orphan_anchoring.py` (or the file that owns the 09305081 shape): the drifted id anchors on the node of its date and creates no ghost; a same-section foreign id creates none.
- [x] 1.5 Live-cache pins in a new `tests/test_section8_anchor_parcel_drift.py`: the population before the correction (11 ids in 10 projects) and after (8 ids in 8 projects: 7 foreign and 市府220-2); 華中247 holds seven `taipei` ids; 吳興163-2's `view_rejected` is empty. These read the live payload and the cache, as `test_national_badge.py` does, and name the drift in the assertion text.
- [x] 1.6 Live-payload pin in the new test file: 華中247's node of 2014-04-25 and node of 2015-10-02 each carry both of their cases in `links.taipei`. The smoke harness's overlap guard already runs on every project with callouts; it must stay green after the re-emit (task 4.3).
- [x] 1.7 Run the new tests and confirm each one fails for the stated reason (not an import or fixture error). Result: 21 red (a missing `own_parcels` argument, field or helper; the live payload still holds 11 rejected ids); 2 pass by design — the no-parcels-behaves-as-before pin and the anchoring pin, which guard behavior that must not change.

## 2. The gate and the cache field (domain logic)

- [x] 2.1 Add `own_parcels` to `DiscoveryResult` with an empty default. Write it in discovery from the anchor record, carry it forward on `--fresh`, and fill it in `refresh_project` when the key has a parcel list.
- [x] 2.2 Add the own-parcel acceptance to `verify_view_verified_ids`: a new `own_parcels` argument; condition 1 (section text equal) then condition 2 (`_case_name_carries_parcel`). Keep the shape A / shape B reasons and the missing-name rule unchanged. Comment the why: cite the 華中247 measurement and the 09608220 refusal.
- [x] 2.3 Pass the own parcels from `refresh_project` to the gate: the key's list first, the cache's `own_parcels` second, empty last.
- [x] 2.4 Add the re-decision step first in the view part of `refresh_project`. Report each lifted id in the run report (`view_rejection_lifted`), so a lift never reads as silence.
- [x] 2.5 Run tasks 1.1 to 1.4 and confirm they pass. Run `tests/test_view_case_ownership.py`, `tests/test_refresh_view_absorb.py` and `tests/test_supersede.py` for the S3a and round-trip pins.

## 3. Adapter: the backfill and the correction run

- [x] 3.1 Write `scripts/backfill_own_parcels.py` (durable, undated). It reads `data/projects.json`, and for each cache that holds `view_verified_case_ids` or `view_rejected` it writes `own_parcels` from the anchor record's parcel list. It refuses to run without the single-writer lock, copies each `result.json` it will change into `data/.link_cache_backup_<stamp>_ownparcels/` first, and supports `--dry-run`. It never deletes.
- [x] 3.2 Test the script on a temporary cache directory: dry run writes nothing; a real run writes the field and the backup; a second run changes nothing.
- [x] 3.3 Run the script with `--dry-run`, read the list (expect the caches that hold view ids), then run it for real.
- [x] 3.4 Run the refresh on the three affected caches with the five-part key (`refresh_unplaced_by_cell_section._search_key` shape), under the lock. Run for 華中247 and 吳興163-2 only (市府220-2 and the seven foreign ids are not refreshed, so their records stand). Result: three ids lifted, 0 errors, 26 city requests (13 milestone, 11 header, 2 view page; no search, because no key was passed).

## 4. Re-emit and the pins that move

- [x] 4.1 Re-emit once: `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links`. Confirm exit 0.
- [x] 4.2 Measure the payload: 華中247's seven `taipei` ids and its two joined nodes; the `national_badges` counters; the `view_rejected` population. Re-pin from the measured values. Measured: `national_badges` 806 → 808 (the binding count stays 1,197); joined nodes 30 → 32, area pairs 28 → 30, `implementation_by_case` nodes stay 30 (the two new joined nodes have no implementation payloads, so no new section callout). Re-pinned `tests/test_national_badge.py` and `tests/test_joined_node_callouts.py`; AGENTS.md counts refreshed to 1360 collected / 1359 passed / 1 skipped.
- [x] 4.3 Run `node scripts/viewer_smoke.js` and the full `python -m pytest`. Run `python scripts/check_deploy.py` and read the stale report (the push is the user's step).
- [x] 4.4 Update `docs/inspection-batchE.md` E10: the measured outcome, the three ids, the 市府220-2 exception and its cause, and the limit of the population count.

## 5. Archive

- [x] 5.1 Copy `openspec/` to a temporary directory and run `openspec archive section8-gate-anchor-parcel-drift --yes` there. Read the report (`+ 1, ~ 2`) and compare the synced specs with the delta.
- [x] 5.2 Run the real archive, then `openspec validate --specs`. Commit with path-scoped paths: `openspec: archive section8-gate-anchor-parcel-drift and sync its two spec deltas`.
