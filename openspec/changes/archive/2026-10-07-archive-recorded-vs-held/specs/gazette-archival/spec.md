## ADDED Requirements

### Requirement: The archive distinguishes a recorded publication from a held one

The system SHALL treat the set of publications it has **recorded** in its index as
distinct from the set of documents it currently **holds** on disk, and SHALL answer a
question about publication order from the record rather than from the directory listing.

A publication that the index records but whose document is absent SHALL continue to
occupy its position in the publication order. It SHALL NOT be silently omitted from that
order, because omitting it promotes an earlier publication into its place and makes an
interval spanning two publications read as though the publications were adjacent.

#### Scenario: A recorded publication's document is deleted

- **WHEN** a publication's document is removed from the archive while the index still records it
- **THEN** the publication still occupies its recorded position in the order
- **AND** it is reported as recorded but not held, rather than being absent from the order

#### Scenario: A publication is re-read after its document was deleted

- **WHEN** a publication whose document is absent is ingested again
- **THEN** the publication immediately before it is identified from what was recorded
- **AND** the absence is reported rather than resolved by comparing against an earlier publication

#### Scenario: The order is asked before the incoming publication is archived

- **WHEN** the publication preceding an incoming, not-yet-archived gazette is sought
- **THEN** it is resolved from the publications already recorded
- **AND** the incoming gazette's own absence from the record does not prevent the lookup

### Requirement: Archive damage is surfaced during ingestion

The system SHALL report archive members that are missing, that are present without an
index entry, or whose content no longer matches the digest recorded for them, as part of
an ordinary ingestion.

This reporting SHALL NOT block the ingestion: an absent or altered older member does not
invalidate the publication being ingested, and refusing to proceed would mean a
filesystem accident prevents ingestion permanently.

#### Scenario: A member recorded in the index is missing

- **WHEN** an ingestion runs and the index records a publication whose document is absent
- **THEN** that publication is reported as recorded but not held
- **AND** the ingestion proceeds and writes its output

#### Scenario: A member's bytes were replaced

- **WHEN** an ingestion runs and a held member's content no longer matches the digest recorded for it
- **THEN** the substitution is reported, naming the digest recorded and the digest found
- **AND** the ingestion proceeds and writes its output

#### Scenario: A document is present with no index entry

- **WHEN** an ingestion runs and a gazette document is present that the index does not record
- **THEN** it is reported as held without provenance
- **AND** the ingestion proceeds and writes its output

#### Scenario: The archive is intact

- **WHEN** an ingestion runs and every member is present, indexed, and matches its digest
- **THEN** nothing is reported
- **AND** the absence of a report is the ordinary case, not a skipped check