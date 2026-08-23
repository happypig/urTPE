# viewer-milestone-timeline Specification

## Purpose
Renders official procedural milestone timelines from the national portal (推動歷程) and Taipei platform (階段辦理過程) as expandable timeline cards in the viewer detail pane, with per-node attribution and progressive loading states.
## Requirements
### Requirement: Display national portal 推動歷程 as timeline

The system SHALL render the national portal's 推動歷程 milestones (事業計畫申請/核定日期, 權利變換計畫申請/核定日期, 概要申請/核定日期) as a timeline card in the detail pane when `links.milestones_national` is present on the project.

#### Scenario: National milestones render as timeline
- **WHEN** a project has `links.milestones_national` with one or more entries
- **THEN** a card titled "推動歷程 (國土署)" appears in the detail pane
- **AND** each milestone shows as a row: label (e.g., "事業計畫申請日期") and date value
- **AND** the card is collapsible/expandable with a toggle button

#### Scenario: Empty national milestones show nothing
- **WHEN** `links.milestones_national` is empty or absent
- **THEN** no "推動歷程" card is rendered

### Requirement: Display Taipei platform 階段辦理過程 as timeline

The system SHALL render the Taipei platform's 階段辦理過程 milestones as a timeline card when `links.milestones_taipei` is present on the project.

#### Scenario: Taipei milestones render as timeline
- **WHEN** a project has `links.milestones_taipei` with one or more entries
- **THEN** a card titled "階段辦理過程 (台北市)" appears in the detail pane
- **AND** each milestone shows as a row: label (e.g., "計畫公聽會日期", "申請計畫日期", "公告公展日期", "召開審議會日期", "核定日期", "建照核發日期") and date value
- **AND** the card is collapsible/expandable with a toggle button

#### Scenario: Empty Taipei milestones show nothing
- **WHEN** `links.milestones_taipei` is empty or absent
- **THEN** no "階段辦理過程" card is rendered

### Requirement: Per-node milestone attribution

The system SHALL display per-node milestone badges in the history graph nodes and/or table rows, indicating which milestones belong to that approval stage.

#### Scenario: Node shows relevant milestone badge
- **WHEN** a node has `links.milestones_national` or `links.milestones_taipei` populated
- **THEN** the node shows a badge indicating the milestone source (e.g., "國", "北")
- **AND** hovering or clicking reveals the specific milestones for that node

#### Scenario: Different nodes show different milestones
- **WHEN** a project has both 事業計畫 and 權利變換 nodes with different case_ids
- **THEN** the 事業計畫 node shows its milestones, the 權利變換 node shows its own

### Requirement: Progressive loading states

The system SHALL show loading indicators when milestone data is available from one portal but not the other.

#### Scenario: National data available, Taipei data pending
- **WHEN** `links.milestones_national` is populated but `links.milestones_taipei` is empty
- **THEN** "推動歷程" card renders normally
- **AND** "階段辦理過程" card shows a "載入中..." or "資料未取得" placeholder with the Taipei portal link

#### Scenario: Both portals have data
- **WHEN** both `links.milestones_national` and `links.milestones_taipei` are populated
- **THEN** both cards render fully with no loading indicators

