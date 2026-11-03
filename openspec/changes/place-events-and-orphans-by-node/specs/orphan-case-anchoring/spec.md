# orphan-case-anchoring spec delta — place-events-and-orphans-by-node (wave 5)

## MODIFIED Requirement: Viewer renders orphan ghost node with dotted construction-chain edges

The viewer SHALL render ghost/orphan nodes in the history graph with an "orphan" badge. Each orphan SHALL take its own timeline row ordered by date with the recno nodes. A named orphan sitting between 2 consecutive recno nodes in the same swimlane SHALL shift 32px right of that swimlane's track line. Each orphan SHALL connect with a dotted edge (class `edge orphan`) to the nearest recno node directly above it (latest date ≤ orphan date), or directly under it (earliest date ≥ orphan date) when the orphan is earlier than every recno node in its swimlane.

#### Scenario: Orphan ghost node appears in graph by date with badge

- **WHEN** a project has a ghost node for case_id 09907221
- **THEN** the graph shows a node with an "orphan" badge at its date row among the recno nodes

#### Scenario: Orphan dotted edge to nearest recno node directly above

- **WHEN** an orphan dated 2023-05 renders in a swimlane whose recno nodes are dated 2023-03 and 2023-08
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2023-03 recno node directly above it

#### Scenario: Orphan dotted edge to recno node directly under when earliest

- **WHEN** an orphan dated 2020-01 renders earlier than every recno node in its swimlane (earliest recno dated 2022-01)
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2022-01 recno node directly under it

#### Scenario: Orphan shifts 32px right only when between 2 recnos in same swimlane

- **WHEN** a named orphan dated between two recno nodes occupies the same track column
- **THEN** its node renders 32px right of that column's track line

#### Scenario: Orphan not shifted when outside the swimlane date span

- **WHEN** a named orphan is earlier than every recno node in its swimlane
- **THEN** its node renders on its swimlane's track line (no 32px right shift)

The right-most ghost column for nameless anchors is removed; nameless anchors with no date render no row (§4 decision 4 — current corpus has none with a date; the 3 nameless anchors are §8 defects removed by wave 3b).
