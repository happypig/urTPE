## Purpose

Codify the project graph's spatial model: which column each element occupies, how much vertical space rows take, and how the graph is viewed (centered, pinch-zoomable, drag-pannable) on desktop and touch, with a responsive split that favors the detail section on narrow screens.

## ADDED Requirements

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
