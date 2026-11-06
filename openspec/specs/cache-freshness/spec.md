# cache-freshness Specification

## Purpose

How the pipeline notices that a link cache predates the gazette it is emitting
for, and how a targeted refresh re-derives the case milestones such a cache is
missing — so a newly approved case is bound to its record instead of falling to
the positional fallback.
## Requirements
### Requirement: A cache written before the gazette is reported

The system SHALL report, in the run output, how many project caches were last
written before the publication date being emitted for, because such a cache's
case milestones were captured before any approval published since. The signal
SHALL be the cache file's last-write time: a project cache stores no publication
date field (measured 2026-11-02 — none of the 726 caches carries one), so a
requirement phrased on a stored date would be inert on every real cache. The
report SHALL NOT refresh anything: a refresh is an explicit act, separate from
emission.

#### Scenario: Caches predate the gazette being emitted

- **WHEN** an emission runs for a gazette and project caches were last written before that publication date
- **THEN** the run reports how many caches predate it, and names the refresh command
- **AND** the emission proceeds — the report is informational, not a refusal

#### Scenario: A cache was written on or after the gazette

- **WHEN** a project cache was last written on or after the gazette being emitted
- **THEN** it is not counted as predating it

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
cache, so the offline selection can see it, and SHALL record the header's
`uro_chk_date` / `uro_chk_date2` beside the `NAME` when the header carries
them, so the node resolver can read the header as a second approval source
offline (the city's data2 sometimes copies another case's approval date —
玉泉11's 09504263, 吉林705's 09307104).

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
same name guard — and SHALL append every case id it returns that the cache
does not hold to the end of the cache's case list, without re-ordering the
existing ids. Each added case SHALL be re-read like the others and reported
with its search status and header. A failed search SHALL be reported as a failure of that project, not as a search
that found nothing; a project with no anchor 地段 / 地號 SHALL be reported as not
searched. The refresh's added cases and the resolver's probe/search finds
share one rule: a case id is appended, never inserted, and a later emission
binds nodes to cases by the resolver's name-and-date steps, not by list
position.

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

- **WHEN** a cached case holds 申請計畫日期 and 申請核定日期， and the API now reports
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

- **WHEN** a cached case's status is 已核准， it has no approval date, and its header
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

- **WHEN** a cached case's status is 已核准， its own milestones carry an application
  date and no approval date, and its header `NAME` names no recognised outcome
- **THEN** its status is cleared, and the report names the change

#### Scenario: A re-filed case is recorded as superseded

- **WHEN** a case's header reads `無`， and one other case of the project has the same
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

- **WHEN** a case's header reads `無`， and one other case of the project has the same
  header case name, a greater case id and the same 申請計畫日期 / 申請權變日期， but
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

- **WHEN** a project's only awaiting case has a recorded header `無`， or is recorded
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

#### Scenario: The refresh stores the header's approval dates beside the NAME

- **WHEN** the header fetch returns a row whose `uro_chk_date` is 2013-08-20 while
  the case's data2 核定日期 reads 2008/05/15 (玉泉11's 09504263)
- **THEN** the refreshed cache records the header dates for that case
- **AND** the node resolver can bind the case by the header date on the next
  emission, without a request

### Requirement: The refreshed binding replaces the positional fallback for the affected nodes

After a refresh, an emission SHALL bind each affected node to the case whose
approval date matches the node's own date, and SHALL NOT bind it to the
positional fallback, because the previously-missing approval date is now present.

#### Scenario: A newly approved case's node is bound by date

- **WHEN** a node's date equals the approval date the refresh recovered for its case
- **THEN** the node's anchored case is that case
- **AND** the graph's row order for the family follows the nodes' dates ascending

### Requirement: The emitted payload carries the view-verified case list

The pipeline SHALL emit `links.view_verified_case_ids` — the case ids the
project's own national view page names in 相關連結， identity-verified by the
portal itself — into the payload at project level beside `case_schedules`, so
the viewer can distinguish cases the national page asserts from cases only
the parcel search returned. A discovery result without the field (legacy
cache) emits without the key.

#### Scenario: The view page names a case

- **WHEN** 北投區-關渡段二小段-303's national view page view/621 names cases 10803151
  and 10105152 in its 相關連結 block
- **THEN** the payload's `links.view_verified_case_ids` contains both ids

#### Scenario: A legacy cache without the field

- **WHEN** a project's cache predates the field and carries no
  `view_verified_case_ids`
