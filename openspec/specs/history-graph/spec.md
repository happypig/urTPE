# history-graph Specification

## Purpose

Publishes the merged result as a per-project JSON history graph whose revision edges converge on each family's latest approval, and renders it in a browser viewer so an analyst can read one project's full approval timeline.

## Requirements

### Requirement: Emit a valid history graph

The system SHALL emit projects.json containing one graph per project family: nodes for each record (編號, ISO date, stage, track, 區段, is_current) and edges for revision progressions and section branches, with edges converging on the anchor.

#### Scenario: Every record has a node in exactly one project
- **WHEN** projects.json is generated
- **THEN** each record in merged.tsv maps to a node in exactly one project graph
- **AND** no node appears in two projects

#### Scenario: Revision edges point toward the anchor
- **WHEN** a family contains 擬訂 → 變更 → 變更(第二次) approvals ordered by date
- **THEN** edges connect each approval to the next-newer one, terminating at the is_current anchor
- **AND** 事業計畫 and 權利變換 approvals stay on distinguishable tracks

#### Scenario: Section branches are represented
- **WHEN** a family has A區段 and B區段 approvals
- **THEN** the graph records the section on each node and links the section branches to the shared timeline

#### Scenario: JSON is schema-valid
- **WHEN** projects.json is validated against its declared schema
- **THEN** it parses without error and every project contains non-empty nodes and a single anchor

### Requirement: Render the history in a browser viewer

The system SHALL provide a viewer that loads projects.json and renders each project's history, highlighting the current (anchor) approval and distinguishing tracks and sections visually.

#### Scenario: Viewer shows a project timeline
- **WHEN** a user selects a project in the viewer
- **THEN** the timeline renders all its approvals ordered by date, with the anchor highlighted and 事業計畫 / 權利變換 tracks visually distinct
- **AND** 區段 annotations are visible on the relevant nodes

#### Scenario: Viewer handles the full dataset
- **WHEN** the viewer loads projects.json for all 1,419 records
- **THEN** it renders without error and supports browsing and searching across all project families