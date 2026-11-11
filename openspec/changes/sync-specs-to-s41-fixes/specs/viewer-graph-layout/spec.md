## MODIFIED Requirements

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

Every row's interleave key SHALL be the key that ordered the approval rows
themselves: the member's own date, or, when the member carries none, the member's
own event key. The cluster's `effDate` SHALL NOT feed the interleave — it is a
cluster sort sentinel (including `"9999-12-31"` for undated-only clusters), not a
row key, so an undated approval row in a dated cluster SHALL inherit nothing from
its cluster's date.

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

#### Scenario: An undated approval row in a dated cluster interleaves by its own event key

- **WHEN** a project holds a dated cluster whose newest member is dated
  2026-09-29 and an undated approval row whose own event date is 2021-01-12
  (北投區-桃源段四小段424-8: the 變更 cluster anchors the undated recno 615,
  whose carrying case names 建照核發 2021/10/28 and 開工 2022/07/27)
- **THEN** the undated row interleaves at 2021-01-12, and its execution events
  render between it and the next later approval row
- **AND** the undated row does not inherit the cluster's 2026-09-29 date, so no
  execution event renders above the 2021 approval it follows
