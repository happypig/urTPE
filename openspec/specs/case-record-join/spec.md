# case-record-join Specification

## Purpose

Defines how case ids join across the three fields that carry them
(`recovery.cases`, `api_cases`, `links.taipei`), so a consumer never attaches the
wrong case's timeline to a record and never misses a pair because the same case
is spelled two ways.

## Requirements

### Requirement: Case ids normalise to a single space before any join

The system SHALL provide a case-id normalisation that maps the R-form
(`R089213-02`) to its numeric registry form (`089213`), and every join keyed on
case id SHALL compare normalised ids. The stored fields SHALL keep their source
spellings verbatim: normalisation is a read-side rule, never a rewrite of the
emitted data.

#### Scenario: The same case in two spellings joins

- **WHEN** one field holds `R089213-02` and another holds `089213` for the same
  application
- **THEN** a join on the normalised ids matches them
- **AND** neither stored field is rewritten

#### Scenario: A numeric id is its own normalisation

- **WHEN** both fields hold numeric ids
- **THEN** the join behaves as an exact string match
- **AND** the normalisation adds no transformation

### Requirement: Recovery's binding wins precedence over the discovery candidate set

When a record's `recovery.cases` and its project's `links.taipei` disagree on
which case ids anchor that record, the recovery binding SHALL take precedence:
it is the four-check-verified binding (truncated-row-recovery), while
`links.taipei` is the discovery candidate set for the family. The
`ambiguous-zone` flag on a recovery SHALL be carried through as provenance on
the joined result — it marks that the choice was made under ambiguity, and SHALL
NOT be treated as a reason to prefer the discovery set.

#### Scenario: Recovery chose a subset of the discovery candidates

- **WHEN** a record's recovery chose 2 of the 6 cases in `links.taipei` (the
  recno 1005 payload)
- **THEN** a consumer asking for the record's anchoring case ids receives the
  recovery's 2, with the discovery set available as context
- **AND** the `ambiguous-zone` flag travels with the result

#### Scenario: The fields agree

- **WHEN** recovery's cases and the discovery candidates coincide
- **THEN** the join is the common set
- **AND** no precedence decision is needed
