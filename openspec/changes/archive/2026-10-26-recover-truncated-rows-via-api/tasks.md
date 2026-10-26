# tasks — recover-truncated-rows-via-api

## 1. POC — archive the evidence and close the calibration gaps (no product code)

- [x] 1.1 Preserve the exploration probes with this change: copy the working scripts from
      the session temp dir into `probes/` — parcel census (`ab_census2.py`), GeoServer
      intersection (`bim_intersect2.py`, `bim_intersect3.py`), identity recovery
      (`uro_recover_rest.py`, `uro_recover67.py`), PDF cell reader (`pdf_all15.py`) — with a
      README naming what each proved.
- [x] 1.2 T1: run the four-check identity matrix for all 15 rows; record normalized
      `CASE_NAME` vs 案名 equality per row (2 verified so far). Any row failing containment
      but passing similarity lands in the 0.5–0.7 flag band — record which.
      → **15/15 exact** (improves the design table's 14/15); equality 13/15 (930's two
      zone-suffixed cases); address-core containment raw for all 15; no row in the flag
      band. Table in `poc_findings.md` T1.
- [x] 1.3 T2: build the normalization table from observed drift (計劃→計畫, 簡寫 additions,
      spacing) and calibrate the similarity fallback against the 15 known-good pairs; state
      the chosen band.
      → Table: whitespace, （）→(), 計劃→計畫, ㄧ→一 — defensive only (raw containment held
      for all 15). Band unchanged (0.7 / 0.5–0.7), exercised 0 times; accepted pairs ≥0.965.
- [x] 1.4 T8: calibrate the overlap test against 虎林段 (must yield exactly 138) and 美仁段
      (must yield exactly 74 or fail safe to partial); record the threshold and the
      refuse-to-ambiguous rule.
      → Pure fraction thresholds REJECTED (0.6 gap parcels interleave 0.6 tail members).
      Calibrated rule: fragment ∪ {candidates after the last visible parcel with ≥1 vertex
      inside}, accept iff count closes. 虎林段 113+25=138 CLOSES (min tail frac 0.2); 美仁段
      72+3=75≠74 → REFUSE → partial. Never subset-to-count. `poc_findings.md` T8.
- [x] 1.5 T4: sample one archived ROC-era gazette; run identity recovery on its truncated
      rows; record API coverage of pre-2006 cases and the calendar handling.
      → Premise adapted (archive holds no ROC-era publication; oldest 2026-08-11 with
      ROC-dated cells): 8/9 of its truncated rows recovered exact, 1 genuine residual;
      pre-2006 coverage 6/6 exact (2002-03-21 → 2005-03-01); ROC→ISO via existing `to_iso`,
      no new calendar code. `poc_findings.md` T4.
- [x] 1.6 T5: measure request volume and wall time for a full 15-row recovery pass; record
      the budget in this file.
      → Probe ceiling 187 requests / 50 s; product pass ≤ 83 requests (8 unit-keyed lookups
      + 68 name-hit top-calls), ~25 s; no WAF; 4× retry with backoff. `poc_findings.md` T5.
- [x] 1.7 T10: intersect `R089305`'s two polygons against the 2013 vs 2020 gazette lists to
      determine boundary vintage; document the finding and its handling.
      → Premise dissolved: R089305 returns two features, neither the 203-1 unit's boundary
      (overlap 9/97 and 0/97; list ⊄ candidates); the R-form id space is group-level
      (R089305 spans units 190/203-1/208/219/517); no 2013 list exists (2018 ≡ 2020, 97
      parcels). The triple check refuses both polygons → fragment+partial. `poc_findings.md`
      T10.
- [x] 1.8 Update the POC conclusions into design.md (evidence section) before any
      implementation task is checked.
      → Done: `poc_findings.md` written; design.md evidence + D-B/D-D updated (15/15,
      calibrated positional membership rule, budget, id-space finding); open questions
      T1/T2/T4/T8/T10 resolved; spec's list-completion requirement reworded to the
      calibrated rule with the measured refusal scenario added.

## 2. Tests (write fully before any implementation)

- [x] 2.1 Unit (pure matching logic): the four checks accept the 編號 79 fixture and refuse
      each single-check failure (wrong section; fragment not contained; count fragment
      missing; date missing in both fields) — four refusal tests.
      → `tests/test_recovery_match.py` (candidates from the recorded API responses).
- [x] 2.2 Unit: date check passes on `uro_chk_date2` alone; ±1 match accepted only when no
      exact candidate exists, and is flagged.
- [x] 2.3 Unit: multi-case attachment attaches both same-date zone cases, flags
      `ambiguous-zone`, and keeps a single land core (930 fixture).
