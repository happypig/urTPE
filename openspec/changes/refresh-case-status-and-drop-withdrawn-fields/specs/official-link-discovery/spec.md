## MODIFIED Requirements

### Requirement: Capture per-case schedule from the search response

Every discovered case's lifecycle status SHALL be observable per case_id: the viewer SHALL be able to display each case's schedule (已核准 / 已核定 / 已駁回 /
自行撤回 / 已失效 / 審查中 / 施工中), and a project whose every case is
已駁回 / 自行撤回 / 業已失效 SHALL be distinguishable as never-approved (the
national portal will never list it). To provide this, the pipeline SHALL
retain the search response's per-case `schedule` (`case_schedules`) alongside
`candidate_names`, and for cases discovered outside the parcel search SHALL
derive it from `get_project168_top.ashx` `phase`/`NAME` outcome.

The `NAME` derivation SHALL read a case that is *waiting for* approval as in
review, not as approved: a `NAME` ending in a pending phrase (`…申請報府核定中`,
`…核定中`) SHALL derive 審查中, because the word 核定 occurs inside it (measured
2026-11-02: 中正段一小段-68's 10406283 reads 權利變換計畫階段─申請報府核定中 on
the platform and 審查中 in the city's own search list). A `NAME` that states no
outcome (`無`, empty) SHALL derive no schedule rather than a guessed one.

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

#### Scenario: A case waiting for approval derives 審查中
- **WHEN** a case's `get_project168_top.ashx` `NAME` is
  `權利變換計畫階段─申請報府核定中` or `事業計畫及權利變換計畫階段─申請報府核定中`
- **THEN** its derived schedule is 審查中, not 已核准

#### Scenario: An approved case still derives the approved state
- **WHEN** a case's `NAME` is `事業計畫階段─業經本府核定`
- **THEN** its derived schedule is 已核准

#### Scenario: A NAME with no outcome derives nothing
- **WHEN** a case's `NAME` is `無` or empty
- **THEN** no schedule is derived from it
