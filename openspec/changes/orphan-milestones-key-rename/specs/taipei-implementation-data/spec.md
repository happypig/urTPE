## MODIFIED Requirements

### Requirement: Construction slots are provenance-complete

Every emitted 建照核發日期/開工日期/使照核發日期 value SHALL resolve to its
source at the viewer: a carrying case via `milestones_source` or the
implementation payload's `case_id` exact match, or the national portal via
使用核發日期. The resolution chain SHALL require no heuristics. A slot that
resolves by none of these SHALL render as isolated (no source edge, no
provenance label) and SHALL be reported by the corpus provenance validation
with its family, slot, and value. When two cases carry the SAME value for a
slot, the FIRST case read SHALL win the `milestones_source` credit — in the
stage-milestone merge and in the 擬訂 plan-case date pick alike (board D4a,
user decision 2026-11-05: 15 corpus dates in 11 projects credited a later
case, e.g. 榮星53's 建照 2006/07/11 held by both 北區 09001120 and 南區
09001123 was credited to 09001123).

#### Scenario: Stage label resolves via source map
- **WHEN** 建照核發日期 exists in `milestones_taipei`
- **THEN** `milestones_source` names the case whose value won the merge

#### Scenario: An equal value credits the first case read
- **WHEN** two 擬訂 plan cases -A區 (09001120) and -B區 (09001123) both hold
  建照核發日期 2006/07/11, and -A區 is read first (榮星53 shape)
- **THEN** `milestones_source["建照核發日期"]` names 09001120

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
