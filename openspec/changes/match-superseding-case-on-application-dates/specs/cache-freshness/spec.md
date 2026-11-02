## MODIFIED Requirements

### Requirement: The targeted refresh selects caches awaiting an approval

The refresh pass SHALL select a project cache when at least one of its cases
carries an application-for-approval date, no approval date (`核定日期` /
`權變核定日期` / `概要核准日期`), and a cached status that is not terminal. The
application signal SHALL cover every application track — `申請核定日期` /
`權變申請核定日期` (approval applications) and `申請計畫日期` / `申請權變日期` /
`申請概要核准日期` (plan-change applications) — because a plan-change case
approved after the cache was written leaves the same absence (measured
2026-11-02: 北投區-關渡段二小段-303's 11505020 carries only 申請計畫日期/申請權變日期
in the cache while the API reports 核定日期 2026/09/30). A case whose cached
status is 自行撤回 / 已駁回 / 已失效 SHALL NOT make its project a candidate: such a
case was closed without approval and will never gain an approval date
(measured 2026-11-02: 85 of the 176 selected projects carried only such cases).
Nor SHALL a case whose last-read platform header reads `無`, or a case recorded
as superseded by another case: the city re-files an application under a new
case id and leaves the old one with no current state (measured 2026-11-02:
立農段五小段-163-2's 11211211 → 11409026, 虎林段四小段-38's 10806141 → 11510017).
It SHALL re-fetch the milestones for exactly the selected projects, SHALL
preserve every other field the cache already holds, SHALL re-run the national
view-page absorb so the cache gains `view_verified_case_ids` and any case ids
the page names that the parcel search missed, and SHALL report each project's
before/after approval dates so the effect is auditable. It SHALL NOT re-crawl
projects whose cached cases are all resolved.

A successful, non-empty milestone reply SHALL replace the case's cached
milestones, so a date the city has withdrawn leaves the cache (measured
2026-11-02: 士林區-光華段四小段-282's 11408032 kept 申請核定日期 2026/08/18 after the
platform dropped it). Every removed label SHALL be reported per case. A
removed **approval** date SHALL NOT be applied silently: it SHALL be kept and
reported as a conflict, because it decides a node's case binding. An empty
reply or a failed fetch SHALL leave the case's milestones unchanged.

The refresh SHALL also re-derive each refreshed case's status from the
platform's case header (`get_project168_top.ashx` `NAME`) and SHALL report every
status change with its old value, new value and the `NAME` it came from. The
re-derived status SHALL NOT replace a cached later stage (施工中 / 已完工 /
完成成果備查) with the approved state. A header that exists and reads `無` (or has
an empty `NAME`) states that the case has no current state: it SHALL clear a
cached 審查中 or approved-family status (已核准 / 已核定) and SHALL keep a terminal
status (自行撤回 / 已駁回 / 已失效) or a later stage, because a withdrawn case stays
withdrawn and clearing it could hide a project's never-approved reason. A header
that names an unrecognised outcome SHALL keep the cached status, except that a
cached approved-family status on a case whose own milestones carry no approval
date SHALL be cleared. A missing header row is no evidence and SHALL change
nothing. The refresh SHALL record the header `NAME` it read per case in the
cache, so the offline selection can see it.

