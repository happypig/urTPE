## ADDED Requirements

### Requirement: A confirmed pair links regardless of score

When the correction ledger holds a merge confirmation whose two records are both
present, the system SHALL place the two records in the same project family
whatever their similarity score. The confirmation SHALL add exactly one link;
the similarity rule, the 0.7 link threshold and the feature weights SHALL stay
unchanged for every other pair. The merged family SHALL be anchored and named by
the standing anchor rule, so a confirmed pair whose newest record carries a
wrong count still needs that count corrected by its own ledger entry.

#### Scenario: 吉林676's typo row joins its unit

- **WHEN** the ledger confirms 編號 1303 (2010-03-25, `676地號等1筆`) with 編號 1347
  (2008-12-31, `676地號等18筆`) — scored 0.567 by the similarity rule — and
  corrects 1303's land count to 18
- **THEN** 1303 and 1347 form one family
- **AND** the family's project_id is `中山區-吉林段四小段-676地號等18筆`
- **AND** no family `中山區-吉林段四小段-676地號等1筆` is emitted

#### Scenario: A confirmation without the count correction

- **WHEN** the ledger confirms the 1303 ↔ 1347 pair but does not correct 1303's
  land count
- **THEN** the pair still forms one family
- **AND** its project_id carries the anchor's count, `…676地號等1筆`, because the
  anchor rule is unchanged

#### Scenario: Unconfirmed borderline pairs are unaffected

- **WHEN** two records score between 0.5 and 0.7 and no confirmation names them
- **THEN** they are not merged, exactly as before

## MODIFIED Requirements

### Requirement: Surface fragment families as merge candidates

After discovery, the system SHALL detect fragment families: families whose discovered Taipei cases ALL anchor (per the per-node case linkage) inside a single different family. Each detected fragment SHALL be review-flagged on its anchor record (臨界對-style review output — listing the main family it anchors into and the overlapping case count) — detection only; no automatic merge is performed. Families whose discovered cases anchor across multiple main families, or nowhere, SHALL NOT be flagged by this rule. A person answers a flag by appending a merge confirmation to the correction ledger; after the next ingestion the confirmed fragment is part of the main family and is no longer flagged.

#### Scenario: Single-case fragment inside a main family
- **WHEN** family 南港段一小段-101地號等41筆 (1 record) has its only discovered case 10809251 anchored inside 南港段一小段-19-1地號等34筆
- **THEN** the fragment family is review-flagged as a merge candidate of 南港段一小段-19-1地號等34筆

#### Scenario: Mixed anchoring is not flagged
- **WHEN** a family's discovered cases anchor into two or more different families (or partly nowhere)
- **THEN** no merge-candidate flag is raised (ambiguous evidence)

#### Scenario: Flags are review output only
- **WHEN** fragment families are detected
- **THEN** the flag lands in review output (review_flags / report) without mutating family membership or records

#### Scenario: A confirmed fragment is no longer flagged
- **WHEN** the ledger confirms 編號 1303 with 編號 1347 and the gazette is ingested again
- **THEN** no record carries the `片段家族合併候選` flag naming `中山區-吉林段四小段-676地號等1筆` or `中山區-吉林段四小段-676地號等18筆`
