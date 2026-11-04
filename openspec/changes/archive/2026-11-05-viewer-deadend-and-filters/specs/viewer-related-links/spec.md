## MODIFIED Requirements

### Requirement: 相關連結 resolves case names for orphan case_ids via fallback chain

Each city case_id in `links.taipei` (and the orphan/ghost case_ids) SHALL
resolve its display name in 相關連結 via the fallback chain: the case's own
harvested city name (`links.candidate_names`), then the anchored node's 案名,
then the `links.case_milestones` context label (里程碑 N 筆), then the
`links.search_rejected` stored case_name, then the ghost node's case_name,
then the raw case_id. The national link is labelled by the national page's own
name (`links.twur_name`), falling back to the current node's 案名. Per-case
schedule badges render beside each case (已核准 / 已核定 render none — the
default state). D4c (user decision 2026-11-05, board D4c): the family-level
"未曾核定（已駁回/自行撤回/已失效）— 無國土管理署入口網頁" note is removed — a
gazette family holds a gazette approval by construction, and the 4 projects
the note named all carry an approved current node. A project whose
`links.twur` is empty simply shows its 相關連結 list without the note.

#### Scenario: Orphan case_id in search_rejected gets its case name
- **WHEN** `links.search_rejected` = `{"11207021": "擬訂臺北市…概要案"}` and
  相關連結 renders case_id 11207021
- **THEN** the entry is labelled 擬訂臺北市…概要案 (the stored city name)

#### Scenario: Harvested candidate_names precede the milestone-context label
- **WHEN** a case_id appears in both `links.candidate_names` and the
  `links.case_milestones` context
- **THEN** the harvested city name wins

#### Scenario: An anchored case is labelled by its own city name
- **WHEN** a node anchors two cases (the area-split binding) and both carry
  harvested names
- **THEN** each 相關連結 entry shows its own case's name, not the node's
  gazette 案名

#### Scenario: Two cases on one node read apart
- **WHEN** the area-split binding puts 11011241 (-A區) and 11011242 (-B區) on one node
- **THEN** 相關連結 shows two entries, each labelled by its own city name

#### Scenario: The harvest lacks the id — the gazette label stays the fallback
- **WHEN** a node anchors a case absent from `links.candidate_names`
- **THEN** 相關連結 labels it with the node's `case_name` as before

#### Scenario: The 國 label is the national page's own name
- **WHEN** `links.twur_name` is present
- **THEN** the 國 entry is labelled with it

#### Scenario: No cached page — the 國 label falls back
- **WHEN** `links.twur_name` is absent
- **THEN** the 國 entry is labelled with the current node's `case_name` as before

#### Scenario: Rejected/withdrawn 概要 attempts show their status
- **WHEN** `links.case_schedules` = `{"11207021": "已駁回", "11302031": "自行撤回"}` (民生段140-9 shape)
- **THEN** 相關連結 shows "…土地事業概要案 — 已駁回" and "…土地事業概要案 — 自行撤回"
- **AND** no family-level "never approved" note renders

#### Scenario: Never-approved project explains its missing twur link
- **WHEN** every case of the project is 已駁回 / 自行撤回 / 業已失效 and
  `links.twur` is empty
- **THEN** the 相關連結 lists the cases with their per-case badges and no
  family-level note (the note is removed; board D4c)

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
