## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 The 開工 date picks the permit: 寶清57-13 shape — four permits, the city's 開工 names the last one
- [x] 1.2 An unresolved tie emits no permit and carries the candidate list
- [x] 1.3 A 開工 date matching several permits is ambiguous
- [x] 1.4 A single matching permit is the witness, unchanged
- [x] 1.5 The city's 使照 date never chooses the permit — a permit matching only the 使照 date is not the witness
- [x] 1.6 The 開工 date is read from the source map, not from the merged dict — a merged value with no source behind it cannot pick the permit
- [x] 1.7 金華719 shape: the permit on the anchor's own parcel is the witness
- [x] 1.8 The viewer renders no permit text when `links.permit` is absent

## 2. Implementation

- [x] 2.1 `urtpe/permit_sources.py` — `select_permit_witness(permits, city_start_date)`: the permit whose 開工日期 equals the city's, else no witness
- [x] 2.2 `urtpe/links.py` — the call site reads the city's 開工日期 from `milestones_source`, selects the witness, and emits `links.permit.ambiguous` with the candidate list when the tie is unresolved

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1056 passed, 1 skipped
- [x] 3.2 `node scripts\viewer_smoke.js` passes after the re-emit — all checks passed
- [x] 3.3 The re-emit reports the count of projects whose witness changed and the count that became ambiguous — `scripts/probe_step3_permit_diff.py`: **15** witnesses moved, **15** became ambiguous, **0** dropped
- [x] 3.4 The board row for D9g step 3 is marked done with the measured counts
