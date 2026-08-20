## MODIFIED Requirements

### Requirement: Render the history in a browser viewer

The system SHALL provide a viewer that loads projects.json and renders each project's history, highlighting the current (anchor) approval and distinguishing tracks and sections visually.

#### Scenario: Viewer shows a project timeline
- **WHEN** a user selects a project in the viewer
- **THEN** the timeline renders all its approvals ordered by date, with the anchor highlighted and 事業計畫 / 權利變換 tracks visually distinct
- **AND** 區段 annotations are visible on the relevant nodes

#### Scenario: Viewer handles the full dataset
- **WHEN** the viewer loads projects.json for all 1,419 records
- **THEN** it renders without error and supports browsing and searching across all project families

#### Scenario: Graph scales uniformly at any panel width
- **WHEN** the detail panel is narrower than the graph's authored coordinate space
- **THEN** node positions and label text scale uniformly (no horizontal-only squish), keeping labels legible

#### Scenario: Labels remain readable over edges
- **WHEN** a track or section edge passes behind a node label
- **THEN** the label text remains readable against the line

#### Scenario: Graph height follows the node count
- **WHEN** a project has few records
- **THEN** the graph box is sized to its nodes instead of reserving a large fixed height

#### Scenario: District is surfaced on list items
- **WHEN** the list renders project items
- **THEN** each item carries a district color chip alongside the project id