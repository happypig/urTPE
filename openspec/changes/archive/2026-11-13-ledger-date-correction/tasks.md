# Tasks: ledger-date-correction

## 1. Tests first (test-first gate — every task here is checked before any task in groups 2–3)

- [x] 1.1 `tests/test_ledger.py`: an `iso_date` entry keyed on the printed day
  sets the record's `iso_date` and `ymd` and leaves `date` unchanged.
- [x] 1.2 `tests/test_ledger.py`: a stage entry on the same record, keyed on
  the same printed day, applies in the same run as the date entry.
- [x] 1.3 `tests/test_ledger.py`: `2018/5/10` and `2018-02-30` are refused at
  creation.
- [x] 1.4 Run `python -m pytest tests/test_ledger.py -q`; the three new tests
  fail against the unchanged ledger, the rest stay green. (Recorded: 2 failed /
  28 passed — the two apply tests; the refusal test passes on the old code too,
  because an unknown field is refused today.)

## 2. Implementation

- [x] 2.1 `urtpe/ledger.py`: `iso_date` joins `CORRECTABLE_FIELDS`; the
  validator checks a calendar day in ISO form; `apply()` sets `ymd` when it
  sets `iso_date`.
- [x] 2.2 `python -m pytest tests/test_ledger.py -q` green.
- [x] 2.3 Append the recno 986 entry to the ledger (backup first), run the PDF
  ingest of 核定案件-2026-10-28.pdf, verify: 986 reads 2018-05-10 in
  `data/clean.tsv` and in the payload, the family's node order is
  943 → 986 → 793, the project count stays 675, the dashboard figures hold.
- [x] 2.4 Full suite; refresh the count in `AGENTS.md`; docs: a sentence in
  notes §14.-3 and log §43 closing the 德惠段 item.

## 3. Archive

- [x] 3.1 `openspec validate ledger-date-correction --strict` clean; dry-run
  archive on a copy expecting `+ 1, ~ 0, - 0`; real archive; commits
  path-limited (`feat:` for code + tests + data, `openspec:` for the archive).
