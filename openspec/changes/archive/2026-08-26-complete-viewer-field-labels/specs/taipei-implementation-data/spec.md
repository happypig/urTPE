# taipei-implementation-data — Delta: complete viewer field labels

## ADDED Requirements

### Requirement: Attach per-record implementation snapshots

Each approval record SHALL carry an optional `implementation` snapshot of its
anchored case's third.ashx payload (including `case_id` provenance) when that
case has a non-empty payload. Records whose anchored cases have empty or no
payloads SHALL carry none. The field is additive and optional: existing
emitted objects and consumers are unaffected, and `schema_version` is
unchanged.

#### Scenario: Anchored case with payload rides on its record
- **WHEN** a record anchors to a case whose implementation payload is non-empty
- **THEN** that record carries an `implementation` snapshot of that payload
  naming the case_id

#### Scenario: Sibling case without payload
- **WHEN** a record anchors to a case whose implementation payload is empty
- **THEN** that record carries no implementation snapshot

## MODIFIED Requirements

### Requirement: Viewer renders implementation and reward cards

The viewer SHALL render an 執行階段 card (implementation statistics) and a 獎勵資料
card (reward composition) for projects carrying the corresponding objects, using the
portal's own field labels, and SHALL render neither card when the objects are absent.
The new milestone labels 開工日期 / 使照核發日期 SHALL appear in the existing
milestone card without special handling.

Label coverage SHALL be complete for every key observed in the emitted objects:
each key present in the platform's official label inventory (captured from
r_progress_detail.aspx DOM, recorded in `docs/facts_2_portals.md` §12.1) SHALL
render with that Chinese label instead of its raw English key. This covers the
third.ashx date fields (`Eng_Start_Date` → 開工日期, `Ulic_Date` →
使照核發日期, `Report_Date` → 成果報備日期), the implementation statistic keys
(`Bui_Owners_Legal`, `Land_Owners_Pub`, `pc_afterUpdTotalValue`,
`Welfare_Area`, `Road_Cost`, and the upstream all-caps variant
`STATELAND2_OWNER`) and all fourth.ashx volume and
incentive keys (`F1..F6`, `F4_1..F4_3`, `F5_1..F5_6`, `Park_Area`, `Park_Cars`,
`TIME_REWARD`, `SCALE_REWARD`, `GREENBUILD_DESIGN`, `SEISMIC_DESIGN`,
`WISDOMBUILD_DESIGN`, `ACCESSIBLE_DESIGN`, `NEWTECH`, `IMENVIRON`,
`BUILDPLANDES1..4`, `BUILDSAFE_CONDITION`, `CHARITY_BUILD`,
`CULTURAL_MAINTAIN`, `DEVELOP_PUBFACILITY`, `AGREEMENT_CONSTRUCTION`,
`PROREGENERAT1/2`, `VOLUME_HIGHER_REWARD`, `ILLEGAL_FLOORAREA_REWARD`,
`name_reward_no`). Keys outside the inventory MAY fall back to their raw key.
Five semantic labels already in use are retained in place of the inventory's
△F/accounting notation: `F`=允建容積, `F0`=基準容積, `F3`=都市更新獎勵,
`F5`=其他容積獎勵, `F5_3`=人行步道面積.

#### Scenario: Implementation card rendered
- **WHEN** the viewer opens a project whose emitted data includes an `implementation`
  object
- **THEN** an 執行階段 card lists the populated statistics with their Chinese labels
  (e.g. 開闢道路工程費用, 實施都市更新費用)

#### Scenario: Implementation date fields render with Chinese labels
- **WHEN** the rendered `implementation` object contains `Eng_Start_Date`,
  `Ulic_Date`, or `Report_Date` values
- **THEN** those rows show 開工日期 / 使照核發日期 / 成果報備日期 rather than
  the raw English field names

#### Scenario: Incentive reward keys render with official labels
- **WHEN** the rendered `rewards` object contains any of the incentive keys
  (e.g. `TIME_REWARD`, `GREENBUILD_DESIGN`, `SCALE_REWARD`,
  `ILLEGAL_FLOORAREA_REWARD`) or F-family sub-fields (`F4_2`, `F5_6`)
- **THEN** each row shows the official portal label from the §12.1 inventory
  (e.g. 時程獎勵, 綠建築標章之建築設計, 規模獎勵,
  處理違建戶之樓地板面積獎勵) instead of the raw key

#### Scenario: Existing semantic labels preserved
- **WHEN** the rendered `rewards` object contains `F`, `F0`, `F3`, `F5`, or `F5_3`
- **THEN** the rows show 允建容積 / 基準容積 / 都市更新獎勵 / 其他容積獎勵 /
  人行步道面積 (unchanged), not F(㎡)/F0(㎡)/△F3(㎡)/△F5(㎡)/△F5-3(㎡)

#### Scenario: Unlisted key falls back gracefully
- **WHEN** a payload carries a key absent from the official inventory
- **THEN** the row renders using the raw key as label and no rendering error occurs

#### Scenario: Cards absent when no data
- **WHEN** the viewer opens a project without `implementation`/`rewards` objects
- **THEN** no implementation or reward card is rendered and the rest of the detail
  view is unchanged
