## Purpose

Lets an analyst narrow the 718-project list to the districts, approval years, and plan types they care about, and keeps the project-history graph legible at any panel width.

## ADDED Requirements

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

### Requirement: Surface the district dimension in the detail header

The system SHALL echo the project's district chip in the detail header so the list and detail stay visually connected.

#### Scenario: Detail header shows the district chip
- **WHEN** a project's detail is rendered
- **THEN** the header shows the same district color chip as its list item