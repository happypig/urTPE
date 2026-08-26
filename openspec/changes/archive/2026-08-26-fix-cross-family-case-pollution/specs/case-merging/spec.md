# case-merging — Delta: fragment-family merge candidates

## ADDED Requirements

### Requirement: Surface fragment families as merge candidates

After discovery, the system SHALL detect fragment families: families whose
discovered Taipei cases ALL anchor (per the per-node case linkage) inside a
single different family. Each detected fragment SHALL be review-flagged on
its anchor record (臨界對-style review output — listing the main family it
anchors into and the overlapping case count) — detection only; no automatic
merge is performed. Families whose discovered cases anchor across multiple
main families, or nowhere, SHALL NOT be flagged by this rule.

#### Scenario: Single-case fragment inside a main family
- **WHEN** family 南港段一小段-101地號等41筆 (1 record) has its only
  discovered case 10809251 anchored inside 南港段一小段-19-1地號等34筆
- **THEN** the fragment family is review-flagged as a merge candidate of
  南港段一小段-19-1地號等34筆

#### Scenario: Mixed anchoring is not flagged
- **WHEN** a family's discovered cases anchor into two or more different
  families (or partly nowhere)
- **THEN** no merge-candidate flag is raised (ambiguous evidence)

#### Scenario: Flags are review output only
- **WHEN** fragment families are detected
- **THEN** the flag lands in review output (review_flags / report) without
  mutating family membership or records
