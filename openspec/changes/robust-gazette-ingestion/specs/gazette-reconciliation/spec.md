## Purpose

Compares a newly ingested gazette against its predecessor and reports what changed — how many approvals are new, whether the list grew or shrank, and how many pre-existing rows the city re-dated or edited. Its purpose is to make an unexplained change impossible to miss while staying honest about what the published data can actually support.

The scope is deliberately narrow, and that is a measured decision rather than a convenience. Two properties of the source make per-record content diffing unsound:

- **The city edits historical rows.** A land cell's text is not stable across publications, so matching on `(行政區, land, 核定日期)` can report the same unit as both added and removed.
- **The export is re-sorted and recomputed rather than appended to.** New approvals are prepended while the older export was insertion-ordered and the newer one orders history by 核定日期, so a record's position carries no information about its identity.

So an "absent record" cannot be distinguished from an edited or re-dated one by content. This capability therefore reports additions and net change authoritatively, reports historical movement as its own counted signal, and refuses the run only for the conditions the data does support.

The specific counts once quoted for these two properties — 59 differing land cells, 22 approvals moved later and 21 earlier, date-order violations falling from 9 to 1 — were measured on a **contaminated read** and are withdrawn. The reader that produced them absorbed a page-number footer into a 地號 cell and truncated long cells at the row height; with it corrected, the pre-cutoff record set is identical across `1150822`, `1150820` and `1150827` at 1412 records, with 0 lost and 0 gained. The two properties above are retained because they are properties of the publication, not of that read — but they are stated without figures here deliberately, and re-measuring them requires an uncontaminated read of `1151002`.

## MODIFIED Requirements

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

## ADDED Requirements

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