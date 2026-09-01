## MODIFIED Requirements

### Requirement: Join links to projects by land-identity core

The system SHALL attach discovered links to projects and to individual record
nodes by the same land-identity key the merge step anchors on, so each node can
carry the case link for its own approval stage. Date-based node anchoring SHALL
match the node's 核定日期 against the case's approval milestone — which for the
事業計畫/權利變換 tracks is 核定日期/權變核定日期, and for the 事業概要 track is
**概要核准日期** (a 概要 case has no 核定日期; omitting this label silently
degrades 概要-node anchoring to the positional fallback). The date matcher SHALL
accept ROC (`97/1/2`), slash-Gregorian (`2008/01/02`) and ISO (`2008-01-02`)
forms — the PDF pipeline passes raw ROC dates.

#### Scenario: Per-stage city links land on the right node
- **WHEN** a project family contains both a 事業計畫 and a 權利變換 approval
- **THEN** the city case_id for each approval attaches to the corresponding node
- **AND** the shared national-portal link attaches at project level

#### Scenario: 概要 case anchors to its node via 概要核准日期
- **WHEN** a node's date is 2026-03-31 and the family's 概要 case carries
  `概要核准日期 = 2026/03/31` (no 核定日期 — the 概要 track)
- **THEN** the case anchors to that node (previously it fell to the positional
  fallback or stayed unanchored — 延吉段三小段727 shape, operations log §6.14)

#### Scenario: ROC gazette dates anchor correctly in the PDF pipeline
- **WHEN** the PDF pipeline passes the node date as a ROC string (`97/1/2`) and
  the case's 核定日期 is `2008/01/02`
- **THEN** the matcher normalizes both to ISO and anchors the case
  (previously every PDF-pipeline anchoring silently degraded to positional)

#### Scenario: Unresolvable projects are counted
- **WHEN** discovery completes over all projects
- **THEN** the review report lists the number and identities of projects with no resolved link

## ADDED Requirements

### Requirement: Capture per-case schedule from the search response

Every discovered case's lifecycle status SHALL be observable per case_id: the viewer SHALL be able to display each case's schedule (已核准 / 已駁回 /
自行撤回 / 已失效 / 審查中 / 施工中), and a project whose every case is
已駁回 / 自行撤回 / 業已失效 SHALL be distinguishable as never-approved (the
national portal will never list it). To provide this, the pipeline SHALL
retain the search response's per-case `schedule` (`case_schedules`) alongside
`candidate_names`, and for cases discovered outside the parcel search SHALL
derive it from `get_project168_top.ashx` `phase`/`NAME` outcome.

#### Scenario: Rejected and withdrawn 概要 attempts keep their status
- **WHEN** a project's parcel search returns 11207021 (已駁回) and 11302031
  (自行撤回) for the same 概要 unit (民生段140-9 shape)
- **THEN** both case_ids are retained with their schedules and the viewer can
  render 擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案 — 已駁回 / — 自行撤回

#### Scenario: Schedule explains a missing national-portal page
- **WHEN** every case of a project is 已駁回 / 自行撤回 / 業已失效 (never
  approved), and the project therefore has no twur link
- **THEN** the viewer and ledger classify the project as never-approved rather
  than as an unexplained no-match
