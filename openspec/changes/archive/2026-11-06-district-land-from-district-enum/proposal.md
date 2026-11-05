## Why

The Taipei City Government prints three city-side typos in the 地號 column, and
the reader reads them literally. `DISTRICT_RE` (`臺北市(.{1,4}?區)`) demands
the 市, so the cells that print `臺北大安區` and `臺北士林區` (missing 市)
yield an empty `district_land`; the cells that print `臺北市投區` (missing 北,
recnos 488, 558, 927) yield the non-district `投區`, which then travels into
the record's land core (`投區崇仰段三小段156地號等23筆`) — a key no portal page
and no cached project can match.

The corpus was measured on 2026-11-06 over the 1,442 rows of `clean.tsv`
(`scripts/probe_d14b_enum_rows.py`): **7 rows change** under the rule this
change adopts, and no other row moves. The rule takes effect on a PDF ingest
only — `--from-js` carries the stored value forward — so it must land before
the next ingest (D9g step 9, the 2026-11-03 gazette).

## What Changes

- `_land_district` reads the 地號 cell's district from the **collected
  12-district enum** (the values collected from `clean.tsv`'s `district`
  column: 中山區 中正區 信義區 內湖區 北投區 南港區 士林區 大同區 大安區 文山區
  松山區 萬華區) instead of the `臺北市`-anchored regex.
- A cell that prints `臺北大安區` reads `大安區` (recnos 153, 382, 928); a cell
  that prints `臺北士林區` reads `士林區` (recno 926).
- A cell that prints `臺北市投區` reads `''` (recnos 488, 558, 927). The enum
  does not guess the missing 北 — `投區` is not a district, and repairing absent
  data by inference is forbidden.
- The `行政區與地號行政區不一致` flag **keeps firing on 488 / 558 / 927** and
  keeps quoting the printed token (`地號為投區`), even though the normalized
  `district_land` is now empty. The flag reports the publisher's contradiction;
  the field reports the normalized district.
- The section and the parcels of all 7 rows are unchanged. `_section` keeps
  splitting on `DISTRICT_RE`; only the district token changes.
- `project_id` does not move: `slug_for` reads the 行政區 column, not
  `district_land`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `data-cleansing`: a new requirement — the 地號 cell's district is read from
  the collected district enum; the mismatch flag keeps quoting the printed
  token.

## Impact

- `urtpe/cleanse.py` — `_land_district` and the district-enum collection; the
  mismatch flag's quoted token.
- `urtpe/cli.py` — the cleansing call passes the collected enum.
- `data/clean.tsv`, `data/merged.tsv`, `data/projects.json` — 7 rows' `district_land`
  changes (0 → 大安區 / 士林區, 投區 → `''`).
- `data/.link_cache/` — the 3 affected projects' land cores change. Their
  cache directories are named by `project_id` (unchanged), so the lookup is
  unaffected; the stored `land_core` field changes and is written on the next
  discovery write.
- No re-emit of its own: the change lands before the next PDF ingest.
