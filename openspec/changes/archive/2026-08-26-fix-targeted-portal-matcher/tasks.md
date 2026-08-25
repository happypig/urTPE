## 1. Tests first (regression + acceptance)

- [x] 1.1 Add regression tests for candidate keyword derivation: an enumerated land string ("…寶清段四小段599、599-1、…、623地號等27筆") must yield the anchor node's named first parcel `599` (never `623`); fallback path uses the first enumeration token when `first_parcel` is empty
- [x] 1.2 Add strict-match comparison tests: text count `'27'` vs parsed numeric count `27` accepts; differing counts (等7筆 vs 等17筆) reject; count absent on either side leaves section+parcel to decide
- [x] 1.3 Add notation-drift tests: `263之19` ≡ `263-19`, full-width digits ≡ ASCII digits; wrong section or wrong parcel rejects even when the parcel string appears in the page body
- [x] 1.4 Add probe-breadth tests: default limit 8, `--max-probe` override honored, truncation-without-match is noted and the no-match still records to the ledger
- [x] 1.5 Offline acceptance replay: run the fixed matcher against the cached `view/30` HTML (`松山區-寶清段四小段-599地號等27筆`) and assert it now matches; full test suite green

## 2. Matcher logic (pure pipeline logic)

- [x] 2.1 In `load_candidates`: derive the parcel keyword from the anchor node's `first_parcel`, falling back to the first enumeration token of the land string (design D1)
- [x] 2.2 In `view_page_matches`: add a local normalize helper (full-width→ASCII digits, `之`→`-`) applied to parcels/counts, compare counts as strings (design D2)

## 3. Fetch-script adapter / CLI surface

- [x] 3.1 In `find_matching_view` + CLI: replace hardcoded first-5 with configurable probe limit defaulting to 8 via `--max-probe`; print unprobed-count note when truncation ends a search without match (design D3)

## 4. Pre-sweep verification

- [x] 4.1 Dry-run sample (`--dry-run`, small `--max-projects`) over live portal confirms expected accepts/rejects, including 寶清段四小段599 → view/30
- [x] 4.2 Full test suite plus repo lint/typecheck pass

## 5. Recovery sweep (single-writer rule)

- [x] 5.1 Back up `data/.link_cache` and snapshot coverage counters (twur / national_milestones / 使用核發 / Taipei resolved) before the run (design D4)
- [x] 5.2 Run the campaign overnight under standing calibrated intervals with the 07:00 deadline; ledger active
- [x] 5.3 Post-run coverage guard diff — every counter increased or unchanged (abort and investigate otherwise); regenerate viewer once at completion
- [x] 5.4 Verify 松山區-寶清段四小段-599地號等27筆 carries the twur link to view/30 with 推動歷程 milestones (incl. 使用核發 98.03.31) rendered in the viewer

## 6. Documentation

- [x] 6.1 Update `docs/facts_2_portals.md` §0 decision table and revise §16's ceiling analysis to split genuine registry absence from matcher-rejected recoverable population, recording the measured post-fix coverage
- [x] 6.2 Record sweep observations (yield by era, truncation notes, remaining no-match tail) as input for the §12 #3 consolidation and #4 count-normalization changes
