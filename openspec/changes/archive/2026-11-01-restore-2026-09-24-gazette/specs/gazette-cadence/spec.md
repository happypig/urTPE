# gazette-cadence Delta

## Purpose

Restoring a publication into the middle of the archived chain invalidates the change set
that spans the gap it closes. This delta makes the repair explicit: the insertion moves a
predecessor link, and the affected comparisons are re-derived and superseded rather than left
contradicting each other on disk.

## ADDED Requirements

### Requirement: Restoring a publication re-derives the change sets its insertion invalidates

When a publication is restored into the archive at a position between two already-recorded
publications, the system SHALL re-derive every comparison whose predecessor link the
insertion changed, and SHALL mark the superseded change-set files so that exactly one live
change set per transition remains. The re-derivation SHALL read both publications under the
current reader; it SHALL NOT reuse counts recorded under a reader whose version differs.

#### Scenario: A restored gazette becomes the predecessor of an already-ingested one

- **WHEN** a publication is restored into the chain between an ingested predecessor and an
  ingested successor, and the successor's live change set names the old predecessor
- **THEN** a new change set is derived from the restored publication to the successor under
  the current reader
- **AND** the old change-set file is superseded — renamed or marked so the live set is
  unambiguous — with its content preserved

#### Scenario: The transition the gap had skipped gains its change set

- **WHEN** a restoration closes a gap so that two adjacent publications had no comparison on
  record
- **THEN** a change set for that transition is derived and persisted
- **AND** it is indistinguishable in form from any other persisted change set

#### Scenario: The restoration is refused without explicit approval

- **WHEN** a restoration with its re-derivation is offered and the operator has not approved
  the ingestion act
- **THEN** nothing is written: the archive, the index, and the change sets are unchanged
- **AND** the offered restoration is described with its expected effects instead

### Requirement: The restored publication's own ingestion reconciles against its predecessor

When a restored publication is ingested, the reconciliation SHALL run against the
publication the chain names as its predecessor, and the calendar comparison SHALL reflect the
calendars actually read from the two documents. A boundary publication — one whose calendar
differs from its predecessor's — SHALL reconcile successfully: a calendar change is reported,
never a refusal.

#### Scenario: The boundary publication reconciles across the calendar change

- **WHEN** a publication whose dates are Gregorian is ingested against a predecessor whose
  dates are ROC
- **THEN** the reconciliation reports the calendar change
- **AND** the ingestion proceeds and writes its output