- **THEN** the payload emits without the key and nothing fails

### Requirement: The emitted payload carries the replaced-case map

The pipeline SHALL emit `links.superseded_by` — `{old case_id: new case_id}` as
the refresh recorded it — at project level beside `case_schedules`, and SHALL
carry it unchanged through a `--from-js` reload, because the payload is both the
viewer's input and the next run's input. A result without the map emits without
the key.

#### Scenario: A superseded case reaches the payload

- **WHEN** a project's cache records 11211211 as superseded by 11409026
- **THEN** the payload's `links.superseded_by` is `{"11211211": "11409026"}`

#### Scenario: The map survives a reload

- **WHEN** a payload carrying `links.superseded_by` is reloaded with `--from-js` and
  emitted again
- **THEN** the second payload carries the same `links.superseded_by`

#### Scenario: A legacy cache without the map

- **WHEN** a cache carries no `superseded_by`
- **THEN** the payload emits without the key and nothing fails

### Requirement: The refresh verifies view-verified ids by the city's own case name

The refresh SHALL verify every id in the cache's `view_verified_case_ids` against the city's own case name for that id (get_project168_top `CASE_NAME`, persisted per case), deciding by the land core at `LINK_THRESHOLD = 0.7` against the cache's own land core: match → keep; no match → remove the id from `view_verified_case_ids` and record it in `view_rejected` with its reason (shape A / shape B); the 相關連結 label is compared only for the reason text, and a label mismatch with a matching city name SHALL NOT reject. A missing city name SHALL NOT reject. The verification SHALL run on every cache holding `view_verified_case_ids`, whether or not its cases await an approval, because the defect does not depend on the awaiting state.

#### Scenario: A fully-approved cache is still verified

- **WHEN** a cache holds `view_verified_case_ids` but no case awaits an approval (the awaiting-approval selector would skip it)
- **THEN** the view-verified verification still runs on it

#### Scenario: Shape B rejection is recorded

- **WHEN** the city's own case name for a view-verified id names another project while the label matches (09511211 on 大安區-大安段一小段-557)
- **THEN** the id leaves `view_verified_case_ids`
- **AND** `view_rejected[09511211]` records reason "label is right, id is wrong (shape B)"

#### Scenario: The verification does not depend on the awaiting state

- **WHEN** the refresh runs on a cache whose only defect is a foreign view-verified id
- **THEN** the id is verified and recorded even though no milestone changed

### Requirement: The refresh records CASE_NAME per case

The refresh SHALL persist the header row's `CASE_NAME` (the city's own case name, distinct from the `NAME` state field) into the refreshed cache per case, so the view-verified verification and the offer step can decide offline after the run.

#### Scenario: CASE_NAME reaches the cache

- **WHEN** the header fetch returns a row whose `CASE_NAME` is the city's case name
- **THEN** the refreshed cache carries it for that case id
- **AND** a later `--from-js` reload preserves it

### Requirement: A rejected view-verified id is offered to its own project

After the verification pass, for each rejected id whose city-name land core matches exactly one other project's cache land core at `LINK_THRESHOLD = 0.7`, the system SHALL add the id to that project's `city_case_ids` (appended, never re-ordered — the positional fallback binds by index), fetch its milestones when the target cache does not hold them, and record the move as `adopted_from_view[cid] = source_project_id` on the target cache, with the source recording the rejection. When no other project matches, the id stays only in `view_rejected`. When more than one project matches, the system SHALL NOT guess: the id stays only in `view_rejected` with reason "ambiguous owner" — the same rule `data/project_aliases.json` applies to ambiguous pairs. The move SHALL happen under the same single-writer lock and in the same run that writes the source cache. Matching SHALL use the land core, never 編號 or `project_id` (both churn).

#### Scenario: A rejected id lands on its owning project

- **WHEN** rejected id 10202065's city name (大安區辛亥段一小段163地號等5筆) matches exactly one other cache's land core
- **THEN** 10202065 is appended to that cache's `city_case_ids`
- **AND** the target records `adopted_from_view["10202065"] = "中山區-中山段一小段-254地號等13筆"`
- **AND** the run report names the move for both projects

#### Scenario: An id the target already holds is not duplicated

- **WHEN** the offered id is already in the target cache's `city_case_ids` (09807161 → 內湖區-康寧段二小段-262 already holds it)
- **THEN** the id is not appended twice
- **AND** the target still records `adopted_from_view` and the report names the move

