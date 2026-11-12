## ADDED Requirements

### Requirement: A joined node carries implementation per case

A node whose anchored case ids number 2 or more and whose cases each carry an
implementation payload SHALL emit `implementation_by_case` on the node — the
per-case snapshots keyed by case id (joined-node-section-callouts, user
decision 2026-11-12: 在負載中按案例發出). The single `implementation`
snapshot (the D5 statistics pick) SHALL stay unchanged for existing
consumers. The field survives a `--from-js` reload. A node anchoring fewer
than 2 cases with payloads SHALL NOT carry the key.

#### Scenario: A joined node emits both sections

- **WHEN** 敦化363-1 node 537 anchors 10906101 (-A區) and 10906102 (-B區),
  and both payloads carry Ulic_Date (2025/04/29 and 2025/05/06)
- **THEN** the emitted node carries `implementation_by_case` with both
  snapshots keyed by their case ids

#### Scenario: A single-case node stays as it is

- **WHEN** a node anchors one case with a payload
- **THEN** the node carries the single `implementation` snapshot and no
  `implementation_by_case`

#### Scenario: The field survives a rebuild from emitted state

- **WHEN** the payload is reloaded with `--from-js` and re-emitted
- **THEN** `implementation_by_case` is unchanged
