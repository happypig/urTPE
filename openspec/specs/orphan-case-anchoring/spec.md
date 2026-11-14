# orphan-case-anchoring Specification

## Purpose
Anchors orphan case_ids (case_ids in `links.taipei` that have no anchor record — whether guard-rejected cases carrying a known case_name, or accepted-but-unanchored cases identified by stage attribution) as ghost nodes in the history graph when their identity with the project anchor is established (landcore similarity ≥ 0.7, or milestone-source attribution), so their milestone dates appear in the correct chronological context instead of being silently dropped.
## Requirements
### Requirement: Ghost node for landcore-similar orphan case_ids

The pipeline SHALL examine each case_id in `links.taipei` that has no corresponding anchor record in the project's nodes. For each such orphan, it SHALL compute the landcore similarity between the orphan's case_name and the project's anchor record. If similarity ≥ 0.7, the pipeline SHALL create a ghost node in the project's graph with `orphan: true`, the orphan's case_id, its milestones, and provenance from `links.milestones_source` or `links.search_rejected`.

A case recorded in `superseded_by` — the city re-filed it under a new id — SHALL NOT become a ghost node: its undated node showed a process the city has replaced (measured: 10410012, 10806141, 11009142, 11211211 carried an empty-`node_date` node each). The case stays in `links.taipei` (the list is append-only and other readers key on it); only the node is withheld. The successor case carries the live history.

#### Scenario: Orphan with matching landcore becomes ghost node
- **WHEN** a project has `links.taipei` containing case_id 09907221, no node anchors 09907221, and the case_name "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案" has landcore similarity ≥ 0.7 to the project anchor "文山區木柵段三小段623地號等39筆"
- **THEN** the emitted `projects.json` includes a ghost node with `orphan: true`, `case_id: "09907221"`, and its milestone dates (計畫公聽會日期 through 核定日期, 建照核發日期)

#### Scenario: Orphan with low landcore similarity is excluded
- **WHEN** a project has an orphan case_id whose case_name landcore similarity < 0.7 to the project anchor, and the case_id is NOT portal-verified (absent from `view_verified_case_ids`)
- **THEN** no ghost node is created, and the case_id remains only in `links.taipei` (current behavior)

#### Scenario: A superseded case's undated orphan is withheld
- **WHEN** a project's cache records 10806141 as superseded by 11510017, and 10806141 anchors no node (its undated orphan node carried no date — 虎林38)
- **THEN** no ghost node is created for 10806141
- **AND** 10806141 stays in `links.taipei`
- **AND** the successor 11510017 carries the live history

### Requirement: Portal-verified orphans bypass the landcore gate

Case_ids listed in `DiscoveryResult.view_verified_case_ids` — extracted from the project's own national view page 相關連結 — SHALL become ghost nodes regardless of landcore similarity **only when the city's own case name for the id confirms the unit**: the land core of the platform's `CASE_NAME` (get_project168_top) SHALL match the project's land core at `LINK_THRESHOLD = 0.7`, or the name SHALL be parcel-less (a settlement-named unit like 崇仁新村 carries no 地號 and is not decidable by land core — it does not reject), or the name SHALL declare the **same district and section** as the project and **one of the unit's own parcels** (anchor-parcel drift: the 地號 cell and the 案名 start at different parcels, so the land cores differ although the case is the unit's own). A view-verified id whose city name names another project SHALL NOT become a ghost node: it SHALL move to the project's `view_rejected` record with its reason — shape A (the 相關連結 label and the city name both name another project) or shape B (the label is right, the id is wrong — only the city's own case name shows this). A 相關連結 label that names another project while the city name matches SHALL NOT reject the id: the portal's label error is logged in the run report instead. A city name the refresh could not read SHALL NOT reject the id (a missing header is no evidence); the id stays view-verified and, when its label also mismatches, is reported as "label not confirmed".

#### Scenario: Parcel-less portal-verified orphan becomes ghost

