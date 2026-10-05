# gazette-archival Specification

## Purpose

Retains every gazette PDF the system has ingested, together with an append-only record of what each publication yielded. This makes it possible to compare any two publications, to re-read an older gazette with the current reader, and to establish that a record which disappeared from the list was removed by the city rather than lost by the parser.

## Requirements

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

### Requirement: The index distinguishes a gazette's reader from a re-read

An index entry SHALL record the reader identity at a granularity that separates readers
whose emitted cell content could differ, and SHALL distinguish the first ingestion of a
publication from any later re-read of that same publication. A re-read performed with a
different reader SHALL NOT overwrite the provenance of the first ingestion, because the
entry must continue to say which reader first produced the archived data.

Re-ingesting a publication is currently recorded as another entry for that publication.
Over time this makes the index ambiguous as a history: an entry count no longer equals a
publication count, and the reader that produced the current dataset cannot be identified
from it.

#### Scenario: A publication is ingested, then re-read with a corrected reader

- **WHEN** a publication is ingested and later re-read with a reader that differs in cell-content behaviour
- **THEN** both the first ingestion and the re-read are represented
- **AND** the entry identifying the reader that produced the current dataset names the re-read's reader
- **AND** the first ingestion's provenance remains readable

#### Scenario: Several readers have been used over time

- **WHEN** the index spans ingestions made by more than one reader
- **THEN** the reader is readable per entry
- **AND** the publications archived can be distinguished from the number of ingestions performed

#### Scenario: An early entry predates reader identification

- **WHEN** an entry's reader identity is too coarse to say which behaviour it exhibited
- **THEN** the entry is identifiable as such when read back
- **AND** it is not silently treated as equivalent to a precisely identified reader

### Requirement: The index records the provenance of how a gazette was obtained

An index entry SHALL record how the gazette came to be archived: whether it was fetched
from the publisher or supplied from a local path. Where the gazette was fetched, the entry
SHALL record the retrieval metadata needed to explain a later re-upload of identical
content, including the timestamp the publisher reported.

A publisher timestamp SHALL NOT be treated as evidence that a gazette is new, because the
publisher re-uploads unchanged documents under a later timestamp.

#### Scenario: A gazette fetched from the publisher is archived

- **WHEN** a gazette is acquired from the publisher's page and archived
- **THEN** its entry records that it was fetched, with the publisher's reported timestamp
- **AND** the entry carries the content hash that establishes what was actually retrieved

#### Scenario: The publisher re-uploads an unchanged gazette

- **WHEN** the publisher later serves identical content under a later timestamp
- **THEN** a later timestamp alone does not create a new gazette entry
- **AND** the equality of the content is established by hash rather than by timestamp

#### Scenario: A gazette supplied from a local path is archived

- **WHEN** a gazette is ingested from a path on disk rather than fetched
- **THEN** its entry records that it was supplied locally
- **AND** it does not claim a publisher timestamp it never received

### Requirement: The index records what the publication's ordering says about itself

For each archived publication the index SHALL record the count of positions at which the
list's stated order departs from descending approval date. This is a property of the
publication rather than of any one reader, and it is the indicator by which the question of
whether the publisher sorts by date permanently is being tracked.

#### Scenario: A publication is archived

- **WHEN** a gazette is archived
- **THEN** its entry records the count of departures from descending approval date
- **AND** the count is comparable with that of other archived publications

#### Scenario: The count is compared across publications

- **WHEN** the ordering indicator is read for every archived publication
- **THEN** the trend across publications is visible from the index alone
