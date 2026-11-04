## 1. Tests first

- [ ] 1.1 `tests/test_ledger.py`: a `confirm_merge` entry round-trips through `append`/`entries` with both keys, empty `field`, and no field change on either record after `apply`
- [ ] 1.2 `tests/test_ledger.py`: `Correction(confirm_merge=True)` with an empty `with_land_core` or `with_iso_date` raises `ValueError`; `describe()` names both keys and a superseding entry removes it from `effective()`
- [ ] 1.3 `tests/test_ledger.py`: `apply` returns `confirmed_pairs == [(1303, 1347)]` for a two-record fixture shaped like 吉林676; a confirmation whose second key matches no record is listed in `unmatched` and yields no pair; a key matching two records is reported unmatched as ambiguous
- [ ] 1.4 `tests/test_ledger.py`: the report counts 1 field correction + 1 confirmation as 2 applied and names the confirmation's keys
- [ ] 1.5 `tests/test_merge.py`: 1303 (`676地號等1筆`, {676}, 2010-03-25) and 1347 (18 parcels, 2008-12-31) stay two families without a pair (score 0.567, borderline) and form one family with `confirmed_pairs=[(1303, 1347)]`
- [ ] 1.6 `tests/test_merge.py`: with the pair and 1303 `land_count=18`, the project_id is `中山區-吉林段四小段-676地號等18筆`; with the pair alone it is `…676地號等1筆` (anchor rule unchanged)
- [ ] 1.7 `tests/test_merge.py`: an unconfirmed borderline pair in the same input is still not merged
- [ ] 1.8 `tests/test_cli*.py` (existing CLI test module): `build_parser().parse_args([...])` without `--ledger` yields `ledger == str(DEFAULT_LEDGER_PATH)` (the session temp path from `URTPE_LEDGER`); an ingest with no ledger file reports `manual corrections applied: 0`
- [ ] 1.9 Run the new tests and record that they fail for the expected reason (missing field / kwarg / default)

## 2. Domain: ledger and merge

- [ ] 2.1 `urtpe/ledger.py`: add `confirm_merge`, `with_land_core`, `with_iso_date` to `Correction`; validation in `__post_init__`; `describe()` for confirmations
- [ ] 2.2 `urtpe/ledger.py`: `LedgerOutcome.confirmed_pairs`; `apply()` resolves both keys to exactly one recno each, reports unmatched/ambiguous, never sets a field for a confirmation; `report()` includes confirmations in the applied count
- [ ] 2.3 `urtpe/merge.py`: `merge(records, confirmed_pairs=())` → `_clusters` unions each pair before scoring; docstrings cite the case-merging requirement and D5

## 3. Adapter: CLI wiring

- [ ] 3.1 `urtpe/cli.py`: `--ledger` default `str(ledger_mod.DEFAULT_LEDGER_PATH)`; help text names the default and the empty-string opt-out
- [ ] 3.2 `urtpe/cli.py`: pass `ledger_outcome.confirmed_pairs` into the re-merge at the ledger block
- [ ] 3.3 Full suite: `python -m pytest` green; refresh the collected count in AGENTS.md

## 4. First entries and re-ingest

- [ ] 4.1 Read 1303's and 1347's `land` and `iso_date` from `data/clean.tsv`; confirm each normalized key matches exactly one record
- [ ] 4.2 Append to `urtpe-gazettes/corrections.jsonl`: `confirm_merge` 1303 ↔ 1347 and `land_count` → 18 on 1303, `by: happypig`, `why` citing city case 09703184 `…676地號等18筆…`, national view/75, and `docs/inspection-batchD.md` D5
- [ ] 4.3 Ask the user before the re-ingest (it rewrites the tracked `data/` files and `viewer/projects.data.js`); then run the newest archived gazette through `python -m urtpe.cli <pdf> -o data --viewer viewer --links` under the lock
- [ ] 4.4 Verify: ledger report shows 2 applied, 0 unmatched; 681 projects; `中山區-吉林段四小段-676地號等18筆` holds 1303 + 1347; no `片段家族合併候選` flag on either; no other project_id changed (diff old vs new id sets); coverage guard output read and explained
- [ ] 4.5 `node scripts\viewer_smoke.js` passes; the 吉林676 page renders one family

## 5. Docs

- [ ] 5.1 AGENTS.md: replace the "manual-correction ledger is designed but unused" bullet (first use 2026-11-05, default path now applied on every PDF ingest)
- [ ] 5.2 `docs/inspection-batchD.md` D5 → done with the commit SHAs; `docs/portal_operations_log.md` append the ingest
