## MODIFIED Requirements

### Requirement: Never-approved classification is dropped from the viewer

The viewer SHALL keep per-case schedule display in 相關連結 (per-case badges
are a different signal from family-level ones), but SHALL NOT classify a
project as never-approved: the "未曾核定（已駁回/自行撤回/已失效）— 無國土管理署入口網頁"
note and its `never-approved`-family special case are removed (user decision
2026-11-05, board D4c — a gazette family holds a gazette approval by
construction, and the 4 projects the note named all carry an approved current
node). A project whose `links.twur` is empty simply shows its 相關連結 list
without the note.

#### Scenario: Rejected/withdrawn 概要 attempts show their status
- **WHEN** `links.case_schedules` = `{"11207021": "已駁回", "11302031": "自行撤回"}` (民生段140-9 shape)
- **THEN** 相關連結 shows "…土地事業概要案 — 已駁回" and "…土地事業概要案 — 自行撤回"
- **AND** no family-level "never approved" note renders

#### Scenario: A project with no twur link shows no explanatory note
- **WHEN** `links.twur` is empty, whatever its cases' schedules
- **THEN** 相關連結 lists the cases (and the city-platform fallback) with no
  "未曾核定" note

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
