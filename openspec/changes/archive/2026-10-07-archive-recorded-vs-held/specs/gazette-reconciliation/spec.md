## ADDED Requirements

### Requirement: A predecessor that is recorded but not held is reported, not substituted

The system SHALL report that no comparison was possible when the publication preceding
the ingested one is recorded in the archive index but its document is not held, naming
that publication.

The system SHALL NOT fall back to an earlier publication in that case. Comparing against
a non-adjacent publication and presenting the result as an adjacent one attributes one
publication's changes to another: the interval's approval counts, record totals,
historical movement and calendar change all describe the span rather than either
publication.

#### Scenario: The predecessor is recorded but its document is absent

- **WHEN** a gazette is ingested and its immediate predecessor is recorded but its document is not held
- **THEN** the report states that the named predecessor is recorded but not held
- **AND** the report states that no comparison was possible
- **AND** no earlier publication is compared against instead

#### Scenario: No predecessor is recorded at all

- **WHEN** a gazette is ingested and the archive records no earlier publication
- **THEN** the report states that no comparison was possible
- **AND** the two states are distinguishable, because one names a publication and the other does not

#### Scenario: The persisted conclusion records the absence

- **WHEN** a comparison concludes that the predecessor was recorded but not held
- **THEN** the persisted change set carries that reason
- **AND** it does not carry counts derived from a non-adjacent comparison

#### Scenario: An ordinary adjacent comparison is unaffected

- **WHEN** a gazette is ingested and its immediate predecessor is both recorded and held
- **THEN** the comparison proceeds and reports the two publications compared
- **AND** the reported absence does not appear