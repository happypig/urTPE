## ADDED Requirements

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
