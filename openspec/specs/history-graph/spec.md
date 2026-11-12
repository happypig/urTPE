# history-graph Specification

## Purpose

Publishes the merged result as a per-project JSON history graph whose revision edges converge on each family's latest approval, and renders it in a browser viewer so an analyst can read one project's full approval timeline.
## Requirements
### Requirement: Emit a valid history graph

The system SHALL emit projects.json containing one graph per project family: nodes for each record (編號, ISO date, stage, track, 區段, is_current, case_name, land, parcels, aliases, land_count, orig_count, named_anchor, area_section, implementer, planner, review_flags, auto_fixes) and edges for revision progressions and section branches, with edges converging on the anchor. Each project SHALL carry a `published_date` field with the official PDF publication date (統計至 115年8月11日).

#### Scenario: Every record has a node in exactly one project
- **WHEN** projects.json is generated
- **THEN** each record in merged.tsv maps to a node in exactly one project graph
- **AND** no node appears in two projects

#### Scenario: Revision edges point toward the anchor
- **WHEN** a family contains 擬訂 → 變更 → 變更(第二次) approvals ordered by date
- **THEN** edges connect each approval to the next-newer one, terminating at the is_current anchor
- **AND** 事業計畫 and 權利變換 approvals stay on distinguishable tracks

#### Scenario: Section branches are represented
- **WHEN** a family has A區段 and B區段 approvals
- **THEN** the graph records the section on each node and links the section branches to the shared timeline

#### Scenario: JSON is schema-valid
- **WHEN** projects.json is validated against its declared schema
- **THEN** it parses without error and every project contains non-empty nodes and a single anchor

#### Scenario: Nodes carry full original row fields
- **WHEN** a project graph is emitted
- **THEN** each node contains the full CleanRecord fields: case_name, land, parcels, aliases, land_count, orig_count, named_anchor, area_section, implementer, planner, review_flags, auto_fixes

#### Scenario: Project carries official published date
- **WHEN** projects.json is generated
- **THEN** each project has a `published_date` field with the value "統計至 115年8月11日" (from PDF page 1)

#### Scenario: Project carries discovered links
- **WHEN** a project's official links have been resolved by discovery
- **THEN** the project's `links` object contains its national-portal URL and any city-platform case URLs
- **AND** a project with no resolved link carries an empty `links` object

### Requirement: Render the history in a browser viewer

The system SHALL provide a viewer that loads projects.json and renders each project's history, highlighting the current (anchor) approval and distinguishing tracks and sections visually.

#### Scenario: Viewer shows a project timeline
- **WHEN** a user selects a project in the viewer
- **THEN** the timeline renders all its approvals ordered by date, with the anchor highlighted and 事業計畫 / 權利變換 tracks visually distinct
- **AND** 區段 annotations are visible on the relevant nodes

#### Scenario: Viewer handles the full dataset
- **WHEN** the viewer loads projects.json for all 1,419 records
- **THEN** it renders without error and supports browsing and searching across all project families

#### Scenario: Graph scales uniformly at any panel width
- **WHEN** the detail panel is narrower than the graph's authored coordinate space
- **THEN** node positions and label text scale uniformly (no horizontal-only squish), keeping labels legible

#### Scenario: Labels remain readable over edges
- **WHEN** a track or section edge passes behind a node label
- **THEN** the label text remains readable against the line

#### Scenario: Graph height follows the node count
- **WHEN** a project has few records
- **THEN** the graph box is sized to its nodes instead of reserving a large fixed height

