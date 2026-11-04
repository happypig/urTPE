## MODIFIED Requirements

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
