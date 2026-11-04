## MODIFIED Requirements

### Requirement: Capture per-case schedule from the search response

Every discovered case's lifecycle status SHALL be observable per case_id: the viewer SHALL be able to display each case's schedule (已核准 / 已核定 / 已駁回 /
自行撤回 / 已失效 / 審查中 / 施工中) per case. To provide this, the pipeline SHALL
retain the search response's per-case `schedule` (`case_schedules`) alongside
`candidate_names`, and for cases discovered outside the parcel search SHALL
derive it from `get_project168_top.ashx` `phase`/`NAME` outcome. The former
family-level "never-approved" classification is a viewer concern only and is
retired there (viewer-related-links delta, user decision 2026-11-05, board
D4c); the per-case data is unchanged.

The `NAME` derivation SHALL read a case that is *waiting for* approval as in
review, not as approved: a `NAME` ending in a pending phrase (`…申請報府核定中`,
`…核定中`) SHALL derive 審查中, because the word 核定 occurs inside it (measured
2026-11-02: 中正段一小段-68's 10406283 reads 權利變換計畫階段─申請報府核定中 on
the platform and 審查中 in the city's own search list). A `NAME` that states no
outcome (`無`, empty) SHALL derive no schedule rather than a guessed one.

The implementation (third.ashx) construction dates — 開工日期 and 使照核發日期 —
SHALL follow the first 擬訂 plan case of the project (a case named
`擬訂…都市更新事業計畫案` or `擬訂…都市更新事業計畫及權利變換計畫案`), with that case as the
`milestones_source` of each date it supplies (the user rule 2026-11-04; the
city keeps 建照/開工/使照 on the plan case — measured on all 726 caches: 535 on
the plan case).

#### Scenario: A case waiting for approval derives 審查中

- **THEN** the case's derived schedule is 審查中

#### Scenario: Schedules are stored per case

- **WHEN** the search response returns two cases with schedules 已核准 and
  自行撤回
- **THEN** `links.case_schedules` holds both, keyed by case_id

#### Scenario: A nameless response derives no schedule

- **WHEN** a case's header `NAME` is `無`
- **THEN** no schedule is derived for it
