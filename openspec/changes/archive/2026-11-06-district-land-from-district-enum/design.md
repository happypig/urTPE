## Context

`urtpe/cleanse.py` reads the 地號 cell's district with `DISTRICT_RE`
(`臺北市(.{1,4}?區)`) and stores it as `district_land`. Two consumers care:

- the mismatch flag `行政區與地號行政區不一致(地號為{land_district})`
  (`urtpe/cleanse.py:236-238`);
- the land core (`build_land_core_key`, `urtpe/links.py:354`), which prepends
  `district_land` to the section.

The city prints `臺北大安區`, `臺北士林區` (no 市) and `臺北市投區` (no 北) in
this column. The regex reads the first shape as no district and the third as
the non-district `投區`, which then travels into the land core.

`_section` also splits on `DISTRICT_RE` (`urtpe/cleanse.py:90-102`) to find
the 段小段, so the district token and the section token are read by different
rules today. Only the first changes.

## Goals / Non-Goals

**Goals:**

- Read the 地號 cell's district from the corpus's own 行政區 enum.
- Keep the mismatch flag firing, and keep it quoting the printed token.
- Keep the section, the parcels and `project_id` unchanged for every row.

**Non-Goals:**

- Repairing the city's typos. `臺北市投區` stays a publisher error; the reader
  reports it and reads nothing from it.
- Fixing the `臺北大安區` / `臺北士林區` cells in the source. They are read
  correctly, not corrected in place.
- Changing the section split. `_section` keeps the `臺北市` anchor, because
  the section token is a different grammar and a looser district match would
  let a district name leak into the section.

## Decisions

**D1 — The enum is collected from the corpus, not hard-coded.**

`_land_district` needs the set of known district names. The set is the
corpus's own 行政區 column, collected over the records being cleansed in the
same run. A hard-coded 12-name list would be a second source of truth that
drifts from the data (the same reason `DISTRICT_FIXES` is a small map of
*known* typos, not a rule).

*Alternative considered:* a loose regex `臺北市?(.{1,4}?區)`. Rejected — it
reads `投區` from `臺北市投區` (the missing 北) and it accepts any 2–4 character
string ending in 區, so an unrelated cell text would be read as a district.
The enum cannot do either: `投區` is not in it.

*Alternative considered:* widen the enum with `投區`. Rejected — that is
repairing absent data by inference.

**D2 — The enum is threaded through the cleansing call, not read from disk.**

`cleanse_all(records)` gains an optional `districts` argument (the collected
enum). `cleanse(rec, districts=...)` passes it to `_land_district`. When the
caller supplies no enum, the reader falls back to the strict `DISTRICT_RE`
behaviour, so the ~40 existing single-record `cleanse()` call sites in the
tests keep their current answers and no test has to change meaning.

*Alternative considered:* read `clean.tsv`'s district column inside the
cleanser. Rejected — that is an I/O dependency inside the pure cleansing
layer (`config.yaml`'s port/adapter split), and the file may not exist yet
during a run.

**D3 — The flag quotes the printed token; the field holds the normalized one.**

The flag is a report of a publisher contradiction. On `臺北市投區` the
contradiction is real and must stay visible, so the flag keeps its text
`行政區與地號行政區不一致(地號為投區)` even though `district_land` is now `''`.
The two fields therefore read from different tokens: the flag from the
printed one, the field from the enum.

*Alternative considered:* let the flag follow `district_land` (so the 投區
rows lose the flag). Rejected — it would hide a real publisher error, and the
board requires the flag to keep firing on 488 / 558 / 927.

**D4 — The section split does not move.**

`_section` keeps `DISTRICT_RE`. On the 7 changed rows the section and the
parcel list are identical under both readings (measured: 0 section diffs, 0
parcel diffs over 1,442 rows), so the change cannot reach them.

## Risks / Trade-offs

- **[A new 行政區 value appears in a future gazette]** → The enum is collected
  from the corpus, so it grows with the data. A cell naming a district the
  enum lacks reads `''` and its section/parcels are unaffected.

- **[The land core of the 3 affected projects changes]** → `project_id` does
  not move (`slug_for` reads the 行政區 column), and the cache directories are
  named by `project_id`, so the cache lookup is unaffected. The stored
  `land_core` field changes on the next discovery write, and the change makes
  it match the portal's own core form (`北投區崇仰段三小段156地號等23筆` is the
  core the cache already stores for that project).

- **[The enum read differs from the 案名 read]** → Measured over 1,442 rows:
  0 rows differ between an anchored read (`臺北市?` prefix required) and a free
  scan of the cell. The implementation uses the anchored read.

- **[A rebuild from emitted state re-cleanses]** → It does not. `--from-js`
  carries the stored `district_land` forward; the rule takes effect on a PDF
  ingest only.

## Migration Plan

1. Land the code change and the tests (no output changes).
2. The next PDF ingest (D9g step 9, the 2026-11-03 gazette) applies the rule:
   7 rows' `district_land` change, and the report names the count.
3. Rollback: revert the code change. The stored `district_land` returns to its
   previous value on the next ingest; nothing else depends on it.
