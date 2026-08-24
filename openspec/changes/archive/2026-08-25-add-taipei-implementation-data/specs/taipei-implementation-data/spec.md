# taipei-implementation-data Specification

## Purpose

Integrates the Taipei platform's implementation (執行階段, `Get_project168_third.ashx`)
and reward (獎勵資料, `Get_project168_fourth.ashx`) data into the discovery pipeline,
project cache, emitted graph, and viewer — so a project's 開工/使用執照 progress and
容積獎勵 composition are visible without leaving the viewer.

## ADDED Requirements

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

#### Scenario: Implementation card rendered
- **WHEN** the viewer opens a project whose emitted data includes an `implementation`
  object
- **THEN** an 執行階段 card lists the populated statistics with their Chinese labels
  (e.g. 開闢道路工程費用, 實施都市更新費用)

#### Scenario: Cards absent when no data
- **WHEN** the viewer opens a project without `implementation`/`rewards` objects
- **THEN** no implementation or reward card is rendered and the rest of the detail
  view is unchanged
