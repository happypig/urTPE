## ADDED Requirements

### Requirement: Embed milestone timelines inline

The system SHALL embed the 推動歷程 and 階段辦理過程 milestone timelines as expandable cards within the 相關連結 section (or as a sibling section above it), rather than only showing outbound links.

#### Scenario: Milestone cards appear above links
- **WHEN** the project has `links.milestones_national` or `links.milestones_taipei`
- **THEN** timeline cards render above the outbound link list
- **AND** each card has an expand/collapse toggle
- **AND** loading placeholders show when data is absent

## MODIFIED Requirements

### Requirement: Render a 相關連結 section in the detail pane

The system SHALL render a 相關連結 section in the detail pane, below the record table and milestone timelines, listing the project's national-portal link and each city-platform case link as clickable outbound anchors with a stable label.

#### Scenario: Project with both link types
- **WHEN** the selected project has both a national-portal URL and one or more city case URLs
- **THEN** the detail pane shows a 相關連結 section with all links, each opening in a new tab
- **AND** the section appears below the milestone timeline cards

#### Scenario: Project with no resolved links
- **WHEN** the selected project has an empty `links` object
- **THEN** the detail pane renders no 相關連結 section at all

#### Scenario: Multi-case projects list every case
- **WHEN** a project has two city case_ids (事業計畫 and 權利變換)
- **THEN** both city links are listed, not just the first