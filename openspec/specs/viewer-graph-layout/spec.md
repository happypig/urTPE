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

Implementation callout boxes SHALL be placed best-effort so they do not overlap node labels, badge strips, execution events, other callouts, or ghost anchors. Placement MAY temporarily extend the canvas (viewBox height/width) to guarantee a free spot rather than accepting an overlap; only when the canvas cannot grow reasonably MAY a callout sit close to other elements.

#### Scenario: Callout dodges node labels and events
- **WHEN** a callout's candidate spots near its record collide with node label boxes, execution events, or previously placed callouts
- **THEN** the placer tries further candidate spots (below/above, both sides) and extends the canvas if needed, so the callout lands in free space

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
