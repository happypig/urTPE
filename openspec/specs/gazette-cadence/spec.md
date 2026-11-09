# gazette-cadence Specification

## Purpose

Detects when the city publishes a new approved-cases gazette and acquires it, without a
human watching the page, and without mistaking the city's re-upload of an unchanged PDF for
a new publication.
## Requirements
### Requirement: Detect a new gazette by content, not by timestamp

The system SHALL decide whether a newly published gazette exists by comparing the content
it retrieves against what it already holds, and SHALL NOT use a server-reported
last-modified time to make that decision.

The publisher re-uploads the same PDF and advances its timestamp without changing its
content, so a timestamp comparison reports a new gazette where there is none. A
timestamp is recorded as provenance and never used as evidence of change.

#### Scenario: The publisher re-uploads an unchanged PDF under a new timestamp

- **WHEN** the gazette page's PDF link resolves to a document whose content hash matches one already archived
- **THEN** no new gazette is ingested
- **AND** the check reports that the publisher re-uploaded an unchanged document
- **AND** the newer timestamp is recorded as provenance rather than as a change

#### Scenario: A genuinely new gazette is published

- **WHEN** the gazette page's PDF link resolves to a document whose content hash matches no archived document
- **THEN** the document is archived as a new gazette with its publication date and hash

#### Scenario: The page advances its timestamp without changing the PDF link

- **WHEN** the page's own content changes but the PDF it links to is unchanged
- **THEN** no gazette is ingested
- **AND** the reason is reported as an unchanged document rather than as a silent success

### Requirement: Report every check, including the ones that find nothing

The system SHALL record an outcome for every check it performs, so that a missed
publication is distinguishable from a period in which no check ran. A check that finds
nothing SHALL be recorded with that outcome, at the time it ran.

The recorded outcome SHALL include the publisher URL the document was retrieved
from, when one was retrieved. The publisher serves one URL at a time and
repoints it on every publication, so the URL that served a document is
provenance that is lost unless it is written down at the time — and a
version-specific URL remains a durable address for that document afterwards
(measured 2026-11-06: the URL that served the 2026-10-15 gazette still serves
the 2026-10-15 document, a different digest from the current one, while a
fabricated path answers 404).

A check that finds nothing new SHALL still record the URL, because the city
repointing its link without changing the document is exactly the event that
would otherwise lose the association between an address and a publication.

#### Scenario: A check finds nothing new

- **WHEN** a check completes and no new gazette exists
- **THEN** an outcome is recorded stating that no new gazette was found, with the time of the check
- **AND** the absence of an ingestion for that period is explained by the record

#### Scenario: The sequence of checks stops

- **WHEN** no check has been recorded for longer than the expected interval
- **THEN** the gap is detectable from the records alone, without inspecting the publisher
- **AND** a missing check is therefore distinguishable from a check that found nothing

#### Scenario: The check cannot reach the publisher

- **WHEN** the gazette page cannot be retrieved
- **THEN** the failure is recorded as a failed check with its time and cause
- **AND** it is not recorded as a successful check that found nothing new

#### Scenario: A new gazette is retrieved from a version-specific URL

- **WHEN** the check downloads a document from `…/relfile/18558/10496/<uuid>.pdf`
- **THEN** the recorded outcome names that URL
- **AND** the archived document's index entry carries the same URL

#### Scenario: The publisher repoints its link without changing the document

- **WHEN** the check finds content it already holds, served from a URL it did not serve that content from before
- **THEN** the recorded outcome names the URL the document was served from
- **AND** the outcome still reports that the content is unchanged

### Requirement: An unattended check cannot overwrite an emitted dataset

A check SHALL NOT write to the emitted dataset. Acquisition SHALL deposit a gazette into
the archive only, and any ingestion of an archived gazette into the emitted dataset SHALL be
an explicit separate act that acquires the single-writer lock.

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

#### Scenario: An unattended run publishes a derived report

- **WHEN** an unattended run regenerates the release-diff report from the archive
- **THEN** no file under the emitted output tree is written
- **AND** no gazette is ingested
- **AND** only the paths the publication step owns are staged for commit

#### Scenario: The publication push fails

- **WHEN** the report is regenerated and committed but the push does not land
- **THEN** the step reports the failure and exits non-zero
- **AND** the served report is reported stale by the deployment check, because it is not the committed build

### Requirement: The acquired gazette is provably the archived one

The system SHALL verify that an acquired gazette's content matches its archive entry
before treating it as ingested, and SHALL refuse to record an ingestion whose input cannot
be matched to a hashed archive member.

#### Scenario: The served document does not match the archived copy

- **WHEN** the content of the document offered for ingestion does not match the hash recorded for its archive member
- **THEN** the ingestion is refused
- **AND** the mismatch is reported

#### Scenario: An archive entry exists with no hash

- **WHEN** an archived gazette's index entry carries no content hash
- **THEN** the entry cannot be used to prove provenance and the gap is reported
- **AND** the entry is identified as needing a hash rather than being treated as verified

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