- **WHEN** an orphan case_id 09112120 has case_name "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案" (no 地號 → similarity 0.0), no node anchors it, and it is listed in `view_verified_case_ids` (it appears in the project's own view page 相關連結)
- **THEN** a ghost/virtual node is created for it with its harvested case_name, stage/track derived from the name, and `node_date` from its 核定日期 milestone

#### Scenario: Unverified low-similarity orphans remain excluded

- **WHEN** an orphan case_id has a parcel-less case_name, similarity 0.0, and is NOT in `view_verified_case_ids`
- **THEN** no ghost node is created

#### Scenario: A view-verified id whose city name names another project does not become a ghost

- **WHEN** a project's view page lists case_id 09511211 with the label "擬訂臺北市大安區大安段一小段557…" (matching the project's own land core) but the city's own case name for 09511211 is "擬訂臺北市中山區吉林段四小段603…" (similarity 0.0 — shape B)
- **THEN** no ghost node is created for 09511211 on this project
- **AND** the id moves to the project's `view_rejected` with reason "label is right, id is wrong (shape B)"

#### Scenario: A wrong label alone does not reject

- **WHEN** a project's view page labels case_id 10906092 with another project's name (萬華區莒光段三小段519-3) but the city's own case name for it is the project's own unit (中山區吉林段二小段898 — similarity ≥ 0.7)
- **THEN** the id stays view-verified and anchors normally
- **AND** the run report logs the label error for the id

#### Scenario: A missing city name never rejects

- **WHEN** the header fetch returned no row (or the cache holds no CASE_NAME) for a view-verified id whose label names another project
- **THEN** the id stays view-verified
- **AND** the run report marks it "label not confirmed" instead of rejecting it

#### Scenario: A drifted case anchors on the node of its date

- **WHEN** 華中247's view-verified id 09305081 (擬訂 A區, 核定 2014-04-25) is kept by the own-parcel rule and the node 1131 (2014-04-25) already carries 09305082
- **THEN** 09305081 anchors on node 1131 and no ghost node is created for it
- **AND** node 1131 carries both cases in its `links.taipei`

#### Scenario: A same-section case of another unit still does not anchor

- **WHEN** a view-verified id's city name is in the project's own section but declares none of the unit's own parcels
- **THEN** no ghost node is created for it
- **AND** the id moves to the project's `view_rejected` with reason "label and city name name another project (shape A)"

### Requirement: Attribution-provenance fallback when no case_name exists

When an orphan case_id has no case_name in `links.search_rejected`, the pipeline SHALL treat stage-milestone attribution as equivalent proof of unit membership: if `links.milestones_source` attributes at least one milestone label to the orphan's case_id, the pipeline SHALL create the ghost node carrying exactly those attributed labels' dates. A case_id whose dates already anchor onto an existing node SHALL never be ghosted.

#### Scenario: Attributed orphan without case_name becomes ghost
- **WHEN** `links.search_rejected` has no entry for case_id 09907221, `links.milestones_source` attributes milestone labels to it, and no node anchors it
- **THEN** the emitted graph contains a ghost node for 09907221 whose `milestones_taipei` covers exactly those attributed labels

#### Scenario: Node-anchored cases stay unghosted
- **WHEN** a case_id wins milestone attribution but some node's `links.taipei` already anchors it
- **THEN** no ghost node is created for that case_id

### Requirement: Shadowed twins anchor via shared milestone history

An orphan case_id with no case_name and no attribution SHALL still anchor as a ghost node when its per-case milestone record shares at least 3 exact (label, date) pairs with the milestone records of cases already anchored to the unit (shared process history standing in for landcore similarity until case_name harvesting). Its ghost payload SHALL carry exactly the shared (label, date) pairs.

#### Scenario: Shadowed twin becomes a ghost anchor
- **WHEN** orphan case_id 09907223 has zero attributed labels (its twin 09907221 outbid it on all 15) but its own platform record shares 14 exact (label, date) pairs with anchored case 09907222
- **THEN** the graph contains a dashed-circle ghost node for 09907223 alongside 09907221's, and 相關連結 continues to show its milestone context

#### Scenario: Disjoint-history orphans stay excluded
- **WHEN** an orphan's milestone record shares fewer than 3 (label, date) pairs with every anchored case of the unit
- **THEN** no ghost node is created for it

### Requirement: Ghost node carries orphan's milestone dates

