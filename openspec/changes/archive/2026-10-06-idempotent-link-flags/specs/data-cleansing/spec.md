## ADDED Requirements

### Requirement: Emitted review flags carry no duplicates

The emitted dataset SHALL NOT contain the same review flag string more than once on a single
record. Where duplicates exist from earlier runs, the next emission SHALL collapse them,
preserving the order in which the flags were first raised, and no distinct finding SHALL be
lost.

#### Scenario: A record emitted with duplicates

- **WHEN** a record's flags were accumulated by earlier runs and contain the same string more than once
- **THEN** the emitted record carries that string once
- **AND** the flags appear in the order they were first raised

#### Scenario: Nothing is lost by collapsing

- **WHEN** duplicates are collapsed during emission
- **THEN** the set of distinct flags a record carries is unchanged
- **AND** the count of records carrying at least one flag is unchanged