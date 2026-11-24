# taipei-case-discovery Specification

## Purpose
Discovers city-platform (臺北市都市更新審議服務平台, gis.uro.taipei) case_ids and
milestone timelines directly from the platform's internal `ashx` JSON APIs —
searching by land parcel (地段小段 + 母號 + 子號) rather than scraping
JavaScript-rendered pages or depending on the national portal — so every
project with a stable parcel basis gets authoritative milestone dates without
manual curation.
## Requirements
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

The search SHALL ask for **the section form the city uses** when the gazette
omits the 段 from the 段 name. The gazette prints 吳興一小段 where the city
indexes 吳興段一小段. A section that already carries its 段 SHALL NOT gain
another form — the city keeps the 段 the gazette prints (臨沂段三小段), so no
request is spent on an alternative.

The search SHALL continue to the next form while a form yields **no case that
survives the name guard**. A body of another unit's cases is not an answer:
the search for 萬華段一小段 returns five cases of other units, and the unit's
own case lives under the 地號 cell's form.

The name guard SHALL keep a case whose own name declares **any of the unit's
own parcels**, not only the searched one, **and whose declared count passes the
count rule**: the name's `等N筆`, or one of its `原N筆`, SHALL equal the unit's
count at any approval — a count the unit's caches hold or the count of the
unit's own land core. The city indexes a case under whichever parcel it lists
first, and that is not always the unit's first: 臨沂段三小段412's case
10305021 is indexed under 414 while its name declares 412, and its count
matches the unit's, so the guard keeps it. A name that declares an own parcel
and a count the unit never declared SHALL be refused and named in the rejected
evidence: it is the shape of the 54 pairs the count rule refuses (measured
2026-11-24, e.g. 正義段三小段418's neighbour 419等9筆 against the unit's 10).

The name guard SHALL keep the two older forms unchanged: a name that declares
**the searched parcel itself** needs no count test, and the legacy **stem form**
(a name carrying the pre-subdivision stem) SHALL keep its current behaviour —
its cross-listings are a separate open decision (F8 option C) and this change
does not decide them. A parcel-less name SHALL still be admitted only by
corroboration.

A case declaring a parcel of a DIFFERENT unit SHALL still be dropped.

A case found under a parcel or a section form other than the node's own SHALL
still be accepted only on the resolver's own name-and-date acceptance test.

When the caller passes no counts, the count rule SHALL fall back to the unit's
own land-core count alone (the narrower rule, the same fallback the §8 gate
uses); this state is a named behaviour, not a silent widening.

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

#### Scenario: A case indexed under the section form the city uses is found
- **WHEN** the 案名 says 吳興一小段 and the city indexes 吳興段一小段, and the search for 吳興一小段 returns nothing while the search for 吳興段一小段 returns case 10611051
- **THEN** the search finds case 10611051

#### Scenario: A section that already carries its 段 is asked once
- **WHEN** the section is 臨沂段三小段
- **THEN** the search asks for 臨沂段三小段 only

#### Scenario: The walk continues past a body the guard empties
- **WHEN** the search for 萬華段一小段 parcel 519-2 returns five cases whose names declare other parcels, and the search for the 地號 cell's form 萬大段一小段 returns case 10903061
- **THEN** the search finds case 10903061

#### Scenario: A case naming another of the unit's own parcels is kept
- **WHEN** the search for 臨沂段三小段 parcel 414 returns case 10305021, whose name declares parcel 412, and 412 is one of the unit's own parcels, and the name's declared count equals a count the unit declared at one of its approvals
- **THEN** the case is kept

#### Scenario: A case of another unit is still dropped
- **WHEN** the search for 吳興一小段 parcel 330 returns a case whose name declares 58, and 58 is not one of the unit's parcels
- **THEN** the case is dropped and named in the rejected evidence

