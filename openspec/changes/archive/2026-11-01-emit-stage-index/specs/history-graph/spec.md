# history-graph Delta

## ADDED Requirements

### Requirement: Stage index survives a rebuild from emitted state

Every emitted node SHALL carry its `stage_index`, and loading an emitted document
SHALL reconstruct each node's `stage_index` — from the emitted key when present,
otherwise derived from the node's stage text by the same rule the cleanser
applies — so that a rebuild from emitted state groups section branches
(`stage_index`, `track`) identically to the original build. The round trip
emit → load → emit SHALL be lossless for `stage_index`.

#### Scenario: A section-branch family forms the same edges on rebuild

- **WHEN** a project family holds records whose `area_section` values differ
  (甲/A/B) across distinct stages, the document is emitted, and then rebuilt via
  the emitted-state loader
- **THEN** the section-branch edges (`kind: "section"`) formed on the rebuild are
  identical to those formed on the original build
- **AND** no node loads with the sentinel `-1` unless its stage text yields no
  index on the original build either

#### Scenario: An already-deployed document without the key repairs on load

- **WHEN** a loader reads an emitted node that carries no `stage_index` key
- **THEN** the index is derived from the node's stage text (the cleanser's
  `_stage` rule)
- **AND** the resulting grouping matches what a fresh ingest of the same rows
  would produce

#### Scenario: The round trip is lossless

- **WHEN** a document is emitted, loaded, and emitted again
- **THEN** every node's `stage_index` is identical across the two emissions
