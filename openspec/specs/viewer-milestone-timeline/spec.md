# viewer-milestone-timeline Specification

## Purpose
Renders official procedural milestone timelines from the national portal (推動歷程) and Taipei platform (階段辦理過程) as expandable timeline cards in the viewer detail pane, with per-node attribution and progressive loading states.
## Requirements
### Requirement: Display national portal 推動歷程 as timeline

The system SHALL render the national portal's 推動歷程 milestones (事業計畫申請/核定日期, 權利變換計畫申請/核定日期, 概要申請/核定日期) as a timeline card in the detail pane when `links.milestones_national` is present on the project.

#### Scenario: National milestones render as timeline
- **WHEN** a project has `links.milestones_national` with one or more entries
- **THEN** a card titled "推動歷程 (國土署)" appears in the detail pane
- **AND** each milestone shows as a row: label (e.g., "事業計畫申請日期") and date value
- **AND** the card is collapsible/expandable with a toggle button

#### Scenario: Empty national milestones show nothing
- **WHEN** `links.milestones_national` is empty or absent
- **THEN** no "推動歷程" card is rendered

### Requirement: Display Taipei platform 階段辦理過程 as timeline

The system SHALL render the Taipei platform's 階段辦理過程 milestones as a timeline card when `links.milestones_taipei` is present on the project.

#### Scenario: Taipei milestones render as timeline
- **WHEN** a project has `links.milestones_taipei` with one or more entries
- **THEN** a card titled "階段辦理過程 (台北市)" appears in the detail pane
- **AND** each milestone shows as a row: label (e.g., "計畫公聽會日期", "申請計畫日期", "公告公展日期", "召開審議會日期", "核定日期", "建照核發日期") and date value
- **AND** the card is collapsible/expandable with a toggle button

#### Scenario: Empty Taipei milestones show nothing
- **WHEN** `links.milestones_taipei` is empty or absent
- **THEN** no "階段辦理過程" card is rendered

### Requirement: Per-node milestone attribution

The system SHALL display per-node milestone badges in the history graph nodes and/or table rows, indicating which milestones belong to that approval stage. Each node's emitted `links.milestones_taipei` SHALL be the **anchored case's own per-case timeline** from `case_milestones[anchored_case_id]` — not the project-level last-write-wins merged dict (the §5 chimera: 319 families carry multiple distinct 核定日期 across cases, so the merged value shows the newest case's date on every node). When the anchored case has no per-case timeline (legacy caches, or the case's `second.ashx` returned empty), the node SHALL fall back to the project-level merged dict; the merged dict itself remains at project level unchanged (the 階段辦理過程 card and `milestones_source` provenance are untouched).

#### Scenario: Node shows relevant milestone badge
- **WHEN** a node has `links.milestones_national` or `links.milestones_taipei` populated
- **THEN** the node shows a badge indicating the milestone source (e.g., "國", "北")
- **AND** hovering or clicking reveals the specific milestones for that node

#### Scenario: Different nodes show different milestones
- **WHEN** a project has both 事業計畫 and 權利變換 nodes with different case_ids
- **THEN** the 事業計畫 node shows its milestones, the 權利變換 node shows its own

#### Scenario: Node emits its anchored case's own 核定日期, not the merged chimera
- **WHEN** the family 中山區-中山段一小段-254地號等13筆 has case 09811141 (核定 2012/08/27, anchored to node 1219) and case 09811142 (核定 2016/08/23 — the last-fetched, hence merged-dict winner)
- **THEN** node 1219's `links.milestones_taipei.核定日期` is `2012/08/27` (its own case), not `2016/08/23`

#### Scenario: Fallback to merged dict when the anchored case has no per-case timeline
- **WHEN** the family 中山區-中山段一小段-254地號等13筆 has case 09811141 (核定 2012/08/27, anchored to node 1219) and case 09811142 (核定 2016/08/23 — the last-fetched, hence merged-dict winner)
- **THEN** node 1219's `links.milestones_taipei.核定日期` is `2012/08/27` (its own case), not `2016/08/23`

#### Scenario: Fallback to merged dict when the anchored case has no per-case timeline
- **WHEN** a node's anchored case has no `case_milestones` entry (legacy cache without per-case data)
- **THEN** the node's `links.milestones_taipei` falls back to the project-level merged `milestones_taipei` (current behavior preserved)

