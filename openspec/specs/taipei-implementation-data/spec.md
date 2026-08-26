# taipei-implementation-data Specification

## Purpose

Integrates the Taipei platform's implementation (執行階段, `Get_project168_third.ashx`)
and reward (獎勵資料, `Get_project168_fourth.ashx`) data into the discovery pipeline,
project cache, emitted graph, and viewer — so a project's 開工/使用執照 progress and
容積獎勵 composition are visible without leaving the viewer.

## Requirements

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

### Requirement: Fetch implementation data per discovered case

The system SHALL POST each discovered Taipei case_id to
`ashx/Get_project168_third.ashx` (after the existing second.ashx milestone fetch)
and retain the response payload per case. Failures SHALL be recorded without
aborting discovery, consistent with the existing per-case fetch behavior.

#### Scenario: Completed case returns implementation fields
- **WHEN** the implementation fetch for a completed case (e.g. 09811141) returns
  `Eng_Start_Date`, `Ulic_Date`, or `Exe_Way` values
- **THEN** those values are stored under that case's implementation payload

#### Scenario: Non-final cases return empty payloads
- **WHEN** the implementation fetch for a revision case returns all-empty fields
- **THEN** an empty payload is stored for that case and no error is raised

#### Scenario: Fetch failure does not abort discovery
- **WHEN** the third.ashx POST fails after retries for one case
- **THEN** the failure is recorded for that case and discovery continues with the
  remaining cases

### Requirement: Fetch reward data per discovered case

The system SHALL POST each discovered Taipei case_id to
`ashx/Get_project168_fourth.ashx` and retain the response payload per case, with the
same failure tolerance as the implementation fetch.

#### Scenario: Reward fields returned for a case
- **WHEN** the reward fetch returns non-empty 容積獎勵 fields (e.g. `F0`, `F`, `F3`)
- **THEN** those values are stored under that case's reward payload

#### Scenario: Reward fetch yields no data
- **WHEN** the reward fetch returns all-empty fields or a malformed body
- **THEN** an empty payload is stored without error

### Requirement: Cache implementation and reward payloads additively

The per-project cache SHALL persist per-case implementation and reward payloads as
new fields alongside existing fields. Projects whose caches predate this capability
SHALL remain loadable, behaving as if the payloads were empty.

#### Scenario: New cache carries payloads
- **WHEN** discovery completes for a project and writes its cache
- **THEN** the cache file contains per-case implementation and reward payloads
  without removing any existing field

#### Scenario: Pre-existing cache stays loadable
- **WHEN** a cache written before this capability is loaded
- **THEN** implementation and rewards are treated as absent (empty), and no
  migration error occurs

### Requirement: Emit implementation milestones and objects at project level

Emission SHALL attach implementation outcomes at PROJECT level (the built outcome
belongs to the project, with the carrying case recorded as provenance), bumping
`schema_version` to 2:

- `milestones_taipei` SHALL additionally carry 開工日期 (`Eng_Start_Date`) and
  使照核發日期 (`Ulic_Date`) — and 成果報備日期 (`Report_Date`) when non-empty —
  sourced from the case whose payload contains them.
- An optional `implementation` object SHALL carry the non-date third.ashx fields
  (實施方式, 基地面積, 土地使用分區, 產權/安置/停車/費用 statistics) plus the
  provenance case_id.
- An optional `rewards` object SHALL carry the fourth.ashx 容積獎勵 fields.
- Consumers of the version-1 schema SHALL keep working: all new fields are optional
  and no existing field changes meaning.

#### Scenario: Project with a completed case emits milestones
- **WHEN** a project's discovered cases include one whose implementation payload has
  `Eng_Start_Date` 2013/09/10 and `Ulic_Date` 2016/08/29
- **THEN** the emitted project carries `milestones_taipei` entries
  開工日期 = 2013/09/10 and 使照核發日期 = 2016/08/29, and `schema_version` = 2

#### Scenario: Provenance recorded
- **WHEN** implementation values are emitted for a project
- **THEN** the emitted `implementation` object identifies which case_id supplied them

#### Scenario: Project with no implementation data
- **WHEN** every discovered case returns empty third/fourth payloads (e.g. projects
  still under review)
- **THEN** the emitted project has no `implementation`/`rewards` objects (or empty
  ones), no new milestone labels, and remains valid under the version-1 consumer
  contract

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

### Requirement: Emit milestones source map

While merging per-case stage milestones into the project-level
`milestones_taipei` (last-write-wins per label), the system SHALL additionally
record which case won each label into an additive optional
`milestones_source` map (label → case_id) attached to the project links.
Labels merged from implementation payloads SHALL resolve to the payload's
provenance case_id. The map SHALL be absent when no case provided any
milestone. `schema_version` is unchanged and existing consumers are
unaffected.

#### Scenario: Single carrying case provable for 建照
- **WHEN** only one anchored case's stage milestones contain 建照核發日期
  (e.g. case 10011041 in 金華段四小段513-3, whose four sibling cases carry none)
- **THEN** `milestones_source["建照核發日期"]` equals that case_id even after
  the merge

#### Scenario: Later case overwrites and wins the map entry
- **WHEN** two cases carry different 建照核發日期 values and the merge keeps
  the later case's value
- **THEN** `milestones_source["建照核發日期"]` names that winning case, so the
  viewer can attribute the slot truthfully

#### Scenario: No milestones at all
- **WHEN** every case returns empty stage milestones and no implementation
  dates exist
- **THEN** no `milestones_source` map is attached and nothing else changes

### Requirement: Construction slots are provenance-complete

Every emitted 建照核發日期/開工日期/使照核發日期 value SHALL resolve to its
source at the viewer: a carrying case via `milestones_source` or the
implementation payload's `case_id` exact match, or the national portal via
使用核發日期. The resolution chain SHALL require no heuristics. A slot that
resolves by none of these SHALL render as isolated (no source edge, no
provenance label) and SHALL be reported by the corpus provenance validation
with its family, slot, and value.

#### Scenario: Stage label resolves via source map
- **WHEN** 建照核發日期 exists in `milestones_taipei`
- **THEN** `milestones_source` names the case whose value won the merge

#### Scenario: Implementation date resolves via case_id
- **WHEN** 開工日期/使照核發日期 equals the best implementation payload's date
- **THEN** the slot resolves to that payload's `case_id`

#### Scenario: National-only 使照 resolves via the 國 mapping
- **WHEN** 使照核發日期 is absent from Taipei milestones but 使用核發日期 exists
- **THEN** the slot resolves to the national portal (green source group)

#### Scenario: Unresolvable slot is reported
- **WHEN** a slot value resolves by none of the resolution paths
- **THEN** the corpus provenance validation fails listing the family, slot,
  and value, and the event renders as isolated rather than misattributed
