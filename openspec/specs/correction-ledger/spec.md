# correction-ledger Specification

## Purpose

Records manual data corrections as durable, append-only entries keyed on stable content rather than on the per-gazette 編號, and re-applies them on every rebuild. This replaces one-off scripts that patch emitted output in place, which a rebuild silently reverts.

## Requirements

### Requirement: Record corrections as append-only entries

The system SHALL record each manual correction as an entry appended to a durable ledger, capturing the publication it applies to, the record it matches, the field changed, the new value, the reason, who made it, and when. Entries SHALL only ever be appended; correcting a mistake SHALL mean appending a superseding entry.

#### Scenario: A correction is recorded

- **WHEN** a person corrects the 事業種類 of one record from 其他 to 事業計畫
- **THEN** an entry is appended naming the record, the field, the new value, the reason, the author, and the timestamp
- **AND** no existing entry is modified

#### Scenario: A correction is itself wrong

- **WHEN** a recorded correction is found to be incorrect
- **THEN** a new entry is appended that supersedes it
- **AND** the superseded entry remains in the ledger as history

#### Scenario: An accepted record removal is recorded

- **WHEN** a person verifies with the city that a record was legitimately removed from the list
- **THEN** an entry is appended recording that acceptance, which permits a later ingestion that finds the record missing

### Requirement: Match corrections on stable content, not on 編號

The system SHALL identify the record a correction applies to by its land core and approval date, never by 編號, because 編號 is a position within one publication and shifts whenever approvals are prepended.

#### Scenario: The same case appears at a different 編號

- **WHEN** a correction recorded against a record that was 編號 621 in one publication is applied to a later publication in which that record is 編號 631
- **THEN** the correction is applied, because it is matched on land core and approval date

#### Scenario: A correction no longer matches any record

- **WHEN** a correction's land core and approval date match no record in the gazette being processed
- **THEN** the correction is reported as unmatched rather than being applied to a different record
- **AND** the ingestion itself is not aborted

### Requirement: Apply corrections on every rebuild

The system SHALL apply all applicable ledger entries after cleansing and before project families are formed, so that a full rebuild reproduces every correction rather than reverting it.

#### Scenario: A rebuild reproduces prior corrections

- **WHEN** the pipeline is re-run over a previously ingested gazette
- **THEN** every matching correction is applied again and the emitted records carry the corrected values
- **AND** no manual correction previously applied by other means is lost

#### Scenario: Corrections affect project identity

- **WHEN** a correction changes a field that participates in a project's identity
- **THEN** the corrected value is used when forming project identities
- **AND** the resulting identity change is reported by reconciliation

#### Scenario: A systematic rule replaces an individual correction

- **WHEN** a correction is superseded by a general cleansing rule that handles the case for every record
- **THEN** the rule applies and the ledger entry remains recorded as history

### Requirement: Report applied corrections

The system SHALL report how many ledger entries were applied, how many were unmatched, and which, so that corrections are visible in the normal run output rather than only in the ledger file.

#### Scenario: Corrections are visible in the run report

- **WHEN** an ingestion applies 12 ledger entries and finds 1 unmatched
- **THEN** the review report states both figures and names the unmatched entry
- **AND** the report also states that 12 manual corrections were applied

#### Scenario: Ledger is empty

- **WHEN** the ledger contains no entries
- **THEN** the report states that no manual corrections were applied
