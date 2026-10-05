## ADDED Requirements

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