#### Scenario: An ambiguous owner is not guessed

- **WHEN** a rejected id's city-name land core matches two or more other caches
- **THEN** no cache is modified
- **AND** `view_rejected` records reason "ambiguous owner"

#### Scenario: No matching project

- **WHEN** a rejected id's city-name land core matches no other cache
- **THEN** the id stays only in `view_rejected`

### Requirement: The report names every rejection and offer

The run report SHALL name every rejected view-verified id with its reason and shape, every id offered to another project with both project ids, and every label error accepted under decision-table row 4, each with counts, the same way truncated records are named and counted — a rejection that vanished silently would read as a complete dataset.

#### Scenario: The report names the three §8 rejections

- **WHEN** the pass runs over the 2026-11-04 corpus
- **THEN** the report names 10202065, 09511211 and 09807161 as rejected with their shapes
- **AND** names 10906092 as accepted with a label error

#### Scenario: Every offer is named

- **WHEN** an id is offered to another project's cache
- **THEN** the report names the source project, the target project and the id

### Requirement: Case refresh records 無 / empty 目前辦理情形 as readable state

When 基本資料 / 目前辦理情形 reads 無, the refresh SHALL set the case's schedule
state to 「無」, and when the header row exists and 目前辦理情形 is empty, the
refresh SHALL set the state to 「NA」. The refresh SHALL keep these instead of
clearing the cached state to "". A missing header row ({}/None) remains "no
evidence" and SHALL keep the cached state.

**Reason**: 無 and empty are honest platform readings; clearing them hides
information that belongs on the per-case badge.

#### Scenario: 無 reading is stored as 「無」

- **WHEN** the case header NAME reads 無
- **THEN** case_schedules[cid] = 「無」 after refresh

#### Scenario: Empty reading is stored as 「NA」

- **WHEN** the case header row exists and NAME reads ""
- **THEN** case_schedules[cid] = 「NA」 after refresh

#### Scenario: Missing header keeps cached state

- **WHEN** the header fetch returns no row ({} / None)
- **THEN** case_schedules[cid] is unchanged

### Requirement: The emitted payload carries the national page's own name

The pipeline SHALL store the project's national view page `<title>` 案名 as `twur_name` in the cache and the emitted payload, parsed from the cached `view.html` at absorb time (re-parse, no request). The title is the portal's own name for the project — its first 擬訂 case — and the viewer labels the 國 entry with it (C10: 452 of 632 projects with a cached page showed the wrong name under the current-node rule). A cache without `view.html` emits without the key.

#### Scenario: twur_name reaches the payload
- **WHEN** a project's cached `view.html` `<title>` reads "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案-都更查詢-內政部國土管理署都市更新入口網"
- **THEN** `links.twur_name` carries "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案"

#### Scenario: A cache without a view page emits without the key
- **WHEN** the cache holds no `view.html`
- **THEN** the payload carries no `twur_name` key for the project

### Requirement: The whole-corpus refresh runs in resumable slices

The system SHALL provide a whole-corpus refresh that brings every project
cache to the current state — new-case discovery (B1), status re-derivation
(B5), a cleared status kept as a value (B6), the view-page absorb (C2), and
the per-case headers (§7 4.1) — running in slices of about 100 projects
(user decision 2026-11-04). Each slice SHALL take the single-writer lock,
write into `data/.link_cache/` only, record a checkpoint naming its last
finished project, and release the lock. The tracked datasets
(`projects.json`, `viewer/projects.data.js`) SHALL be emitted once, after
the last slice, through the standing emission path. A re-run SHALL skip the
projects the checkpoint records as finished.

The refresh SHALL decide what to fetch by one cheap signal per source, and
SHALL fetch in full only when the signal moves (the board's design,
2026-11-04): the national page's 資料更新日期 (one request per project; the
absorb re-runs only when the date is later than the cached page's), the city
parcel search (compare case ids and `schedule`), and the case header
(compare `NAME`, `uro_chk_date`, `uro_chk_date2`). A finished case (已完工 /
完成成果備查, or a 使照核發日期 present) SHALL skip its header fetch unless
the page or the parcel search moved. Every skip SHALL be counted in the run
report per source, so "not fetched because unchanged" never reads as
"fetched and empty". The refresh SHALL reuse the standing `refresh_project`
per project and the node resolver for any node the date matcher cannot
place; each slice SHALL run under the coverage guard.

