# truncated-row-recovery Specification

## Purpose

Restores gazette records that the publisher's row-height truncation pushed out of the
dataset, by re-identifying them in the city's own case APIs and map service and re-emitting
them with auditable provenance. Opt-in; without the flag nothing changes.

## ADDED Requirements

### Requirement: The recovery is opt-in and the default run is untouched

The system SHALL perform recovery only when the run carries `--recover-truncated`. A run
without the flag SHALL produce output byte-identical to the previous behaviour, SHALL NOT
make recovery-related network requests, and SHALL still exclude and name truncated records
as before.

#### Scenario: Default run is byte-identical

- **WHEN** the pipeline runs without `--recover-truncated` on a gazette containing truncated
  rows
- **THEN** raw.tsv, merged.tsv, projects.json and the run report are identical to the
  pre-change output
- **AND** no request is sent to `gis.uro.taipei/ashx/` or `zonegeo.udd.gov.taipei/` for
  recovery purposes

### Requirement: Truncated rows are re-identified from their own surviving cells

The system SHALL derive the identity search key from the truncated row's own cells — the
section and first parcel parsed from the 案名 (hyphen-split into 母號/子號), and the declared
parcel-count fragment — and SHALL query `Get_updcase_list(sectstr, monobuf, sunobuf)`, then
`get_project168_top` for each name-matching candidate. A candidate SHALL be accepted only
when all of the following hold, each checked independently:

1. **Same unit.** The candidate's district and 段/小段 match the row's.
2. **The surviving name is contained.** The row's surviving 案名 fragment, normalised, is a
   substring of the candidate's `CASE_NAME` (or reaches the similarity fallback band with
   the count fragment matching).
3. **The declared count appears.** The candidate name carries the declared count
   (e.g. `等74筆(原54筆)`).
4. **The date closes.** The gazette 核定日期 equals the candidate's `uro_chk_date` or
   `uro_chk_date2`; a ±1-day match is accepted but flagged.

Accepted rows SHALL be emitted into the merge with provenance (case_id, source endpoint,
date-check result) and an audit entry. A row with no qualifying candidate SHALL stay
excluded and named (residual).

#### Scenario: 編號 79 is recovered from its own 案名

- **WHEN** the truncated row 編號 79 (2026/1/14, 松山區, 案名 surviving
  `美仁段二小段694地號等74筆(原54筆)`) is recovered
- **THEN** `Get_updcase_list(美仁段二小段, 0694, 0000)` returns a case whose name contains
  `74筆(原54筆)`
- **AND** `get_project168_top` for that case returns `uro_chk_date = 2026-01-14`, equal to
  the gazette date
- **AND** the row is emitted with land core from the 案名, provenance case `R098505`, and an
  audit entry

#### Scenario: The date may be in either stage field

- **WHEN** the matching candidate carries its approval date in `uro_chk_date2` rather than
  `uro_chk_date` (e.g. 變更(第三次) 權利變換 cases)
- **THEN** the date check passes on the field that matches
- **AND** the provenance records which field closed the check

#### Scenario: A ±1-day match is flagged, not silent

- **WHEN** the closest candidate's approval date differs from the gazette date by one day
- **THEN** the row is accepted only when no exact-date candidate exists
- **AND** the provenance flags the date delta

#### Scenario: A row the APIs do not know stays a named residual

- **WHEN** no candidate satisfies the four checks for a truncated row
- **THEN** the row stays excluded
- **AND** the run report names it as residual, distinct from recovered rows

### Requirement: Same-unit same-date cases attach together

When several accepted candidates share the same unit and the same approval date (zone pairs
such as 雙園段二小段505 變更(第二次) -A區/`09610233` and -B區/`09610237`, both 2017-12-12),
the row SHALL attach all of them, and the attachment SHALL be flagged
`ambiguous-zone`. The row SHALL keep a single land core taken from its own 案名; the zone
split SHALL NOT split the land core or the project.

#### Scenario: 編號 930 attaches both zone cases

- **WHEN** row 930 (2017/12/12, 雙園段二小段505地號等77筆) matches API cases `09610233`
  (-A區) and `09610237` (-B區) on the same date
- **THEN** both case ids are attached with provenance
- **AND** the row is flagged `ambiguous-zone`
- **AND** the project's land core remains 雙園段二小段505地號等77筆

### Requirement: Parcel-list completion is two-tiered and never inferred from the count alone

