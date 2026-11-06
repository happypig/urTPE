## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [ ] 1.1 An emptied 核定日期 cell is retained for the recovery pass, with its surviving cells, when the flag is on
- [ ] 1.2 Without the flag the emptied row is dropped and the tripwire refuses
- [ ] 1.3 The reader's date marker is distinct from the 地號 truncation marker
- [ ] 1.4 An emptied date cell is recovered from the name alone — 編號 3's case, `11501034` → 2026-10-15
- [ ] 1.5 The candidates must agree on exactly one date; zero or several leaves the row a residual
- [ ] 1.6 A count disagreement refuses (the row's `等12筆` against the city's `等13筆`)
- [ ] 1.7 A stage-ordinal disagreement refuses
- [ ] 1.8 A track disagreement refuses
- [ ] 1.9 The counts are compared as numbers — a row writing `地號1筆` and a case writing `地號1筆` agree
- [ ] 1.10 A compatibility ideograph does not hide the track (利 as U+F9DD)
- [ ] 1.11 `date_check` refuses an empty wanted date (D17)
- [ ] 1.12 An agreeing 核定公告 date carries no flag
- [ ] 1.13 A disagreeing 核定公告 date is flagged, and the recovered date is unchanged
- [ ] 1.14 The list's silence carries no flag and yields no date
- [ ] 1.15 A recovered row is exempt from the tripwire's date rule
- [ ] 1.16 A recovered row is counted as recovered, not as an edit or a withdrawal

## 2. Implementation

- [ ] 2.1 `urtpe/extract.py` — the reader marks an empty 核定日期 cell with its own source fault, and `to_raw_records` carries it
- [ ] 2.2 `urtpe/recovery.py` — the name-only candidate rule (NFKC, the count comparison, the ordinal and track checks) and the empty-`want` guard on `date_check`
- [ ] 2.3 `urtpe/recovery_pass.py` — the widened path: recover the date, compare the 核定公告 date and flag a disagreement, record the provenance
- [ ] 2.4 `urtpe/tripwire.py` — a recovered row is exempt from the date rule
- [ ] 2.5 `urtpe/reconcile.py` — the recovered row is listed in `recovered_records`, so it is neither an edit nor a withdrawal

## 3. Verification

- [ ] 3.1 The full suite passes (`python -m pytest`)
- [ ] 3.2 The ingest of the 2026-10-28 gazette runs with `--recover-truncated` and exits 0
- [ ] 3.3 The run report names the recovered row and its provenance, and the recovered count is 1
- [ ] 3.4 The reconciliation reports the approval as recovered, not withdrawn and not edited
- [ ] 3.5 The re-emit reports the project diff, and every changed project is attributed
- [ ] 3.6 `node scripts\viewer_smoke.js` passes after the re-emit
- [ ] 3.7 The board row for D9g step 9a is marked done with the measured counts, and step 9's row with the ingest's outcome
