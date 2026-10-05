## Purpose

Retains every gazette PDF the system has ingested, together with an append-only record of what each publication yielded. This makes it possible to compare any two publications, to re-read an older gazette with the current reader, and to establish that a record which disappeared from the list was removed by the city rather than lost by the parser.

## ADDED Requirements

### Requirement: Archive every ingested gazette

The system SHALL retain a verbatim copy of every gazette PDF it ingests, outside the git working tree, named by the publication date read from the document. Archived gazettes SHALL never be overwritten or deleted by the system.

#### Scenario: A gazette is archived on ingestion

- **WHEN** a gazette PDF is successfully ingested
- **THEN** a copy is retained outside the git working tree, named by its 統計至 publication date
- **AND** re-ingesting the same publication date does not create a second copy or alter the existing one

#### Scenario: The archive is not tracked by git

- **WHEN** the archive is inspected from within the repository
- **THEN** its contents are not staged or committed, and the repository's tracked file list does not include gazette PDFs

#### Scenario: Storage growth is bounded and known

- **WHEN** the archive holds N gazettes
- **THEN** total size is approximately N × 2 MB
- **AND** no gazette is ever evicted

### Requirement: Maintain an append-only gazette index

The system SHALL maintain an append-only index recording, for each archived gazette, its publication date, ingest timestamp, record count, project count, and reader version. The index SHALL only ever be appended to.

#### Scenario: Ingesting appends one entry

- **WHEN** a gazette is ingested
- **THEN** exactly one entry is appended recording its publication date, ingest time, record count, project count, and reader version
- **AND** no existing entry is altered

#### Scenario: Re-ingesting a known publication

- **WHEN** a gazette whose publication date is already in the index is ingested again
- **THEN** a new entry is appended recording that repeat ingest, and the earlier entry remains unchanged

#### Scenario: Index identifies the most recent publication

- **WHEN** the current publication date is needed
- **THEN** it is read from the newest index entry rather than from any separately maintained value

### Requirement: Support re-reading an archived gazette

The system SHALL be able to process any archived gazette with the current reader, so that historical records can be regenerated under present-day parsing rules rather than retaining whatever a past reader produced.

#### Scenario: Re-reading an older gazette after a reader change

- **WHEN** an archived gazette is processed after the reader's behaviour has changed
- **THEN** it is read under the current reader's rules, producing output consistent with how the newest gazette is read
- **AND** the ingest is recorded in the index as a repeat ingest of that publication date