- [x] 2.4 Unit: list completion — GIS triple check accepts the 虎林段 fixture (138 list,
      fragment ⊆ set, surplus explained) and refuses when the count does not close (美仁段
      pre-calibration fixture) → fragment+partial.
      → `tests/test_recovery_lists.py` (recorded candidate sets; also the T10
      fragment-containment refusal).
- [x] 2.5 Unit: named-anchor discrimination — `(原東星大樓基地)` is never treated as a zone
      marker; `(甲區段)` and `-B區` are.
- [x] 2.6 Unit: normalized typo repair (`78-1`→`718-1`) emits the flag and the audit line;
      unrepaired fragments never silently change.
- [x] 2.7 Unit: residual path — a row with no qualifying candidate stays excluded and named.
      → the real residual (南港段一小段561, recorded family of 22, no name hit).
- [x] 2.8 Adapter tests (HTTP): ashx and GeoServer calls are keyed lookups only (no
      enumeration pattern); request failures degrade to residual, never abort the run.
      → `tests/test_recovery_sources.py` (recorded bodies; the no-enumeration guard is a
      source-level assertion).
- [x] 2.9 Acceptance (end-to-end, offline fixtures + recorded responses): a flagged run on
      the current gazette emits ~1,442 records, +5 projects, report shows
      `RECOVERED: 14 … / INCOMPLETE: 1 …`; a run without the flag is byte-identical to the
      pre-change output.
      [numbers updated 2026-10-26 per the measured 15/15 matrix, `poc_findings.md` T1:
      expect RECOVERED: 15 / INCOMPLETE: 0 — 美仁段 is recovered with a partial list, not
      residual; ~1,442 records stands (1,427 + 15)]
      → `tests/test_recovery_acceptance.py` on the acceptance gazette (the 15 real
      fragments + the real residual) with a golden pre-change baseline captured from the
      unflagged code (`tests/fixtures/recovery/golden_unflagged/`).

## 3. Implementation — extraction (keep-and-mark under the flag)

- [x] 3.1 extract.py: under the flag, truncated rows are retained in raw.tsv marked as
      source faults carrying 核定日期, 行政區, 案名 fragment, 地號 fragment; without the
      flag, drop before emission unchanged.
      → `_page_records(..., retain_truncated)`; the mark rides `parse_error` in raw.tsv
      (no new column — the flag-less TSV bytes must not change).
- [x] 3.2 extract.py: marked rows bypass cleansing/merge until the recovery pass resolves
      or abandons them; abandoned rows rejoin the plain exclusion path.
      → `RawRecord.source_fault`; `cleanse_all` skips marked rows; residuals rejoin the
      exclusion path with their 編號 explained to the tripwire.

## 4. Implementation — recovery adapter (I/O) and matching (pure)

- [x] 4.1 Pure module: four-check matcher, date-field resolution, zone-grouping
      (same-unit same-date), named-anchor discrimination — no I/O.
      → `urtpe/recovery.py`.
- [x] 4.2 Adapter `gis.uro.taipei/ashx/`: `Get_updcase_list` keyed lookup (hyphen-split,
      4-digit padding), `get_project168_top`; parse `uro_chk_date`/`uro_chk_date2`.
      → `urtpe/recovery_sources.py` (`AshxClient`); top called only for name-hit
      candidates (the measured ≤83-request budget).
- [x] 4.3 Adapter GeoServer WFS: boundary by `ID='<case>'` on `uro-redevelop-ALL-5`;
      whole-section pull of `LAND-ALL-TWD97`; containment test with the calibrated overlap
      threshold; no CQL BBOX (T9).
      → `GeoServerClient.unit_geometry` (≥1-ring-vertex membership + section cadastre);
      numeric ids skipped without a request.
- [x] 4.4 Pure module: two-tier list completion (D-D) and normalized typo repair (D-F).
      → `complete_unit_list` (positional tail + vertex containment + count closes, never
      subset-to-count) and `repair_fragment` (printed-order contradiction + one-deletion
      match fitting the printed slot — the measured 78-1→718-1 case has three one-deletion
      neighbours, so the slot is what disambiguates).
- [x] 4.5 Wire provenance + audit entries into the emission records and run report;
      RECOVERED/INCOMPLETE lines (D7).
      → provenance rides `RawRecord.recovery` → `CleanRecord.recovery` → node["recovery"]
      (additive; TSVs unchanged); `report.recovery_report` renders both lines per-row.

## 5. Implementation — CLI, merge integration, docs

- [x] 5.1 cli.py: `--recover-truncated` flag; threaded through the single-writer run; no
      flag → no recovery code path executes.
      → verified by the unflagged acceptance test (transport monkeypatched to raise; the
      run succeeds).