#### Scenario: District is surfaced on list items
- **WHEN** the list renders project items
- **THEN** each item carries a district color chip alongside the project id

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
the national 使用核發日期). After the construction badge, the item SHALL
display a dead-end state badge when the project's current (is_current) recno
node's own case carries a dead-end schedule in `case_schedules` — 已失效 /
自行撤回 / 已駁回 — naming that state verbatim (user decision 2026-11-05,
board D4c: the state of the current approval's own case, not the family's; 1
project today, 龍泉段一小段-534's 11201181 已失效). The family-level grey
chips (審查中 / 撤回) and the 未核定 badge are REMOVED: a gazette approval
proves the unit was approved, and an older case's state must not label the
current approval (the 4 撤回/未核定 projects all hold an approved current
node). A project with no construction badge and no dead-end current case
shows no state badge. Badge colours: 建照 orange, 開工 red, 使照 green, dead-end state
grey.

Each list item SHALL also be reachable and activatable by keyboard, and the
selection SHALL be written to the URL (viewer-url-writeback-keyboard,
2026-11-12): every item carries `tabindex="0"` and `role="button"`, shows a
visible focus indicator (`:focus-visible`), and Enter or Space activates it
exactly as a click does. Selecting a project — by click or by keyboard —
SHALL write `#project=<encodeURIComponent(project_id)>` into the URL with
`history.replaceState` (one history entry per page load; never a push per
click), so a reader can copy the selection out of the address bar. The
deep-link read half (`openFromHash`, the hash format, the dashboard's
encoding) SHALL NOT change.

#### Scenario: Latest milestone wins the badge
- **WHEN** a project has 建照核發日期 2018/12/21 and 使照核發日期 2024/04/24
  (no 開工)
- **THEN** the list item shows the 使照 badge (the latest construction event),
  rendered green

#### Scenario: Dead-end current case shows the state badge after the construction badge
- **WHEN** a project's current recno node's first case is 11201181 and
  `case_schedules[11201181]` is 已失效 (龍泉段一小段-534)
- **THEN** the list item shows the grey 已失效 badge
- **AND** when the project also carries a construction date, the dead-end
  badge renders after the construction badge

#### Scenario: An approved current node shows no dead-end badge despite dead older cases
- **WHEN** a project's current node is an approved 擬訂 事業概要 and an older
  case of the family is 已駁回 or 已失效 (民生段-140-9, 市府段三小段-331,
  雙連段一小段-416-6)
- **THEN** the list item shows no state chip (no 審查中, 撤回 or 未核定 chip
  exists any more)

#### Scenario: In-review without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and its
  `case_schedules` include 審查中 (37 families measured)
- **THEN** the list item shows no state chip (in-review is the default state;
  the grey 審查中 chip is removed)

#### Scenario: Withdrawn without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and every
  case in its `case_schedules` is 自行撤回 / 已駁回 / 已失效, but its current
  recno node's own case has no dead-end schedule (市府段三小段-331,
  雙連段一小段-416-6, 民生段-140-9)
- **THEN** the list item shows no state chip (the grey 撤回 chip is removed —
  the current approval decides, not older cases)

#### Scenario: No construction dates and no case schedule shows nothing
- **WHEN** a project carries none of the three construction dates and its
  current node's case has no `case_schedules` entry
- **THEN** its list item shows no stage badge

#### Scenario: In-review and approved states mark nothing
- **WHEN** a project's cases are 審查中 or 已核准 (37 in-review families
  measured)
- **THEN** its list item shows no state badge (approved/in-review is the
  default state)

#### Scenario: No construction dates and no dead-end current case shows nothing
- **WHEN** a project carries none of the three construction dates and its
  current node's case has no dead-end schedule
- **THEN** its list item shows no stage badge

#### Scenario: A list item is focusable and keyboard-activatable
- **WHEN** a project item renders in the left-hand list
- **THEN** it carries `tabindex="0"` and `role="button"`
- **AND** Enter or Space activates it exactly as a click does

#### Scenario: Selecting a project writes the URL
- **WHEN** a project is selected, by click or by keyboard
- **THEN** the URL hash becomes `#project=<encodeURIComponent(project_id)>`
- **AND** the write is a `replaceState`, so the history stack gains no entry

#### Scenario: The deep link's read half is unchanged
- **WHEN** the page is opened with `#project=<id>` in the hash, or the hash
  changes while the page is open