The recovered row's parcel list SHALL come from the PDF fragment. When the unit's case id is
in the R-form of the GeoServer boundary layer (`uro-redevelop-ALL-5`) and a boundary polygon
exists, the system MAY reconstruct the full unit list by intersecting the boundary with
`LAND-ALL-TWD97` restricted to the row's 段/小段, under the calibrated membership rule
(measured 2026-10-26, `poc_findings.md` T8): a candidate parcel carries at least one ring
vertex strictly inside the boundary polygon, and — when it is not already visible in the
fragment — sorts after the fragment's last visible parcel in gazette order, because the
printed list is complete-sorted up to the cut and a true member outside the fragment must
sort after it. The reconstruction is accepted only when all of the following hold, each
checked independently:

1. **The fragment is contained.** Every parcel visible in the PDF fragment (after
   normalized typo repair) appears among the candidate parcels.
2. **The count closes.** The reconstructed list's parcel count equals the 案名's declared
   count. When it does not, the reconstruction is refused as a whole — a subset SHALL
   never be selected to force the count.
3. **The surplus is explained.** A candidate excluded from the reconstruction either sorts
   before the fragment's last visible parcel (the publisher would have printed it before
   the cut) or has no ring vertex inside the boundary; no other exclusion mechanism
   exists, and no parcel outside the membership rule is ever included to reach the
   declared count. A containment-fraction threshold alone SHALL NOT be used as the test
   (measured: boundary-touching neighbours and true members overlap in fraction).

Where any condition fails, the row SHALL carry the PDF fragment flagged `partial`. A
GIS-verified defect in the fragment (e.g. the city's `78-1` where the cadastre has
`718-1`) MAY be repaired, and SHALL be flagged `normalized` when it is. The full list SHALL
never be produced from the declared count alone.

#### Scenario: The 虎林段 unit's full list is reconstructed

- **WHEN** the recovered rows of 虎林段四小段38地號等138筆(原120筆) (case `R089601`) are
  completed
- **THEN** the boundary ∩ `LAND-ALL-TWD97` candidate set (148 parcels) is reduced to the
  declared 138 by the calibrated membership rule (positional tail + vertex containment)
- **AND** every one of the 113 parcels visible in the PDF fragment is present
- **AND** the 25 added parcels are exactly the continuation of the truncated series
  (`93-17`…`93-41`)
- **AND** the row is flagged with the list source (`gazette fragment + GIS tail`)

#### Scenario: A reconstruction that does not close the count is refused

- **WHEN** the calibrated membership rule yields a reconstructed list whose count differs
  from the declared count (美仁段 `R098505`: 72 fragment + 3 tail candidates = 75 vs
  declared 74)
- **THEN** the reconstruction is refused and no subset is selected to force the count
- **AND** the row keeps the PDF fragment flagged `partial`

#### Scenario: A numeric-form unit keeps its fragment flagged partial

- **WHEN** a recovered row's matching case id is numeric-form (e.g. `09610233`), for which
  no boundary polygon exists
- **THEN** the row keeps the PDF fragment flagged `partial`
- **AND** no list is invented from the declared count

#### Scenario: A GIS-verified fragment typo is repaired with a flag

- **WHEN** the PDF fragment contains `78-1` where the cadastre and the API's own unit name
  establish `718-1`
- **THEN** the fragment is repaired to `718-1`
- **AND** the repair is flagged `normalized` in the record and named in the run report

### Requirement: The run report never presents a recovered gazette as faithful

The run report SHALL state, alongside the emitted count: the number of truncated rows
recovered (naming each with its provenance), and the number still excluded (residual),
naming each. Both lines SHALL appear whenever either count is non-zero, and the report
SHALL continue to state that the emitted dataset is not a faithful copy of the publication
when any row was excluded or recovered.

#### Scenario: The report splits recovered from residual

- **WHEN** a run recovers 14 rows and leaves 1 residual
- **THEN** the report shows `RECOVERED: 14 …` naming each row and its provenance, and
  `INCOMPLETE: 1 …` naming the residual
- **AND** the not-a-faithful-copy statement remains

### Requirement: Recovery is parse-time, single-writer, and bounded

Recovery SHALL run inside the normal ingestion pass whenever the flag is on, including
re-ingestion of archived gazettes (each publication's conclusion is rewritten per the
archive's design). Recovery SHALL NOT run outside the single-writer lock, and its request
volume SHALL remain bounded (parcel-keyed lookups only; no enumeration sweeps).

#### Scenario: Re-ingesting an archived gazette with the flag recovers its rows

- **WHEN** an archived gazette is re-ingested with `--recover-truncated`
- **THEN** its truncated rows are recovered under the same checks
- **AND** the archive's change set for that publication is rewritten, consistent with the
  archival design

#### Scenario: The recovery makes no enumeration requests

- **WHEN** recovery runs for any number of rows
- **THEN** every API request is keyed by a section+parcel from a surviving cell or an
  already-known identity
- **AND** no request pattern enumerates parcels or sections
