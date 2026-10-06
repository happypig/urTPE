## MODIFIED Requirements

### Requirement: Search city cases by land parcel via the Taipei JSON API

The system SHALL discover city-platform case_ids by POSTing to the Taipei
platform's `ashx/Get_updcase_list.ashx` endpoint with the project's 地段小段
(section) and first parcel (split into 母號/子號), and SHALL extract numeric
detail ids from each result's `details` URL query string rather than the
entry's `case_id` field, which holds internal codes.

Where the searched parcel carries a 子號 and the search returns nothing, the system
SHALL retry the 母號 alone. The gazette prints the post-subdivision parcel while the
platform's index is keyed on the pre-subdivision stem, so a single-form search silently
finds nothing and the omission is indistinguishable from a project that has no cases.
The retry SHALL fire only after an empty result and results SHALL be merged by numeric
detail id.

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

#### Scenario: An empty result retries the pre-subdivision stem
- **WHEN** the gazette parcel is 711-3 and a search on 711-3 returns no entries
- **THEN** the system searches 母號 711 and uses those results
- **AND** cases declared under 711 are not lost merely because the gazette prints the
  post-subdivision form

#### Scenario: No retry when the searched parcel matched
- **WHEN** a search on a hyphenated parcel returns at least one entry
- **THEN** no stem retry is issued, keeping the ordinary case to a single request

### Requirement: Taipei case search rejects cases outside the searched parcel

`search_taipei_cases_api` SHALL keep a searched case when the case's own `case_name` declares the searched parcel — the anchor record's named first parcel (mono part; sub-parcel suffix tolerated in 之 ↔ - and full-width ↔ ASCII forms) — extending the §6.7 guard to all cross-family pollution. Cases whose name declares a *different* parcel (sibling R13 概要 cases, foreign same-section cases) SHALL NOT enter `city_case_ids`, and therefore SHALL NOT contribute milestones to the project's merged timeline.

A unit named for a place rather than a parcel declares no 地號 at all, which is not evidence of a foreign family. Where a case's name declares no parcel, it SHALL be kept when it corroborates the searched record by carrying a named-area token that the anchor record's name also carries (e.g. 崇仁新村). Corroboration SHALL NOT rescue a case that declares a parcel of its own: a name carrying a conflicting 地號 is rejected regardless of any shared area token.

Every case the guard rejects SHALL remain reported in `search_rejected`, so a case left out for want of corroboration is auditable and can be recorded by hand rather than vanishing.

#### Scenario: Own-family cases survive the guard
- **WHEN** the search for 寶清段一小段 parcel 57-13 returns 10212211 (擬訂…57-13地號等1筆…) and 10212212/10212214/11412018 (…57-13地號等1筆…)
- **THEN** all four remain in `city_case_ids`