# recover-truncated-rows-via-api

## Why

Publisher truncation removes the 地號 tail of long gazette cells at the printed row height;
the text is absent from the PDF. On the 2026-10-15 gazette this excludes 15 records covering
only 8 renewal units — and because every row of a big unit truncates identically, corpus
borrowing fails for 17 of 21 historical cases: 5 units are entirely absent from the dataset
(虎林段四小段38地號等138筆 among them). The city, however, holds the same units in two other
systems we have verified live: the `gis.uro.taipei` ashx case APIs (which return the complete
案名 and approval dates per case) and the UDD GeoServer WFS (`uro-redevelop-ALL-5` case
boundaries ∩ `LAND-ALL-TWD97`, 421,857 cadastral parcels). Exploration on 2026-10-25/26
matched 14 of the 15 excluded rows to an API case by exact date, and reconstructed the
虎林段 unit's full 138-parcel list from the map service. The excluded records are real
approvals; the data to restore them exists.

Decisions recorded 2026-10-26 (exploration session): D1 opt-in flag; D2 attach all
same-unit same-date cases; D3 keep PDF fragment + partial flag; D4 exact date first, ±1
flagged; D6 applies at parse time whenever the flag is on; D7 report keeps both RECOVERED
and INCOMPLETE lines; D8 reconstruct lists only when the triple check holds; D9 repair
GIS-verified cell typos with a flag; D10 document the GeoServer WFS; D11 recovery rows only.

## What Changes

- New opt-in CLI flag `--recover-truncated`. Without it, output is byte-identical to today.
- Under the flag, extraction retains truncated rows (marked with their surviving fragments:
  date, 行政區, 案名 fragment, 地號 fragment) instead of dropping them; a recovery adapter
  then queries the ashx APIs and the GeoServer WFS.
- Identity recovery per row: `Get_updcase_list(sectstr, monobuf, sunobuf)` keyed from the
  row's own 案名 (section + first parcel, hyphen-split), filtered by the declared-count
  fragment, then `get_project168_top`. Accepted only when all checks hold: district/section
  consistent; declared-count fragment contained in the API `CASE_NAME`; approval date found
  in `uro_chk_date` or `uro_chk_date2` equal to the gazette date (±1 day allowed but
  flagged); match unique among same-date candidates.
- Multi-case attachment: when several same-unit cases share the approval date (zone pairs
  such as 雙園段 -A/-B), the row attaches all of them, flagged `ambiguous-zone`.
- Parcel-list completion, two tiers: R-form unit ids with a GeoServer boundary polygon get
  the unit list reconstructed (boundary ∩ `LAND-ALL-TWD97` by section, deterministic tail
  selection) when the triple check holds — declared count closes, PDF fragment ⊆ GIS set,
  and the surplus parcels are explained (skip-pattern continuation); otherwise the row keeps
  the PDF fragment flagged `partial`. GIS-verified cell typos (e.g. `78-1`→`718-1`) are
  repaired with a `normalized` flag, never silently.
- Recovered rows enter the normal merge with provenance (case_id, source endpoint, date
  check) and an audit entry; the run report splits `RECOVERED: N … / INCOMPLETE: M …` and
  the gazette is still never described as a faithful copy.
- Documentation: `docs/urotpe_api.md` gains the GeoServer WFS section (D10).
- **BREAKING** only under the flag (dataset grows by the recovered rows; expected
  1,427→~1,442 records, +5 projects on the current gazette). Default output unchanged.

## Capabilities

### New Capabilities

- `truncated-row-recovery`: the opt-in recovery of publisher-truncated gazette rows from the
  city's case APIs and map service — identity checks, multi-case attachment, two-tier
  parcel-list completion, provenance, and reporting.

### Modified Capabilities

- `pdf-tsv-extraction`: under `--recover-truncated`, publisher-truncated rows are retained
  in raw.tsv marked as source faults (with their surviving fragments) instead of dropped
  before emission; without the flag the existing exclude-and-name behaviour is unchanged.

## Impact

- `urtpe/cli.py` — new flag, threaded to extraction and the recovery pass (single-writer run
  unchanged).
- `urtpe/extract.py` — keep-and-mark mode under the flag.
- New recovery adapter (port/adapter split: pure matching logic separate from the I/O
  adapters for `gis.uro.taipei/ashx/` and `zonegeo.udd.gov.taipei/geoserver/`).
- `.link_cache` — recovered units create project caches via the normal link flow; 5 new
  project identities expected on the current gazette (coverage guard must see additions, not
  a re-key).
- Viewer — recovered rows carry provenance flags for display.
- Sequencing: lands after `check-declared-parcel-counts` so hyphen-cut rows (1005-class) are
  consistently flagged by one mechanism.
- POC evidence and open technical items (identity normalization table, overlap threshold,
  ROC-era depth, request budget) live in design.md and tasks.md.
