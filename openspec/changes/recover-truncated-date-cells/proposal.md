## Why

The 2026-10-28 gazette prints a row with **no 核定日期**. 編號 3 —
`變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市更新事業計畫案`
— has every other cell complete (26 parcels, and the 案名 declares 26) and an
empty date cell. There is **no ink** in that cell: the page's words jump from
`3` straight to `大安區`.

The tripwire refuses the ingest (exit 4), which is correct — a record whose
date is unknown cannot be placed on a timeline or reconciled against its
predecessor. But the **city holds the date**: case `11501034`'s header reads
`uro_chk_date 2026-10-15` and its data2 reads `核定日期 2026/10/15` — the exact
date the corpus already holds for this approval (node recno 1 of
`大安區-通化段四小段-336地號等26筆`).

The recovery pass exists for exactly this class of publisher defect, but its
scope is a truncated **地號** cell. A truncated **date** is the mirror image: the
identity is intact and the date is missing, so the pass's anchor has to
invert — the 案名 must carry the identity alone, and the date is what gets
recovered.

## What Changes

- **The reader marks a truncated date cell** with its own `source_fault`, so
  the recovery pass owns the row's outcome and the run report names it.
- **The recovery pass recovers the date from the name alone.** The candidate is
  chosen by: same unit, the declared count agrees, the **stage ordinal**
  agrees, and the **track set** equals the row's. The approved candidates must
  then carry exactly **one** date.
- **The 168 list's `MEMO` joins as a flag, not as a date source.** It carries
  the city's 核定**公告** date, which is a different date from the 核定日期
  (measured: they agree in 99 of 109 joinable rows and differ in 10, by weeks
  or months), and it is **empty for all 33** cases where the PDF's date and the
  platform's date disagree — so it cannot settle them. Where it is present it
  is a second confirmation, and a disagreement is recorded.
- **The tripwire exempts a recovered row**, so the ingest it unblocks is not
  refused for the fault the recovery just repaired.
- **The reconciliation lists the recovered row** under `recovered_records`, so
  the run does not report the city as having edited or withdrawn an approval it
  never touched.

## The measured rule

Over 59 gazette rows (one parcel search per row, one header per candidate):

| | Count |
|---|---|
| **recoverable — exactly one date** | **57** |
| residual — no candidate survives the name rule | 2 |
| **ambiguous — several dates** | **0** |

And the accuracy, against the corpus's own dates: the recovered date **equals**
the corpus's date in **55 of 57**. The 2 disagreements are 1 day apart (the
`pm1` case the existing flag exists for) and 16 days apart (the PDF and the
platform genuinely disagree, and no candidate carries the PDF's date).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `truncated-row-recovery`: a truncated **date** cell is recovered from the
  name alone, and the 168 list's 核定公告 date is a flag.
- `pdf-tsv-extraction`: the reader marks a truncated date cell.
- `gazette-reconciliation`: a recovered date row is not publisher movement.

## Impact

- `urtpe/extract.py` — the reader's marker.
- `urtpe/recovery.py` — the name-only candidate rule and the empty-`want` guard.
- `urtpe/recovery_pass.py` — the widened path and the provenance.
- `urtpe/tripwire.py` — the recovered row's exemption.
- `urtpe/reconcile.py` — the recovered row in `recovered_records`.
- `data/.link_cache/` — the 168 list's snapshot is read, not written.
- One ingest of the 2026-10-28 gazette, and one re-emit.