- **THEN** that project's graph opens, as before

### Requirement: Node order survives a rebuild from emitted state

A rebuild that starts from an emitted graph rather than from the gazette SHALL restore
each node's calendar ordering before the family's approvals are ordered. Ordering keys
SHALL be derived from the node's own approval date and never from 編號, which is a
coordinate that shifts as the city prepends and re-dates rows, so an ordering that
degrades to 編號 silently inverts a project's timeline.

Because such a rebuild reads the emitted payload as its input, a node missing its
ordering key would otherwise re-emit in the same wrong order on every subsequent run,
making the inversion permanent rather than transient.

#### Scenario: A node's ordering key is restored from its date

- **WHEN** an emitted node carries a date but no ordering key
- **THEN** the key is reconstructed from that date
- **AND** it is never left at its empty default while the node carries a date

#### Scenario: Approvals order by date, not by 編號

- **WHEN** a family's members are 編號 1362 dated 2008-01-02 (變更) and 編號 1407 dated 2005-02-24 (擬訂)
- **THEN** the rebuilt graph emits 1407 before 1362
- **AND** the anchor is highlighted rather than placed first, since 編號 order and date
  order disagree for this family

#### Scenario: No dated node is left unordered

- **WHEN** an emitted payload is examined node by node
- **THEN** no node carrying a date carries the empty ordering key

### Requirement: The emitted document carries a total, disjoint record-to-project partition

The ingestion SHALL verify, after merge and before any artifact is written, that
the merge partition is total and disjoint over the cleansed records: every
cleansed record belongs to exactly one project family, and the family members sum
to the cleansed record count. The emitted document SHALL also agree with the
cleansed records it was built from: the document's record count SHALL equal the
cleansed count. A violation SHALL be reported with the violating records named,
and SHALL be evaluated before `projects.json`, the TSVs, or the viewer data are
written — a check that runs after the damage is not a check. A partition
violation SHALL block the emission (exit 4, the tripwire contract): unlike
missing link data, a lost or double-counted record is data corruption, not
absence.

The census check SHALL verify the family set that is actually emitted. A
manual correction whose confirmed merge unions two records changes the family
count, so the check SHALL run **after** the correction ledger is applied and
SHALL compare against that post-correction family set. The count the check
reports — in the run report and in the tripwire report — SHALL be the count of
the emitted family set, so a report never states a count the payload does not
carry.

Every path that emits a document SHALL hold the partition, not only the path
that reads a PDF. A rebuild from an already-emitted document SHALL verify the
partition of that document **before** it is loaded into families: the document's
record count SHALL agree with the records its nodes carry, each family's member
list SHALL agree with that family's nodes, and each family's anchor SHALL be one
of that family's nodes. The verification SHALL use the output tree's
`clean.tsv` as an independent reference when that file is present, so a
document that lost a record **and** had its own count rewritten to match — a
shape no internal check can see — is still refused. A violation on this path
SHALL block the emission (exit 4, the tripwire contract) and SHALL name the
missing records.

#### Scenario: The partition is total and disjoint

- **WHEN** an ingestion completes merge and every cleansed record appears in
  exactly one project family
- **THEN** the census check passes and nothing is reported
- **AND** the emitted document's record count equals the cleansed record count

#### Scenario: A record is lost between cleanse and merge

- **WHEN** a cleansed record appears in no project family
- **THEN** the census check names the record and blocks the emission
- **AND** nothing is written: `projects.json`, the TSVs, and the viewer data stay
  as they were

#### Scenario: A record appears in two families

- **WHEN** a cleansed record appears in more than one project family
- **THEN** the census check names the record and both families, and blocks the
  emission
- **AND** nothing is written

#### Scenario: The census check sees the family set the payload carries

- **WHEN** a manual correction confirms a merge that unions two records into one
  family, so the merged family count is one lower than the uncorrected count
