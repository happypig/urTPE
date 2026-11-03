## Why

`extract_landcore_from_case_name` (urtpe/links.py:976) returns "" for 3 city
name shapes, and the orphan gate (`urtpe/links.py:2455`) then drops the case
without a report. Measured (Batch C, C4): 33 cached case names are
unparseable; 8 real cases in 3 projects are dropped from the graph silently —
華中247 loses its whole A區/B區 history (09305081, 09305082, 09407301–09407304),
長安709 loses 09205060, 南港531-4 loses 09406102.

## What Changes

- The extractor learns 3 shapes: the 、-list before 地號
  (`長安段三小段709、711地號等2筆`), `(原NNN)` inside the parcel or count
  (`105(原90)地號等13筆(原24筆)`), and spaces before 地號/筆
  (`1-1 地號等11 筆`). Compatibility characters are NFKC-normalised before
  matching (the 擬訂臺北市 prefix with U+F963 北, Appendix A).
- Every city name that still yields no land core is reported by the run
  report, not dropped silently (AGENTS.md: never repair absent data by
  inference; never drop silently).
- Re-emit only (no fetch): the 8 dropped cases come back as orphan nodes.

## Capabilities

### Modified Capabilities
- `orphan-case-anchoring`: the ghost landcore extraction SHALL accept the
  、-list, `(原NNN)` and spaced shapes plus NFKC; names that still yield no
  land core SHALL be named in the run report.

## Impact

- `urtpe/links.py`: `extract_landcore_from_case_name` (NFKC + 3 shapes);
  the orphan gate reports unparseable names.
- Re-emit (`data/` + `viewer/projects.data.js`): 8 orphan nodes return.
