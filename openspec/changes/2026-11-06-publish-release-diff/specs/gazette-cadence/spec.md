## MODIFIED Requirements

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