#### Scenario: An own-parcel name with an undeclared count is refused
- **WHEN** the search for 正義段三小段 parcel 418 returns case 09810291, whose name declares parcel 419 (one of the unit's own parcels) with the count 等九筆 (9), and the unit's counts at every approval are 10
- **THEN** the case is refused with a reason naming the count, and is recorded in `search_rejected`
- **AND** the refusal does not depend on which parcel the search asked for

#### Scenario: A count of an earlier approval passes the guard
- **WHEN** a case's name declares one of the unit's own parcels with a count the unit declared at an earlier approval (a count its cache holds), as 華興段一小段8's case 09708111 does with 13
- **THEN** the case is kept

#### Scenario: The searched parcel itself needs no count
- **WHEN** a case's name declares the searched parcel with a count the unit never declared
- **THEN** the case is kept (the count rule does not widen to the exact form)

#### Scenario: The stem form keeps its behaviour
- **WHEN** a case's name carries the pre-subdivision stem of the searched parcel (e.g. 大龍段一小段265地號 while the unit is 265-7), with or without a passing count
- **THEN** the guard's verdict is the one it gives today, whichever way it falls (the stem form's cross-listings await F8 option C)

#### Scenario: No counts passed falls back to the land-core count
- **WHEN** the caller passes the unit's parcels without counts and the case name declares an own parcel with a count equal to the unit's land-core count
- **THEN** the case is kept
- **AND** when the count differs from the land-core count, the case is refused

### Requirement: Fetch milestone timelines per case via the Taipei JSON API

The system SHALL fetch each case's 階段辦理過程 timeline by POSTing its case_id
to `ashx/Get_project168_second.ashx`, mapping response fields to labelled
milestones via the fixed field map, skipping empty values, and normalising ISO
datetimes to dates.

#### Scenario: Milestones resolve for a known case
- **WHEN** the timeline for case_id 10110181 is fetched
- **THEN** labelled milestones including 核定日期 2020/11/17 are returned

#### Scenario: Empty fields produce no milestones
- **WHEN** a response row has empty date fields
- **THEN** those labels are omitted

#### Scenario: Error or malformed response yields empty dict
- **WHEN** the API errors after retries or returns non-JSON
- **THEN** the milestone dict is empty and discovery continues

### Requirement: Handle compressed responses

The system SHALL detect gzip-compressed HTTP bodies via magic bytes and
decompress before decoding.

#### Scenario: Gzipped body is decompressed
- **WHEN** a body starts with gzip magic bytes
- **THEN** it is decompressed before UTF-8 decoding

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

### Requirement: A third id source, the national portal's title search

The system SHALL discover city-platform case ids from a **third source** when
the parcel search and the 168 list both return nothing: the national portal's
own search (`twur.nlma.gov.tw/zh/urban/rebuild/0?title=<段小段>&city_id=2`),
whose result pages name the unit's view id and whose 相關連結 block names the
city case ids.

The 懷生段一小段928 case is not indexed by the parcel search under any
section form the gazette prints. The portal's title search finds it, and the
page's 相關連結 names case 10002141.

The portal's title search returns **every unit in the 段小段**, not the one
asked for: 臨沂段三小段's page names four units (412, 318, 370, …) and
懷生段一小段's names four (928, 121-4, 32, 931). A row of another unit is
not this project's case, so a row SHALL be scoped by the unit's own parcel —
the same scope the 168 list uses, and for the same reason.

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

#### Scenario: A row of another unit is not read

- **WHEN** the national portal's title search for 懷生段一小段 returns a page
  for parcel 931, and the unit's own parcel is 928
- **THEN** that page's ids are not read, and its view id is not recorded

#### Scenario: A portal id without a header confirmation is not added

- **WHEN** the national portal's title search returns a view page whose
  相關連結 names an id whose header returns no row
- **THEN** the id does not enter the project's case list
- **AND** the case is named in the refresh report as unconfirmed

#### Scenario: The portal's own view id is recorded too

- **WHEN** the national portal's title search returns a view page for the unit
- **THEN** the view id and its URL are recorded on the project
- **AND** the national milestones read from that page are recorded