#### Scenario: A slice is resumable

- **WHEN** the whole-corpus refresh is interrupted during slice 4 of 7
- **THEN** a re-run skips the projects slices 1–3 finished
- **AND** it resumes from slice 4's first unfinished project

#### Scenario: Each slice takes the lock

- **WHEN** a slice refreshes its projects
- **THEN** the single-writer lock is held for the slice's writes and released after
- **AND** the tracked datasets are not touched by the slice

#### Scenario: The emission happens once, after the last slice

- **WHEN** the checkpoint records every payload project as finished
- **THEN** the standing `--from-js` emission path produces the tracked datasets once
- **AND** the emission-fault check and the coverage guard run over the final state

#### Scenario: A finished case skips its header fetch

- **WHEN** a case's cached schedule is 已完工 or 完成成果備查, or its milestones
  carry a 使照核發日期, and neither the national page nor the parcel search moved
- **THEN** its `get_project168_top` fetch is skipped
- **AND** the report counts it as skipped-unchanged

#### Scenario: A moved page re-absorbs

- **WHEN** the live national page's 資料更新日期 is later than the cached page's
- **THEN** the view absorb re-runs for that project
- **AND** any case id the page newly names is fetched

#### Scenario: The report counts every skip

- **WHEN** the refresh completes
- **THEN** the report prints fetched / skipped-unchanged / failed per source
- **AND** a failure names the project, never silently dropped

### Requirement: The refresh re-derives the merged milestone projection

After the per-case pass, the refresh SHALL re-derive the project's merged
milestone projection from the cases' own per-case milestones over the project's
case ids, and SHALL write that projection and its per-label source map into the
cache. The refresh previously rewrote each case's milestones and left the
merged projection as it was, so the two drifted apart: measured on 2026-11-06,
85 of the 719 caches that hold per-case milestones diverged from a merge over
their own case ids, 84 lost or altered a label, 66 carried a conflicting
value, and 14 projects emitted no construction date that a case actually holds
(`松山區-寶清段四小段-599地號等27筆` showed no 建照核准 date while its cache held
`2006/05/12` under case `09303270`).

The re-derivation SHALL project the cases **exactly**: a label whose value no
case carries any more SHALL be dropped from the projection, because the city
withdrew or re-dated it (`士林區-光華段四小段-282地號等2筆`'s 審議通過日期 reads
`2026/09/23` today, not the stored `2026/03/18`). The withdrawn-approval rule
(the per-case conflict rule) still governs the per-case layer and is unchanged
by this requirement.

The re-derivation SHALL NOT displace the implementation layer's dates: those
are added at emission time from the data3 payload, not from the merged
projection.

#### Scenario: A case appended after the merge reaches the projection

- **WHEN** a project's cache holds cases `11011241` and `11011242`, whose merged
  projection says `召開幹事會日期 = 2022/11/15`, and the case id `11508023` is
  appended with `召開幹事會日期 = 2026/10/02`
- **THEN** the refreshed projection holds `召開幹事會日期 = 2026/10/02`
- **AND** the source map names the case that won the label

#### Scenario: A withdrawn label leaves the projection

- **WHEN** a project's merged projection holds `公告公展日期 = 2011/01/10` and no
  case carries that label any more (`大同區-市府段二小段-220-2地號等54筆` shape)
- **THEN** the refreshed projection does not hold `公告公展日期`

#### Scenario: A re-dated label carries the new value

- **WHEN** a project's merged projection holds `審議通過日期 = 2026/03/18` and its
  case now reads `2026/09/23`
- **THEN** the refreshed projection holds `審議通過日期 = 2026/09/23`

#### Scenario: A project whose cases did not move keeps its projection

- **WHEN** the cases' per-case milestones are unchanged by the refresh
- **THEN** the refreshed projection equals the stored one

### Requirement: The refresh re-fetches the implementation layer per case

The refresh SHALL re-fetch the implementation payload (the 執行階段 endpoint) and
the rewards payload (the 獎勵資料 endpoint) for every **live** case that
carries an approval date and has no implementation entry, and SHALL store the
replies per case. The refresh previously fetched only the milestones endpoint
and the case header, so a project whose implementation payload was empty stayed
empty: `文山區-實踐段二小段-641地號等1筆` had no 開工 and no 使照 while the live
implementation endpoint for its case `09009032` holds `2004/09/24` and
`2007/10/31`.

