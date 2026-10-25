# check-declared-parcel-counts

## Why

臺北市都市更新處 publishes the gazette; our reader (extract.py) turns it into raw.tsv. The
approved `pdf-tsv-extraction` spec requires that a 地號 cell ending in a half sub-parcel
number ("a half sub-parcel number such as `139-`") be treated as publisher truncation, but
the implemented detector (`TRUNCATED_TAIL_RE = [、，,]$|\d$`) does not match a hyphen
ending. Measured 2026-10-26 on the current gazette (統計至 2026-10-15): 編號 1005
(2017-02-16, 雙園段二小段505地號等77筆) ends its cell at `…578、579-` — cut mid-token —
with 76 of the 77 declared parcels, and was emitted with no fault reported. The same row
ends `…579-` in every held gazette (編號 999 in 2026-08-27, 1003 in 2026-10-01, 1004 in
2026-10-13). That is exactly the failure the spec's "a partial gazette is never presented
as complete" requirement exists to prevent, and it is present in the shipped data today.

## What Changes

- **Fix the detector to match the approved spec**: cell endings that end mid-token at a
  hyphen (`…579-`) are classified as publisher truncation, as the `139-` scenario already
  requires.
- **Add a declared-count check — scoped by measurement.** The original proposal checked
  every row's visible count against its 案名's declared count. The POC census
  (`poc_findings.md`, archived with this change) falsified that: per Gregorian gazette it
  would newly exclude ~44 records whose cells the publisher completed (closing phrase
  present) and whose mismatch is a city-side 案名 inconsistency, plus reader-counter
  artefacts. The check as adopted runs **only on cells that lost their closing phrase**,
  in the visible < declared direction, and routes them into the existing
  publisher-truncation path (excluded and named, or completed under the three existing
  checks).
- **Correct the parcel counter it depends on**: a space where a separator belongs
  delimits two parcels (`163 164`); a space followed by `-digits` continues one token
  (`573 -6`); closing-phrase variants (`地號等22土地`, `地號等2筆(原17筆)土地`, chained
  `…土地)等 4 筆土地`) are stripped before counting so their digits never masquerade as
  parcels.
- Rows whose 案名 declares no count are not count-checked and keep today's behaviour;
  cells whose closing phrase is present are never count-checked.
- Emission changes, measured (corpus completions included, as the CLI builds it): the
  current gazette emits 1,441 → 1,438 — 編號 188 (永昌段四小段46-4), 1005 (雙園段二小段505)
  and 1206 (萬隆段二小段519) become excluded-and-named; 編號 695/702/726/827 (the four
  永昌段三小段159 stages) become completed from 2026-08-11 編號 684 with their lists
  repaired. The shipped dataset's source (1151006, 1,439 records) becomes 1,436 on its
  next re-ingestion. This is an intentional **BREAKING** change to the default dataset,
  decided 2026-10-26 (decision in poc_findings.md §4: option A).
- No new data sources, no network access — this is offline extraction logic only.

## Capabilities

### New Capabilities

- *(none)*

### Modified Capabilities

- `pdf-tsv-extraction`: the "Distinguish reader faults from source faults" requirement
  gains (a) enforcement of the already-specified half sub-parcel ending, (b) a
  declared-count-vs-visible-count check applied to every 地號 cell that lost its closing
  phrase, with a shortfall routing the row into the existing exclude/name/complete path,
  and (c) the measured counting rules above. The "Publisher truncates a cell at the row
  height", "terminal wording variations" and "partial gazette" scenarios extend
  accordingly; the previously proposed every-row requirement is withdrawn before
  implementation (see the delta's REMOVED note).

## Impact

- `urtpe/extract.py` — detector regex, the scoped count check, and the parcel counter;
  no I/O changes.
- Run report / tripwire counts — up to three more named exclusions and four completions
  per Gregorian gazette; report format unchanged, cause carried in the fault detail.
- Emitted dataset — measured above (1,441 → 1,438 on the current gazette; 1,439 → 1,436
  on 1151006 re-ingestion).
- Tests — existing truncation tests keep passing; new tests for the hyphen ending, the
  scoped count check (including its refusal paths), and the corrected counter.
- Follow-on: `recover-truncated-rows-via-api` consumes the same flagged-row path; this
  change is sequenced first so the two do not double-handle the 1005-class rows (its
  completion is refused by the containment check by design — the cut token `579` is
  bounded as `579-2` in the only complete candidate).
