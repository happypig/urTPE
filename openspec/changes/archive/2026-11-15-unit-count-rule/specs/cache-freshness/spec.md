## MODIFIED Requirements

### Requirement: The refresh verifies view-verified ids by the city's own case name

The refresh SHALL verify every id in the cache's `view_verified_case_ids` against the city's own case name for that id (get_project168_top `CASE_NAME`, persisted per case), deciding by the land core at `LINK_THRESHOLD = 0.7` against the unit's land core (the core that the project id spells when the id is a unit id, otherwise the cache's own land core): match → keep; no match → remove the id from `view_verified_case_ids` and record it in `view_rejected` with its reason (shape A / shape B); the 相關連結 label is compared only for the reason text, and a label mismatch with a matching city name SHALL NOT reject. A missing city name SHALL NOT reject. The verification SHALL run on every cache holding `view_verified_case_ids`, whether or not its cases await an approval, because the defect does not depend on the awaiting state.

A city name whose land core does not match SHALL still be kept when it declares the **same district and section** as the unit's land core, one of the unit's **own parcels** (the parcels of the unit's 地號 cell), **and** a declared parcel count that passes the count rule below. The gazette prints two parcel lists for one unit and they can start with different parcels, so the land core, which keys on the first parcel, can differ while the case belongs to the unit. A name in the same section that declares none of the unit's own parcels is another unit and SHALL still be rejected. When the refresh has no list of the unit's own parcels, the land-core rule alone decides, as before.

The **count rule**: a name passes when its declared count (`等N筆`), or one of its `原N筆` values, equals the unit's count at any approval of the unit. The unit's counts are the cache's `own_counts` together with the unit's own land-core count. The count rule guards the own-parcel form only; a name whose land core matches the unit's at `LINK_THRESHOLD` is kept without it. When the cache holds no `own_counts`, the unit's land-core count is the only count, so the narrower rule decides, and the refresh SHALL name the ids it decided that way.

#### Scenario: A fully-approved cache is still verified

- **WHEN** a cache holds `view_verified_case_ids` but no case awaits an approval (the awaiting-approval selector would skip it)
- **THEN** the view-verified verification still runs on it

#### Scenario: Shape B rejection is recorded

- **WHEN** the city's own case name for a view-verified id names another project while the label matches (09511211 on 大安區-大安段一小段-557)
- **THEN** the id leaves `view_verified_case_ids`
- **AND** `view_rejected[09511211]` records reason "label is right, id is wrong (shape B)"

#### Scenario: The verification does not depend on the awaiting state

- **WHEN** the refresh runs on a cache whose only defect is a foreign view-verified id
- **THEN** the id is verified and recorded even though no milestone changed

#### Scenario: A case that names another of the unit's own parcels is kept

- **WHEN** the project 萬華區-華中段一小段-247地號等26筆 (cell parcels `247、248、201-2、…、366-13`) has view-verified ids 09305081 and 09407302, and the city names them `…華中段一小段201-2、352地號等26筆…-A區` and `…-B區` (land core `201-2`, similarity 0.45)
- **THEN** both ids stay in `view_verified_case_ids`
- **AND** neither id is recorded in `view_rejected`

#### Scenario: A case in the same section that names none of the unit's parcels is rejected

- **WHEN** the project 信義區-犁和段一小段-102地號等3筆 has view-verified id 09608220, and the city names it `…信義區犁和段一小段165地號等20筆…`, and `165` is not one of the unit's own parcels
- **THEN** the id leaves `view_verified_case_ids`
- **AND** `view_rejected[09608220]` records reason "label and city name name another project (shape A)"

#### Scenario: A case of the same parcel in another district is rejected

- **WHEN** a view-verified id's city name carries one of the unit's own parcel numbers but names another district or another section
- **THEN** the id is rejected, because the section check fails first

#### Scenario: Without a parcel list the land-core rule alone decides

- **WHEN** the refresh runs without the unit's own parcel list and the city name's land core scores below 0.7
- **THEN** the id is rejected exactly as before this change

#### Scenario: A wrong land core in the cache does not decide a case

- **WHEN** the project 大同區-市府段二小段-220-2地號等54筆 has a cache whose land core reads 中正區市府段二小段220-2地號等54筆, and view-verified id 09609301 has the city name `…大同區市府段二小段220-2地號等54筆…`
- **THEN** the id stays in `view_verified_case_ids`, because the unit's land core is the one the project id spells
- **AND** the id is not recorded in `view_rejected`

#### Scenario: A drifted name with an equal declared count is kept

- **WHEN** the project 萬華區-華中段一小段-247地號等26筆 holds `own_counts` containing 26 and the city names view-verified id 09305081 `…201-2、352地號等26筆…-A區`
- **THEN** the id stays in `view_verified_case_ids`

#### Scenario: A name with a count the unit never had is rejected

- **WHEN** a view-verified id's city name declares the unit's own district, section and one of its own parcels, and a count (`等N筆`, and any `原N筆`) that is none of the unit's counts at any approval
- **THEN** the id leaves `view_verified_case_ids` and is recorded in `view_rejected`

#### Scenario: A count the unit had at an earlier approval passes

- **WHEN** the city names the id with one of the unit's own parcels and a count that the unit's earlier approval declared, and the unit's latest count differs
- **THEN** the id is kept

#### Scenario: No counts means the equal-count rule, and the report says so

- **WHEN** the cache holds no `own_counts` and a view-verified id is decided by the own-parcel form
- **THEN** only the unit's land-core count counts as equal
- **AND** the report names the ids decided without `own_counts`


## ADDED Requirements

### Requirement: The cache carries the unit's declared counts

The system SHALL persist, in each project's cache beside the unit's own parcels, the declared parcel counts the unit had at every approval (each record's land count and original count), as a sorted list of distinct integers. Discovery SHALL write it on a new cache and SHALL bring a cached result's list up to the payload's, writing only on change. A cache written before the field existed SHALL load with an empty list. An empty list SHALL be a named state in the refresh report, never a silent fallback.

#### Scenario: A new cache carries the counts

- **WHEN** discovery runs for a project whose records declared 4 and 13 parcels
- **THEN** the cache's counts are `[4, 13]`

#### Scenario: A cached result follows the payload

- **WHEN** discovery finds a cache whose counts are empty or differ from the project's
- **THEN** it writes the project's counts and writes nothing when they are equal

#### Scenario: An old cache loads

- **WHEN** a cache written before the field existed is loaded
- **THEN** its counts are an empty list and loading raises no error
