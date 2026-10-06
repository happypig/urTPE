## ADDED Requirements

### Requirement: Node order survives a rebuild from emitted state

A rebuild that starts from an emitted graph rather than from the gazette SHALL restore
each node's calendar ordering before the family's approvals are ordered. Ordering keys
SHALL be derived from the node's own approval date and never from 編號, which is a
coordinate that shifts as the city prepends and re-dates rows, so an ordering that
degrades to 編號 silently inverts a project's timeline.

Because such a rebuild reads the emitted payload as its input, a node missing its
ordering key would otherwise re-emit in the same wrong order on every subsequent run,
making the inversion permanent rather than transient.

#### Scenario: A node's ordering key is restored from its date

- **WHEN** an emitted node carries a date but no ordering key
- **THEN** the key is reconstructed from that date
- **AND** it is never left at its empty default while the node carries a date

#### Scenario: Approvals order by date, not by 編號

- **WHEN** a family's members are 編號 1362 dated 2008-01-02 (變更) and 編號 1407 dated 2005-02-24 (擬訂)
- **THEN** the rebuilt graph emits 1407 before 1362
- **AND** the anchor is highlighted rather than placed first, since 編號 order and date
  order disagree for this family

#### Scenario: No dated node is left unordered

- **WHEN** an emitted payload is examined node by node
- **THEN** no node carrying a date carries the empty ordering key