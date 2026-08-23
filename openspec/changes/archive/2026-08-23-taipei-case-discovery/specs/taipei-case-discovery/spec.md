## Purpose

Discovers city-platform (臺北市都市更新審議服務平台, gis.uro.taipei) case_ids and
milestone timelines directly from the platform's internal `ashx` JSON APIs —
searching by land parcel (地段小段 + 母號 + 子號) rather than scraping
JavaScript-rendered pages or depending on the national portal — so every
project with a stable parcel basis gets authoritative milestone dates without
manual curation.

## ADDED Requirements

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