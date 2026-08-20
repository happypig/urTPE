## MODIFIED Requirements

### Requirement: Emit a valid history graph

The system SHALL emit projects.json containing one graph per project family: nodes for each record (編號, ISO date, stage, track, 區段, is_current, links) and edges for revision progressions and section branches, with edges converging on the anchor. Each project SHALL carry a `links` object with its discovered official web URLs (national portal view URL and Taipei City platform case URLs), empty when discovery resolved none.

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

#### Scenario: Project carries discovered links
- **WHEN** a project's official links have been resolved by discovery
- **THEN** the project's `links` object contains its national-portal URL and any city-platform case URLs
- **AND** a project with no resolved link carries an empty `links` object