- [x] 5.2 Merge integration: recovered rows enter the similarity merge with their land
      core; new project caches created via the normal link flow; verify the coverage guard
      sees additions (T6).
      → recovered rows are normal records past the pass; the acceptance test observes
      +8 projects on the fixture (additions, not a re-key); the live +5 check is 6.2.
- [x] 5.3 Viewer: display provenance flags (recovered, partial, normalized,
      ambiguous-zone) on affected nodes.
      → `viewer/app.js` gains a 復原 column (badge strip + list source + case ids) fed by
      node["recovery"]; additive only — nodes without recovery render empty.
- [x] 5.4 Docs: `docs/urotpe_api.md` gains the GeoServer WFS section (D10); append a dated
      entry to `docs/portal_operations_log.md`; AGENTS.md counts refreshed after emission.
      → §6 added to urotpe_api.md (two layers, R-form group-level id space, SRS trap,
      document-route absence); §25 appended to the operations log; AGENTS.md test counts
      667→703 / 666→702.

## 6. Verification

- [x] 6.1 Full offline suite passes (`python -m pytest`).
      → **702 passed, 1 skipped** (the deliberate skip at test_idempotent_flags.py:117).
- [x] 6.2 Flagged run on the current gazette into a temp output tree: acceptance scenario
      2.9 verified against real API responses; diff reviewed row by row.
      [measured 2026-10-26, live (核定案件-2026-10-23.pdf, 統計至 2026-10-15): rc=0,
      tripwire PASS, 1,442 records / 694 projects = flag-less 689 +5, RECOVERED: 4 /
      INCOMPLETE: 0. The other 11 truncated rows were completed offline by the
      pre-existing corpus mechanism (older gazettes hold their full lists) — 15 restored
      in total, matching the predicted +15 records. Diff reviewed: 4 added rows (188,
      1005, 1131, 1206), 0 removed, 0 changed. Rows 188 (R089213-02: boundary missing
      46-5/47 — vintage mismatch, fragment-not-contained) and 1131 (R091007-02: tail 108
      ≠ 105 — refuse-to-ambiguous) stayed fragment+partial by the calibrated fail-safes,
      measured live (`probes/review_flagged_live.py`). The corpus-completed rows are
      recorded by the pre-existing completion audit.]
      [probes/verify_flagged_live.py + review_flagged_live.py; archive copied to temp —
      live archive and change sets untouched]
- [x] 6.3 Flag-less run re-executed: byte-identical to the pre-change emission (hash
      compare of raw.tsv, merged.tsv, projects.json).
      → A/B form (the committed data/ is stale relative to check-declared-parcel-counts —
      emitted 2026-10-07, that extraction change landed 2026-10-26 — so the honest baseline
      is a worktree at HEAD): raw.tsv / clean.tsv / merged.tsv / projects.json (normalized)
      all byte-identical between HEAD and this tree, flag-less, same copied archive
      (`probes/verify_flagless_ab.py`). The offline golden (`golden_unflagged/`) proves the
      same on the fixture gazette. The committed data/ refresh is an operator step that
      predates this change and is not part of it.
- [x] 6.4 `openspec validate` clean for this change; `python scripts\baseline_silent_failures.py`
      still passes.
      → validate: "recover-truncated-rows-via-api is valid"; baseline end state as
      expected (items 1–4 caught, item 5 reads yes — --links stays advisory by design).

## 7. Reconciliation attribution (found during the live ingestions)

- [x] 7.1 Test-first: a recovered row is reported under `recovered`, not `edited`; the
      exemption is keyed on the land the run actually completed, so an ordinary historical
      edit in the same run stays an edit; the persisted change set records the count and a
      run that recovered nothing records zero.
      → `tests/test_reconcile.py` (two cases), `tests/test_change_set.py` (two cases).
- [x] 7.2 reconcile/changeset/CLI: `ReconcileResult.recovered` + report line, threaded from
      the recovery outcome; `change_set_payload` writes `recovered` beside — not inside —
      `unresolvable`.
      → measured cause: the predecessor is re-read without `--recover-truncated`, so all 4
      recovered rows on 2026-10-06 and 2026-10-15 were published as `edited: 4`. Delta
      spec: `specs/gazette-reconciliation/spec.md`.
- [x] 7.3 Re-ingest 2026-10-06 and 2026-10-15 with the flag so both change sets record
      `recovered: 4` / `edited: 0`; confirm the emitted dataset is unchanged
      (1,442 records / 694 projects, `published_date` 2026-10-15).
      → 2026-10-06: 1,441 records, net +5 (1,436→1,441), `edited: 0 / recovered: 4`;
      2026-10-15 (with `--links`, all cache hits): 1,442 records, net +5 (1,437→1,442),
      same split. Emission unchanged: 1,442 / 694, `published_date` 2026-10-15, 4 nodes
      with `recovery` provenance. Full suite 705 + 1 skip.


