## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [ ] 1.1 The 開工 date picks the permit: 寶清57-13 shape — four permits, the city's 開工 names the last one
- [ ] 1.2 An unresolved tie emits no permit and carries the candidate list
- [ ] 1.3 A 開工 date matching several permits is ambiguous
- [ ] 1.4 A single matching permit is the witness, unchanged
- [ ] 1.5 The city's 使照 date never chooses the permit — a permit matching only the 使照 date is not the witness
- [ ] 1.6 The 開工 date is read from the source map, not from the merged dict — a stale merged value does not pick the permit
- [ ] 1.7 金華719 shape: the permit on the anchor's own parcel is the witness
- [ ] 1.8 The viewer renders no permit text when `links.permit` is absent

## 2. Implementation

- [ ] 2.1 `urtpe/permit_sources.py` — `select_permit_witness(permits, city_start_date)`: the permit whose 開工日期 equals the city's, else no witness
- [ ] 2.2 `urtpe/links.py` — the call site reads the city's 開工日期 from `milestones_source`, selects the witness, and emits `links.permit.ambiguous` with the candidate list when the tie is unresolved

## 3. Verification

- [ ] 3.1 The full suite passes (`python -m pytest`)
- [ ] 3.2 `node scripts\viewer_smoke.js` passes after the re-emit
- [ ] 3.3 The re-emit reports the count of projects whose witness changed and the count that became ambiguous
- [ ] 3.4 The board row for D9g step 3 is marked done with the measured counts
