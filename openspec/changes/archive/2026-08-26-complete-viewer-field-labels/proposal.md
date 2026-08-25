# Complete Viewer Field Labels + Construction-Phase Graph Annotations

## Why

Viewer users reading the 獎勵資料 and 執行階段 cards see raw English keys —
`GREENBUILD_DESIGN`, `TIME_REWARD`, `Eng_Start_Date`, `△F5-6`-style sub-fields —
wherever `viewer/app.js` lacks a label mapping. The maps (`IMPL_LABELS`,
`REWARD_LABELS`) were built from a single live-probed case whose reward flags
were empty, so the incentive-key half was never populated. A corpus scan over
the 691 caches (2026-08-25, facts §12 #9) found ~2,500 non-empty reward
payloads carrying **41 distinct keys, 37 without labels**, plus 3 third.ashx
date fields rendering as raw keys inside the 執行階段 card. The official
Chinese labels are now fully captured from the platform's own
r_progress_detail.aspx DOM (facts §12.1), so completion is pure transcription —
no further probing needed.

Separately, the graph itself hides a project's construction progress: 建照核發/
開工/使照 dates sit buried inside milestone cards, and the anchor record's key
implementation stats (實施方式/基地面積/原戶數) require expanding two cards to
find. Surfacing them as graph annotations makes completed-vs-in-construction
projects distinguishable at a glance.

## What Changes

- Extend `REWARD_LABELS` in `viewer/app.js` with the official labels for all
  currently-unmapped keys: the F-family volume fields (`F1..F6`,
  `F4_1..F4_3`, `F5_1..F5_6`, `Park_Area`, `Park_Cars`) and the incentive keys
  (`TIME_REWARD`, `SCALE_REWARD`, `GREENBUILD_DESIGN`, `SEISMIC_DESIGN`,
  `WISDOMBUILD_DESIGN`, `ACCESSIBLE_DESIGN`, `NEWTECH`, `IMENVIRON`,
  `BUILDPLANDES1..4`, `BUILDSAFE_CONDITION`, `CHARITY_BUILD`,
  `CULTURAL_MAINTAIN`, `DEVELOP_PUBFACILITY`, `AGREEMENT_CONSTRUCTION`,
  `PROREGENERAT1/2`, `VOLUME_HIGHER_REWARD`, `ILLEGAL_FLOORAREA_REWARD`,
  `name_reward_no`).
- Add the 3 missing `IMPL_LABELS` entries (`Eng_Start_Date` 開工日期,
  `Ulic_Date` 使照核發日期, `Report_Date` 成果報備日期).
- Naming policy (hybrid): keep the five existing semantic labels
  (`F`=允建容積, `F0`=基準容積, `F3`=都市更新獎勵, `F5`=其他容積獎勵,
  `F5_3`=人行步道面積); everything else takes the official DOM label verbatim
  from facts §12.1.
- Render construction-phase events inside the history graph timeline:
  建照核發 → 開工 → 使照 as dated nodes in a dedicated E) 執行階段 column,
  attributed by a source-colored edge (pink Taipei / green national) to the
  latest approval dated on or before the event; 使照 corroborated by the
  national portal renders green with a 國 badge and a western date
  (民國 115 → 2026).
- Render per-record implementation callouts (實施方式/基地面積/原戶數)
  tail-attached to each carrying record, with values changed vs the nearest
  earlier carrying record highlighted red.
- Attach per-record implementation snapshots at emission (additive optional
  node field riding on the §6.6 date anchoring; `schema_version` unchanged,
  existing consumers unaffected).
- Retire the standalone 相關連結 section behind a debug toggle (default
  hidden): portal links live on the graph (北/國 badges and event labels are
  hyperlinks to their source); the project list sorts by 現況 recno ascending.
- Fetch and cache untouched; the one emission addition (per-record snapshots)
  is additive and optional.
- No part of this scope is gated on the PDF-parsing/similarity POC findings —
  neither the parsing nor the merge/threshold surface is touched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `taipei-implementation-data`: strengthen the "Viewer renders implementation
  and reward cards" requirement — every key observed in the emitted
  `implementation`/`rewards` objects SHALL render with its official portal
  Chinese label (no raw-key fallback for known keys), per the label inventory
  in facts §12.1; plus a new additive requirement attaching per-record
  implementation snapshots to their anchored records.
- `history-graph`: construction-phase events render as dated nodes in an
  E) 執行階段 timeline column with source-colored attribution edges, 國 badge,
  carrying-case provenance, and per-record diff-highlighted callouts.
- `viewer-related-links`: the standalone 相關連結 section is retired behind a
  debug toggle (default hidden); portal links live on the graph nodes instead.

## Impact

- `viewer/app.js` + `viewer/app.css`: label tables, timeline events, per-record
  callouts, hyperlinked badges.
- `urtpe/links.py`: additive per-record implementation snapshot attach (one
  block in the existing attach flow).
- `urtpe/cleanse.py`: 事業換計畫 → 事業計畫 typo normalization (recno 621,
  user-reported).
- Tests: `tests/test_viewer_labels.py` (structural), `tests/test_links.py`
  (snapshot attach), `tests/test_cleanse.py` (typo).
- Source of truth for labels: `docs/facts_2_portals.md` §12.1 (frozen record).
