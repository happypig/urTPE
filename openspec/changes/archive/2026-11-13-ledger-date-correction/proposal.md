# Proposal: ledger-date-correction

## Why

The correction ledger can set a record's track, stage, section, parcel, count,
implementer, planner and name, but not its approval date. The gazette prints
one wrong year: recno 986 (中山區-德惠段二小段-813-1地號等6筆, 變更 事業計畫及權利變換)
reads 2017/5/10, while the city's own case 10409213 records the approval on
2018/05/10 and the family's 擬訂 row (recno 943) is dated 2017-11-23 — a 變更
cannot precede its 擬訂 by six months. The dashboard's new review rule prefers
the 擬訂 node and so sidesteps the row, but the graph still draws the 變更 above
the 擬訂, the approvals-by-year chart counts it in 2017, and every reader of the
payload inherits the typo. The user asked for the fix on 2026-11-13. A dated
one-off script would be reverted by the next rebuild; the ledger is the place.

## What Changes

- `iso_date` joins the ledger's correctable fields. An entry names the record
  by its land cell and **printed** approval date (the match key is unchanged)
  and sets the corrected ISO day; the printed `date` text is kept as the
  gazette's own print, and the record's `ymd` follows the corrected day.
- A malformed or non-calendar value is refused when the entry is created, the
  way an unknown field is refused today.
- One ledger entry for recno 986, applied by a PDF ingest.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `correction-ledger`: one requirement added (ADDED, no existing requirement
  changes): a printed approval date can be corrected.

## Impact

- `urtpe/ledger.py`: `CORRECTABLE_FIELDS` gains `iso_date`; the entry
  validator checks the value is a calendar day in ISO form; `apply()` sets
  `ymd` alongside `iso_date`.
- `tests/test_ledger.py`: three tests.
- The ledger file and one PDF ingest (data, payload). The 德惠段 family's
  node order, the 2017/2018 approval counts and the project's idle clock move;
  the project count does not.
