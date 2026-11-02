# cache-freshness Delta

## Purpose

How the pipeline notices that a link cache predates the gazette it is emitting
for, and how a targeted refresh re-derives the case milestones such a cache is
missing — so a newly approved case is bound to its record instead of falling to
the positional fallback.

## ADDED Requirements

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
carries an application-for-approval date (`申請核定日期` / `權變申請核定日期`) and
no approval date (`核定日期` / `權變核定日期` / `概要核准日期`) — the state a case
is in between applying for approval and receiving it. It SHALL re-fetch the
milestones for exactly those projects, SHALL preserve every other field the cache
already holds, and SHALL report each project's before/after approval dates so the
effect is auditable. It SHALL NOT re-crawl projects whose cached cases are all
resolved.

#### Scenario: A project's case has since been approved

- **WHEN** a cached case holds 申請核定日期 but no 核定日期, and the city's API now
  reports a 核定日期 for it
- **THEN** the refresh updates that case's milestones in place
- **AND** reports the project with the old and new approval dates
- **AND** every other cached field is preserved

#### Scenario: A project's cases are all resolved

- **WHEN** every cached case carries an approval date
- **THEN** the project is not selected and is not re-fetched

#### Scenario: A project's case is still awaiting approval

- **WHEN** a cached case holds 申請核定日期, no approval date, and the API still
  reports none
- **THEN** the cache is left unchanged
- **AND** the project is reported as still awaiting approval

### Requirement: The refreshed binding replaces the positional fallback for the affected nodes

After a refresh, an emission SHALL bind each affected node to the case whose
approval date matches the node's own date, and SHALL NOT bind it to the
positional fallback, because the previously-missing approval date is now present.

#### Scenario: A newly approved case's node is bound by date

- **WHEN** a node's date equals the approval date the refresh recovered for its case
- **THEN** the node's anchored case is that case
- **AND** the graph's row order for the family follows the nodes' dates ascending
