# data-cleansing Specification

## Purpose

Cleans the raw TSV into a normalized dataset: fixes known data errors, derives structured fields (parcels, counts, aliases, sections, stages), auto-applies obvious fixes, and flags ambiguous cases for review.
## Requirements
### Requirement: Normalize known data errors

The system SHALL correct the known error classes: district "松化區" to "松山區", "計劃" to "計畫", "ㄧ" to "一", treat "權利變換案" as equivalent to "權利變換計畫案", and normalize the 案名 abbreviation "土地都市更新計畫案" to "土地都市更新事業計畫案" (when the 案名 does not already contain 事業計畫) — the PDF-era gazette abbreviation verified against the platform's own `CASE_NAME` (live cross-reference 18/18, data: `data/_gengxin_plan_crossref.json`). Each application of this rule SHALL be noted in the record's `auto_fixes`.

#### Scenario: District typo corrected
- **WHEN** a record has 行政區 = "松化區"
- **THEN** clean.tsv records 行政區 = "松山區"
- **AND** the correction is noted in the review report

#### Scenario: Character and variant normalization
- **WHEN** a name contains "計劃" or the bopomofo character "ㄧ"
- **THEN** it is emitted as "計畫" and "一" respectively

#### Scenario: Abbreviated 案名 gains 事業
- **WHEN** a record's 案名 is "擬訂臺北市中山區長春段二小段775地號等3筆土地都市更新計畫案" (no 事業計畫)
- **THEN** it is emitted as "擬訂臺北市中山區長春段二小段775地號等3筆土地都市更新事業計畫案"
- **AND** the correction is noted in `auto_fixes` as 案名補事業(都市更新計畫案簡寫)
- **AND** the record's track derives as 事業計畫 (not the synthetic 都市更新計畫)

#### Scenario: Already-full names are untouched
- **WHEN** a record's 案名 already contains "事業計畫" (e.g. "變更…土地都市更新事業計畫及擬訂權利變換計畫案")
- **THEN** the name is emitted unchanged and no auto-fix is recorded

#### Scenario: Downstream track vocabulary collapses the synonym
- **WHEN** cleansing completes over the corpus (10 affected nodes / 6 families at the 2026-08-30 census)
- **THEN** no node emits the synthetic track `都市更新計畫` — affected nodes derive track `事業計畫`
- **AND** the viewer's four-column placement of those nodes is unchanged (both tracks map to column 1)

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

#### Scenario: Parcels derived from the 案名 when the 地號 cell is malformed
- **WHEN** a 地號 cell cannot supply a parcel list (e.g. "…1251筆土地" missing 地號) but the 案名 identifies the parcel (e.g. "…125地號1筆土地…")
- **THEN** the parcel set is populated from the 案名
- **AND** the malformed source cell is still flagged in review_flags

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

### Requirement: Per-track stage derivation for combined-track nodes

A node whose 事業種類 is 事業計畫、權利變換 (combined track) and whose 案名 carries two stage ordinals — `[stage1]…事業計畫及[stage2]權利變換計畫案` — SHALL derive **per-track stages**: `stage_事業計畫 = stage1`, `stage_權利變換 = stage2` (e.g. 中正區-臨沂段一小段-507 recno 1: 案名 `變更臺北市…事業計畫及變更(第二次)權利變換計畫案` → 事業計畫 at 變更, 權利變換 at 變更(第二次)). Uniform-ordinal 案名 (`…事業計畫及權利變換計畫案` with one shared ordinal, or identical ordinals) keep the single derived stage for both tracks. The single `stage` field remains unchanged for compatibility; the per-track stages are additive fields.

#### Scenario: Split-stage combined node derives both stages
- **WHEN** a combined-track node's 案名 is `變更臺北市中正區臨沂段一小段507地號等3筆土地都市更新事業計畫及變更(第二次)權利變換計畫案`
- **THEN** the record derives `stage_事業計畫 = 變更` and `stage_權利變換 = 變更(第二次)`

#### Scenario: Uniform-ordinal combined node keeps the shared stage
- **WHEN** a combined-track node's 案名 is `變更(第四次)…事業計畫及權利變換計畫案` (one ordinal covering both)
- **THEN** both per-track stages equal the single ordinal

#### Scenario: The single stage field is unchanged
- **WHEN** the per-track derivation runs
- **THEN** `stage` remains the 案名-prefix stage (existing clustering, table, and graph placement are unaffected)

