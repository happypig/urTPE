## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 An emptied 核定日期 cell is retained for the recovery pass, with its surviving cells, when the flag is on
- [x] 1.2 Without the flag the emptied row is dropped and the tripwire refuses
- [x] 1.3 The reader's date marker is distinct from the 地號 truncation marker
- [x] 1.4 An emptied date cell is recovered from the name alone — 編號 3's case, `11501034` → 2026/10/15
- [x] 1.5 The candidates must agree on exactly one date; zero or several leaves the row a residual
- [x] 1.6 A count disagreement refuses (the row's `等12筆` against the city's `等13筆`)
- [x] 1.7 A stage-ordinal disagreement refuses
- [x] 1.8 A track disagreement refuses
- [x] 1.9 The counts are compared as numbers — a row writing `地號1筆` and a case writing `地號1筆` agree
- [x] 1.10 A compatibility ideograph does not hide the track (利 as U+F9DD)
- [x] 1.11 `date_check` refuses an empty wanted date (D17)
- [x] 1.12 An agreeing 核定公告 date carries no flag
- [x] 1.13 A disagreeing 核定公告 date is flagged, and the recovered date is unchanged
- [x] 1.14 The list's silence carries no flag and yields no date
- [x] 1.15 A recovered row is exempt from the tripwire's date rule — **satisfied without a change**: the recovery runs BEFORE the tripwire (`urtpe/cli.py:292` vs `:322`), and the recovered date is written in the cell format the reader parses, so the tripwire sees a date
- [x] 1.16 A recovered row is counted as recovered, not as an edit or a withdrawal

## 2. Implementation

- [x] 2.1 `urtpe/extract.py` — the reader marks an empty 核定日期 cell with its own source fault, and `to_raw_records` carries it
- [x] 2.2 `urtpe/recovery.py` — the name-only candidate rule (NFKC, the count comparison, the ordinal and track checks), the cell-format date, and the empty-`want` guard on `date_check`
- [x] 2.3 `urtpe/recovery_pass.py` — the widened path: recover the date, compare the 核定公告 date and flag a disagreement, record the provenance
- [x] 2.4 `urtpe/tripwire.py` — **no change needed**: the recovery precedes the tripwire, so the recovered row carries a date the tripwire accepts (the design assumed an exemption was needed; the run order already provides it)
- [x] 2.5 `urtpe/reconcile.py` — **no change needed**: the recovered date makes the row's identity key match the predecessor's exactly, so `withdrawn_recent` does not fire and `recovered_records` already routes the row out of the edit count

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1086 passed, 1 skipped
- [x] 3.2 The ingest of the 2026-10-28 gazette runs with `--recover-truncated` and exits **0**; the tripwire **PASSES**
- [x] 3.3 The run report names the recovered row and its provenance: `編號 3: RECOVERED 核定日期 2026/10/15 (cases 11501034, from the 案名 alone)`. 5 recovered, 0 residual
- [x] 3.4 The reconciliation reports the approval as recovered, not withdrawn and not edited: **0 re-dated, 0 edited, 0 vanished**, 2 new approvals, net +6
- [x] 3.5 The re-emit reports the project diff: 681 projects changed and 1 is new; **680 of the 681 changed projects have identical content** — the change is the 編號 renumbering (編號 is a coordinate). The one project whose content differs gained the new 2026-10-28 approval (case `10609183`)
- [x] 3.6 `node scripts\viewer_smoke.js` passes after the re-emit — all checks passed
- [x] 3.7 The board rows for D9g steps 9a and 9 are marked done with the measured counts

## Measured notes

- **The recovered date must be written in the cell format.** The reader's
  `to_iso` accepts `2026/10/15` and `115/8/27` and **rejects** the hyphenated
  ISO form, so a recovered date in the wrong shape would fail the tripwire's
  date rule and the cleanser. `_iso_to_cell` writes `YYYY/M/D`.
- **Two measured units are no longer in the corpus** — 桃源段三小段251 and
  玉成段五小段545. Neither was in the 2026-10-15 corpus either, so they had
  gone before. `tests/test_merge_count_shrink.py` now identifies its measured
  pairs by their **content** (the unit's fragment and the two counts) rather
  than by 編號, because the 2026-10-28 gazette renumbered the whole corpus,
  and it reports the absent units instead of failing on them.
- **`openspec/config.yaml`'s stated approval count** moved from 1,442 to
  1,444, and the publication date from 2026-10-15 to 2026-10-28.
