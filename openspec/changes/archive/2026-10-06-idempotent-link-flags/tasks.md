# Tasks — idempotent-link-flags

The `rules` block asks for a POC on PDF parsing and similarity calibration. Neither applies:
no PDF is read and nothing is merged. The evidence is the raise site quoted in `design.md`
and the measured counts (282 nodes, 1162 occurrences, +280 per run).

## 1. Tests (written first, deliberately failing)

- [x] 1.1 **PASSES.** The flag is present after first observation.Test that a stage/platform disagreement is flagged on first observation
- [x] 1.2 **PASSES.** A second pass leaves the list identical.Test that re-running discovery over unchanged input adds no second copy
- [x] 1.3 **PASSES.** Count and text unchanged; the list is compared, not just its length.Test that repeating the comparison leaves flag count and text unchanged
- [x] 1.4 **PASSES.** Two differing flag strings are both retained.Test that two *different* flags on one record are both kept
- [x] 1.5 **PASSES.** `graph._dedupe` collapses; the live dataset went 282 duplicated nodes to **0**.Test that emission collapses duplicate flag strings
- [x] 1.6 **PASSES.** First-appearance order preserved by the seen-set walk.Test that collapsing preserves first-appearance order
- [x] 1.7 **PASSES.** `set(emitted) == set(flags)` asserted directly.Test that collapsing loses no distinct flag
- [x] 1.8 **PASSES.** Flagged-record count asserted unchanged across collapsing.Test that the number of records carrying at least one flag is unchanged

## 2. Implementation

- [x] 2.1 **PASSES.** `links.py:1494` now builds the flag into a local and appends only when absent.`links.py:1494` raises the flag only when absent
- [x] 2.2 **PASSES.** `graph._dedupe` at emission, so the already-dirty rows collapse too.Emission collapses duplicates on a record, preserving first-appearance order
- [x] 2.3 **PASSES.** No other flag source changed; `review_flags` is written in exactly one place.No other flag source changes behaviour

## 3. Data

- [x] 3.1 **PASSES.** 1162+ occurrences of one string collapsed; total flag occurrences now 376, duplicated nodes 0.One `--links` run collapses the 1162 occurrences to one per affected node
- [x] 3.2 **RECORDED CORRECTION.** The task said 'unchanged at 282'. That was wrong: 282 was the count of nodes carrying a *duplicated* flag, not of nodes carrying any flag. The flagged-node count is 348, of which 282 previously had duplicates and 66 were already clean.Flagged-node count is unchanged at 282
- [x] 3.3 **PASSES.** Two consecutive `--from-js --links` runs: **0 differing projects**.A second `--links` run is byte-identical to the first — the acceptance test
- [x] 3.4 DONE as its own commit.Commit `data/projects.json` and `viewer/projects.data.js` as their own commit, so the ~880-string deletion is not mistaken for churn

## 4. Documentation

- [x] 4.1 **PASSES.** The `docs/cli_flow_v2.md` section survives and now names both defects found under it.`docs/cli_flow_v2.md` already records the finding, the three wrong diagnoses, and the run-twice discriminator; confirm it survives this change

## 5. Acceptance

- [x] 5.1 **PASSES.** 597 tests, 1 skipped; `validate --specs --strict` 21/21; change validates strict.Full suite green; `openspec validate idempotent-link-flags --strict` clean
- [x] 5.2 **PASSES.** 0 differing projects across two `--from-js --links` runs.Two consecutive `--from-js --links` runs produce 0 differing projects
- [x] 5.3 **PASSES.** 709 -> 709 projects, project order identical, +1 twur and -0 twur, override link present.The override's link is still present and nothing else changed
## 6. A second defect, found by the acceptance test rather than by reading

Fixing the flags did **not** make the run idempotent: 97 projects still differed. My task
3.2 and acceptance 5.2 had assumed one defect, and the acceptance test is what proved
there were two.

The remainder was `project.links["orphan_nodes"]`, whose order follows an unordered
collection of case ids (`links.py:1170`). The content was identical — the same two cases
swapped between runs. Pinning `PYTHONHASHSEED` still left 95 differing, so it was not
string-hash order; the likely driver is the concurrent Taipei fetches completing in a
different order.

**Third hypothesis wrong in a row** — hash-seed order, then convergence, then string
hashing. What actually worked was the cheap discriminator recorded in
`docs/cli_flow_v2.md`: run it twice, and check whether a value *grew* (append bug) or
*moved* (ordering bug). Neither reading of the symptom identified either cause; the
comparison did.

The fix is `_sorted_orphan_nodes`, applied at publication rather than at build, so the
arbitrary order cannot return the next time someone appends to the list.