- **THEN** the census check compares the cleansed records against the corrected
  family set
- **AND** the tripwire report and the run report state the corrected family
  count, which is the count the emitted document carries

#### Scenario: A rebuild from emitted state refuses a document that lost a record

- **WHEN** a document to be rebuilt carries one record fewer than its own record
  count states
- **THEN** the rebuild refuses the document and names the missing record
- **AND** nothing is written: `projects.json`, the TSVs, and the viewer data stay
  as they were

#### Scenario: A rebuild refuses a document whose count was rewritten to match

- **WHEN** a document lost a record and its own record count was rewritten so
  that the count agrees with the records it carries, and the output tree holds a
  `clean.tsv` naming the lost record
- **THEN** the rebuild compares the document against that `clean.tsv`, names the
  lost record, and refuses the document
- **AND** nothing is written

#### Scenario: A rebuild refuses a document whose family lost its anchor

- **WHEN** a document's family names an anchor record that its own nodes do not
  carry
- **THEN** the rebuild names the family and its missing anchor and refuses the
  document
- **AND** the run does not fail with an unhandled error

#### Scenario: A rebuild of a complete document proceeds

- **WHEN** a document to be rebuilt carries every record its count states, every
  family's members in that family's nodes, and every family's anchor among them
- **THEN** the rebuild proceeds and emits the document
- **AND** the output tree's `clean.tsv`, where present, holds exactly the
  records the document carries

### Requirement: Stage index survives a rebuild from emitted state

Every emitted node SHALL carry its `stage_index`, and loading an emitted document
SHALL reconstruct each node's `stage_index` — from the emitted key when present,
otherwise derived from the node's stage text by the same rule the cleanser
applies — so that a rebuild from emitted state groups section branches
(`stage_index`, `track`) identically to the original build. The round trip
emit → load → emit SHALL be lossless for `stage_index`.

#### Scenario: A section-branch family forms the same edges on rebuild

- **WHEN** a project family holds records whose `area_section` values differ
  (甲/A/B) across distinct stages, the document is emitted, and then rebuilt via
  the emitted-state loader
- **THEN** the section-branch edges (`kind: "section"`) formed on the rebuild are
  identical to those formed on the original build
- **AND** no node loads with the sentinel `-1` unless its stage text yields no
  index on the original build either

#### Scenario: An already-deployed document without the key repairs on load

- **WHEN** a loader reads an emitted node that carries no `stage_index` key
- **THEN** the index is derived from the node's stage text (the cleanser's
  `_stage` rule)
- **AND** the resulting grouping matches what a fresh ingest of the same rows
  would produce

#### Scenario: The round trip is lossless

- **WHEN** a document is emitted, loaded, and emitted again
- **THEN** every node's `stage_index` is identical across the two emissions

### Requirement: Status-chip vocabulary gains 無 / NA per-case labels

The per-case badge SHALL render 「無」 when 基本資料 / 目前辦理情形 reads 無 and
「NA」 when it reads empty. These labels SHALL apply only to the per-case badge;
the family status chip (審查中 / 撤回) and the never-approved readers SHALL skip
無 / NA so they read exactly as before.

**Reason**: 無 / NA are honest per-case readings and must not be folded into the
family-level chip vocabulary.

#### Scenario: Per-case badge renders 「無」 for 無 reading

- **WHEN** a case's 目前辦理情形 reads 無
- **THEN** its badge shows [無]

#### Scenario: Per-case badge renders 「NA」 for empty reading

- **WHEN** a case's 目前辦理情形 reads empty
- **THEN** its badge shows [NA]

#### Scenario: Family chip ignores 無 / NA

- **WHEN** every case's state is 無 or empty, or mixed with terminal states
- **THEN** the family status chip reads as if 無 / NA cases were absent

### Requirement: 國 badge binds to the recno node a national label names

