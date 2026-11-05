## ADDED Requirements

### Requirement: Emitted review flags carry a stable order

The system SHALL emit a record's `review_flags` in a **stable order** that does
not depend on the order the pipeline happened to raise them. The order SHALL be
the case id the flag names (ascending, compared as text), then the flag text.

A flag that names no case id SHALL sort before the flags that do, by its text.

The set of flags on a record SHALL NOT change: the same distinct flags are
emitted, each once. Only their positions change. The requirement exists because
the order was otherwise a function of the pipeline's traversal order — a
ledger merge that reorders one family's members reordered the flags on the
nodes it touched, with nothing in the data to say so.

#### Scenario: Two orphan flags on one node keep a fixed order

- **WHEN** a node carries `孤兒案件未達相似度門檻(案10908274:0.54<0.70:…)` and `孤兒案件未達相似度門檻(案11411017:0.54<0.70:…)`
- **THEN** the emitted flags list the `10908274` flag before the `11411017` flag
- **AND** the two flags are the only flags on the node

#### Scenario: The order does not depend on the merge that produced it

- **WHEN** the same node's flags are raised in the reverse order
- **THEN** the emitted flag list is identical, byte for byte

#### Scenario: A flag that names no case id sorts first

- **WHEN** a node carries `階段與平台案件狀態不一致(公報變更(第二次)/平台變更)` and `孤兒案件未達相似度門檻(案10908274:0.54<0.70:…)`
- **THEN** the emitted flags list the 階段 flag before the 孤兒 flag

#### Scenario: No flag is added or lost

- **WHEN** a record's flags are sorted
- **THEN** the set of distinct flags is unchanged
- **AND** each distinct flag appears once

#### Scenario: A duplicate flag still collapses to one

- **WHEN** a record's flags carry the same string three times
- **THEN** the emitted record carries that string once
