# gazette-reconciliation — delta for recover-truncated-rows-via-api

## ADDED Requirements

### Requirement: A row the reader recovered is not reported as a publisher edit

When a run completes publisher-truncated rows from the city's APIs, those rows SHALL be
reported under their own count, distinct from re-dated and edited historical rows. The
predecessor is re-read without the recovery pass, so a recovered row is absent from the
previous side by construction; recording that absence as an edit asserts a change to the
published list that did not happen — the same misattribution the corpus exclusion fixes for
a reader that dropped rows (measured 2026-10-07, 13 rows reported as "edited"). The
persisted change set SHALL carry the count as its own field, outside both the authoritative
signals and the unresolvable movement: nothing the city published changed, so it is not
movement, and the cause is known exactly, so it is not unresolvable.

Only rows this run actually completed SHALL leave the edit count. A run that recovers
nothing SHALL record zero rather than omit the field.

#### Scenario: A flagged re-ingestion's four completions are not edits

- **WHEN** a gazette is ingested with `--recover-truncated` and this run recovers 4 rows
  whose land is absent from the predecessor's unflagged read
- **THEN** the report states `recovered by this reader: 4` and names each row
- **AND** those 4 rows are not counted among the edited rows
- **AND** the persisted change set records `recovered: 4` with `unresolvable.edited`
  counting only rows whose land the city actually changed

#### Scenario: A run without the flag records zero

- **WHEN** a comparison runs on a gazette ingested without `--recover-truncated`
- **THEN** the persisted change set records `recovered: 0`
- **AND** an ordinary historical edit in the same comparison is still counted as edited
