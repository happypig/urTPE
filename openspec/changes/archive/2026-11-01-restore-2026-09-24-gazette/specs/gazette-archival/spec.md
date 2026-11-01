# gazette-archival Delta

## Purpose

Repairs two archival behaviours the 2026-09-24 gap exposed: a re-stored publication silently
replacing content under the same `gazette_id` and poisoning every older digest check, and a
verified member sitting in quarantine with no path back into the archive.

## ADDED Requirements

### Requirement: Re-filing a quarantined member preserves the evidence

The system SHALL be able to re-file a quarantined archive candidate into the archive under
its publication date once its identity is established by digest, and SHALL record in the new
index entry that the document was restored from quarantine. The quarantined location SHALL be
reported in the run output; the restoration SHALL NOT delete the quarantine record.

#### Scenario: A quarantined file is re-filed under its publication name

- **WHEN** a file quarantined under a download name hashes to a digest previously recorded
  for a publication the index does not hold
- **THEN** the file is copied into the archive under the publication's name
- **AND** the appended index entry names the quarantine location it was restored from
- **AND** the run output reports the restoration with both names

#### Scenario: A quarantined file is NOT re-filed

- **WHEN** a quarantined candidate's digest matches nothing previously recorded
- **THEN** the file stays quarantined
- **AND** the refusal is reported rather than guessed at

## MODIFIED Requirements

### Requirement: Archive every ingested gazette

The system SHALL retain a verbatim copy of every gazette PDF it ingests, outside the git
working tree, named by the publication date read from the document. Archived gazettes SHALL
never be deleted by the system. When content for a publication date already held is stored
again and the bytes differ, the system SHALL replace the copy only after appending an index
entry that records the digest being superseded and the digest now held, so a corrected
re-upload is traceable rather than silent.

#### Scenario: A gazette is archived on ingestion

- **WHEN** a gazette PDF is successfully ingested
- **THEN** a copy is retained outside the git working tree, named by its 統計至 publication date
- **AND** re-ingesting the same publication date with identical content does not create a
  second copy or alter the existing one

#### Scenario: A corrected re-upload replaces held content

- **WHEN** content is stored for a publication date whose held copy hashes differently
- **THEN** the index entry appended for the new store names the superseded digest and the
  new digest
- **AND** the replaced copy is the one named by the new digest

#### Scenario: The archive is not tracked by git

- **WHEN** the archive is inspected from within the repository
- **THEN** its contents are not staged or committed, and the repository's tracked file list
  does not include gazette PDFs

#### Scenario: Storage growth is bounded and known

- **WHEN** the archive holds N gazettes
- **THEN** total size is approximately N × 2 MB
- **AND** no gazette is ever evicted

### Requirement: Archive damage is surfaced during ingestion

The system SHALL report archive members that are missing, that are present without an index
entry, or whose content does not match the digest recorded for them, as part of an ordinary
ingestion. A digest mismatch SHALL NOT be reported when the recorded digest belongs to a
digest chain the index itself documents — an index entry naming the digest it supersedes
makes the older entry's mismatch an expected consequence of a recorded replacement, not
damage. This reporting SHALL NOT block the ingestion: an absent or altered older member does
not invalidate the publication being ingested, and refusing to proceed would mean a
filesystem accident prevents ingestion permanently.

#### Scenario: A member recorded in the index is missing

- **WHEN** an ingestion runs and the index records a publication whose document is absent
- **THEN** that publication is reported as recorded but not held
- **AND** the ingestion proceeds and writes its output

#### Scenario: A member's bytes were replaced

- **WHEN** an ingestion runs and a held member's content no longer matches the digest
  recorded for it, and no index entry documents that digest as superseded
- **THEN** the substitution is reported, naming the digest recorded and the digest found
- **AND** the ingestion proceeds and writes its output

#### Scenario: A member's digest was superseded by a recorded re-store

- **WHEN** an ingestion runs and a held member's content matches a digest that a later index
  entry names as superseded for the same publication
- **THEN** the older entry's mismatch is not reported as damage
- **AND** the superseding entry is the publication's current digest

#### Scenario: A document is present with no index entry

- **WHEN** an ingestion runs and a gazette document is present that the index does not record
- **THEN** it is reported as held without provenance
- **AND** the ingestion proceeds and writes its output

#### Scenario: The archive is intact

- **WHEN** an ingestion runs and every member is present, indexed, and matches its digest
- **THEN** nothing is reported
- **AND** the absence of a report is the ordinary case, not a skipped check
