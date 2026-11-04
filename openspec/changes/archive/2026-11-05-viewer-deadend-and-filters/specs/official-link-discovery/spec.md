## MODIFIED Requirements

### Requirement: Capture per-case schedule from the search response

Every discovered case's lifecycle status SHALL be observable per case_id: the viewer SHALL be able to display each case's schedule (已核准 / 已核定 / 已駁回 /
自行撤回 / 已失效 / 審查中 / 施工中). To provide this, the pipeline SHALL
retain the search response's per-case `schedule` (`case_schedules`) alongside
`candidate_names`, and for cases discovered outside the parcel search SHALL
derive it from `get_project168_top.ashx` `phase`/`NAME` outcome. The former
family-level "never-approved" classification (a project whose every case is
已駁回 / 自行撤回 / 業已失效力 read as never-approved) is retired from the
viewer (viewer-related-links delta, user decision 2026-11-05, board D4c); the
per-case data this requirement captures is unchanged.

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
the first plan case, 14 on a later plan case of an area split, 16 echoed). In
an area split each area's 擬訂 plan case SHALL supply its own building's dates
(榮星53: 北區 09001120, 南區 09001123). The one-payload statistics rule (D5)
SHALL keep governing the statistics fields — the emitted `implementation`
object stays the best-populated payload with its own `case_id`. A date field
no plan case carries SHALL fall back to the best-populated payload's value
with a review flag naming the carrier (3 cases corpus-wide); a field carried
by 2+ plan cases with differing values SHALL surface a conflict flag.

#### Scenario: Rejected and withdrawn 概要 attempts keep their status
- **WHEN** a project's parcel search returns 11207021 (已駁回) and 11302031
  (自行撤回) for the same 概要 unit (民生段140-9 shape)
- **THEN** both case_ids are retained with their schedules and the viewer can
  render 擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案 — 已駁回 / — 自行撤回

#### Scenario: Schedule explains a missing national-portal page
- **WHEN** every case of a project is 已駁回 / 自行撤回 / 業已失效 (never
  approved), and the project therefore has no twur link
- **THEN** the per-case schedules are retained and shown per case (the
  family-level never-approved classification is retired from the viewer;
  board D4c)

#### Scenario: A case waiting for approval derives 審查中
- **WHEN** a case's `get_project168_top.ashx` `NAME` is 權利變換計畫階段─申請報府核定中
- **THEN** the case's derived schedule is 審查中

#### Scenario: An approved case still derives the approved state
- **WHEN** a case's `NAME` ends 業經本府核定
- **THEN** the case's derived schedule is the approved state

#### Scenario: A NAME with no outcome derives nothing
- **WHEN** a case's `NAME` reads 無 or is empty
- **THEN** no schedule is derived for the case

#### Scenario: The plan case's 開工/使照 are emitted with the plan case as source
- **WHEN** a project's data3 payloads hold 開工日期 2012/07/13 and 使照核發日期
  2015/07/13 on the first 擬訂 plan case 09710240, and a later 變更 case
  09710242 carries more statistics
- **THEN** `milestones_taipei` carries 開工日期 2012/07/13 and 使照核發日期
  2015/07/13 with `milestones_source` naming 09710240 (德惠573 shape —
  previously dropped, the project read as national-only)

#### Scenario: An area split takes each area's plan case dates
- **WHEN** two 擬訂 plan cases -A區 and -B區 exist and -A區 carries 開工日期
- **THEN** the date comes from -A區's payload; -B區's differing own dates join
  theirs (榮星53 shape)

#### Scenario: A date no plan case carries falls back with a flag
- **WHEN** no 擬訂 plan case payload carries 使照核發日期 and a 權利變換 case does
- **THEN** the date is taken from that case with a review flag naming it
  (pre-2000 仁愛114 shape)
