## ADDED Requirements

### Requirement: A repeated discovery run does not re-raise a flag it already raised

Where discovery compares a record's published stage against the platform case it anchored to
and finds them inconsistent, the disagreement SHALL be flagged. Raising that flag SHALL be
idempotent: re-running discovery over unchanged input SHALL NOT add a second copy of a flag
the record already carries.

A flag that has already been raised is evidence about the record, not an event that occurred
again. Counting occurrences instead of recording the finding makes an emitted dataset a
counter of how many times the pipeline has run, which is not a property of the gazettes.

#### Scenario: The disagreement is flagged on first observation

- **WHEN** discovery compares a record's published stage with the stage of the platform case it anchored to and they differ
- **THEN** the record carries a flag describing the disagreement

#### Scenario: A second run does not flag it again

- **WHEN** discovery runs again over the same records and the same anchored case
- **THEN** the record still carries exactly one copy of that flag
- **AND** no additional copy is added

#### Scenario: The flag text is unchanged by repetition

- **WHEN** a flag has already been raised for a disagreement
- **THEN** repeating the comparison produces the same flag text and adds nothing
- **AND** the flags a record carries are unchanged in content and count

#### Scenario: Distinct disagreements are still all reported

- **WHEN** a record carries flags for two different conditions
- **THEN** both appear, once each
- **AND** deduplication does not collapse flags that differ in text

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