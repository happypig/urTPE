# orphan-case-anchoring spec delta — place-events-and-orphans-by-node (wave 5)

## MODIFIED Requirement: Viewer renders orphan ghost node with dotted construction-chain edges

The viewer SHALL render ghost/orphan nodes in the history graph with an "orphan" badge. Each orphan SHALL take its own timeline row ordered by date with the recno nodes. A named orphan in a track column SHALL shift 32px right of its track line. Each orphan SHALL connect to the nearest recno node in time with a dotted edge (class `edge orphan`).

#### Scenario: Orphan ghost node appears in graph by date with badge

- **WHEN** a project has a ghost node for case_id 09907221
- **THEN** the graph shows a node with an "orphan" badge at its date row among the recno nodes

#### Scenario: Orphan dotted edge to nearest recno node

- **WHEN** an orphan node renders
- **THEN** a dotted edge (class `edge orphan`) connects it to the nearest recno node directly above it, or directly under it when earlier than every recno node

#### Scenario: Orphan shifts 32px right of track line

- **WHEN** a named orphan occupies a track column
- **THEN** its node renders 32px right of that column's track line

The right-most ghost column for nameless anchors is removed; nameless anchors with no date render no row (§4 decision 4 — current corpus has none with a date; the 3 nameless anchors are §8 defects removed by wave 3b).
