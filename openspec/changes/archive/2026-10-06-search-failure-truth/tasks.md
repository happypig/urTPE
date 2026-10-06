# Tasks — search-failure-truth

The `rules` block asks for a POC validating positional PDF parsing and similarity
calibration. Neither applies: no PDF is read and nothing is merged. The evidence for this
change is the code path quoted in `design.md` plus live portal probes.

## 1. Tests — a search that could not run (written first, deliberately failing)

- [x] 1.1 **PASSES.** `search_portal` returns `(OUTCOME_ERROR, [])` when the request raises.Test that a search request which raises is reported as an error, not an empty result
- [x] 1.2 **PASSES.** A successful search with no `/view/` links returns `(OUTCOME_MISS, [])`.Test that a search request which succeeds with no results is reported as a miss
- [x] 1.3 **PASSES.** The helper maps a failed search to the error outcome before any probe, so the entry carries no exclusion.Test that a failed search produces an error ledger entry carrying no re-probe exclusion
- [x] 1.4 **PASSES.** Both entries carry `view_ids_checked: []`; only `twur_class` separates them, which is the point.Test that a failed search and an empty search are distinguishable in the ledger
- [x] 1.5 **PASSES.** Both failure modes asserted directly on `search_portal`.Test that every return path of the search carries an outcome
- [x] 1.6 **PASSES.** `probes == 0` — no candidate pages existed to probe.Test that an error search makes no probe requests, since there is nothing to probe

## 2. Implementation

- [x] 2.1 **PASSES.** `search_portal` returns `(outcome, view_ids)`; the collapse of two causes into `[]` was the root.`search_portal` returns `(outcome, view_ids)` instead of collapsing both causes into `[]`
- [x] 2.2 **PASSES.** `find_matching_view_with_outcome` short-circuits on the search outcome.`find_matching_view_with_outcome` maps a failed search to the error outcome
- [x] 2.3 **PASSES.** The existing caller branch already recorded `OUTCOME_ERROR` without probing; only its input changed.The caller records the error without probing, since no candidate pages exist
- [x] 2.4 **PASSES.** Six stubs in `test_sweep_failure_truth.py` and one in `test_fetch_remaining_portal.py` updated for the tuple shape. A regex-based edit left backslash-escaped quotes in the test file, which is a SyntaxError; caught by the run and normalised.Existing call sites and tests updated for the new return shape

## 3. Documentation

- [x] 3.1 **DONE.** Three-outcome table extended to cover the search phase.`docs/cli_flow_v2.md` — the three-outcome table covers the search phase, not only probes
- [x] 3.2 **DONE.** Recorded in design D3: 14 existing zero-result entries stay as they are, 9 of which are correct misses and 5 unknowable.Record that the 14 existing zero-result entries are not reclassified, and why

## 4. Acceptance

- [x] 4.1 **PASSES.** 566 tests, `validate --strict` clean.Full suite green; `openspec validate search-failure-truth --strict` clean
- [x] 4.2 **PASSES.** No live probe needed; the paths are pure logic over an injected fetcher. The live dry run was still used to confirm exit 0.No live probe of the portal is required to verify this; the paths are pure logic over an injected fetcher
## 5. Notes

**The larger goal was measured and abandoned, and that is the finding.** The 48
`has-approved` / `mixed/other` projects were to be chased by searching on their case names.
Three probes against the live portal, before any code was written:

1. **The portal does not respond to 案名 search at all.** Full case name returned *no*
   view ids in all three projects tried, where the section name returned 1, 2 and 4.
   Building case-name search would have produced zero additional candidates.
2. **Where pages are returned, they belong to other projects.** Titles inspected
   directly: 通化段六小段202等7筆 drew 665等31筆 and 497等22筆; 通化段五小段447等5筆 drew
   191-4等24筆, 191-1等6筆, 242等10筆 and 416等13筆. Same 段/小段, wrong parcel. The strict
   matcher is correct to reject them.
3. **Across the population:** of the 48, nine have a section search returning nothing at
   all, and 39 had pages, with all 162 probed view ids rejected on parcel/count.

So the twur portal does not list these units. `has-approved` is a fact about the *Taipei*
case system, not about twur coverage — a unit can hold a city-approved case and still
never appear on the national portal. The `recoverable` class was being read as
"recoverable on twur", which is a stronger claim than the data supports.

The remaining headroom is **20 unprobed view ids** across the 10 projects that hit
`--max-probe 8`. That is a flag, not a feature.

**Two residual conflation bugs found in one day, one level apart.** The probe loop and
the search that feeds it each collapsed "failed" into "empty". Fixing the outer one
first would have left the inner one in place, and the inner one is the rarer path.
