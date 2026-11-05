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

The system SHALL apply all applicable ledger entries after cleansing and before project families are formed, so that a full rebuild reproduces every correction rather than reverting it. Every ingestion of a gazette document SHALL read the ledger at its default location (`corrections.jsonl` beside the gazette archive, overridable by environment or by an explicit ledger path) without the operator naming it; an operator SHALL NOT be able to drop every correction by omitting an option. An absent ledger file SHALL mean that no corrections exist and SHALL be reported as such. A rebuild from an already-emitted dataset keeps the families as emitted and therefore keeps every correction applied when they were formed.

#### Scenario: A rebuild reproduces prior corrections

- **WHEN** the pipeline is re-run over a previously ingested gazette
- **THEN** every matching correction is applied again and the emitted records carry the corrected values
- **AND** no manual correction previously applied by other means is lost

#### Scenario: The ledger applies without an explicit option

- **WHEN** a gazette is ingested and the operator names no ledger path
- **THEN** the ledger at the default location is read and its entries are applied
- **AND** the run report states how many corrections were applied

#### Scenario: No ledger file exists yet

- **WHEN** a gazette is ingested and the default ledger file does not exist
- **THEN** the ingestion completes
- **AND** the report states that no manual corrections were applied

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

### Requirement: Confirm a merge between two records

The ledger SHALL accept a merge-confirmation entry that names two records, each by
its land and approval date (the same content key as a field correction, never
編號), together with the reason, the author and the timestamp. A confirmation
SHALL change no field of either record; it SHALL only state that the two records
belong to one project family. A confirmation SHALL be superseded the same way as
any other entry, by appending a later entry that names it.

When either named record is absent from the gazette being processed, the
confirmation SHALL be reported as unmatched, SHALL link nothing, and SHALL NOT
abort the ingestion.

#### Scenario: A person confirms a flagged merge candidate

- **WHEN** a person appends a merge confirmation naming 編號 1303
  (`臺北市中山區吉林段四小段676地號等1筆土地`, 2010-03-25) and 編號 1347
  (`臺北市中山區吉林段四小段671-3、…、688地號等18筆土地`, 2008-12-31), with the
  reason that the city's case 09703184 names the unit `676地號等18筆`
- **THEN** the entry is appended with both keys, the reason, the author and the
  timestamp
- **AND** no field of either record changes because of it

#### Scenario: One named record is missing

- **WHEN** a merge confirmation names a record whose land and date match no record
  in the gazette being processed
- **THEN** the run report lists the confirmation as unmatched
- **AND** no family is linked because of it
- **AND** the ingestion completes

#### Scenario: Confirmations are counted in the run report

- **WHEN** an ingestion applies 1 field correction and 1 merge confirmation
- **THEN** the review report states 2 manual corrections applied and names the
  merge confirmation with both of its keys

