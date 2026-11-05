# case-merging Specification

## Purpose

Links the approvals of one 更新單元 across stages, sections, and land-coverage changes into a project family, and derives a stable, append-friendly project_id anchored on the family's latest approval.
## Requirements
### Requirement: Link records by similarity

The system SHALL link two records into the same project family when their
similarity is at least 0.7, computed over section match, first-parcel match
or alias, parcel-set overlap, land-count bridge (原N筆), named anchor, with
implementer as corroboration only.

A site-shrink approval SHALL link across the shrink: when district, section
and first parcel match exactly **and** one record's `orig_count` equals the
other's `land_count` — the gazette's own `(原N筆)` declaring the continuity —
the similarity SHALL be computed without the parcel-Jaccard term, the
surviving components normalised over their sum (the empty-parcel rule's
redistribution), with the count bridge counting as a full match. A plan
change that replaces the parcel set SHALL NOT split its family because the
new parcels do not overlap the old ones.

#### Scenario: Stage approvals of one unit link together
- **WHEN** the same unit has 擬訂 and 變更(第N次) approvals with matching section, first parcel, and overlapping parcels (e.g. 永昌段三小段159's six approvals)
- **THEN** all of them are placed in the same project family

#### Scenario: Same section and implementer but different parcels stay separate
- **WHEN** the same section and implementer have approvals on distinct parcels (e.g. 中華工程 寶清段 57-13 vs 57-2 vs 57 vs 51-3)
- **THEN** each parcel group forms its own family and the groups are not merged

#### Scenario: Section-split approvals merge
- **WHEN** one unit is approved as separate A區段 and B區段 records with identical parcel sets (e.g. 逸仙段二小段151)
- **THEN** the A and B records belong to the same family

#### Scenario: Coverage change links across parcel generations
- **WHEN** one record is "513-3地號等11筆" and a later record is "513-3地號等13筆(原11筆)" with the same section and implementer
- **THEN** they are linked into the same family despite the changed parcel count

#### Scenario: A site shrink links across the replaced parcel set
- **WHEN** recno 978 is "…吳興段二小段790-6地號等4筆(原29筆)…" and recno 1157 is
  "…吳興段二小段790-6地號等29筆…" — same district, section and first parcel,
  the shrink's `orig_count` (29) equals the older approval's `land_count`,
  and the parcel sets share 1 of 32
- **THEN** the pair links at 1.0 (section .35 + first parcel .2 + count
  bridge .1, normalised over the surviving weights)
- **AND** the family keeps one project_id, one national page and one case set

#### Scenario: Eleven measured shrink pairs link
- **WHEN** the corpus carries the 11 measured shrink pairs (吳興790-6, 中山202,
  中正44, 犁和89, 桃源251, 立農513, 南港566, 玉成545, 芝蘭130, 玉泉91, 金華719)
- **THEN** each pair's shrink record joins its older family
- **AND** no pair stays split on the Jaccard term alone

#### Scenario: A coincidental count match without a shrink does not bridge
- **WHEN** two same-section records share a first parcel and a count value
  but neither carries an `(原N筆)` linking its `orig_count` to the other's
  `land_count`
- **THEN** the standing similarity rule decides the pair unchanged

#### Scenario: Renumbering links via alias
- **WHEN** two records share a section and implementer and one record's parcel equals the other's 原地號 alias
- **THEN** they are linked into the same family

#### Scenario: Named-anchor units link without parcels
- **WHEN** two records share a named anchor (e.g. 原東星大樓基地) with no parcel overlap
- **THEN** they are placed in the same family

#### Scenario: Borderline pairs are flagged, not linked
- **WHEN** two records score between 0.5 and 0.7
- **THEN** they are NOT merged automatically
- **AND** the pair is recorded in the review report for confirmation

#### Scenario: Singletons are their own family
- **WHEN** a record has no similarity link above 0.7 to any other record
- **THEN** it forms a family of one

#### Scenario: Empty parcel lists no longer cap the score below the link threshold
- **WHEN** both records have unparseable (empty) parcel sets but agree on district, section, first parcel, and land count
- **THEN** the similarity is computed without the vanished Jaccard term, allowing the pair to link at 0.7 or above

#### Scenario: Identical land links across an implementer change
- **WHEN** two records share the same land key but different implementers (e.g. 南港段一小段531地號等2筆, 台灣肥料 → 愛山林)
- **THEN** they are placed in the same project family

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

### Requirement: Emit merged dataset

The system SHALL emit merged.tsv containing every record with its project_id, unit-level fields, is_current flag, and review flags, preserving traceability to the source 編號.

#### Scenario: Complete coverage of records
- **WHEN** the merge step finishes
- **THEN** every record in clean.tsv appears exactly once in merged.tsv with a project_id
- **AND** the record's source 編號 is preserved

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

