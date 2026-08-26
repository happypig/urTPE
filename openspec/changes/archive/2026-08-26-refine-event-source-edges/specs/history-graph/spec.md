# history-graph — Delta: source-group edges, tooltips, callout zones

## MODIFIED Requirements

### Requirement: Render the construction-phase chain beside the anchor record

The viewer SHALL render a project's construction-phase dates — 建照核發日期,
開工日期, 使照核發日期 — as dated event nodes inside the history graph's
timeline: each event occupies its own date-ordered row in a dedicated
E) 執行階段 column (rightmost), so the graph reads chronologically.

Events SHALL group by provenance into maximal chronological runs sharing a
source — a Taipei carrying case (anchored to its record via the per-node
linkage or the emitted `milestones_source` map) or the national portal
(使照 filled solely from 使用核發日期). Edges SHALL follow the groups:

- a solid edge connects each Taipei group's owning record to the group's
  first event (pink), and the 現況 node to the first event of each
  national-only group (green);
- a solid chain joins consecutive events within the same group;
- a dashed edge joins chronologically adjacent groups, colored by the
  incoming group (pink dashed between two Taipei cases, green dashed when
  entering a national-only group);
- no edge SHALL connect an event to a record that is not its group's source.

The events SHALL draw from the already-emitted milestone fields
(`links.milestones_taipei`, `links.milestones_national`,
`links.milestones_source`, `implementation.case_id`) without any
emission-format change beyond the additive source map, and SHALL render only
the slots whose date value exists. A 使照 event corroborated by the national
portal (使用核發日期 in `links.milestones_national`) SHALL carry a small
國 badge and render a western date (民國 years converted, 115 → 2026). When
the carrying case is provable — exact match against the emitted
`implementation.case_id` payload or the `milestones_source` map — the events
SHALL display that case's provenance (案`<case_id>` and, when it anchors via
the per-node linkage, the owning record's 編號). Slots without provable
provenance carry no case label.

Event hyperlinks SHALL appear only when the event's carrying case anchors to
no record — the sole access point in that case. When the carrying case
anchors to a record, the record's 北 badge already opens the case page and
the event label SHALL be plain colored text. National-sourced events SHALL
not duplicate the twur link (the 現況 node's 國 badge covers it).

#### Scenario: Single-source family chains from its owning record
- **WHEN** all three dates come from case 10011041, which anchors to
  recno 1040 (e.g. 金華段四小段513-3)
- **THEN** one solid pink edge runs 1040 → 建照， and solid pink edges chain
  建照 → 開工 → 使照； recno 797 (case 10011042) receives no edge and the
  event labels are plain text without hyperlinks

#### Scenario: Event attributed to its provenance owner, not the plan in force
- **WHEN** 使照核發日期 2019-09-10 postdates the 變更 approval 2019-05-14
  (case 10011042) but its carrying case is 10011041 (recno 1040)
- **THEN** no edge connects the 使照 event to recno 797 — attribution follows
  provenance, not the plan-in-force heuristic

#### Scenario: Mixed sources chain with a dashed transition
- **WHEN** 建照/開工 come from a Taipei case anchored to recno 1042 and 使照
  is filled solely from the national portal
- **THEN** a solid pink edge runs 1042 → 建照， a solid pink chain joins
  建照 → 開工， a green dashed edge joins 開工 → 使照， and the 使照 node
  carries the 國 badge with a twur-hyperlinked 現況 國 badge as the national
  access point

#### Scenario: Event attributed to the plan in force
- **WHEN** 建照核發日期 2017-07-14 falls after approval 2016-07-05 but before
  approval 2019-08-01 (e.g. 河堤段四小段263-19)
- **THEN** the 建照 event's attribution edge points at the 2016-07-05 approval,
  while 使照核發日期 2021-10-25 attributes to the 2019-08-01 approval

#### Scenario: National-mapped event shows the 國 badge with western date
- **WHEN** the 使照 slot is filled from the national portal (使用核發日期
  110.10.25 in `links.milestones_national`)
- **THEN** that event node displays a small 國 badge and the date renders
  western as 2021/10/25

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

#### Scenario: Unanchored carrying case keeps id-only provenance and its link
- **WHEN** the carrying case_id anchors to no record
- **THEN** the provenance shows the bare case_id without a 編號 suffix, and
  the event label remains the sole hyperlink to that case's detail page

#### Scenario: Unprovable provenance stays unlabeled
- **WHEN** a slot value cannot be exactly matched to the `implementation`
  payload or the `milestones_source` map
- **THEN** that node shows no case label rather than a guessed one

#### Scenario: Project with no construction events
- **WHEN** none of the three dates exists for the project
- **THEN** no event nodes or attribution edges render, leaving the graph unchanged

#### Scenario: Annotations never cover existing graph elements
- **WHEN** a project renders events or callouts (any record count or column layout)
- **THEN** no event node, attribution edge, callout, or tail intersects any
  approval node or its labels — callouts are placed at the first of six
  candidate spots around their record that overlaps nothing

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

## ADDED Requirements

### Requirement: Badge rollover tooltips name their target

The graph's portal badges SHALL expose a rollover tooltip naming their
destination: each 北 badge SHALL show `案<case_id>` for the case it links to
(so sibling records are distinguishable, e.g. 案10011041 vs 案10011042), and
the 現況 node's 國 badge SHALL show the national view identifier
(`view/<id>`).

#### Scenario: 北 badge rollover names its case
- **WHEN** the pointer rests on a record's 北 badge whose anchored case is
  10011042
- **THEN** the tooltip shows 案10011042

#### Scenario: 國 badge rollover names the view
- **WHEN** the pointer rests on the 現況 node's 國 badge
- **THEN** the tooltip shows the national view identifier (e.g. view/262)

### Requirement: List items surface the construction stage

Each project item in the left-hand list SHALL display a two-character
construction stage badge — 建照， 開工， or 使照 — derived from whichever of
the three construction milestones carries the latest date (使照 falls back to
the national 使用核發日期). Projects with none of the three dates SHALL show
no badge. The badge is a read-only status chip; it adds no interaction.
Badge colours: 建照 orange, 開工 red, 使照 green.

#### Scenario: Latest milestone wins the badge
- **WHEN** a project has 建照核發日期 2018/12/21 and 使照核發日期 2024/04/24
  (no 開工)
- **THEN** the list item shows the 使照 badge (the latest construction event),
  rendered green

#### Scenario: No construction dates, no badge
- **WHEN** a project carries none of the three construction dates
- **THEN** its list item shows no stage badge
