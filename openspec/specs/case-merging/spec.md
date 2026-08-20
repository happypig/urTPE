# case-merging Specification

## Purpose

Links the approvals of one 更新單元 across stages, sections, and land-coverage changes into a project family, and derives a stable, append-friendly project_id anchored on the family's latest approval.

## Requirements

### Requirement: Link records by similarity

The system SHALL link two records into the same project family when their similarity is at least 0.7, computed over section match, first-parcel match or alias, parcel-set overlap, land-count bridge (原N筆), named anchor, with implementer as corroboration only.

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

### Requirement: Anchor a family on its latest approval

The system SHALL designate the anchor of each family as the record with the newest 核定日期, breaking ties deterministically (closest to 編號 1), and SHALL derive project_id from the anchor's normalized name-core, never from 編號.

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

### Requirement: Emit merged dataset

The system SHALL emit merged.tsv containing every record with its project_id, unit-level fields, is_current flag, and review flags, preserving traceability to the source 編號.

#### Scenario: Complete coverage of records
- **WHEN** the merge step finishes
- **THEN** every record in clean.tsv appears exactly once in merged.tsv with a project_id
- **AND** the record's source 編號 is preserved