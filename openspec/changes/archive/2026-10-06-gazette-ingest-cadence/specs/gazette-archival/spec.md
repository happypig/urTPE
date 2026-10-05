## ADDED Requirements

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