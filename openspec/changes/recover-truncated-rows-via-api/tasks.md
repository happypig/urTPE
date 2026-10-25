# tasks — recover-truncated-rows-via-api

## 1. POC — archive the evidence and close the calibration gaps (no product code)

- [ ] 1.1 Preserve the exploration probes with this change: copy the working scripts from
      the session temp dir into `probes/` — parcel census (`ab_census2.py`), GeoServer
      intersection (`bim_intersect2.py`, `bim_intersect3.py`), identity recovery
      (`uro_recover_rest.py`, `uro_recover67.py`), PDF cell reader (`pdf_all15.py`) — with a
      README naming what each proved.
- [ ] 1.2 T1: run the four-check identity matrix for all 15 rows; record normalized
      `CASE_NAME` vs 案名 equality per row (2 verified so far). Any row failing containment
      but passing similarity lands in the 0.5–0.7 flag band — record which.
- [ ] 1.3 T2: build the normalization table from observed drift (計劃→計畫, 簡寫 additions,
      spacing) and calibrate the similarity fallback against the 15 known-good pairs; state
      the chosen band.
- [ ] 1.4 T8: calibrate the overlap test against 虎林段 (must yield exactly 138) and 美仁段
      (must yield exactly 74 or fail safe to partial); record the threshold and the
      refuse-to-ambiguous rule.
- [ ] 1.5 T4: sample one archived ROC-era gazette; run identity recovery on its truncated
      rows; record API coverage of pre-2006 cases and the calendar handling.
- [ ] 1.6 T5: measure request volume and wall time for a full 15-row recovery pass; record
      the budget in this file.
- [ ] 1.7 T10: intersect `R089305`'s two polygons against the 2013 vs 2020 gazette lists to
      determine boundary vintage; document the finding and its handling.
- [ ] 1.8 Update the POC conclusions into design.md (evidence section) before any
      implementation task is checked.

## 2. Tests (write fully before any implementation)

- [ ] 2.1 Unit (pure matching logic): the four checks accept the 編號 79 fixture and refuse
      each single-check failure (wrong section; fragment not contained; count fragment
      missing; date missing in both fields) — four refusal tests.
- [ ] 2.2 Unit: date check passes on `uro_chk_date2` alone; ±1 match accepted only when no
      exact candidate exists, and is flagged.
- [ ] 2.3 Unit: multi-case attachment attaches both same-date zone cases, flags
      `ambiguous-zone`, and keeps a single land core (930 fixture).
- [ ] 2.4 Unit: list completion — GIS triple check accepts the 虎林段 fixture (138 list,
      fragment ⊆ set, surplus explained) and refuses when the count does not close (美仁段
      pre-calibration fixture) → fragment+partial.
- [ ] 2.5 Unit: named-anchor discrimination — `(原東星大樓基地)` is never treated as a zone
      marker; `(甲區段)` and `-B區` are.
- [ ] 2.6 Unit: normalized typo repair (`78-1`→`718-1`) emits the flag and the audit line;
      unrepaired fragments never silently change.
- [ ] 2.7 Unit: residual path — a row with no qualifying candidate stays excluded and named.
- [ ] 2.8 Adapter tests (HTTP): ashx and GeoServer calls are keyed lookups only (no
      enumeration pattern); request failures degrade to residual, never abort the run.
- [ ] 2.9 Acceptance (end-to-end, offline fixtures + recorded responses): a flagged run on
      the current gazette emits ~1,442 records, +5 projects, report shows
      `RECOVERED: 14 … / INCOMPLETE: 1 …`; a run without the flag is byte-identical to the
      pre-change output.

## 3. Implementation — extraction (keep-and-mark under the flag)

- [ ] 3.1 extract.py: under the flag, truncated rows are retained in raw.tsv marked as
      source faults carrying 核定日期, 行政區, 案名 fragment, 地號 fragment; without the
      flag, drop before emission unchanged.
- [ ] 3.2 extract.py: marked rows bypass cleansing/merge until the recovery pass resolves
      or abandons them; abandoned rows rejoin the plain exclusion path.

## 4. Implementation — recovery adapter (I/O) and matching (pure)

- [ ] 4.1 Pure module: four-check matcher, date-field resolution, zone-grouping
      (same-unit same-date), named-anchor discrimination — no I/O.
- [ ] 4.2 Adapter `gis.uro.taipei/ashx/`: `Get_updcase_list` keyed lookup (hyphen-split,
      4-digit padding), `get_project168_top`; parse `uro_chk_date`/`uro_chk_date2`.
- [ ] 4.3 Adapter GeoServer WFS: boundary by `ID='<case>'` on `uro-redevelop-ALL-5`;
      whole-section pull of `LAND-ALL-TWD97`; containment test with the calibrated overlap
      threshold; no CQL BBOX (T9).
- [ ] 4.4 Pure module: two-tier list completion (D-D) and normalized typo repair (D-F).
- [ ] 4.5 Wire provenance + audit entries into the emission records and run report;
      RECOVERED/INCOMPLETE lines (D7).

## 5. Implementation — CLI, merge integration, docs

- [ ] 5.1 cli.py: `--recover-truncated` flag; threaded through the single-writer run; no
      flag → no recovery code path executes.
- [ ] 5.2 Merge integration: recovered rows enter the similarity merge with their land
      core; new project caches created via the normal link flow; verify the coverage guard
      sees additions (T6).
- [ ] 5.3 Viewer: display provenance flags (recovered, partial, normalized,
      ambiguous-zone) on affected nodes.
- [ ] 5.4 Docs: `docs/urotpe_api.md` gains the GeoServer WFS section (D10); append a dated
      entry to `docs/portal_operations_log.md`; AGENTS.md counts refreshed after emission.

## 6. Verification

- [ ] 6.1 Full offline suite passes (`python -m pytest`).
- [ ] 6.2 Flagged run on the current gazette into a temp output tree: acceptance scenario
      2.9 verified against real API responses; diff reviewed row by row.
- [ ] 6.3 Flag-less run re-executed: byte-identical to the pre-change emission (hash
      compare of raw.tsv, merged.tsv, projects.json).
- [ ] 6.4 `openspec validate` clean for this change; `python scripts\baseline_silent_failures.py`
      still passes.
