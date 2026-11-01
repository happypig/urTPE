# history-graph Delta

## ADDED Requirements

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
