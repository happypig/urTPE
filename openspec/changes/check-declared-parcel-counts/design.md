# design — check-declared-parcel-counts

## Context

Flow: PDF → positional parse (extract.py) → raw.tsv → cleanse → merge → merged.tsv →
projects.json (+ viewer). The fault-classification logic lives in extract.py's parse loop:
`TRUNCATED_TAIL_RE` decides whether a 地號 cell looks truncated; only truncated-looking
cells reach `land_cell_is_complete` (declared-vs-visible) and `complete_truncated_cell`
(corpus borrowing, three checks). Actors: the city (publisher, truncates at row height),
the reader (this pipeline), and downstream consumers of merged.tsv. See proposal.md for the
motivating event: 編號 1005 entered the current gazette's reading with 76 of 77 parcels,
cell ending `…579-`.

The original design of this change ran a declared-count check on **every** row. The POC
census (`poc_findings.md`, archived 2026-10-26) falsified that: across the seven held
gazettes, 353 rows have visible < declared and 354 have visible > declared — per Gregorian
gazette ~44 would have been newly excluded, most of them cells the publisher *completed*
(their closing phrase is present) whose mismatch is a city-side 案名 inconsistency, and
several of them artefacts of the reader's own counters. The design below is the revised
one; the decision (option A) is recorded in poc_findings.md §4.

## Goals / Non-Goals

**Goals:**

- Enforce the spec's half-sub-parcel ending (`…579-`) in the detector.
- Catch cuts the tail regex cannot see, on cells that lost their closing phrase, via the
  declared-count check.
- Keep the no-flag default pipeline offline, deterministic, and single-writer.

**Non-Goals:**

- No API recovery of excluded rows (that is `recover-truncated-rows-via-api`, opt-in).
- No change to cleansing, merge, or viewer behaviour.
- No re-classification of the page-number-in-cell reader fault.
- No review flagging of 案名-vs-cell count mismatches on complete cells (48 per Gregorian
  gazette, systemic city-side inconsistencies; ledger/cleanse territory).

## Decisions

- **D-1: The count check is scoped to cells that lost their closing phrase.** A cell
  carrying its closing phrase (`地號等N筆土地` and measured variants, bare `地號等N筆`
  included) was drawn to completion by the publisher; a visible≠declared mismatch there is
  a city-side inconsistency between two published fields, not evidence of a cut. The
  check therefore runs only when `closing_phrase_present(land)` is false, and only in the
  visible < declared direction. Alternative — checking every row (the original D-1) — was
  rejected on the census evidence: it would exclude the 長安段140/萬華段894/中正段44
  families, all complete as published.
- **D-2: Both signals feed one truncation decision, then one rescue.** A row is truncated
  iff (tail pattern fires) OR (no closing phrase AND declared is not None AND visible <
  declared); then, if the visible count equals the declared count, the cell lost only its
  closing phrase and is kept — the existing `land_cell_is_complete` rescue, which now
  measures with the corrected counter. The rescue order is not cosmetic: the census first
  mis-scored 1150827 編號 868/909 (the documented closing-phrase rescues) as new
  exclusions until the rescue was applied before classification. Rows with no declared
  count keep tail-only behaviour.
- **D-3: Missing declared count disables the count check for that row.**
  `declared_parcel_count` already returns None for names without "等N筆"; the check is
  skipped rather than guessed. (A hyphen-ending cell with no declared count is still
  tail-caught — a cell ending mid-token is incomplete regardless of any count.)
- **D-4: The counter is corrected before it is trusted.** `parcel_token_count` and
  `_parcel_tokens` change in two measured ways: (a) spaces are no longer stripped before
  tokenising — `163 164` is two parcels, while `\d+(?:\s*-\s*\d+)?` keeps `573 -6` as the
  single parcel 573-6 (a space followed by `-digits` continues the token; a space followed
  by bare digits delimits two); (b) the closing phrase is stripped chunk-wise from the
  right (replacing `LAND_TERMINATOR_RE`), so `地號等22土地`, `地號等2筆(原17筆)土地` and
  chained `地號等 18 筆土地)等 4 筆土地` neither leak their count digits as parcels nor
  hide the phrase. A parenthetical recap after the phrase (`土地(原161-5、…地號等10筆土地)`)
  still inflates the visible count; it only ever pushes visible *above* declared, which
  cannot cause an exclusion, and is recorded here rather than parsed.
- **D-5: Count-caught rows take the existing completion path unchanged.**
  `complete_truncated_cell`'s three checks decide, per row, completed vs excluded. Measured
  on the current gazette: the four 永昌段159 stages complete from 2026-08-11 編號 684;
  編號 188 (46-4), 1005 (505) and 1206 (519) are excluded because the mid-token cut token
  (`114`, `579`, `575`) is absent from the complete candidate — the containment check
  working as specified ("bounded differently"). No new completion rules.
- **D-6: Report wording, not schema.** Exclusions carry their cause in the existing
  `CellFault.detail` (tail-caught vs count-caught), and `extract_pdf_with_meta` reports
  both counts; the meta key set grows by `excluded_by_tail` / `excluded_by_count` only
  when both are present. Tripwire PASS/FAIL semantics are untouched: exclusions are
  reported and accounted, never a silent short gazette.

## Risks / Trade-offs

- [The counter change alters existing counts] → the census scanned every held gazette for
  outcome changes under the revised rule: zero for the ROC-era gazettes, and for the
  Gregorian ones only the 7 intended truncations; no existing rescue or completion flips.
  The full offline suite plus the task 5.2 temp-tree diff are the regression guards.
- [A city-side 案名 typo produces a false exclusion] → the check fires only on
  closing-phrase-lost cells, where the list is provably short of the row's own claim; the
  measured false-positive class (complete cells) is excluded from scope by D-1. Both
  directions remain observable in the census report; the ledger (keyed on land core +
  date) can correct confirmed cases.
- [Count parse ambiguity, e.g. "6筆(原4筆)"] → `declared_parcel_count` takes the first
  "等N筆" match, which is the current count; unchanged semantics, covered by tests.
- [Cells cut inside the closing phrase with a complete list, e.g. `…762地號等`] → visible
  equals declared, the check does not fire, the record is emitted as today (measured:
  編號 1188-class rows).

## Migration Plan

Land behind the test suite (tests written first, per the openspec gate); re-run the
pipeline on the current gazette into a temp tree. Measured expectation for that run:
1,441 records today → 1,438, with 編號 188/1005/1206 excluded and named, and
編號 695/702/726/827 completed from 2026-08-11 編號 684. The shipped dataset (1151006,
1,439) becomes 1,436 on its next re-ingestion, with the same three exclusions. Rollback =
revert the single detector+check commit; no data migration. Downstream
`viewer/projects.data.js` re-emits on the next `--from-js` run.

## Open Questions

- None. The original open question (whether archived gazettes contain additional
  hyphen-cut rows) is answered by the census: the four Gregorian gazettes carry the same
  seven; the ROC-era ones carry none — the Gregorian re-render introduced the cuts.
