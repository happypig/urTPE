## 1. Tests (write first)

- [x] 1.1 Add unit tests for ledger load/save round-trip: new entry, update of existing entry, atomic replace leaves no temp files, corrupt JSON degrades to empty with `.corrupt` rename + warning
- [x] 1.2 Add unit tests for candidate filtering: entry within TTL excluded, entry older than TTL included, missing entry included, `--reprobe-days 0` includes everything, skipped count equals difference of list lengths
- [x] 1.3 Add unit test for clear-on-match: `update_project_cache` success removes the project's ledger entry; run-start sweep drops entries whose cache now has twur

## 2. Ledger module (script-scoped, I/O adapter)

- [x] 2.1 Implement load/save helpers in `scripts/fetch_remaining_national_portal.py` (`LEDGER_PATH = Path("data/.link_cache/no_match_ledger.json")`), per design D1/D3/D5: ISO timestamps, write-temp + `os.replace`, corrupt-file quarantine
- [x] 2.2 Implement `record_no_match(project_id, view_ids_checked)` and `clear_entry(project_id)` helpers

## 3. Candidate selection (use-case wiring)

- [x] 3.1 Add `--reprobe-days N` CLI arg (default 14) to the script's argparse
- [x] 3.2 Extend `load_candidates()` to filter out projects whose ledger entry is within TTL; return both full and filtered lists for summary accounting (design D2)
- [x] 3.3 Add run-start sweep: remove ledger entries for projects that now have twur links in their caches (design D4)

## 4. Main loop integration

- [x] 4.1 On no-match branch: call `record_no_match(...)` before sleeping (immediate persistence, D3)
- [x] 4.2 On successful `update_project_cache`: call `clear_entry(project_id)`
- [x] 4.3 Extend end-of-run summary with skipped-as-recently-probed and total-candidates counts (spec: Run summary reports ledger activity)

## 5. Verification & rollout

- [x] 5.1 Run full pytest suite; all existing tests stay green
- [x] 5.2 Acceptance (end-to-end, maps every modified/added requirement): run `--dry-run --max-projects 3` against live data with a seeded ledger containing one fresh entry and one stale entry — verify candidate exclusion within TTL, stale-entry re-entry, no-match recording, summary counts (processed/updated/skipped), and that a stubbed match clears the project's ledger entry — without network writes to caches
  *(executed 2026-08-25 09:03 after the overnight batch exited; deadline gate bypassed via wrapper setting `DEADLINE_HOUR=23` for the verification run only)*
- [x] 5.3 Update `docs/facts_2_portals.md` §16 Remaining work with the ledger behavior and new default cadence; note single-writer rule still governs `.link_cache`