#### Scenario: Project-level merged dict is unchanged
- **WHEN** the per-node emission fix runs
- **THEN** the project-level `links.milestones_taipei` (chimera, with `milestones_source` provenance) is emitted as before — the 階段辦理過程 card and construction-chain provenance are unaffected

### Requirement: Progressive loading states

The system SHALL show loading indicators when milestone data is available from one portal but not the other.

#### Scenario: National data available, Taipei data pending
- **WHEN** `links.milestones_national` is populated but `links.milestones_taipei` is empty
- **THEN** "推動歷程" card renders normally
- **AND** "階段辦理過程" card shows a "載入中..." or "資料未取得" placeholder with the Taipei portal link

#### Scenario: Both portals have data
- **WHEN** both `links.milestones_national` and `links.milestones_taipei` are populated
- **THEN** both cards render fully with no loading indicators

#### Scenario: Combined-track node renders per-track stages
- **WHEN** node 1 (2026-08-11) of 中正區-臨沂段一小段-507 derives stage_事業計畫 = 變更 and stage_權利變換 = 變更(第二次) (per-track derivation, data-cleansing delta)
- **THEN** the node label reads `1 · 2026-08-11 變更/變更(第二次)` and the table 階段 column shows the same
- **AND** uniform-ordinal or single-track nodes keep the single-stage form

### Requirement: Execution events render once, sourced from records or ghost anchors

The history graph SHALL render each execution date (建照核發日期 / 開工日期 / 使照核發日期) exactly once, in the shared execution column. An execution date whose provenance is an orphan case (non-PDF, no anchor record) SHALL NOT be duplicated in the ghost column; instead, the orphan's dashed-circle ghost anchor node connects to that event with a slanted solid pink source edge, exactly as anchored records do.

#### Scenario: 建照核發日期 renders once with its orphan source
- **WHEN** 建照核發日期 2022/02/17 is attributed to orphan case 09907221 in 文山區-木柵段三小段-623地號等39筆
- **THEN** the graph shows a single 建照核發日期 event, connected to the 09907221 dashed-circle anchor by a slanted solid pink edge
- **AND** no second 建照核發日期 appears in the ghost column

#### Scenario: Ghost anchors without construction dates render bare
- **WHEN** an orphan ghost anchor's payload contains no execution dates (e.g., 09907223)
- **THEN** only its dashed-circle anchor node renders in the ghost column

### Requirement: Source-colored edge semantics for execution events

The history graph SHALL link execution events to their sources with portal-colored edges: (1) each source group's earliest event receives a slanted solid `event-edge` (pink `taipei` / green `national`) from its source — the anchored record node, or the orphan's ghost anchor; national-fallback groups attach to the 現況 record; (2) adjacent events of the SAME source connect by a vertical solid `event-link` in the group's color; (3) adjacent events of DIFFERENT sources connect by a vertical dashed `event-link` in the incoming group's color (pink for Taipei cases, green for the national fallback). Timeline rows (records and events) SHALL use half the previous vertical pitch so records and execution dates sit close together.

#### Scenario: Source edge slants from record to the group's earliest event
- **WHEN** a source group's earliest execution event has anchored provenance (e.g., 開工日期 2022/08/26 matching implementation case 09907222 anchored to recno 829)
- **THEN** a slanted pink `event-edge` connects the recno-829 node to that event

#### Scenario: Same-source chain connects vertically solid
- **WHEN** a project's three execution dates share one source (e.g., 北投區-振興段四小段-166-2地號等34筆: 建照 2020/12/08, 開工 2021/02/20, 使照 2025/04/15 all from case 10211302)
- **THEN** 建照→開工 and 開工→使照 connect by vertical solid pink `event-link`s, with one slanted source edge from the owning record to the earliest event

#### Scenario: Cross-source transition connects vertically dashed
- **WHEN** the last event of one source group and the first event of a different source group are adjacent
- **THEN** they connect by a vertical dashed `event-link` in the incoming group's color

#### Scenario: Timeline rows use the compact pitch
- **WHEN** a project graph renders records and execution events
- **THEN** consecutive timeline rows are separated by half the previous vertical pitch (32px, down from 64px)

