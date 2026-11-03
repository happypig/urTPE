# viewer-graph-layout Specification

## Purpose
Codify the project graph's spatial model: which column each element occupies, how much vertical space rows take, and how the graph is viewed (centered, pinch-zoomable, drag-pannable) on desktop and touch, with a responsive split that favors the detail section on narrow screens.
## Requirements
### Requirement: Content-addressed row pitch

The vertical gap between timeline rows SHALL depend on row content: consecutive node rows (PDF milestones or virtual/orphan nodes) SHALL be separated by the normal height (64px); rows involving execution dates (建照/開工/使照) SHALL use half height (32px).

#### Scenario: Consecutive nodes keep normal height
- **WHEN** two approval milestones (or a milestone and a virtual node) are adjacent in the timeline
- **THEN** the space between them is the normal 64px row height

#### Scenario: Execution-date rows use half height
- **WHEN** a timeline row contains an execution date event
- **THEN** the space around that row is the half height (32px)

#### Scenario: Execution date starts ½ row under nearest approval above it

- **WHEN** a project's timeline has an approval node and 建照核發日期 follows it
- **THEN** the 建照 row starts 32px (½ node row) under the approval node directly above it

#### Scenario: Event-to-event pitch stays 32px

- **WHEN** a project has 建照核發日期 2023-04-27 and 開工日期 2023-07-03 consecutive
- **THEN** the 開工 row starts 32px under the 建照 row

#### Scenario: Event→approval keeps full clearance

- **WHEN** an execution date row is immediately followed by an approval row
- **THEN** the space between them is the normal 64px row height

### Requirement: Four-column grid arrangement

The graph SHALL arrange elements in four fixed columns: (1) 事業概要 / 事業計畫 / 都市計畫; (2) combined plan×權利變換 tracks (事業計畫、權利變換 and 都市計畫、權利變換); (3) 桃利變換 / 其他; (4) execution dates (建照/開工/使照). Virtual milestone nodes SHALL occupy columns 1–3 according to their own 事業種類.

#### Scenario: Execution dates always form the fourth column
- **WHEN** a project renders execution events
- **THEN** all execution events align in the fourth column, right of the track columns

### Requirement: Centered, pinch-zoomable graph viewport

The graph SHALL render inside a viewport that centers it horizontally, supports two-finger pinch to enlarge/shrink, and supports drag to pan. Desktop pointers SHALL receive equivalent behavior (drag-pan, ctrl/wheel zoom).

#### Scenario: Graph centers horizontally
- **WHEN** the graph is narrower than its viewport
- **THEN** it renders centered in the horizontal middle

#### Scenario: Two-finger pinch zooms
- **WHEN** the user pinch-zooms on the graph
- **THEN** the graph scales around the pinch point within min/max bounds

### Requirement: Responsive list/detail balance

On narrow viewports the project list SHALL cap its visible height (fewer items, scrollable) so the detail section below/beside keeps the majority of the viewport.

#### Scenario: Narrow viewport favors the detail section
- **WHEN** the viewport is narrower than the desktop breakpoint
- **THEN** the project list caps its height (scrollable) and the detail section occupies the remaining space

### Requirement: Callout placement keeps clearance from nodes and labels

Implementation callout boxes SHALL be placed in a reserved gutter column left of the leftmost track
column, one per callout row, in timeline order. Each box starts at its record's row and moves down only
when it would overlap the box above it; boxes never move up. A leader connects each box to its own node
circle. No callout box SHALL overlap any node label, badge strip, event row, other callout box, ghost
anchor, or stage-band chip; stage bands/count chips are not drawn (see the stage-bands removal below),
so nothing else occupies the gutter.

**Reason**: The previous dodging search (8 fixed spots around the node, canvas extension fallback) could
not protect the callout's own node, could clamp a candidate onto that node, underestimated CJK label width,
and never tested lines. Moving callouts out of the graph area removes all four gap classes at once.

#### Scenario: Callout lands inside the gutter

- **WHEN** a project has at least one implementation callout
- **THEN** the graph reserves a callout gutter left of the leftmost track column, and every callout box
  lies fully inside it

#### Scenario: Callouts stack without overlap

- **WHEN** two callouts would overlap in the gutter
- **THEN** the later callout moves down, keeping a small gap, never up; each box's leader still connects
  to its own node circle

#### Scenario: Long values wrap then cut

- **WHEN** a callout value is wider than the gutter box
- **THEN** it wraps to at most 2 lines, the rest is cut with an ellipsis, and the full value is available
  as a tooltip

#### Scenario: Every checkable layout pair is verified

- **WHEN** `scripts/viewer_smoke.js` lays out every project that has a callout
- **THEN** no two placed rectangles intersect, every callout box lies inside the gutter, and no leader
  segment crosses a callout box or a node label

#### Scenario: Callout dodges node labels and events
- **WHEN** a callout's candidate spots near its record would collide with node label boxes, execution events, or previously placed callouts
- **THEN** the placer does not dodge: no further candidate spots are tried and the canvas is never extended; the box stacks downward inside the reserved gutter (the dodging search is removed by this change)

#### Scenario: Node label boxes include their full visual footprint
- **WHEN** collision boxes are computed for placement
- **THEN** each node's box covers its label lines and the badge strip above it, and each event/ghost anchor contributes its own box

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

### Requirement: Stage bands and count chips removed from rendering

Stage clustering still groups nodes by 第N次 and tags undated members as (未核定), but clusters with ≥2
members SHALL NOT render a soft band or a count chip. Single-member groups render bare, as before.

**Reason**: The stage-band chip collides with the callout gutter column, and the band adds a second visual
layer behind the tracks.

#### Scenario: No stage band drawn

- **WHEN** a stage cluster has ≥2 members
- **THEN** no soft band rectangle and no count chip text render behind those members

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

