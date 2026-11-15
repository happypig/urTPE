## MODIFIED Requirements

### Requirement: The refresh verifies view-verified ids by the city's own case name

The refresh SHALL verify every id in the cache's `view_verified_case_ids` against the city's own case name for that id (get_project168_top `CASE_NAME`, persisted per case), deciding by the land core at `LINK_THRESHOLD = 0.7` against the unit's land core (the core that the project id spells when the id is a unit id, otherwise the cache's own land core): match → keep; no match → remove the id from `view_verified_case_ids` and record it in `view_rejected` with its reason (shape A / shape B); the 相關連結 label is compared only for the reason text, and a label mismatch with a matching city name SHALL NOT reject. A missing city name SHALL NOT reject. The verification SHALL run on every cache holding `view_verified_case_ids`, whether or not its cases await an approval, because the defect does not depend on the awaiting state.

A city name whose land core does not match SHALL still be kept when it declares the **same district and section** as the cache's own land core **and** one of the unit's **own parcels** (the parcels of the unit's 地號 cell). The gazette prints two parcel lists for one unit and they can start with different parcels, so the land core, which keys on the first parcel, can differ while the case belongs to the unit. A name in the same section that declares none of the unit's own parcels is another unit and SHALL still be rejected. When the refresh has no list of the unit's own parcels, the land-core rule alone decides, as before.

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


## ADDED Requirements

### Requirement: The refresh heals a cache land core that disagrees with its project id

A unit's project id is the slug of its land core: `{district}-{section}-{first parcel}地號等{count}筆`. When the project id has that shape and the cache's land core differs from the core the id spells, the refresh SHALL use the id's core for every decision that compares a case name with the unit (the re-decision of a recorded rejection and the view-verified verification), SHALL write the id's core into the cache, and SHALL name the project in its report with the old and the new core. A cache whose land core already equals the id's core SHALL report nothing. A project id that does not have the unit-id shape (a `-N` twin, a `未解析-N` id, an id with an unknown count) SHALL keep the cache's own land core and SHALL be healed of nothing. A cache whose land core is empty SHALL be healed from a unit id.

#### Scenario: A wrong district is healed in one refresh

- **WHEN** the refresh runs on the cache of 大同區-市府段二小段-220-2地號等54筆 whose land core reads 中正區…
- **THEN** the cache's land core reads 大同區市府段二小段220-2地號等54筆 afterwards
- **AND** the report names the project with the old and the new core

#### Scenario: A correct land core reports nothing

- **WHEN** the refresh runs on a cache whose land core equals the core its project id spells
- **THEN** the report names no healed land core

#### Scenario: A twin id keeps the cache's land core

- **WHEN** the project id is 大同區-市府段二小段-220-2地號等54筆-2
- **THEN** the refresh keeps the cache's own land core and heals nothing

#### Scenario: An empty land core is filled from the id

- **WHEN** a cache of a unit id has an empty land core
- **THEN** the refresh writes the core the id spells
