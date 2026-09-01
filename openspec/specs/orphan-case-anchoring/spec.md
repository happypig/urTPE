# orphan-case-anchoring Specification

## Purpose
Anchors orphan case_ids (case_ids in `links.taipei` that have no anchor record — whether guard-rejected cases carrying a known case_name, or accepted-but-unanchored cases identified by stage attribution) as ghost nodes in the history graph when their identity with the project anchor is established (landcore similarity ≥ 0.7, or milestone-source attribution), so their milestone dates appear in the correct chronological context instead of being silently dropped.
## Requirements
### Requirement: Ghost node for landcore-similar orphan case_ids

The pipeline SHALL examine each case_id in `links.taipei` that has no corresponding anchor record in the project's nodes. For each such orphan, it SHALL compute the landcore similarity between the orphan's case_name and the project's anchor record. If similarity ≥ 0.7, the pipeline SHALL create a ghost node in the project's graph with `orphan: true`, the orphan's case_id, its milestones, and provenance from `links.milestones_source` or `links.search_rejected`.

#### Scenario: Orphan with matching landcore becomes ghost node
- **WHEN** a project has `links.taipei` containing case_id 09907221, no node anchors 09907221, and the case_name "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案" has landcore similarity ≥ 0.7 to the project anchor "文山區木柵段三小段623地號等39筆"
- **THEN** the emitted `projects.json` includes a ghost node with `orphan: true`, `case_id: "09907221"`, and its milestone dates (計畫公聽會日期 through 核定日期, 建照核發日期)

#### Scenario: Orphan with low landcore similarity is excluded
- **WHEN** a project has an orphan case_id whose case_name landcore similarity < 0.7 to the project anchor, and the case_id is NOT portal-verified (absent from `view_verified_case_ids`)
- **THEN** no ghost node is created, and the case_id remains only in `links.taipei` (current behavior)

### Requirement: Portal-verified orphans bypass the landcore gate

Case_ids listed in `DiscoveryResult.view_verified_case_ids` — extracted from the project's own national view page 相關連結 (the portal itself asserts the case belongs to the unit) — SHALL become ghost nodes regardless of landcore similarity. This covers parcel-less case names (e.g. settlement-named units like 崇仁新村 whose platform names carry no 地號 and would score 0.0).

#### Scenario: Parcel-less portal-verified orphan becomes ghost
- **WHEN** an orphan case_id 09112120 has case_name "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案" (no 地號 → similarity 0.0), no node anchors it, and it is listed in `view_verified_case_ids` (it appears in the project's own view page 相關連結)
- **THEN** a ghost/virtual node is created for it with its harvested case_name, stage/track derived from the name, and `node_date` from its 核定日期 milestone

#### Scenario: Unverified low-similarity orphans remain excluded
- **WHEN** an orphan case_id has a parcel-less case_name, similarity 0.0, and is NOT in `view_verified_case_ids`
- **THEN** no ghost node is created

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

When a ghost node is created, its `milestones_taipei` and `milestones_national` SHALL be populated from the corresponding entries in `links.milestones_source` that map to the orphan's case_id, and its `case_id` field SHALL be set for portal linking.

#### Scenario: Ghost node shows correct milestones
- **WHEN** `links.milestones_source` maps 14 dates to case_id 09907221
- **THEN** the ghost node's `milestones_taipei` contains those 14 dates with their labels

### Requirement: Ghost landcore extraction handles single-段 sections and 概要-track dates

The orphan landcore extraction SHALL accept single-段 sections (`民生段140-9地號等3筆`) as well as 段小段 sections — village-renewal and older units use single-段 names, and rejecting them silently drops every orphan of the family (民生段140-9 shape: two 概要 orphans, one 已駁回 one 自行撤回). The ghost's `node_date` SHALL fall back through the approval-date labels in track order: `核定日期` → `權變核定日期` → `概要核准日期`.

#### Scenario: Single-段 orphan cases become ghosts
- **WHEN** a project's 案名 land core is `松山區民生段140-9地號等3筆` (single-段) and two orphan 概要 cases carry candidate_names with the same land fragment
- **THEN** both orphans pass the similarity gate and render as virtual nodes with their harvested names

#### Scenario: 概要 ghost carries its approval date
- **WHEN** an orphan 概要 case has `概要核准日期 = 2026/03/31` and no 核定日期
- **THEN** the ghost's `node_date` is `2026-03-31` (previously empty, leaving the virtual node undated and mispositioned — 延吉段三小段727 shape)

### Requirement: Ghost node provenance flag

The ghost node SHALL have `orphan: true` and `provenance: "orphan-case-anchoring"` fields so the viewer can distinguish it from anchored records.

#### Scenario: Ghost node marked with orphan flag
- **WHEN** a ghost node is created for orphan case_id 09907221
- **THEN** the node has `orphan: true` and `provenance: "orphan-case-anchoring"`

### Requirement: Viewer renders orphan ghost node with dotted construction-chain edges

The viewer SHALL render ghost nodes in the history graph with an "orphan" badge and connect their construction-chain events (建照/開工/使照) with dotted edges to visually group them as a phase sequence.

#### Scenario: Orphan ghost node appears in graph with badge
- **WHEN** a project has a ghost node for case_id 09907221
- **THEN** the graph shows a node with an "orphan" badge, and its 建照/開工/使照 events are connected by dotted edges

