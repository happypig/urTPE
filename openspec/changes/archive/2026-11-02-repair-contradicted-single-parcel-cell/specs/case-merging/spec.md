# Delta: case-merging

## ADDED Requirements

### Requirement: A repaired contradiction no longer splits its family

When cleansing repaired a single-parcel 地號 cell contradiction (the
data-cleansing rule), the affected record SHALL link into its family by the
standing similarity rule with no threshold or weight change: the repaired
parcel set removes the spurious Jaccard zero, so identical section +
first-parcel + count scores at or above 0.7.

#### Scenario: The 615 twin dissolves

- **WHEN** the corpus contains the repaired recno 759 (案名 615地號1筆) alongside recno 536/314/84 of the same unit
- **THEN** recno 759 joins the family of 536/314/84
- **AND** the family's project_id is `內湖區-文德段二小段-615地號等1筆` with no `-2` dedup sibling
