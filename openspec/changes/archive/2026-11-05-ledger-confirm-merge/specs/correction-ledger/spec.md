## ADDED Requirements

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

## MODIFIED Requirements

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
