# cache-freshness Delta

## MODIFIED Requirements

### Requirement: The targeted refresh selects caches awaiting an approval

The refresh pass SHALL select a project cache when at least one of its cases
carries an application-for-approval date and no approval date (`核定日期` /
`權變核定日期` / `概要核准日期`). The application signal SHALL cover every
application track — `申請核定日期` / `權變申請核定日期` (approval
applications) and `申請計畫日期` / `申請權變日期` / `申請概要核准日期`
(plan-change applications) — because a plan-change case approved after the
cache was written leaves the same absence (measured 2026-11-02:
北投區-關渡段二小段-303's 11505020 carries only 申請計畫日期/申請權變日期 in
the cache while the API reports 核定日期 2026/09/30). It SHALL re-fetch the
milestones for exactly those projects, SHALL preserve every other field the
cache already holds, SHALL re-run the national view-page absorb so the cache
gains `view_verified_case_ids` and any case ids the page names that the
parcel search missed, and SHALL report each project's before/after approval
dates so the effect is auditable. It SHALL NOT re-crawl projects whose cached
cases are all resolved.

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
- **THEN** the cache is left unchanged
- **AND** the project is reported as still awaiting approval

#### Scenario: The refresh backfills the view-verified case list

- **WHEN** the refresh runs on a cache whose `view_verified_case_ids` is absent (a
  cache predating the field) and the project has a national view page
- **THEN** the refreshed cache carries `view_verified_case_ids` — the case ids the
  page's 相關連結 block names
- **AND** any named case the parcel search missed is added to `city_case_ids` with its
  milestones fetched

## ADDED Requirements

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
