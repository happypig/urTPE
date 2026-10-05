# gazette-reconciliation Specification

## Purpose

Compares a newly ingested gazette against its predecessor and reports what changed — how many approvals are new, whether the list grew or shrank, and how many pre-existing rows the city re-dated or edited. Its purpose is to make an unexplained change impossible to miss while staying honest about what the published data can actually support.

The scope is deliberately narrow, and that is a measured decision rather than a convenience. Two properties of the source make per-record content diffing unsound:

- **The city edits historical rows.** A land cell's text is not stable across publications, so matching on `(行政區, land, 核定日期)` can report the same unit as both added and removed.
- **The export is re-sorted and recomputed rather than appended to.** New approvals are prepended while the older export was insertion-ordered and the newer one orders history by 核定日期, so a record's position carries no information about its identity.

So an "absent record" cannot be distinguished from an edited or re-dated one by content. This capability therefore reports additions and net change authoritatively, reports historical movement as its own counted signal, and refuses the run only for the conditions the data does support.

The counts once quoted for these two properties — 59 differing land cells, 22 approvals moved later and 21 earlier — were measured on a **contaminated read** and are withdrawn: the reader that produced them absorbed a page-number footer into a 地號 cell and truncated long cells at the row height. With it corrected, the pre-cutoff record set is identical across `1150822`, `1150820` and `1150827` at 1412 records, with 0 lost and 0 gained.

The date-order figure was withdrawn on a different and mistaken ground. It was recorded as "9 to 1" and then set aside as *not re-derivable* until `1151002` had been read by the corrected reader — not because the number was doubtful. That read has now happened, and the figure stands: departures from descending approval date are **9, 9 and 1** across `1150820`, `1150827` and `1151002`. The single `1151002` departure is 編號 109 (2025-08-05) above 編號 110 (2025-11-26) — the same unit's 第二次 and 第三次 權利變換, so it is a re-dated historical row rather than a failure to sort. The publisher sorts by date and then re-dates history behind itself; whether that continues is tracked per publication by `gazette-cadence`.

Two measurement properties make the naive count wrong, and both report as healthy rather than broken. `1151002` repeats 編號 1 as a running page head on all 246 pages, so a raw table scan reads 1681 rows for 1436 records and inflates the departure count to 246. And `1151002` publishes Gregorian dates where earlier publications use ROC, so a single-calendar parser finds no dates at all and reports **zero** departures. A departure count is therefore meaningless without its denominator.

## Requirements

### Requirement: Report new approvals and net change between publications

The system SHALL compare a newly ingested gazette against the previously archived gazette and report how many approvals are new, and how much the total record count changed. A record is new when its approval date falls after the newest approval date in the previous gazette.

#### Scenario: Approvals prepended to the list

- **WHEN** a gazette adds approvals newer than any in its predecessor
- **THEN** the number of new approvals is reported, and the change in total record count is reported
- **AND** the run is not blocked, even though every 編號 has shifted

#### Scenario: Every 編號 shifts without any record changing

- **WHEN** five approvals are prepended so that every existing 編號 increases by five
- **THEN** five new approvals and a net change of +5 are reported
- **AND** no existing record is reported as added, removed, or changed

#### Scenario: First ever ingestion

- **WHEN** a gazette is ingested and no previous gazette is archived
- **THEN** the report states that no comparison was possible rather than reporting every record as new

#### Scenario: Out-of-order re-read

- **WHEN** a gazette older than the newest archived one is ingested
- **THEN** it is compared against its immediate predecessor in the archive rather than against the newest gazette
- **AND** the report names which two publications were compared

### Requirement: Report re-dated and edited historical rows

The system SHALL report, as a separate counted signal, how many pre-existing rows changed between publications, distinguishing rows whose land description changed from rows whose approval date moved. Such movement SHALL be reported and SHALL NOT by itself block the run.

#### Scenario: Historical row re-dated by the city

- **WHEN** an approval present in both publications carries a later approval date in the newer one
- **THEN** it is counted as re-dated and reported
- **AND** the run is not blocked

#### Scenario: Historical land description edited

- **WHEN** an approval present in both publications has a different land description in the newer one
- **THEN** it is counted as edited and reported
- **AND** the run is not blocked

#### Scenario: Re-dating observed at scale

- **WHEN** a publication re-dates many historical rows
- **THEN** the report states the re-dated and edited counts
- **AND** the change in the new-approval count and the net change are reported alongside, so the two effects can be told apart

### Requirement: Refuse to complete when the list shrinks

The system SHALL abort the ingestion when the new gazette contains fewer records in total than its predecessor, or when approvals present in the previous gazette's newest cohort are absent from the new gazette's newest cohort. Historical row movement alone SHALL NOT block; a strict mode MAY promote it to blocking.

#### Scenario: Total record count shrinks

- **WHEN** the new gazette contains fewer records than the previous one
- **THEN** the run aborts, reporting both counts, and writes no output

#### Scenario: A recently published approval is withdrawn

- **WHEN** an approval in the previous gazette's newest cohort is absent from the new gazette's newest cohort
- **THEN** the run aborts and names the withdrawn approval

#### Scenario: An old record disappears while the list grows

- **WHEN** an approval dated years earlier is absent from the new gazette while the total record count has increased
- **THEN** the disappearance is reported among the historical changes, with the record's district and land description
- **AND** the run is not blocked, because the published data cannot distinguish this from an edit or a re-dating

#### Scenario: Strict mode treats historical disappearance as blocking

- **WHEN** strict reconciliation is requested and a historical row cannot be matched in the new gazette
- **THEN** the run aborts unless the disappearance is recorded as accepted in the correction ledger

