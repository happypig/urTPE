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
