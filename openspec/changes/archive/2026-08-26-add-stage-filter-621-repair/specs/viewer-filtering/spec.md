# viewer-filtering — Delta: construction stage filter

## ADDED Requirements

### Requirement: Filter the project list by construction stage

The left-list filter bar SHALL include a construction-stage dimension
(labelled 施工階段， positioned next to 事業種類) with the fixed options
建照 / 開工 / 使照. A project's stage SHALL derive from the same
`constructionStage` derivation the list badge uses — the latest of
建照核發日期 / 開工日期 / 使照核發日期 (使照 falling back to the national
使用核發日期) — so the filter and the badge never disagree. Selecting one or
more stages SHALL restrict the list to projects whose stage is among them;
projects without any construction stage SHALL be excluded while the
dimension is active. The dimension SHALL combine with the existing
地區/年度/事業種類 dimensions under the same multi-select semantics.

#### Scenario: 使照 filter selects completed projects
- **WHEN** the user selects only 使照
- **THEN** the list shows exactly the projects whose latest construction
  event is 使照核發日期 (including national-fallback values), and the count
  line reflects the restriction

#### Scenario: Combines with other dimensions
- **WHEN** 使照 and 大安區 are both selected
- **THEN** the list shows only 大安區 projects whose stage is 使照

#### Scenario: Projects without construction dates
- **WHEN** any stage is selected
- **THEN** projects carrying none of the three construction dates are
  excluded from the list

#### Scenario: Filter and badge agree
- **WHEN** a project passes the 使照 filter
- **THEN** its list item badge shows 使照 (same derivation, no divergence)
