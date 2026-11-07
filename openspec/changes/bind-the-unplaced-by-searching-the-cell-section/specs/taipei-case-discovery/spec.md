## MODIFIED Requirements

### Requirement: Search city cases by land parcel via the Taipei JSON API

The system SHALL discover city-platform case_ids by POSTing to the Taipei
platform's `ashx/Get_updcase_list.ashx` endpoint with the project's 地段小段
and first parcel, extracting numeric detail ids from each result's `details`
URL.

The search SHALL ask for **every parcel of the unit**, not only the first one
the gazette prints. A case the city indexes under a parcel other than the
unit's first is the same unit's case: the 臨沂段三小段412 case is indexed
under parcel 414, and the 復興段一小段3 case is indexed under parcels 7, 7-1
and 20-3.

The search SHALL ask for **both section forms the unit is known under** when
the gazette's 案名 and 地號 columns disagree. The 案名 says 河堤五小段 and the
地號 cell says 河堤段五小段; the city indexes the 地號 cell's form. A search
that returns nothing under the 案名's form SHALL retry the 地號 cell's form
before the unit is declared unresolved.

A case found under a parcel or a section form other than the node's own SHALL
still be accepted only on the resolver's own name-and-date acceptance test.

#### Scenario: Parcel search returns r_progress cases
- **WHEN** the system searches 玉泉段二小段 with 母號 40
- **THEN** numeric case_ids are extracted from `r_progress_detail.aspx?case_id=<digits>` detail URLs

#### Scenario: Internal codes are not used as detail ids
- **WHEN** an entry's `case_id` field is an internal code but its `details` URL carries a numeric id
- **THEN** the numeric id is used

#### Scenario: Non-progress cases are filtered out
- **WHEN** an entry's details URL does not point at `r_progress_detail.aspx`
- **THEN** it is excluded

#### Scenario: A case indexed under another parcel of the same unit is found
- **WHEN** the unit 臨沂段三小段 declares parcels 412, 412-1, 413, 413-1, 414, 414-1, 415, 415-1, 418, 419, 420 and 421, and the search for 412 returns no case naming 412 while the search for 414 returns case 10305021
- **THEN** the search over the unit's parcels finds case 10305021
- **AND** the case is offered to the resolver for acceptance

#### Scenario: A case indexed under the 地號 cell's section is found
- **WHEN** the 案名 says 河堤五小段 and the 地號 cell says 河堤段五小段, and the search for 河堤五小段 returns nothing while the search for 河堤段五小段 returns case 11005053
- **THEN** the search over the unit's section forms finds case 11005053

### Requirement: A second id source, confirmed by the case header

The system SHALL discover city-platform case ids from a **second source** when
the parcel search does not return them: the city's 168 list
(`ashx/Get_project168.ashx`), whose entries name the case ids of the 168
fast-track programme.

A case id from that list SHALL enter the project's case ids only when its own
case header (`ashx/get_project168_top.ashx`) confirms it: the header SHALL
return a row that names the case and carries its 案名. A header that returns
nothing SHALL NOT confirm the id, and the id SHALL NOT enter the case list.

The header confirmation exists because the list is a register of cases, not of
the project's cases: an id can name a case in another unit. The 案名 the header
carries is the city's own name for the case, and it is what the resolver's
name step matches against.

The id SHALL be **appended** to the project's case list, never inserted — the
positional fallback binds by index, so the existing ids keep their positions.

#### Scenario: A case the parcel search omitted is confirmed and added

- **WHEN** the parcel search for a project returns no case id, and the 168 list
  names an id whose header returns a row with the case's 案名
- **THEN** the id is appended to the project's case list
- **AND** the id's milestones are read like every other case's

#### Scenario: An unconfirmed id is not added

- **WHEN** an id from the 168 list has no header row
- **THEN** the id does not enter the project's case list
- **AND** the case is named in the refresh report as unconfirmed

#### Scenario: An id the search already returned is not added twice

- **WHEN** the 168 list names an id the parcel search already returned
- **THEN** the id is not appended a second time

#### Scenario: The existing ids keep their positions

- **WHEN** an id is appended to a project's case list
- **THEN** the ids already in the list keep their order

## ADDED Requirements

### Requirement: A third id source, the national portal's title search

The system SHALL discover city-platform case ids from a **third source** when
the parcel search and the 168 list both return nothing: the national portal's
own search (`twur.nlma.gov.tw/zh/urban/rebuild/0?title=<段小段>&city_id=2`),
whose result pages name the unit's view id and whose 相關連結 block names the
city case ids.

The 懷生段一小段928 case is not indexed by the parcel search under any
section form the gazette prints. The portal's title search finds it, and the
page's 相關連結 names case 10002141.

An id read from a portal page SHALL enter the project's case ids only when
the case's own header (`ashx/get_project168_top.ashx`) confirms it: the header
SHALL return a row that names the case and carries its 案名. A header that
returns nothing SHALL NOT confirm the id.

The id SHALL be **appended** to the project's case list, never inserted.

#### Scenario: A case the parcel search does not index is found by the portal

- **WHEN** the parcel search for 懷生段一小段 parcel 928 returns nothing under
  every section form the gazette prints, and the national portal's title
  search returns a view page whose 相關連結 names case 10002141
- **THEN** the id is read from the page
- **AND** the header for 10002141 returns a row naming the case, so the id is
  appended to the project's case list

#### Scenario: A portal id without a header confirmation is not added

- **WHEN** the national portal's title search returns a view page whose
  相關連結 names an id whose header returns no row
- **THEN** the id does not enter the project's case list
- **AND** the case is named in the refresh report as unconfirmed

#### Scenario: The portal's own view id is recorded too

- **WHEN** the national portal's title search returns a view page for the unit
- **THEN** the view id and its URL are recorded on the project
- **AND** the national milestones read from that page are recorded
