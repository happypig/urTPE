## MODIFIED Requirements

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
