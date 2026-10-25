# tasks — check-declared-parcel-counts

## 1. POC — measure the blast radius before any code changes

- [x] 1.1 Census: sweep the current gazette (2026-10-15) and every archived gazette in
      `D:\project\urtpe-gazettes\` with the count check as a read-only script; record every
      row where visible ≠ declared, split by direction (visible<declared / visible>declared)
      and by detector status (tail-caught / escaped). Expected finding to confirm: 編號 1005
      escaped, tail not fired. (Measured 2026-10-26, see poc_findings.md: 1005 confirmed —
      but the expected single-row blast radius is falsified; 59 flip-class + 48 review-class
      rows in the current gazette.)
- [x] 1.2 From the census, decide and record: the flip list for the default dataset
      (expected 1,427 → 1,426 on the current gazette) and whether any visible>declared row
      exists (drives review-flag tests). Archive the census output with this change.
      (Decision 2026-10-26, option A in poc_findings.md §4: the every-row check is
      withdrawn; adopted scope = closing-phrase-lost cells + corrected counter. Measured
      flip list: current gazette 1,441 → 1,383 under the specced check, 1,441 → 1,438
      under the adopted rule (編號 188/1005/1206 excluded, 695/702/726/827 completed from
      2026-08-11 編號 684); 1151006: 1,439 → 1,436. visible>declared rows exist (48 per
      Gregorian gazette) and are NOT review-flagged — out of scope, census archived as
      `census_declared_counts.txt`.)

## 2. Tests (write fully before any implementation)

- [x] 2.1 Unit test: detector classifies a cell ending `…578、579-` (mid-token hyphen) as
      truncated when declared > visible — the 編號 1005 shape, built from the real cell
      text (76 visible, 77 declared, no closing phrase).
- [x] 2.2 Unit test: count check routes a cell that lost its closing phrase, ends in a
      non-tail character (e.g. `…547(部分)`), and shows visible < declared into the
      publisher-truncation path.
- [x] 2.3 Unit test: a row whose 案名 declares no count is emitted normally when no tail
      pattern fires (no closing phrase, visible ≥ 1, no fault); and a no-count cell ending
      mid-token at a hyphen is still tail-caught (incomplete regardless of any count).
- [x] 2.4 Unit test: a cell whose closing phrase IS present with visible ≠ declared is
      emitted with no fault and no exclusion (the real 編號 427 shape: 案名 declares 521,
      cell declares and lists 52; plus the `163 164` space-separator cell).
- [x] 2.5 Unit test: visible == declared with a dangling tail still completes via
      `land_cell_is_complete` (existing "closing phrase lost" behaviour unchanged).
- [x] 2.6 Unit test: corpus completion still offered for count-caught rows (three checks
      unchanged), and refused when the count does not close.
- [x] 2.7 Unit tests for the corrected counter: `163 164` counts as two parcels;
      `573 -6` counts as one; `地號等22土地` / `地號等2筆(原17筆)土地` /
      `地號等 18 筆土地)等 4 筆土地` leak no count digits and are recognised as closing
      phrases; regression: all existing truncation tests pass unchanged (tail patterns
      preserved for already-caught shapes). Full suite: 666 passed, 1 skipped (the
      deliberate node-payload skip).
- [x] 2.8 Acceptance test (end-to-end, offline fixture PDF): a gazette containing the
      1005-shaped row (cell ending `579-`) and a `(部分)`-cut row emits both as excluded,
      named in the faults with page/row/column and the tail-vs-count cause.

## 3. Implementation — extraction (pure pipeline logic)

- [x] 3.1 extract.py: extend `TRUNCATED_TAIL_RE` to match a trailing sub-parcel hyphen
      (`\d-$`), per the approved spec's `139-` scenario.
- [x] 3.2 extract.py: add the closing-phrase detector (iterative closing-chunk strip +
      bare-count form) and the declared-count reconciliation step scoped by it (design
      D-1/D-2): run for every row with a declared count whose closing phrase is absent,
      alongside the tail-pattern branch; apply the count-equal rescue before exclusion;
      skip rows with no declared count (D-3).
- [x] 3.3 extract.py: correct the parcel counter (design D-4) — space-delimiting tokens
      with the `-digits` continuation arm, closing-chunk stripping replacing
      `LAND_TERMINATOR_RE` — shared by `parcel_token_count` and `_parcel_tokens`.

## 4. Implementation — report/tripwire wiring (adapter/output)

- [x] 4.1 Ensure the run report distinguishes, in its counts, exclusions caught by tail
      pattern vs by count check (both are publisher faults; the report names each record;
      cause rides in the CellFault detail per design D-6). `CellFault.cause` +
      `excluded_by_tail` / `excluded_by_count` meta keys + the CLI WARN split.
- [x] 4.2 Confirm tripwire PASS/FAIL semantics unchanged: exclusions are reported, never a
      silent short gazette. (Tripwire code untouched; its tests pass; the 編號 accounting
      flows through the unchanged `excluded_recnos` path — confirmed again by 5.2.)

## 5. Verification

- [x] 5.1 Full offline test suite passes (`python -m pytest`). 666 passed, 1 skipped
      (the deliberate node-payload skip at tests/test_idempotent_flags.py).
- [x] 5.2 Re-run the pipeline on the current gazette into a temp output tree (never
      `data/`; archive root repointed to a temp copy, live archive untouched): confirmed
      1,438 records (baseline HEAD run: 1,441, 編號 1131 excluded); raw.tsv diff is exactly
      the 7 newly-truncated rows — 編號 188/1005/1206 absent (excluded and named, causes
      3 tail / 1 count in the CLI WARN), 編號 695/702/726/827 changed lines carrying their
      completed 113-parcel lists from 2026-08-11 編號 684 — and no other row differs.
      Tripwire PASS with the accounted-INCOMPLETE line.
- [x] 5.3 Update `AGENTS.md`/docs where the detector is described (tail patterns + count
      check), and `docs/cli_flow_v2.md` only by appending if a row format changed. (The
      raw.tsv row format did not change, so `docs/cli_flow_v2.md` was not touched and its
      pinned `--links` line stays as asserted by `scripts/baseline_silent_failures.py`;
      AGENTS.md's 地號-cell invariant and the stale test counts were updated.)
