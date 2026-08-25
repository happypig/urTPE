# history-graph — Delta: construction-phase annotations

## ADDED Requirements

### Requirement: Render the construction-phase chain beside the anchor record

The viewer SHALL render a project's construction-phase dates — 建照核發日期,
開工日期, 使照核發日期 — as dated event nodes inside the history graph's
timeline: each event occupies its own date-ordered row in a dedicated
E) 執行階段 column (rightmost), so the graph reads chronologically. Each event
SHALL connect by a thin attribution edge to the approval record it belongs
under — the latest approval whose 核定日期 is on or before the event date
(the plan in force when the event occurred) — and consecutive 開工/使照
events SHALL be joined by a solid connector. The events SHALL draw from the
already-emitted milestone fields (`links.milestones_taipei` /
`links.milestones_national`) without any emission-format change, and SHALL
render only the slots whose date value exists. A 使照 event corroborated by
the national portal (使用核發日期 in `links.milestones_national`) SHALL carry
a small 國 badge. When the carrying case is provable — the emitted
`implementation.case_id` whose payload dates exactly equal the slot value —
the 開工 and 使照 events SHALL display that case's provenance (case_id and,
when it anchors via the per-node linkage, the owning record's 編號). Slots
without provable provenance (建照核發日期 comes from the merged stage
timeline) carry no case label.

Event colour encodes the source portal: Taipei-sourced events render pink
(label and attribution edge) with the label hyperlinked to the carrying
case's detail page; a 使照 event corroborated by the national portal renders
green with its label hyperlinked to the national view page. The 開工→使照
connector takes the 使照 event's source colour.

#### Scenario: Full chain renders in the timeline
- **WHEN** a project's milestones contain 建照核發日期, 開工日期, and 使照核發日期
- **THEN** three dated event nodes appear in the E) 執行階段 column at their
  chronological positions, each joined by a thin attribution edge to the latest
  approval dated on or before the event, and 開工/使照 joined to each other by
  a solid connector

#### Scenario: Event attributed to the plan in force
- **WHEN** 建照核發日期 2017-07-14 falls after approval 2016-07-05 but before
  approval 2019-08-01 (e.g. 河堤段四小段263-19)
- **THEN** the 建照 event's attribution edge points at the 2016-07-05 approval,
  while 使照核發日期 2021-10-25 attributes to the 2019-08-01 approval

#### Scenario: Partial chain renders only existing events
- **WHEN** only 開工日期 and 使照核發日期 exist (no 建照核發日期)
- **THEN** exactly those two event nodes render in the E) 執行階段 column,
  each attributed to its plan-in-force approval, with no empty placeholder nodes

#### Scenario: National-mapped event shows the 國 badge
- **WHEN** the 使照 slot is filled from the national portal (使用核發日期 present in
  `links.milestones_national`)
- **THEN** that chain node displays a small 國 badge indicating national provenance

#### Scenario: Carrying case shown on implementation dates
- **WHEN** the 開工/使照 values equal the emitted `implementation` payload's dates
  (provenance case_id available, e.g. 大安區仁愛段四小段114地號: construction
  data lives on sibling case 08610011 while the 現況 record anchors case 08610013)
- **THEN** those chain nodes display the carrying case_id as provenance

#### Scenario: Provenance names the owning record when anchored
- **WHEN** the carrying case anchors to a record via the per-node case linkage
- **THEN** the provenance also shows that record's 編號
  (e.g. `案08610011 · 編號1419`), telling the reader which approval's
  implementation produced the dates

#### Scenario: Unanchored carrying case keeps id-only provenance
- **WHEN** the carrying case_id anchors to no record
- **THEN** the provenance shows the bare case_id without a 編號 suffix

#### Scenario: Unprovable provenance stays unlabeled
- **WHEN** a slot value cannot be exactly matched to the `implementation`
  payload (e.g. 建照核發日期 from the merged stage timeline)
- **THEN** that node shows no case label rather than a guessed one

#### Scenario: Taipei-sourced events show no national badge
- **WHEN** all chain values come from `links.milestones_taipei` and the national
  milestones carry no matching 使用核發日期
- **THEN** no chain node displays the 國 badge

#### Scenario: Project with no construction events
- **WHEN** none of the three dates exists for the project
- **THEN** no event nodes or attribution edges render, leaving the graph unchanged

#### Scenario: Annotations never cover existing graph elements
- **WHEN** a project renders events or callouts (any record count or column layout)
- **THEN** no event node, attribution edge, callout, or tail intersects any
  approval node or its labels — callouts are placed at the first of six
  candidate spots around their record that overlaps nothing

### Requirement: Render per-record implementation callouts

For each approval record whose snapshot carries implementation data, the
viewer SHALL render a callout dialog tail-attached to that record's node,
listing 實施方式, 基地面積, and 原戶數 (populated fields only, official Chinese
labels). Values that differ from the nearest earlier carrying record's
callout SHALL be highlighted in red, so plan-revision drift (e.g. 基地面積
3,056 → 4,003) is visible at a glance. Records without an implementation
snapshot SHALL render no callout.

#### Scenario: Callout attaches to its owning record
- **WHEN** a record's snapshot carries 實施方式 = 權利變換, 基地面積 = 3,056,
  原戶數 = 98
- **THEN** a tail-attached callout on that record's node lists those rows

#### Scenario: Changed values highlight against the earlier record
- **WHEN** a later carrying record reports 基地面積 = 4,003 and 原戶數 = 115
  where the earlier carrying record showed 3,056 / 98
- **THEN** the later callout shows 4,003 and 115 in red; unchanged values
  (實施方式 = 權利變換) stay neutral

#### Scenario: Records without implementation
- **WHEN** no record carries an implementation snapshot
- **THEN** no callout renders and the graph layout is otherwise unchanged
