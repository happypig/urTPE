## MODIFIED Requirements

### Requirement: The emitted document carries a total, disjoint record-to-project partition

The ingestion SHALL verify, after merge and before any artifact is written, that
the merge partition is total and disjoint over the cleansed records: every
cleansed record belongs to exactly one project family, and the family members sum
to the cleansed record count. The emitted document SHALL also agree with the
cleansed records it was built from: the document's record count SHALL equal the
cleansed count. A violation SHALL be reported with the violating records named,
and SHALL be evaluated before `projects.json`, the TSVs, or the viewer data are
written — a check that runs after the damage is not a check. A partition
violation SHALL block the emission (exit 4, the tripwire contract): unlike
missing link data, a lost or double-counted record is data corruption, not
absence.

The census check SHALL verify the family set that is actually emitted. A
manual correction whose confirmed merge unions two records changes the family
count, so the check SHALL run **after** the correction ledger is applied and
SHALL compare against that post-correction family set. The count the check
reports — in the run report and in the tripwire report — SHALL be the count of
the emitted family set, so a report never states a count the payload does not
carry.

Every path that emits a document SHALL hold the partition, not only the path
that reads a PDF. A rebuild from an already-emitted document SHALL verify the
partition of that document **before** it is loaded into families: the document's
record count SHALL agree with the records its nodes carry, each family's member
list SHALL agree with that family's nodes, and each family's anchor SHALL be one
of that family's nodes. The verification SHALL use the output tree's
`clean.tsv` as an independent reference when that file is present, so a
document that lost a record **and** had its own count rewritten to match — a
shape no internal check can see — is still refused. A violation on this path
SHALL block the emission (exit 4, the tripwire contract) and SHALL name the
missing records.

#### Scenario: The partition is total and disjoint

- **WHEN** an ingestion completes merge and every cleansed record appears in
  exactly one project family
- **THEN** the census check passes and nothing is reported
- **AND** the emitted document's record count equals the cleansed record count

#### Scenario: A record is lost between cleanse and merge

- **WHEN** a cleansed record appears in no project family
- **THEN** the census check names the record and blocks the emission
- **AND** nothing is written: `projects.json`, the TSVs, and the viewer data stay
  as they were

#### Scenario: A record appears in two families

- **WHEN** a cleansed record appears in more than one project family
- **THEN** the census check names the record and both families, and blocks the
  emission
- **AND** nothing is written

#### Scenario: The census check sees the family set the payload carries

- **WHEN** a manual correction confirms a merge that unions two records into one
  family, so the merged family count is one lower than the uncorrected count
- **THEN** the census check compares the cleansed records against the corrected
  family set
- **AND** the tripwire report and the run report state the corrected family
  count, which is the count the emitted document carries

#### Scenario: A rebuild from emitted state refuses a document that lost a record

- **WHEN** a document to be rebuilt carries one record fewer than its own record
  count states
- **THEN** the rebuild refuses the document and names the missing record
- **AND** nothing is written: `projects.json`, the TSVs, and the viewer data stay
  as they were

#### Scenario: A rebuild refuses a document whose count was rewritten to match

- **WHEN** a document lost a record and its own record count was rewritten so
  that the count agrees with the records it carries, and the output tree holds a
  `clean.tsv` naming the lost record
- **THEN** the rebuild compares the document against that `clean.tsv`, names the
  lost record, and refuses the document
- **AND** nothing is written

#### Scenario: A rebuild refuses a document whose family lost its anchor

- **WHEN** a document's family names an anchor record that its own nodes do not
  carry
- **THEN** the rebuild names the family and its missing anchor and refuses the
  document
- **AND** the run does not fail with an unhandled error

#### Scenario: A rebuild of a complete document proceeds

- **WHEN** a document to be rebuilt carries every record its count states, every
  family's members in that family's nodes, and every family's anchor among them
- **THEN** the rebuild proceeds and emits the document
- **AND** the output tree's `clean.tsv`, where present, holds exactly the
  records the document carries

## ADDED Requirements

### Requirement: The proof of the partition is re-derivable from the emitted files

The system SHALL provide a read-only means of re-deriving the partition of an
emitted dataset from the emitted files themselves — the document, the cleansed
record file, and the merged record file — so a reader can confirm that every
cleansed record sits in exactly one family, that no record sits in two, and
that no family holds a record the cleansing does not, without trusting the
run that produced them. The proof SHALL name the counts it compared, and a
record it cannot account for SHALL be named rather than counted.

#### Scenario: The partition is re-derived from the emitted files

- **WHEN** the emitted document, the cleansed record file and the merged record
  file are read
- **THEN** the proof reports the record count each file holds, the number of
  records appearing in two families, the number of cleansed records in no
  family, and the number of family members the cleansing does not hold
- **AND** the proof states plainly whether the partition is total and disjoint

#### Scenario: A record in no family is named

- **WHEN** a cleansed record appears in no family of the emitted document
- **THEN** the proof names that record
- **AND** the proof does not report the partition as total