When a ghost node is created, its `milestones_taipei` and
`milestones_taipei_case` SHALL be populated from the corresponding entries in
`links.milestones_source` that map to the orphan's case_id, and its `case_id`
field SHALL be set for portal linking. The per-case dict is named
`milestones_taipei_case` because it holds the Taipei platform's
per-case milestones (the `Get_project168_second.ashx` data) — the name
`milestones_national` falsely claimed the national portal's data space
(board D1: name wrong, data right). A rebuild from an already-emitted payload
SHALL read an old orphan's `milestones_national` as `milestones_taipei_case`
(load alias), so previously emitted files keep rendering.

#### Scenario: Ghost node shows correct milestones
- **WHEN** `links.milestones_source` maps 14 dates to case_id 09907221
- **THEN** the ghost node's `milestones_taipei` contains those 14 dates with their labels

#### Scenario: The per-case dict is named for its source
- **WHEN** an orphan node is emitted
- **THEN** its per-case milestone dict is `milestones_taipei_case` (Taipei ashx
  data; slash-Gregorian dates), distinct from the project-level
  `milestones_national` (twur 推動歷程, ROC-dot dates)

#### Scenario: An old payload loads under the new key
- **WHEN** `--from-js` loads an emitted payload whose orphan nodes carry
  `milestones_national`
- **THEN** the value loads as `milestones_taipei_case` and the viewer renders
  the node unchanged

### Requirement: Ghost landcore extraction handles single-段 sections and 概要-track dates

The orphan landcore extraction SHALL accept single-段 sections (`民生段140-9地號等3筆`) as well as 段小段 sections — village-renewal and older units use single-段 names, and rejecting them silently drops every orphan of the family (民生段140-9 shape: two 概要 orphans, one 已駁回 one 自行撤回). The extraction SHALL also accept, measured city shapes the single regex missed: a 、-list before 地號 (`長安段三小段709、711地號等2筆` — the land core keys on the first parcel), an `(原NNN)` suffix inside the parcel or the count (`105(原90)地號等13筆(原24筆)`), and spaces before 地號 or 筆 (`1-1 地號等11 筆`). The extraction SHALL NFKC-normalise the name before matching (the 擬訂臺北市 prefix with the compatibility form U+F963 of 北 breaks the 臺北市 split — Appendix A). An orphan case_name that still yields no land core SHALL be named in the run report, not dropped silently; a parcel-less name (崇仁新村) stays excluded from the similarity gate by design and is not reported as unparseable. The ghost's `node_date` SHALL fall back through the approval-date labels in track order: `核定日期` → `權變核定日期` → `概要核准日期`.

#### Scenario: Single-段 orphan cases become ghosts
- **WHEN** a project's 案名 land core is `松山區民生段140-9地號等3筆` (single-段) and two orphan 概要 cases carry candidate_names with the same land fragment
- **THEN** both orphans pass the similarity gate and render as virtual nodes with their harvested names

#### Scenario: 概要 ghost carries its approval date
- **WHEN** an orphan 概要 case has `概要核准日期 = 2026/03/31` and no 核定日期
- **THEN** the ghost's `node_date` is `2026-03-31` (previously empty, leaving the virtual node undated and mispositioned — 延吉段三小段727 shape)

#### Scenario: A 、-list orphan name extracts its first parcel
- **WHEN** an orphan case_name reads `變更臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案-A區`
- **THEN** the extraction yields a land core with first parcel 201-2, and the case passes the similarity gate against the 華中段一小段 anchor (09305081 shape)

#### Scenario: An (原NNN) orphan name extracts without the suffix
- **WHEN** an orphan case_name reads `擬訂臺北市南港區中南段105(原90)地號等13筆(原24筆)土地都市更新事業計畫案`
- **THEN** the extraction yields the land core without the `(原…)` parts (105地號等13筆)

#### Scenario: Spaced 地號/筆 extract
- **WHEN** an orphan case_name reads `擬訂臺北市北投區奇岩段四小段1-1 地號等11 筆土地都市更新事業計畫案`
- **THEN** the extraction yields the land core `奇岩段四小段1-1地號等11筆`

#### Scenario: A compatibility 北 still extracts
- **WHEN** an anchor name carries the compatibility form of 北 (U+F963) after 臺 (三興972 shape)
- **THEN** the extraction recovers the land core (NFKC before matching)