### Requirement: Report project identities that moved

The system SHALL report every project whose identity changed between the previous gazette and the new one, so that cached data keyed on the former can be migrated deliberately. A total re-keying SHALL be reported as its own outcome.

#### Scenario: A project's anchor advances to a changed land description

- **WHEN** a project's newest approval reports a different parcel count than its earlier approvals
- **THEN** both the previous and the current project identity are reported as a move
- **AND** the number of unmoved project identities is also reported

#### Scenario: No identities moved

- **WHEN** every project identity is unchanged between two publications
- **THEN** the report states that zero identities moved

#### Scenario: Total identity re-keying

- **WHEN** every project identity differs between two publications
- **THEN** this is reported explicitly as a total re-key rather than as an ordinary number of moves
- **AND** the run aborts pending confirmation, because cached data keyed on the previous identities would be orphaned

### Requirement: Report the calendar and structural shape of the publication

The system SHALL report which calendar the publication used, alongside the new-approval count and the net change.

#### Scenario: Calendar changed between publications

- **WHEN** the new publication prints Gregorian dates and the previous printed Republic of China dates
- **THEN** the report states the calendar change explicitly
- **AND** every record is still emitted with an ISO-8601 date

#### Scenario: Same calendar as before

- **WHEN** the new publication uses the same calendar as the previous
- **THEN** the report records that the calendar is unchanged

### Requirement: Accept historical disappearances recorded in the ledger

The system SHALL treat a historical row's disappearance as explained when the correction ledger records that removal as accepted, and SHALL report it as accepted rather than as an unexplained change.

#### Scenario: Accepted historical disappearance

- **WHEN** a correction records that a specific historical approval was verified as legitimately removed
- **THEN** the disappearance is reported as accepted
- **AND** in strict mode it does not block the run

### Requirement: Explain a change in new-approval count

The system SHALL report the previous gazette's newest approval date alongside the new-approval count, so that a reader can tell a genuine absence of new approvals from a publication that re-dated its newest rows.

#### Scenario: Newest approval date is shown

- **WHEN** a reconciliation report is produced
- **THEN** it states the previous gazette's newest approval date and the number of current approvals later than it

### Requirement: A total re-key is reported as a distinct outcome by every guard

A wholesale change of project identity SHALL be reported as its own outcome, distinct
from an ordinary move count and distinct from "nothing changed". Any guard placed over
the caches SHALL observe it, because a guard that cannot see it passes while every cache
is orphaned.

#### Scenario: Every identity changes

- **WHEN** a run leaves no project identity present both before and after
- **THEN** the outcome is reported as a total re-key, naming the count before and after
- **AND** it is not reported as an absence of regressions

#### Scenario: Every cache directory is orphaned

- **WHEN** every cached identity is absent from the new dataset
- **THEN** that is reported as a fault rather than recorded as information
- **AND** the report states that no cached identity survived, so the caches cannot be located by name

#### Scenario: Some identities move

- **WHEN** some identities are present before and after and some are only before
- **THEN** ordinary regressions and the newly absent identities are reported separately
- **AND** the newly absent identities are not reported as regressions on identities that still exist

#### Scenario: A run changes nothing

- **WHEN** the identities before and after are identical
- **THEN** no re-key is reported and no fault is raised

#### Scenario: The guard and the reconciliation agree

- **WHEN** a run re-keys every identity
- **THEN** reconciliation and the cache guard report the same outcome
- **AND** neither reports success while every cache is orphaned

### Requirement: The change set is persisted, not only printed

The system SHALL write the outcome of each comparison to durable storage alongside the
archive, so that what a past ingestion concluded remains available to a later run and to an
operator after the terminal output is gone. The persisted form SHALL identify both
publications compared, and SHALL distinguish the authoritative signals — new approvals and
net change — from movement that the data cannot resolve.

A persisted change set SHALL record the project identities that gained an approval, since
that set is the input a downstream consumer needs and cannot reconstruct from counts alone.

#### Scenario: A comparison concludes and the console output is discarded

- **WHEN** a gazette is reconciled against its predecessor
- **THEN** the comparison's outcome is written to durable storage
- **AND** it can be read back later without re-running the ingestion

#### Scenario: A downstream run needs to know which projects changed

- **WHEN** a consumer asks which projects gained an approval in a given publication
- **THEN** the persisted change set names those projects
- **AND** naming them does not require re-reading either gazette

#### Scenario: The comparison could not be made

- **WHEN** a gazette is ingested with no predecessor to compare against
- **THEN** the persisted record states that no comparison was possible
- **AND** it does not present an empty change set as though the publications were identical

#### Scenario: A comparison is revisited

- **WHEN** a persisted change set for a publication is read after later publications have been ingested
- **THEN** it still describes the comparison that was actually made at that time
- **AND** it is not recomputed against a newer predecessor

### Requirement: The reader that produced an archive entry is identified accurately

An archive entry SHALL record the identity of the reader that produced it in a form that
distinguishes readers whose output could differ. An entry whose reader is not identified at
that granularity SHALL NOT be treated as equivalent to one that is, because a comparison
across two such entries cannot establish what changed in the source.

#### Scenario: Comparing entries produced by readers that differ

- **WHEN** two archive entries are compared and their readers are known to differ in a way that affects cell content
- **THEN** the comparison reports that the readers differ
- **AND** movement between them is not attributed to the publisher

#### Scenario: An entry predates reader identification

- **WHEN** an archive entry records a reader identity too coarse to distinguish a corrected reader from the one it replaced
- **THEN** the entry is reported as having an unverified reader
- **AND** a comparison involving it says so rather than presenting the result as clean
