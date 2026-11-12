## MODIFIED Requirements

### Requirement: Filter the project list by construction stage

The left-list filter bar SHALL include a plan-and-execution dimension (labelled 計畫與執行， replacing 施工階段) with the fixed options 建照 / 開工 / 使照 / 已失效 / 自行撤回 / 已駁回 / 事業概要 / 事業計畫 / 事業計畫、權利變換 / 權利變換. Every project matches AT MOST ONE option (board D4d, user decision 2026-11-05), decided in this order: a project with construction dates matches only its 建照/開工/使照 stage (the same `constructionStage` derivation the list badge uses, so filter and badge never disagree); otherwise a project whose current recno node's case carries a dead-end schedule matches only that state (the same definition as the list's dead-end badge — 已失效 / 自行撤回 / 已駁回 / 已撤銷, the revoked state added 2026-11-10); otherwise it matches only its current node's exact track — 事業計畫、權利變換 matches only its own option, never 事業計畫 or 權利變換. Selecting one or more options SHALL restrict the list to projects whose single state is among them. The dimension SHALL combine with the existing 地區/年度/事業種類 dimensions under the same multi-select semantics.

#### Scenario: 使照 filter selects completed projects
- **WHEN** the user selects only 使照
- **THEN** the list shows exactly the projects whose latest construction event is 使照核發日期 (including national-fallback values), and the count line reflects the restriction

#### Scenario: Combines with other dimensions
- **WHEN** 使照 and 大安區 are both selected
- **THEN** the list shows only 大安區 projects whose state is 使照

#### Scenario: A construction project matches no 計畫 option
- **WHEN** a project has any of 建照/開工/使照 and its current node's track is 事業計畫
- **THEN** the project matches 開工 (say) and matches none of 事業概要/事業計畫/事業計畫、權利變換/權利變換

#### Scenario: A dead-end project matches no 計畫 option
- **WHEN** a project has no construction date and its current node's case is 已失效 (龍泉段一小段-534)
- **THEN** the project matches 已失效 only

#### Scenario: Combined track matches only its own option
- **WHEN** a project's current node's track is 事業計畫、權利變換 and the project has no construction date and no dead-end current case
- **THEN** the project matches only 事業計畫、權利變換 (not 事業計畫, not 權利變換)

#### Scenario: Projects without construction dates
- **WHEN** any option is selected
- **THEN** projects carrying none of the ten states are excluded from the list

#### Scenario: Filter and badge agree
- **WHEN** a project passes the 使照 filter
- **THEN** its list item badge shows 使照 (same derivation, no divergence)

#### Scenario: A revoked project matches 已撤銷

- **WHEN** a project has no construction date and its current node's case
  derives 已撤銷 (the header reads 業經本府撤銷核准)
- **THEN** the project matches 已撤銷 only