#### Scenario: An unparseable orphan name is named, not dropped silently
- **WHEN** an orphan case_name still yields no land core after NFKC and the learned shapes (e.g. a 號-without-地號 name)
- **THEN** the run report names the project and the case_id with its name

### Requirement: Ghost node provenance flag

The ghost node SHALL have `orphan: true` and `provenance: "orphan-case-anchoring"` fields so the viewer can distinguish it from anchored records.

#### Scenario: Ghost node marked with orphan flag
- **WHEN** a ghost node is created for orphan case_id 09907221
- **THEN** the node has `orphan: true` and `provenance: "orphan-case-anchoring"`

### Requirement: Viewer renders orphan ghost node with dotted construction-chain edges

The viewer SHALL render ghost/orphan nodes in the history graph with an "orphan" badge. Each orphan SHALL take its own timeline row, interleaved with the recno nodes by the case_id order (an undated orphan carries its stage cluster's effective date). A dated nameless 孤 anchor joins the timeline by date like a named orphan; an undated nameless anchor renders no row (the right-most ghost column is removed — wave 5 §4; the 3 nameless anchors were §8 defects removed by wave 3b). "Between 2 consecutive recnos" and "nearest recno" mean RENDERED ROWS in the timeline, not dates: an undated orphan has no date of its own, so a date-based test never fires for it (corpus: 30 orphans row-between but undated, 7 dated). A named orphan whose row sits between 2 consecutive recno rows of the same swimlane SHALL shift 32px right of that swimlane's track line. Each orphan whose schedule is NOT a dead end (已失效 / 自行撤回 / 已駁回 / 已撤銷) SHALL connect with a dotted edge (class `edge orphan`) to the recno row directly above it — its branch-off point — or to the recno row directly under it when no recno row sits above. A dead-end orphan connects only upward, to its branch-off row; when no recno row sits above it, it renders with no dotted edge (user decision 2026-11-05, board D4b — an edge pointing down out of a closed case draws a flow that never happened; measured 160 such edges, against 78 up-edges that stay). Example: 11012301 (applies 2021-12-29, withdraws, no date) renders between 734@2019-12-18 and 393@2022-12-29 in the 事業計畫、權利變換 swimlane, shifts 32px right, and its dotted edge goes to 734 — the revision it was filed against — not to the later 393; the live path keeps its solid edge 734 → 393 (dead-end branch vs ongoing path).

#### Scenario: Orphan ghost node appears in graph by date with badge

- **WHEN** a project has a ghost node for case_id 09907221
- **THEN** the graph shows a node with an "orphan" badge at its date row among the recno nodes

#### Scenario: Orphan dotted edge to the recno row directly above

- **WHEN** an orphan renders between recno nodes dated 2023-03 and 2023-08 in its swimlane
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2023-03 recno node directly above it

#### Scenario: Undated orphan branches from the recno row directly above, not the later recno it was filed against

- **WHEN** an undated orphan (case_id 11012301) renders between recno 734 (2019-12-18) and recno 393 (2022-12-29) in the same swimlane
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to recno 734, not to recno 393

#### Scenario: Orphan dotted edge to recno row directly under when no recno row sits above

- **WHEN** a live orphan (schedule not 已失效 / 自行撤回 / 已駁回 / 已撤銷) renders earlier than every recno node in its swimlane (earliest recno dated 2022-01)
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2022-01 recno node directly under it

#### Scenario: A dead-end orphan above every recno row renders no dotted edge

- **WHEN** an orphan whose schedule is 已失效 / 自行撤回 / 已駁回 / 已撤銷 renders earlier than every recno node in its swimlane (e.g. 北安段一小段25's 09609061 已失效)
- **THEN** no dotted edge connects it to any recno row (no edge points out of a closed case)
- **AND** the node still renders its row, badge and schedule text

#### Scenario: Orphan shifts 32px right only when between 2 recno rows in same swimlane

- **WHEN** a named orphan's row sits between 2 consecutive recno rows of the same track column (dated or undated)
- **THEN** its node renders 32px right of that column's track line

#### Scenario: Orphan not shifted when no recno row sits above it in the swimlane

- **WHEN** a named orphan renders earlier than every recno row of its swimlane
- **THEN** its node renders on its swimlane's track line (no 32px right shift)

