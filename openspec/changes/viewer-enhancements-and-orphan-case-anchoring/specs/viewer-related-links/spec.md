## MODIFIED Requirements

### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place: each approval node with an anchored Taipei case SHALL expose its 北 badge as a hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge hyperlink to the project's national view page when one exists; and each construction-event node SHALL label as a hyperlink to its source portal — Taipei case page (pink) when Taipei-sourced, national view page (green) when national-mapped. The standalone 相關連結 section SHALL be retired behind an explicit debug toggle that defaults to hidden.

#### Scenario: Approval node links to its anchored case
- **WHEN** a record anchors to Taipei case 09804142
- **THEN** that node's 北 badge opens `r_progress_detail.aspx?case_id=09804142` in a new tab

#### Scenario: Current node links to the national view
- **WHEN** the project has a national view URL
- **THEN** the 現況 node's 國 badge opens the twur view page in a new tab

#### Scenario: Link section hidden by default, available for debugging
- **WHEN** the detail pane renders
- **THEN** no 相關連結 list appears unless the user explicitly enables the 除錯 toggle, which reveals the full link list (with 案名 annotations) for debugging purposes

### ADDED Requirements

### Requirement: 相關連結 resolves case names for orphan case_ids via fallback chain

When rendering the 相關連結 debug section, the system SHALL resolve the case name for each case_id in `links.taipei` using the following fallback chain (real case names always take precedence over the synthetic milestone-context label):
1. Node-level: `node.links.taipei` → `node.case_name` (current behavior)
2. Ghost/virtual payloads: `links.orphan_nodes[].case_name` (harvested real names)
3. Project-level `links.candidate_names[cid]` (harvested search/case-header names; emitted since the 2026-08-29 pipeline fix)
4. Project-level `links.case_milestones` keys: if the case_id exists in `links.case_milestones`, use the associated milestone dates as context or infer the case name
5. Project-level `links.search_rejected`: if the case_id exists in `links.search_rejected`, use the stored case_name
6. If no name found, render the case_id without a name (current fallback)

When a case's `schedule` is known (from the search response or `top.ashx`, via `links.case_schedules`), the 相關連結 entry SHALL append the status badge — 已駁回 / 自行撤回 / 已失效 / 審查中 / 施工中 (已核准 is the default focus state and its badge is omitted) — so the case state is visible without leaving the viewer. A project whose every case is 已駁回 / 自行撤回 / 業已失效 SHALL surface "never approved — no national-portal page" as the reason it has no twur link.

#### Scenario: Rejected/withdrawn 概要 attempts show their status
- **WHEN** `links.case_schedules` = `{"11207021": "已駁回", "11302031": "自行撤回"}` (民生段140-9 shape)
- **THEN** 相關連結 shows "…土地事業概要案 — 已駁回" and "…土地事業概要案 — 自行撤回"

#### Scenario: Never-approved project explains its missing twur link
- **WHEN** every case of the project is 已駁回 / 自行撤回 / 業已失效 and `links.twur` is empty
- **THEN** the detail pane surfaces "never approved — no national-portal page" instead of an unexplained absence

### Requirement: 相關連結 lists case_ids in ascending order

The 相關連結 debug list SHALL render `links.taipei` in **case_id ascending order** regardless of platform search-response order (corpus audit 2026-08-31: 91/564 multi-id arrays unsorted, 34 adjacent swaps = platform order drift). At attach time the pipeline SHALL emit `links.taipei` case_id-ascending, so the 相關連結 list, the graph row order (family-wide case_id interleave), and the platform search order agree by construction. Anchored assignments (`node.links.taipei`) are unaffected — sorting the project-level list never re-anchors cases.

#### Scenario: Platform order drift is normalized
- **WHEN** discovery returns `["10906091", "11403002", "10906092"]` for a family (platform-order, not ascending)
- **THEN** the emitted `links.taipei` is `["10906091", "10906092", "11403002"]` and 相關連結 lists them in that order

### ADDED Requirements

### Requirement: Gazette stage anomalies surface as review flags

When the gazette PDF's printed 階段 disagrees with the platform's recorded case state for the anchored case (e.g. 吉林段四小段603 node 920 dated 2018-01-25: the gazette prints 擬訂 but the platform case 09511214 is a 變更 已核准), the record SHALL carry a review flag (案名階段與平台案件狀態不一致 — gazette printing anomaly candidate) instead of silently keeping the stage unexamined. Stage parsing remains faithful to the PDF text; the flag routes the row to human review.

#### Scenario: Gazette 擬訂 anomaly is flagged, not corrected
- **WHEN** a node's printed 階段 is 擬訂 but its anchored case's platform name is 變更… with an approval outcome
- **THEN** the node keeps the printed stage and carries a review flag naming the disagreement
- **AND** no parser rewrite changes the emitted stage for the flagged row

#### Scenario: Orphan case_id in search_rejected gets its case name
- **WHEN** `links.search_rejected` contains `{"09907221": "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"}`
- **THEN** 相關連結 shows "臺北市都市更新審議服務平台 (case_id: 09907221) — 擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"

#### Scenario: Harvested candidate_names precede the milestone-context label
- **WHEN** `links.candidate_names` has `{"09112120": "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案"}` and `links.case_milestones` also has an entry for 09112120
- **THEN** 相關連結 shows the real case name, NOT the synthetic "里程碑 N 筆" label

#### Scenario: Orphan case_id in case_milestones gets context
- **WHEN** `links.case_milestones` has an entry for case_id 09907223 with its milestone dates
- **THEN** 相關連結 renders the case_id with any available context from the milestones

#### Scenario: Orphan with no fallback shows raw case_id
- **WHEN** an orphan case_id is absent from nodes, orphan_nodes, candidate_names, case_milestones, and search_rejected
- **THEN** 相關連結 shows "臺北市都市更新審議服務平台 (case_id: 09907223)" without a case name (current fallback behavior)