For a case whose header reads `無`, the refresh SHALL record which case
superseded it when exactly one other case of the project has the identical
header case name, a numerically greater case id, and the same date for every
application date the `無` case carries (`申請核定日期` / `權變申請核定日期` /
`申請計畫日期` / `申請權變日期` / `申請概要核准日期`), the `無` case carrying at
least one application date and at least three dated labels. Other dates MAY
differ, because a re-filed case re-runs later steps (measured 2026-11-02:
雅祥段一小段-227-4's 11009142 → 11510001 held its public exhibition again;
吉林段四小段-705-3's 10410012 → 11503012 records a different 召開幹事會日期); the
report SHALL name every dated label of the `無` case whose date the successor
does not share. When several cases qualify the refresh SHALL report the case
as ambiguous and record nothing. A `無` case with no qualifying case SHALL be
reported by name as having no successor found.

Before re-reading its cases, the refresh SHALL repeat the parcel search the
project's discovery used — the anchor record's 地段, first 地號 and 案名, with the
same name guard — and SHALL append every case id it returns that the cache does
not hold to the end of the cache's case list, without re-ordering the existing
ids, because the positional fallback binds by index. Each added case SHALL be
re-read like the others and reported with its search status and header. A
failed search SHALL be reported as a failure of that project, not as a search
that found nothing; a project with no anchor 地段 / 地號 SHALL be reported as not
searched.

The run report SHALL list cases closed without approval, cases superseded (with
their successor), `無` cases with no successor found, ambiguous cases, and added
cases, each separately from cases still awaiting approval.

#### Scenario: A project's case has since been approved

- **WHEN** a cached case holds 申請核定日期 but no 核定日期， and the city's API now
  reports a 核定日期 for it
- **THEN** the refresh updates that case's milestones in place
- **AND** reports the project with the old and new approval dates
- **AND** every other cached field is preserved

#### Scenario: A plan-change application has since been approved (303 shape)

- **WHEN** a cached case holds only 申請計畫日期 / 申請權變日期 with no approval date,
  and the API now reports 核定日期 for it
- **THEN** the refresh selects the project and updates the case's milestones in place

#### Scenario: A project's cases are all resolved

- **WHEN** every cached case carries an approval date
- **THEN** the project is not selected and is not re-fetched

#### Scenario: A project's case is still awaiting approval

- **WHEN** a cached case holds an application date, no approval date, and the API still
  reports none
- **THEN** the case's approval state is unchanged
- **AND** the project is reported as still awaiting approval

#### Scenario: The refresh backfills the view-verified case list

- **WHEN** the refresh runs on a cache whose `view_verified_case_ids` is absent (a
  cache predating the field) and the project has a national view page
- **THEN** the refreshed cache carries `view_verified_case_ids` — the case ids the
  page's 相關連結 block names
- **AND** any named case the parcel search missed is added to `city_case_ids` with its
  milestones fetched

#### Scenario: A project whose awaiting cases were all closed is not selected

- **WHEN** a project's only awaiting cases are cached as 自行撤回 or 已駁回
  (南海段一小段-687 11012301, 信義段二小段-142 11105301, 三玉段一小段-672 09812232)
- **THEN** the project is not selected and is not re-fetched

#### Scenario: One open awaiting case keeps the project selected

- **WHEN** a project has one awaiting case cached as 自行撤回 and another awaiting
  case cached as 審查中
- **THEN** the project is selected

#### Scenario: A date the city withdrew leaves the cache

- **WHEN** a cached case holds 申請計畫日期 and 申請核定日期, and the API now reports
  only 申請計畫日期 (光華段四小段-282 shape)
- **THEN** the refreshed case holds only 申請計畫日期
- **AND** the report names 申請核定日期 as removed for that case

#### Scenario: A withdrawn approval date is a conflict, not an edit

- **WHEN** a cached case holds 核定日期 and the API's non-empty reply lacks it
- **THEN** the cached 核定日期 is kept
- **AND** the report names the case and the date as a conflict

#### Scenario: An empty reply changes nothing

- **WHEN** the API returns no milestones for a cached case, or the fetch fails
- **THEN** the case's cached milestones are unchanged

#### Scenario: An in-review case's stale approved status is corrected

- **WHEN** a cached case's status is 已核准, it has no approval date, and its header
  `NAME` is `權利變換計畫階段─申請報府核定中` (中正段一小段-68 10406283)
- **THEN** its refreshed status is 審查中
- **AND** the report names the case, 已核准 → 審查中 and the `NAME`

#### Scenario: A 無 header clears an in-review status

- **WHEN** a cached case's status is 審查中 and its header `NAME` is `無`
  (立農段五小段-163-2 11211211)
- **THEN** its status is cleared, and the report names the change and the `NAME`

#### Scenario: A 無 header clears an approved status

- **WHEN** a cached case's status is 已核准 and its header `NAME` is `無`
  (虎林段四小段-38 10806141)
- **THEN** its status is cleared

#### Scenario: A 無 header keeps a terminal status

- **WHEN** a cached case's status is 自行撤回 (or 已駁回 / 已失效) and its header
  `NAME` is `無`
- **THEN** its status stays 自行撤回

#### Scenario: A missing header row changes nothing

- **WHEN** the header call returns no row for a case
- **THEN** its cached status is unchanged and no header is recorded

#### Scenario: An outcome-less NAME keeps a consistent cached status

- **WHEN** a cached case's status is 審查中 and its header `NAME` names no recognised
  outcome (not `無` — a `無` header clears it, see above; this scenario's archived
  form used 立農段五小段-163-2 11211211, whose `無` was later measured to mean a
  superseded copy)
- **THEN** its status stays 審查中

#### Scenario: An outcome-less NAME clears a contradicted approved status

- **WHEN** a cached case's status is 已核准, its own milestones carry an application
  date and no approval date, and its header `NAME` names no recognised outcome
- **THEN** its status is cleared, and the report names the change

#### Scenario: A re-filed case is recorded as superseded

- **WHEN** a case's header reads `無`, and one other case of the project has the same
  header case name, a greater case id, and milestones containing all of the first
  case's dated labels with the same dates (11211211 → 11409026)
- **THEN** the cache records 11211211 as superseded by 11409026
- **AND** the report lists 11211211 as superseded by 11409026, not as awaiting

#### Scenario: A different case name is not a successor

- **WHEN** a `無` case's milestones are contained in another case's, but the header
  case names differ
- **THEN** no successor is recorded and the case is reported as having none

#### Scenario: Two qualifying successors are ambiguous

- **WHEN** two cases qualify as the successor of one `無` case
- **THEN** no successor is recorded and the case is reported as ambiguous

#### Scenario: A re-filed case whose later steps were re-run is recorded as superseded

- **WHEN** a case's header reads `無`, and one other case of the project has the same
  header case name, a greater case id and the same 申請計畫日期 / 申請權變日期, but
  different 公告公展日期 (11009142 → 11510001)
- **THEN** the cache records 11009142 as superseded by 11510001
- **AND** the report names 公告公展日期 among the dates that differ

#### Scenario: A different application date is not a successor

- **WHEN** a `無` case and a same-named, newer case differ in 申請計畫日期
- **THEN** no successor is recorded

#### Scenario: A case without an application date is not matched

- **WHEN** a `無` case carries no application date
- **THEN** no successor is recorded

#### Scenario: A sparse case is not matched

- **WHEN** a `無` case carries fewer than three dated labels
- **THEN** no successor is recorded

#### Scenario: A 無 or superseded case does not make its project a candidate

- **WHEN** a project's only awaiting case has a recorded header `無`, or is recorded
  as superseded
- **THEN** the project is not selected

#### Scenario: The refresh finds a case filed after the cache was written

- **WHEN** the parcel search for 虎林段四小段 38 returns 11510017, which the cache
  does not hold
- **THEN** 11510017 is appended after the existing case ids, in their old order
- **AND** its milestones and header are read, its status is 審查中
- **AND** 10806141 is recorded as superseded by 11510017
- **AND** the report lists 11510017 as added

#### Scenario: A failed search is a failure

- **WHEN** the parcel search raises for a selected project
- **THEN** the project is reported as failed, and its cache is unchanged

#### Scenario: A later cached stage is never downgraded

- **WHEN** a cached case's status is 施工中 (or 已完工 / 完成成果備查) and its header
  `NAME` is `事業計畫階段─業經本府核定`
- **THEN** its status stays 施工中

#### Scenario: The production refresh re-derives the status

- **WHEN** the refresh runs with its default platform adapters (no fetcher injected)
- **THEN** the case status is re-derived from the case header, not only the milestones
- **AND** the parcel search runs, so a newly filed case id is appended

#### Scenario: The report separates closed cases from awaiting ones

- **WHEN** a selected project's refreshed case header reads `…實施者自行撤回`
- **THEN** the run report lists that case as closed without approval, not as still
  awaiting approval
