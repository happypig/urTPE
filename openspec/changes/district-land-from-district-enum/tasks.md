## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 A 臺北大安區 cell reads `district_land = 大安區`, and its section and parcels are unchanged
- [x] 1.2 A 臺北市投區 cell reads `district_land = ''` and keeps the flag `行政區與地號行政區不一致(地號為投區)`
- [x] 1.3 A 臺北士林區 cell reads `district_land = 士林區`
- [x] 1.4 A cell that prints `臺北市中正區…` reads `中正區` and is unchanged from today's answer
- [x] 1.5 The enum is collected from the corpus's 行政區 column, not hard-coded: a `cleanse` call with an explicit enum reads it, and a call without one keeps the strict `DISTRICT_RE` answer
- [x] 1.6 `cleanse_all` over a record set collects the enum from the records' own 行政區 values
- [x] 1.7 The project identity does not move: a record whose 地號 cell omits 市 keeps its `project_id`

## 2. Implementation

- [x] 2.1 `urtpe/cleanse.py` — `_land_district` reads the cell's district from the collected enum (anchored on `臺北市?`); with no enum it keeps the strict `DISTRICT_RE` behaviour
- [x] 2.2 `urtpe/cleanse.py` — `cleanse(rec, districts=...)` threads the enum to `_land_district`; the mismatch flag keeps quoting the **printed** token, so a `投區` cell still flags
- [x] 2.3 `urtpe/cleanse.py` — `cleanse_all(records)` collects the enum from the records' 行政區 values and passes it down
- [x] 2.4 `urtpe/cli.py` — the cleansing call passes the collected enum

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1013 passed, 1 skipped
- [x] 3.2 `scripts/probe_d14b_cleansed_diff.py` re-cleanses `data/raw.tsv` (1,442 rows) and reports: **7** `district_land` changes, **0** section changes, **0** parcel changes, **0** `land_count` changes, **0** name changes, **0** review-flag changes, **0** other-field changes. The flag still fires on 488 / 558 / 927 with the text `行政區與地號行政區不一致(地號為投區)`
- [x] 3.3 The board row for D9g step 0b is marked done with the measured counts
