## ADDED Requirements

### Requirement: Execution dates start ½ node row under the nearest approval node

An execution event row (建照/開工/使照) that follows an approval row SHALL start ½ node row (32px) under the nearest approval node directly above it in any swimlane. Event-to-event pitch stays 32px. An event followed by an approval keeps the full 64px clearance so badge strips do not touch.

#### Scenario: First execution date sits 32px under the nearest approval above it

- **WHEN** a project's timeline has approval node 370 dated 2023-03-21 and 建照核發日期 2023-04-27 follows it
- **THEN** the 建照 row starts 32px under node 370, not 64px

#### Scenario: Event-to-event pitch stays 32px

- **WHEN** a project has 建照核發日期 2023-04-27 and 開工日期 2023-07-03 consecutive
- **THEN** the 開工 row starts 32px under the 建照 row

#### Scenario: Event→approval keeps full clearance

- **WHEN** an execution date row is immediately followed by an approval row
- **THEN** the space between them is the normal 64px row height

### Requirement: Orphan nodes take their own timeline row by date with a dotted edge

Every orphan node (named virtual node or nameless 孤 anchor with a date) SHALL take its own timeline row ordered by date with the recno nodes. A named orphan in a track column SHALL shift 32px right of its track line. Each orphan SHALL connect to the nearest recno node in time with a dotted edge (class `edge orphan`).

#### Scenario: Orphan row is in date order with recno nodes

- **WHEN** an orphan's date falls between two recno node dates
- **THEN** the orphan's row renders between those two nodes' rows

#### Scenario: Orphan dotted edge to nearest recno node

- **WHEN** an orphan node renders
- **THEN** a dotted edge (class `edge orphan`) connects it to the nearest recno node directly above it, or directly under it when earlier than every recno node

#### Scenario: Named orphan shifts 32px right of its track line

- **WHEN** a named orphan occupies a track column
- **THEN** its node renders 32px right of that column's track line, clearing the line
