## MODIFIED Requirements

### Requirement: 相關連結 resolves case names for orphan case_ids via fallback chain

When rendering the 相關連結 debug section, the system SHALL resolve the case name for each case_id in `links.taipei` using the following fallback chain (real case names always take precedence over the synthetic milestone-context label):
1. Node-level: `node.links.taipei` → `node.case_name` (current behavior)
2. Ghost/virtual payloads: `links.orphan_nodes[].case_name` (harvested real names)
3. Project-level `links.candidate_names[cid]` (harvested search/case-header names; emitted since the 2026-08-29 pipeline fix)
4. Project-level `links.case_milestones` keys: if the case_id exists in `links.case_milestones`, use the associated milestone dates as context or infer the case name
5. Project-level `links.search_rejected`: if the case_id exists in `links.search_rejected`, use the stored case_name
6. If no name found, render the case_id without a name (current fallback)

When a case's `schedule` is known (from the search response or `top.ashx`, via `links.case_schedules`), the 相關連結 entry SHALL append the status badge — 已駁回 / 自行撤回 / 已失效 / 審查中 / 施工中 / 已完工 / 完成成果備查 (已核准 and 已核定 are the approved-family default focus state and their badge is omitted — the city's search list uses both words for an approved case, measured 739 / 14 in the cache on 2026-11-02, so hiding only one rendered the same status two ways) — so the case state is visible without leaving the viewer. When `links.superseded_by` names a case, its 相關連結 entry SHALL read `已由 <case_id> 取代` naming the successor, in place of a status badge, because the city re-filed that application under the successor and the old case has no current state of its own. A project whose every case is 已駁回 / 自行撤回 / 業已失效 SHALL surface "never approved — no national-portal page" as the reason it has no twur link.

#### Scenario: Orphan case_id in search_rejected gets its case name
- **WHEN** `links.search_rejected` contains `{"09907221": "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"}`
- **THEN** 相關連結 shows "臺北市都市更新審議服務平台 (case_id: 09907221) — 擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案"

#### Scenario: Harvested candidate_names precede the milestone-context label
- **WHEN** `links.candidate_names` has `{"09112120": "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案"}` and `links.case_milestones` also has an entry for 09112120
- **THEN** 相關連結 shows the real case name, NOT the synthetic "里程碑 N 筆" label

#### Scenario: Rejected/withdrawn 概要 attempts show their status
- **WHEN** `links.case_schedules` = `{"11207021": "已駁回", "11302031": "自行撤回"}` (民生段140-9 shape)
- **THEN** 相關連結 shows "…土地事業概要案 — 已駁回" and "…土地事業概要案 — 自行撤回"

#### Scenario: Never-approved project explains its missing twur link
- **WHEN** every case of the project is 已駁回 / 自行撤回 / 業已失效 and `links.twur` is empty
- **THEN** the detail pane surfaces "never approved — no national-portal page" instead of an unexplained absence

#### Scenario: Orphan with no fallback shows raw case_id
- **WHEN** an orphan case_id is absent from nodes, orphan_nodes, candidate_names, case_milestones, and search_rejected
- **THEN** 相關連結 shows "臺北市都市更新審議服務平台 (case_id: 09907223)" without a case name (current fallback behavior)

#### Scenario: Both approved-family words omit the badge
- **WHEN** `links.case_schedules` = `{"10406282": "已核定", "10011271": "已核准"}`
- **THEN** neither 相關連結 entry carries a status badge

#### Scenario: An in-review case shows its badge
- **WHEN** `links.case_schedules` = `{"10406283": "審查中"}`
- **THEN** the 相關連結 entry for 10406283 carries the badge `[審查中]`

#### Scenario: A superseded case names its successor

- **WHEN** `links.superseded_by` = `{"11211211": "11409026"}`
- **THEN** the 相關連結 entry for 11211211 reads `已由 11409026 取代`
- **AND** it carries no status badge
