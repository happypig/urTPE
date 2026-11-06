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

#### Scenario: Parcel search returns r_progress cases
- **WHEN** the system searches 玉泉段二小段 with 母號 40
- **THEN** numeric case_ids are extracted from `r_progress_detail.aspx?case_id=<digits>` detail URLs

#### Scenario: Internal codes are not used as detail ids
- **WHEN** an entry's `case_id` field is an internal code but its `details` URL carries a numeric id
- **THEN** the numeric id is used

#### Scenario: Non-progress cases are filtered out
- **WHEN** an entry's details URL does not point at `r_progress_detail.aspx`
- **THEN** it is excluded

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

