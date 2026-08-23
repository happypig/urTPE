## ADDED Requirements

### Requirement: Search city cases by land parcel via the Taipei JSON API

The system SHALL discover city-platform case_ids by POSTing to the Taipei
platform's `ashx/Get_updcase_list.ashx` endpoint with the project's 地段小段
(section) and first parcel (split into 母號/子號), and SHALL extract numeric
detail ids from each result's `details` URL query string rather than the
entry's `case_id` field, which holds internal codes.

#### Scenario: Parcel search returns r_progress cases
- **WHEN** the system searches 玉泉段二小段 with 母號 40
- **THEN** entries whose `details` URL matches `r_progress_detail.aspx?case_id=<digits>`
  yield numeric case_ids (e.g. 09708181, 10104121, 10110181, 11502013)

#### Scenario: Internal codes are not used as detail ids
- **WHEN** a search entry's `case_id` field is an internal code (e.g. `R091306-02`)
  while its `details` URL carries a numeric id
- **THEN** the numeric id from the URL is used and the internal code is ignored

#### Scenario: Non-progress cases are filtered out
- **WHEN** a search entry's `details` URL does not point at `r_progress_detail.aspx`
  (e.g. 劃定 or 更新地區 entries)
- **THEN** that entry is excluded from the discovered case_ids

### Requirement: Fetch milestone timelines per case via the Taipei JSON API

The system SHALL fetch each case's 階段辦理過程 milestone timeline by POSTing its
case_id to `ashx/Get_project168_second.ashx`, mapping the response fields to
labelled milestones (計畫公聽會日期, 核定日期, 建照核發日期, …) via the fixed
field map, skipping empty values, and normalising ISO datetime values to dates.

#### Scenario: Milestones resolve for a known case
- **WHEN** the timeline for case_id 10110181 is fetched
- **THEN** labelled milestones including 計畫公聽會日期 2012/10/18,
  審議會審議通過日期 2020/06/08, 核定日期 2020/11/17 and 建照核發日期 2021/09/15
  are returned

#### Scenario: Empty fields produce no milestones
- **WHEN** a response row has empty values for some date fields
- **THEN** those labels are omitted from the milestone dict

#### Scenario: Error or malformed response yields empty dict
- **WHEN** the API returns non-JSON (`err`) or the request fails after retries
- **THEN** the milestone dict is empty and the failure is recorded without aborting discovery

### Requirement: Handle compressed responses

The system SHALL detect gzip-compressed HTTP bodies (magic bytes) and
decompress them before decoding, because request headers advertise
`Accept-Encoding: gzip` and servers honour it.

#### Scenario: Gzipped body is decompressed
- **WHEN** a fetch receives a body starting with gzip magic bytes
- **THEN** it is decompressed before UTF-8 decoding and parsed as HTML/JSON normally

## MODIFIED Requirements

### Requirement: Crawl the national portal for each project's view page

The system SHALL treat the national portal as a **supplementary** source: after
Taipei resolution, the system SHALL look up the project's land-identity core in
the cached bulk portal index (falling back to curated mappings when absent) to
attach the `twur.nlma.gov.tw/zh/urban/rebuild/view/<id>` URL and 推動歷程, and
SHALL continue with Taipei results regardless of national-portal failures.
City case_ids SHALL NOT be scraped from portal view pages.

#### Scenario: Land-identity core resolves a unique case
- **WHEN** the join looks up the core `玉泉段二小段40地號等29筆` in the portal index
- **THEN** it resolves exactly one case and records its twur view URL as a supplementary link

#### Scenario: Initial-vs-latest stage mismatch does not break matching
- **WHEN** the project's anchor name is a later-stage approval (變更…) but the portal names the initial approval (擬訂…)
- **THEN** matching still succeeds because both the Taipei parcel search and the portal index use land identity (section + first parcel), not full titles

#### Scenario: No portal case exists
- **WHEN** the core has no entry in the portal index
- **THEN** discovery falls back to curated mappings for a twur view_id, and otherwise proceeds with whatever Taipei resolution produced
- **AND** the missing twur URL does not affect city case_ids or milestones

#### Scenario: Ambiguous core matches multiple portal cases
- **WHEN** the core matches more than one portal index entry
- **THEN** the project is flagged for review rather than guessed
- **AND** no twur link is attached