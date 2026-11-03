## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Stage bands and count chips removed from rendering

Stage clustering still groups nodes by 第N次 and tags undated members as (未核定), but clusters with ≥2
members SHALL NOT render a soft band or a count chip. Single-member groups render bare, as before.

**Reason**: The stage-band chip collides with the callout gutter column, and the band adds a second visual
layer behind the tracks.

#### Scenario: No stage band drawn

- **WHEN** a stage cluster has ≥2 members
- **THEN** no soft band rectangle and no count chip text render behind those members