The selection SHALL be per case, not per project: a project whose payload
holds entries for other cases still needs the missing one (`萬華區-青年段一小段-130地號等3筆`
holds payload entries for two of its three cases, and the missing one is the one
that carries the dates).

An empty reply SHALL leave the case without an implementation entry, and SHALL
NOT be stored as an empty entry.

#### Scenario: A case with no implementation entry gains one

- **WHEN** a live case carries `核定日期` and the cache holds no implementation entry for it, and the endpoint returns `{"Eng_Start_Date": "2004/09/24"}`
- **THEN** the refreshed cache holds that entry for the case
- **AND** the project's merged projection is unchanged by the fetch

#### Scenario: A case that already has an implementation entry is not re-fetched

- **WHEN** a live case carries `核定日期` and the cache already holds an implementation entry for it
- **THEN** the refresh issues no implementation request for that case

#### Scenario: An empty reply stores nothing

- **WHEN** the implementation endpoint returns no fields for a selected case
- **THEN** the cache holds no implementation entry for that case

### Requirement: A case the city emptied is labelled 無

When the refresh reads an **empty** header row **and** empty milestones for a
case, the refresh SHALL record the case's state as 無, and SHALL NOT keep the
stale state the cache held. Two empty sources in the same refresh are the
measured shape of a case the city moved (`萬華區-青年段一小段-130地號等3筆`'s
`11501041` → `11510008`; `信義區-虎林段四小段-38地號等138筆`'s `11410001` →
`11502012`).

The label SHALL NOT claim a removal: the case keeps its id, it stays in the
project's case list, it keeps its cached data, and no successor is recorded for
it. The city states nothing about a removal, so the pipeline must not claim
one. The parcel search is not part of the rule — the search omits approved ids
for known reasons, so its absence is no evidence.

A case whose header reads a **state** — including a revoked one — SHALL NOT be
labelled 無. `美仁800`'s `09707196` reads 業經本府撤銷核准 and is not this shape:
its header is not empty, so the rule does not touch it.

The refresh report SHALL name every case it labels 無.

#### Scenario: An emptied case is labelled 無

- **WHEN** a case's header row is empty and its milestones are empty, and the cache holds its state as 已核准
- **THEN** the refreshed cache records the case's state as 無
- **AND** the case keeps its id and its entry in the project's case list

#### Scenario: A revoked case is not labelled 無

- **WHEN** a case's header names 業經本府撤銷核准
- **THEN** the case's state is not 無
- **AND** the case's cached data is unchanged

#### Scenario: One empty source is not enough

- **WHEN** a case's header row is empty but its milestones are not
- **THEN** the case's state is not labelled 無 by this rule

#### Scenario: The report names every labelled case

- **WHEN** the refresh labels cases 無
- **THEN** the report names each of them with its case id

### Requirement: An aliased cache directory is merged, not shadowed

When a project's current cache directory exists and an **aliased** directory
(the project's former identity, per `data/project_aliases.json`) also exists,
the system SHALL **merge** the aliased directory's content into the current
one rather than ignoring it.

The merge SHALL add the aliased directory's case ids and per-case milestones
that the current directory lacks, and SHALL keep the current directory's own
content on a conflict. The current directory's identity fields (its own
`project_id` and `land_core`) SHALL NOT be overwritten — the current id is the
one the dataset holds.

**Reason:** the current directory can be a stub. A run that wrote a fresh
directory under a project's new identity, before the old directory's content
was carried over, left the richer directory unreadable — `resolve_cache_dir`
returned the current directory whenever it existed, so the alias was never
consulted. The result was silent: two nodes kept the flag
`節點未能對應平台案件` although the case and its milestones were in the cache
all along (南港566: case `10708311`, 核定 2019-11-20, and `10006032`, 核定
2016-02-25).

#### Scenario: A stub and a richer aliased directory are merged

- **WHEN** a project's current cache directory holds one case id and an aliased
  directory holds three
- **THEN** the current directory holds all three case ids
- **AND** the current directory's own `project_id` and `land_core` are unchanged

#### Scenario: A conflict keeps the current directory's value

- **WHEN** both directories carry milestones for the same case id and they
  differ
- **THEN** the current directory's value is kept

#### Scenario: No aliased directory changes nothing

- **WHEN** a project has no aliased directory
- **THEN** the cache is read and written exactly as before

#### Scenario: The merge is reported

- **WHEN** a merge added case ids or milestones to a project's cache
- **THEN** the run names the project and what was added

