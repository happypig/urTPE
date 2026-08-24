# Add Taipei Implementation Data (third.ashx + fourth.ashx)

## Why

Viewer readers (researchers, urban-renewal reviewers, residents tracking a case) currently
see only the pre-approval process trace: the pipeline integrates `Get_project168_second.ashx`
(階段辦理過程) but never calls `Get_project168_third.ashx` (執行階段 — 開工日期,
使照核發日期, 成果報備日期, 安置/停車/費用/土地產權統計) or `Get_project168_fourth.ashx`
(獎勵資料 — 容積獎勵組成). Both endpoints are documented and live-probed (facts §10.4–10.5,
`scripts/probe_third_6projects.py` proved availability for 6 projects), so 開工/使用執照
dates are knowable today yet absent from `projects.json` and the viewer — the exact dates
that answer "is this project actually being built?". Bundling this integration with the
upcoming bulk discovery refresh means one network pass instead of two.

## What Changes

- Discovery (`urtpe/links.py`) additionally POSTs `Get_project168_third.ashx` and
  `Get_project168_fourth.ashx` for each discovered Taipei case_id (after the existing
  second.ashx milestone fetch), storing results per case.
- `DiscoveryResult` and per-project caches gain `implementation` (third.ashx payload,
  keyed by case_id with provenance) and `rewards` (fourth.ashx payload).
- Emission (`schema_version` 1 → 2): projects carry new optional `implementation` and
  `rewards` objects; `milestones_taipei` gains 開工日期 / 使照核發日期 / 成果報備日期
  labels from the completed case, so the existing milestone cards render them with no UI
  change.
- Viewer (`viewer/app.js`) gains two cards mirroring the portal's own tabs: 執行階段
  (implementation stats) and 獎勵資料 (rewards), rendered only when data exists.
- Prerequisite (tracked, not part of this change's spec surface): the `STAGE_FIELD_MAP`
  round-2 corrections (comm_hold_date relabel, outline_ok_date / jud_ok_date0 /
  comm_hold_date0 additions) land before the bulk discovery pass — see facts §6.2/§16.

**Provisional scope (gated on observed data, not contracts):** "only the completed
case carries third/fourth values" is an empirical pattern (case 141 family +
6-project probe), not a guaranteed invariant — the design must tolerate any case
carrying data. fourth.ashx field semantics are unverified (every probe returned
empty values); values are stored raw and labeled provisionally until a populated
case is seen.

## Capabilities

### New Capabilities
- `taipei-implementation-data`: fetching, caching, and emitting Taipei implementation
  (third.ashx 執行階段) and reward (fourth.ashx 獎勵資料) data per case, attached at
  project level with case provenance, and rendering it in the viewer.

### Modified Capabilities
<!-- none — existing requirements (official-link-discovery, viewer-milestone-timeline)
     are unchanged; new labels flow through existing milestone rendering. -->

## Impact

- `urtpe/links.py`: `DiscoveryResult` (+`implementation`, `+rewards`), discovery flow
  (+2 POSTs per case), cache read/write (additive fields — old caches stay valid).
- `urtpe/viewer.py` / emission: `schema_version` 1 → 2, new optional project objects.
- `viewer/app.js` + `app.css`: two new optional cards.
- `tests/test_links.py`, `tests/fixtures_links.py`: fixtures for third/fourth payloads,
  attachment and emission tests.
- Network: ~+2 POSTs/case (~2,800 total on the bulk pass, Taipei platform — no WAF observed).
- Sequencing: bulk discovery refresh runs AFTER this change + STAGE_FIELD_MAP round 2
  (facts §12 sequence); `fetch_remaining_national_portal.py` unaffected.