A national approval label (事業計畫核定日期, 權利變換計畫核定日期,
第一次變更事業計畫核定日期, …) carries a stage (擬訂, 第N次變更) and a
track (事業計畫 / 權利變換). The viewer SHALL bind each label to at most one
recno node, decided once per project, not per node: the label's candidates are
the nodes carrying the label's stage and a matching track (a combined-track
node, 事業計畫、權利變換, matches a label of either track). Binding SHALL
resolve by exact date first; if several nodes share the label's date, or the
label's date matches no node exactly, the ±1-day window (公告-vs-committee
offset) SHALL decide; if 2 or more nodes survive a step, or no node qualifies
at any step, the label SHALL bind nothing and no node gains the 國 badge from
it. Application dates (…申請日期) and 使用核發日期 name no stage and SHALL
never bind. A node SHALL also keep its 國 badge when `links.view_verified_case_ids`
lists its anchored case (the portal's direct assertion). The 現況 rule
(`node.is_current` alone) is removed.

**Reason**: scoring per node badged every candidate of a multi-match label —
19 labels, 41 badged nodes, 16 unearned 國 (C1). Binding per label gives one
owner per label or none.

#### Scenario: 國 binds to the node with matching stage+track

- **WHEN** a national label 事業計畫核定日期 111.08.02 names stage 擬訂 track
  事業計畫 and exactly one recno node carries that stage and track
- **THEN** that node gets the 國 badge

#### Scenario: A single-candidate label binds whatever its date

- **WHEN** a label names stage+track that exactly one node carries, and the
  node's date differs from the label's date by more than 1 day
- **THEN** that node still gets the 國 badge (one candidate cannot tie)

#### Scenario: 國 binds by date tie-break

- **WHEN** two recno nodes share stage 變更 track 事業計畫, dated 111.08.02 and
  112.03.21, and the national label 第一次變更事業計畫核定日期 reads 112.03.21
- **THEN** only the 112.03.21 node gets 國

#### Scenario: The ±1-day window decides among several candidates

- **WHEN** two recno nodes share stage+track, dated 2023-03-20 and 2023-09-01,
  and the label's date converts to 2023-03-21
- **THEN** only the 2023-03-20 node gets 國 (within ±1 day; the other is not)

#### Scenario: A tie that ±1 day cannot break binds nothing

- **WHEN** two recno nodes share stage+track, both dated 2023-03-20, and the
  label's date converts to 2023-03-21
- **THEN** neither node gets 國 from this label (2 survivors after the window)

#### Scenario: view_verified_case_ids still grants 國

- **WHEN** `links.view_verified_case_ids` lists the node's anchored case
- **THEN** that node keeps its 國 badge

#### Scenario: 現況 alone no longer grants 國

- **WHEN** a node is 現況 but its case is not view-verified and no national label
  binds to it
- **THEN** it carries no 國 badge

#### Scenario: application dates and 使用核發日期 bind nothing

- **WHEN** a national label 使用核發日期 or 事業計畫申請日期 is present
- **THEN** it binds to no recno node for the 國 badge

### Requirement: The proof of the partition is re-derivable from the emitted files

The system SHALL provide a read-only means of re-deriving the partition of an
emitted dataset from the emitted files themselves — the document, the cleansed
record file, and the merged record file — so a reader can confirm that every
cleansed record sits in exactly one family, that no record sits in two, and
that no family holds a record the cleansing does not, without trusting the
run that produced them. The proof SHALL name the counts it compared, and a
record it cannot account for SHALL be named rather than counted.

#### Scenario: The partition is re-derived from the emitted files

- **WHEN** the emitted document, the cleansed record file and the merged record
  file are read
- **THEN** the proof reports the record count each file holds, the number of
  records appearing in two families, the number of cleansed records in no
  family, and the number of family members the cleansing does not hold
- **AND** the proof states plainly whether the partition is total and disjoint

#### Scenario: A record in no family is named

- **WHEN** a cleansed record appears in no family of the emitted document
- **THEN** the proof names that record
- **AND** the proof does not report the partition as total

