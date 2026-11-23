## MODIFIED Requirements

### Requirement: An unattended check cannot overwrite an emitted dataset

A check SHALL NOT write to the emitted dataset. Acquisition SHALL deposit a gazette into
the archive only, and any ingestion of an archived gazette into the emitted dataset SHALL be
an explicit separate act that acquires the single-writer lock. That act is started either by
a person or by the PDF-cycle coordinator under the gates of the `pdf-cycle-coordinator`
capability. A check, a poller and a publication step SHALL NOT start it.

An unattended check MAY publish a report derived from the archive. Publication
SHALL write no file under the emitted output tree and SHALL NOT ingest, so the
guarantee above is preserved: the emitted dataset is still only ever written by
an explicit ingestion. A publication step SHALL stage only the paths it owns,
so an unrelated modification in the working tree is neither committed nor
discarded by it.

A publication step SHALL report a failed push as a failure. The report
committed by a step whose push did not land is ahead of the served one, which
the deployment check reports as stale — visible rather than silent.

#### Scenario: A new gazette is detected by an unattended run

- **WHEN** an unattended check discovers a gazette it has not seen
- **THEN** the gazette is archived and indexed
- **AND** no emitted dataset is read, rewritten or replaced

#### Scenario: A gazette is ingested into the dataset

- **WHEN** an archived gazette is ingested into the emitted dataset
- **THEN** that is a separate act from acquiring it, under the single-writer lock
- **AND** an unattended check never initiates it
- **AND** only a person or the PDF-cycle coordinator, under its gates, may initiate it

#### Scenario: An unattended run publishes a derived report

- **WHEN** an unattended run regenerates the release-diff report from the archive
- **THEN** the publication step writes no file under the emitted output tree
- **AND** the publication step ingests no gazette
- **AND** only the paths the publication step owns are staged for commit

#### Scenario: The publication push fails

- **WHEN** the report is regenerated and committed but the push does not land
- **THEN** the step reports the failure and exits non-zero
- **AND** the served report is reported stale by the deployment check, because it is not the committed build

#### Scenario: A coordinator reads the result of a check

- **WHEN** a check discovers a new gazette and the PDF-cycle coordinator runs after it
- **THEN** the check itself has only archived and indexed the gazette
- **AND** any ingestion that follows is started by the coordinator, not by the check


## ADDED Requirements

### Requirement: The publication step publishes the generated pages as one set, and only when the report or the counts changed

The publication step SHALL own four generated pages and no other path: the release-diff report, the coverage report, the domain model and the ETL page. It SHALL publish them as one set, and only when the release-diff report differs from the committed report (ignoring the report's generation stamp) or the emitted payload's project or record count differs from the committed payload's. When neither differs, it SHALL commit nothing and SHALL leave the other pages as it found them, because a page that differs from the committed copy in a date alone may belong to an emission still waiting for review. It SHALL stage only the owned pages that exist or are tracked, so a page that does not exist is skipped and is not an error.

The step SHALL refuse, with exit 2 and without committing, when the source of any generator of an owned page has uncommitted changes, or when the payload is present but its counts cannot be read. A payload that is absent from both the commit and the working tree SHALL NOT trigger publication by its counts. The step SHALL write no file under the emitted output tree.

A step that is run again after its push failed SHALL push the commit that is ahead of the remote and SHALL exit 0 when the push lands, even though it has nothing new to commit.

#### Scenario: The report changed

- **WHEN** the release-diff report differs from the committed one
- **THEN** every owned page that differs from the committed copy is committed together in one path-limited commit
- **AND** another session's staged file is not committed and stays staged

#### Scenario: Only the counts changed

- **WHEN** the release-diff report is unchanged but the payload's project or record count differs from the committed payload's
- **THEN** the owned pages that differ are committed, and the report stays byte-identical to the committed one

#### Scenario: Nothing changed

- **WHEN** the report is unchanged and the counts are unchanged
- **THEN** nothing is committed or pushed
- **AND** the other owned pages are left exactly as they were found, even if they differ from the committed copy in a date

#### Scenario: An owned page does not exist

- **WHEN** an owned page is neither on disk nor tracked
- **THEN** the step publishes the pages that do exist and reports no error

#### Scenario: A generator of an owned page is uncommitted

- **WHEN** the source of the coverage report's, the domain model's or the ETL page's generator has uncommitted changes
- **THEN** the step exits 2 and commits nothing

#### Scenario: The counts cannot be read

- **WHEN** the payload is present but carries no readable counts
- **THEN** the step exits 2 and commits nothing

#### Scenario: A retry after a failed push lands

- **WHEN** the step committed the pages, its push failed, and it is run again
- **THEN** it pushes the commit that is ahead of the remote and exits 0
