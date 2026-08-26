# taipei-implementation-data — Delta: milestones source provenance

## ADDED Requirements

### Requirement: Emit milestones source map

While merging per-case stage milestones into the project-level
`milestones_taipei` (last-write-wins per label), the system SHALL additionally
record which case won each label into an additive optional
`milestones_source` map (label → case_id) attached to the project links.
Labels merged from implementation payloads SHALL resolve to the payload's
provenance case_id. The map SHALL be absent when no case provided any
milestone. `schema_version` is unchanged and existing consumers are
unaffected.

#### Scenario: Single carrying case provable for 建照
- **WHEN** only one anchored case's stage milestones contain 建照核發日期
  (e.g. case 10011041 in 金華段四小段513-3, whose four sibling cases carry none)
- **THEN** `milestones_source["建照核發日期"]` equals that case_id even after
  the merge

#### Scenario: Later case overwrites and wins the map entry
- **WHEN** two cases carry different 建照核發日期 values and the merge keeps
  the later case's value
- **THEN** `milestones_source["建照核發日期"]` names that winning case, so the
  viewer can attribute the slot truthfully

#### Scenario: No milestones at all
- **WHEN** every case returns empty stage milestones and no implementation
  dates exist
- **THEN** no `milestones_source` map is attached and nothing else changes

### Requirement: Construction slots are provenance-complete

Every emitted 建照核發日期/開工日期/使照核發日期 value SHALL resolve to its
source at the viewer: a carrying case via `milestones_source` or the
implementation payload's `case_id` exact match, or the national portal via
使用核發日期. The resolution chain SHALL require no heuristics. A slot that
resolves by none of these SHALL render as isolated (no source edge, no
provenance label) and SHALL be reported by the corpus provenance validation
with its family, slot, and value.

#### Scenario: Stage label resolves via source map
- **WHEN** 建照核發日期 exists in `milestones_taipei`
- **THEN** `milestones_source` names the case whose value won the merge

#### Scenario: Implementation date resolves via case_id
- **WHEN** 開工日期/使照核發日期 equals the best implementation payload's date
- **THEN** the slot resolves to that payload's `case_id`

#### Scenario: National-only 使照 resolves via the 國 mapping
- **WHEN** 使照核發日期 is absent from Taipei milestones but 使用核發日期 exists
- **THEN** the slot resolves to the national portal (green source group)

#### Scenario: Unresolvable slot is reported
- **WHEN** a slot value resolves by none of the resolution paths
- **THEN** the corpus provenance validation fails listing the family, slot,
  and value, and the event renders as isolated rather than misattributed
