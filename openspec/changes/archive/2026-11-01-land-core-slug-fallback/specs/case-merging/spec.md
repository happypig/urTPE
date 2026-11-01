# case-merging Delta

## MODIFIED Requirements

### Requirement: Anchor a family on its latest approval

The system SHALL designate the anchor of each family as the record with the newest 核定日期, breaking ties deterministically (closest to 編號 1), and SHALL derive project_id from the anchor's normalized name-core, never from 編號. The slug's count component SHALL be the anchor's `land_count`; when the anchor carries none, the system SHALL use the count of the newest family member that carries one, scanning from the anchor outward by 編號 order. The `?` placeholder SHALL remain only when no member of the family carries a count, and that case SHALL be review-flagged on the anchor so an unresolved identity is visible rather than silent.

#### Scenario: Anchor is the newest by date
- **WHEN** a family spans approvals from 2013 to 2026
- **THEN** the anchor is the 2026 approval regardless of its 編號 position
- **AND** the anchor is flagged is_current

#### Scenario: project_id is stable across revisions
- **WHEN** a new 變更(第N次) approval for the same unit is added later
- **THEN** the family's project_id does not change
- **AND** the new approval becomes the anchor by date

#### Scenario: Coverage change re-anchors to the newest state
- **WHEN** the latest approval has a newer parcel configuration than earlier members (e.g. 13筆 supersedes 11筆)
- **THEN** project_id reflects the latest state's name-core

#### Scenario: The anchor carries no count but a family member does
- **WHEN** the anchor's 案名 declares no count (`land_count` null) while another member of the same family carries one (e.g. the unit's earlier 擬訂 printed 地號等1筆)
- **THEN** project_id uses that member's count, not the `?` placeholder
- **AND** the two broken identities (寶清段一小段51-13, 崇仁新村青年段一小段711-3) resolve to real land cores

#### Scenario: No member carries a count
- **WHEN** no record in the family declares a count
- **THEN** project_id keeps the `?` placeholder
- **AND** the anchor is review-flagged naming the missing identity component
