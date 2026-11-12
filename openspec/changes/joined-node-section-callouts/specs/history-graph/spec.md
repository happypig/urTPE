## MODIFIED Requirements

### Requirement: Render per-record implementation callouts

The viewer SHALL render implementation callouts — compact dialogs tail-
attached to their carrying record's node — for a subset of carrying records:
the chronologically FIRST carrying record, and any later carrying record
whose values differ from the nearest earlier carrying record's. Carrying
records whose values are identical to the previous carrier SHALL render no
callout (e.g. 永昌段四小段366-3's three identical 權利變換/1041.0/12.0
records render one callout, on the first). Each callout lists 實施方式，
基地面積， 原戶數， and 土地使用分區 (populated fields only, official Chinese
labels). The 使用分區 row SHALL join the non-empty
Landkind1/2/3 values with `/` after abbreviating each zone: 第N種X區 renders
as the zone abbreviation plus numeral (第三種住宅區 → 住三， 第三種商業區 →
商三)， 第N之一種X區 keeps the sub-numeral (第三之一種住宅區 → 住三之一)，
already-abbreviated forms are kept without their parentheticals (商三特
(原屬第三種住宅區) → 商三特)， X區(特) renders 住特-style, 第N種特定X區
prefixes 特 (第三種特定商業區 → 特商三)， and X用地 drops the 用地 suffix
(道路用地 → 道路)； unknown forms render verbatim. Values that differ from
the nearest earlier carrying record's callout SHALL be highlighted in red.
Every callout SHALL render fully inside the graph viewport — no part clipped
or covered: the placement collision set excludes the callout's own record,
candidate rects are clamped into the viewBox (extending it when needed), and
no callout rect may intersect another record's or label's rect. Records
without an implementation snapshot SHALL render no callout.

A joined node — one anchoring 2+ city cases that each carry an implementation
payload — SHALL render one callout box **per section** (joined-node-section-
callouts, user decision 2026-11-12: 在負載中按案例發出)： the payload's
`implementation_by_case` carries the per-case snapshots keyed by case id,
the box header names the case's area suffix (`[A區]` — parsed from the case
name), and the diff marker compares within a section across nodes, never
across sections. A callout row SHALL render on ONE line whatever the value's
length: the box width follows the widest row's content, the graph's gutter
takes the widest box (the former 160 px clamp is retired, along with the
wrap-height model built to predict wrapping that no longer happens), and the
SVG width grows with the gutter (the centering rule already handles
`svgW > W`). Measured 2026-11-13 on the 675-project payload: 1,426 callouts,
739 of which wrapped under the old cap; the widest value needs ~302 px.

#### Scenario: First carrying record renders the baseline callout
- **WHEN** the earliest carrying record's snapshot carries 實施方式 = 權利變換，
  基地面積 = 3,056, 原戶數 = 98
- **THEN** a tail-attached callout on that record's node lists those rows

#### Scenario: Identical successors stay silent
- **WHEN** later carrying records report values identical to the previous
  carrier (永昌段四小段366-3: recnos 584 and 246 repeat 761's
  權利變換/1041.0/12.0)
- **THEN** only recno 761 renders a callout; recnos 584 and 246 render none

#### Scenario: 使用分區 row abbreviates and joins
- **WHEN** the snapshot carries Landkind1 = 第三種住宅區 and
  Landkind2 = 第三之一種住宅區 (Landkind3 empty)
- **THEN** the callout's 4th row shows `住三/住三之一`

#### Scenario: Diff-triggered record renders with red values
- **WHEN** a later carrying record reports 實施方式 = 事業計畫及權利變換計畫
  where the previous carrier showed 權利變換 (永昌段四小段366-3 recno 8)
- **THEN** that record renders a callout with the changed value in red

#### Scenario: Callout fully visible at any graph position
- **WHEN** a callout is placed near a record at any graph position
  (including the top row and leftmost column)
- **THEN** the entire callout rect lies inside the viewBox, intersects no
  other record's or label's rect, and its tail reaches the carrying node

#### Scenario: Records without implementation
- **WHEN** no record carries an implementation snapshot
- **THEN** no callout renders and the graph layout is otherwise unchanged

#### Scenario: A joined node renders one box per section
- **WHEN** a node anchors -A區 and -B區 cases whose payloads both exist
  (敦化363-1 node 537: -A 使照 2025/04/29, -B 2025/05/06)
- **THEN** the node renders two callout boxes, one per case, each headed
  with the case's area suffix
- **AND** the diff marker compares within a section across nodes, not across
  sections

#### Scenario: A callout row never wraps
- **WHEN** a callout value is wider than the old 160 px cap (the widest
  corpus value needs ~302 px)
- **THEN** the box grows to the value's natural width and the row renders on
  one line
- **AND** the graph's gutter and SVG width grow with the box
