# viewer-graph-layout Delta

## ADDED Requirements

### Requirement: The version graph interleaves approvals and execution events chronologically, ascending top-to-bottom

The version graph SHALL draw its timeline top-to-bottom in ascending date order:
the oldest row at the top, the newest at the bottom. Execution events
(建照核發日期 / 開工日期 / 使照核發日期) SHALL sit between the approval nodes
they chronologically follow — an execution date between two approval dates SHALL
render between those two approvals' rows. All ordering comparisons SHALL run on
normalised ISO dates: execution dates arriving in slash form (`2023/04/27`) or
ROC dot form (`110.10.25`) SHALL be normalised to ISO before the interleave, and
the displayed text SHALL keep its conventional rendering. The stored payload
SHALL stay verbatim.

#### Scenario: An execution date between two approvals renders between them

- **WHEN** a project's approvals are dated 2022-08-02 and 2026-10-15, and its
  建照核發日期 is 2023-04-27
- **THEN** the 建照 row renders between the 2022-08-02 and 2026-10-15 approval
  rows
- **AND** the vertical order top-to-bottom is 2022-08-02, 2023-04-27, 2026-10-15

#### Scenario: Two execution dates order by their own chronology

- **WHEN** a project has 建照核發日期 2023-04-27 and 開工日期 2023-07-03
- **THEN** the 建照 row renders above the 開工 row

#### Scenario: The timeline ascends top-to-bottom

- **WHEN** a project's approvals span 2022-08-02 to 2026-10-15
- **THEN** the 2022-08-02 approval row is the topmost approval row and the
  2026-10-15 approval row is the bottommost

#### Scenario: Execution dates normalise before ordering

- **WHEN** an execution date arrives as `2023/04/27` and an approval date is the
  ISO `2023-03-21`
- **THEN** the ordering comparison treats 2023-04-27 as the later date
- **AND** the comparison is not defeated by the `/` vs `-` byte difference

#### Scenario: The displayed execution date keeps its conventional form

- **WHEN** an execution event's payload date is `2023/04/27`
- **THEN** the row displays the date in the viewer's established rendering
- **AND** the payload field is unchanged
