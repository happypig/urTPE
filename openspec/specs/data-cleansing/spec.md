# data-cleansing Specification

## Purpose

Cleans the raw TSV into a normalized dataset: fixes known data errors, derives structured fields (parcels, counts, aliases, sections, stages), auto-applies obvious fixes, and flags ambiguous cases for review.

## Requirements

### Requirement: Normalize known data errors

The system SHALL correct the known error classes: district "松化區" to "松山區", "計劃" to "計畫", "ㄧ" to "一", and treat "權利變換案" as equivalent to "權利變換計畫案".

#### Scenario: District typo corrected
- **WHEN** a record has 行政區 = "松化區"
- **THEN** clean.tsv records 行政區 = "松山區"
- **AND** the correction is noted in the review report

#### Scenario: Character and variant normalization
- **WHEN** a name contains "計劃" or the bopomofo character "ㄧ"
- **THEN** it is emitted as "計畫" and "一" respectively

### Requirement: Convert dates to ISO

The system SHALL convert 核定日期 from ROC calendar (YY/M/D) to ISO-8601 (ROC year + 1911) in clean.tsv.

#### Scenario: ROC date conversion
- **WHEN** a record's date is "115/8/11"
- **THEN** clean.tsv emits the ISO date 2026-08-11

### Requirement: Derive structured fields

The system SHALL derive and expose structured fields per record: 段X小段, first parcel, full parcel set with 原地號 aliases, parcel count, original count (原N筆), named anchor (原XX基地/國宅/整宅), 區段 (甲/A/B), stage (擬訂/變更/變更(第N次)), and plan track (事業計畫/權利變換).

#### Scenario: Parcel and count parsing
- **WHEN** a 地號 cell is "臺北市北投區奇岩段三小段 1-1、85、86、…地號等11筆土地"
- **THEN** clean.tsv exposes section="奇岩段三小段", first_parcel="1-1", parcel set {1-1,85,86,…}, and land_count=11

#### Scenario: Coverage change annotation captured
- **WHEN** a 案名 contains "(原10筆)"
- **THEN** the original count (10) is captured in orig_count separately from the current count

#### Scenario: Parcel renumbering alias captured
- **WHEN** a 地號 cell is "689地號(原726地號)等40筆土地"
- **THEN** the parcel set includes alias 726 for parcel 689

#### Scenario: Named anchor captured
- **WHEN** a 案名 references "原東星大樓基地"
- **THEN** the named_anchor field is populated with that anchor

#### Scenario: Stage and track derived
- **WHEN** a 案名 is "變更(第二次)…都市更新權利變換計畫案"
- **THEN** stage="變更(第二次)" and track="權利變換" are derived

### Requirement: Auto-fix obvious, flag ambiguous

The system SHALL apply obvious fixes automatically and route ambiguous cases to a review/flag column with a reason, without guessing.

#### Scenario: Ambiguous record flagged with reason
- **WHEN** a record's 案名 district disagrees with its 地號 district (e.g. 中正區 in name, 大同區 in parcels)
- **THEN** the record is emitted with a populated review flag describing the contradiction
- **AND** no district value is silently overwritten for that record

### Requirement: Emit a review report

The system SHALL produce a review report listing every auto-fix and every flagged record with its 編號, field, and reason.

#### Scenario: Report covers all interventions
- **WHEN** the cleansing step finishes
- **THEN** the report contains one entry per auto-fix and one entry per flagged record, each traceable to a 編號