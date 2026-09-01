# viewer-filtering Specification

## Purpose

Lets an analyst narrow the project list to the districts, approval years, and plan types they care about, and keeps the project-history graph legible at any panel width.
## Requirements
### Requirement: Filter the project list by district, year, and plan type

The system SHALL provide multi-select filters above the project list for 地區 (12 districts), 年度 (approval years), and 事業種類 (`事業計畫`, `權利變換`, `事業計畫、權利變換`, `事業概要`, `都市更新計畫`, `其他`), combined with the existing search box.

#### Scenario: Selecting districts narrows the list
- **WHEN** the user checks 中山區 and 大安區 in the 地區 filter
- **THEN** the list shows only projects whose district is 中山區 or 大安區
- **AND** the live count label updates to the number of matching projects

#### Scenario: Filters combine with AND across dimensions
- **WHEN** the user checks 地區=大安區, 年度=2023, and 事業種類=事業計畫
- **THEN** the list shows only projects matching all three active filters at once

#### Scenario: Year and plan type use any-member semantics
- **WHEN** a project family spans approvals in 2019, 2021, and 2025 (擬訂, 變更, 變更(第二次))
- **THEN** the project appears when 年度 includes any of 2019/2021/2025
- **AND** it appears when 事業種類 includes any track present among its members

#### Scenario: District is a single value per project
- **WHEN** a project's district is 南港區
- **THEN** the 地區 filter selects it only when 南港區 is checked, regardless of member counts

#### Scenario: An unchecked filter is inactive
- **WHEN** the 年度 filter has no value checked
- **THEN** it does not restrict the list, and only the other active filters apply

#### Scenario: Search combines with the selectors
- **WHEN** the user types a search term while selectors are active
- **THEN** the list shows only projects matching the active selectors AND the search term

#### Scenario: Result count and empty state
- **WHEN** a filter combination matches 42 projects
- **THEN** the viewer shows "顯示 42 / 718"
- **AND** when no project matches, it shows an empty state instead of a blank list

### Requirement: Filter the project list by construction stage

The left-list filter bar SHALL include a construction-stage dimension (labelled 施工階段， positioned next to 事業種類) with the fixed options 建照 / 開工 / 使照. A project's stage SHALL derive from the same `constructionStage` derivation the list badge uses — the latest of 建照核發日期 / 開工日期 / 使照核發日期 (使照 falling back to the national 使用核發日期) — so the filter and the badge never disagree. Selecting one or more stages SHALL restrict the list to projects whose stage is among them; projects without any construction stage SHALL be excluded while the dimension is active. The dimension SHALL combine with the existing 地區/年度/事業種類 dimensions under the same multi-select semantics.

#### Scenario: 使照 filter selects completed projects
- **WHEN** the user selects only 使照
- **THEN** the list shows exactly the projects whose latest construction event is 使照核發日期 (including national-fallback values), and the count line reflects the restriction

#### Scenario: Combines with other dimensions
- **WHEN** 使照 and 大安區 are both selected
- **THEN** the list shows only 大安區 projects whose stage is 使照

#### Scenario: Projects without construction dates
- **WHEN** any stage is selected
- **THEN** projects carrying none of the three construction dates are excluded from the list

#### Scenario: Filter and badge agree
- **WHEN** a project passes the 使照 filter
- **THEN** its list item badge shows 使照 (same derivation, no divergence)

### Requirement: Surface the district dimension in the detail header

The system SHALL echo the project's district chip in the detail header so the list and detail stay visually connected.

#### Scenario: Detail header shows the district chip
- **WHEN** a project's detail is rendered
- **THEN** the header shows the same district color chip as its list item

### Requirement: Detail table shows full original row data with expand toggle

The system SHALL render the record table under the graph with all original CleanRecord fields (案名, 地號, 區段, 實施者, 更新規劃單位, review_flags, auto_fixes) as additional columns after 現況, defaulting to analyst essentials with an "展開全部" toggle for the full set.

#### Scenario: Default table shows analyst essentials
- **WHEN** a project detail is rendered
- **THEN** the table shows 編號, 核定日期, 階段, 事業種類, 現況, 案名, 地號, 區段, 實施者, 更新規劃單位, review_flags/auto_fixes
- **AND** an "展開全部" button is visible

#### Scenario: Expand toggle reveals all fields
- **WHEN** the user clicks "展開全部"
- **THEN** the table shows all available original row fields including parcels, aliases, land_count, orig_count, named_anchor, area_section

#### Scenario: Mobile table scrolls horizontally
- **WHEN** the viewport is narrow and the table has many columns
- **THEN** the table container shows a horizontal scrollbar
- **AND** the user can scroll to see all columns without page-level horizontal scroll

### Requirement: 基本面積 displays with conditional color and style based on value thresholds

The left-list project card SHALL render the 基本面積 value with conditional color and font weight based on its numeric value (in square meters, parsed from `p.implementation.Base_Area`):

- **< 500 m²**: purple color (`#8b5cf6`), normal font weight
- **≥ 500 and < 1,000 m²**: default label text color (inherit), normal font weight
- **≥ 1,000 and < 2,000 m²**: orange color (`#f59e0b`), normal font weight
- **≥ 2,000 and < 3,000 m²**: orange color (`#f59e0b`), bold font weight
- **≥ 3,000 m²**: red color (`#ef4444`), bold font weight

The style SHALL apply only to the 基本面積 numeric value and its unit label, not to the 實施者 name or the "基本面積" prefix.

#### Scenario: Small project (<500 m²) shows purple
- **WHEN** a project has `implementation.Base_Area = "350"`
- **THEN** the left-list card renders "基本面積 350" in purple (`#8b5cf6`), normal weight

#### Scenario: Medium-small project (500–999 m²) shows default style
- **WHEN** a project has `implementation.Base_Area = "750"`
- **THEN** the left-list card renders "基本面積 750" with default label color, normal weight

#### Scenario: Medium project (1,000–1,999 m²) shows orange (not bold)
- **WHEN** a project has `implementation.Base_Area = "1500"`
- **THEN** the left-list card renders "基本面積 1500" in orange (`#f59e0b`), normal weight

#### Scenario: Large project (2,000–2,999 m²) shows orange bold
- **WHEN** a project has `implementation.Base_Area = "2425"`
- **THEN** the left-list card renders "基本面積 2425" in orange (`#f59e0b`), bold

#### Scenario: Very large project (≥3,000 m²) shows red bold
- **WHEN** a project has `implementation.Base_Area = "5751"`
- **THEN** the left-list card renders "基本面積 5751" in red (`#ef4444`), bold

#### Scenario: Missing or invalid Base_Area shows no style
- **WHEN** a project has no `implementation` or `Base_Area` is empty/non-numeric
- **THEN** the left-list card shows only 實施者 without 基本面積 (no style applied)

