# Design: ledger-date-correction

## Context

`CorrectionLedger.apply()` matches a record on `(normalize_land(land),
iso_date)` and sets one attribute per entry (`urtpe/ledger.py`). The key is
computed per record when the record is visited, and the merge confirmations
resolve from a key table built before any field is set, so a corrected
`iso_date` cannot disturb another entry's match in the same run. The record
carries three date views: `date` (the printed text), `iso_date` (what every
later step reads: `urtpe/graph.py:64` emits it as the node date, the merge
orders members by recno, the links layer keys on it) and `ymd` (derived from
the print at cleanse time).

## Decisions

### D1 — Correct `iso_date`, keep `date`, follow with `ymd`

The printed text is evidence of what the gazette says and stays. `iso_date` is
the interpretation every consumer reads, so it is the corrected field. `ymd`
is set from the corrected value inside `apply()` so no consumer sees the two
disagree.

### D2 — Match on the printed date

The entry's `match_iso_date` is the printed (wrong) day. That is what the
record carries on every rebuild before the ledger runs, so the entry keeps
matching. A second entry on the same record (a stage correction, say) also
names the printed day.

### D3 — Validate at creation, not at apply

`Correction.__post_init__` already refuses an unknown field. A date value is
checked there too (`datetime.date.fromisoformat`), so a typo in the ledger is
caught when the line is written, not silently applied on a rebuild.

### D4 — One entry, one ingest

recno 986: land cell 臺北市中山區德惠段二小段 813-1、814、814-1、814-3、815、816 地號等 6筆土地,
printed 2017-05-10, corrected to 2018-05-10. Evidence: city case 10409213
(申請計畫日期 2018/01/30, 核定日期 2018/05/10, bound to this recno), and the
family's 擬訂 row 943 dated 2017-11-23. A ledger entry applies only on a PDF
ingest, so one run of 核定案件-2026-10-28.pdf follows.

## Risks

- The archive index and change sets are keyed per publication on raw records
  and run before the ledger; they do not see the correction. That is the same
  position every ledger field has today.
