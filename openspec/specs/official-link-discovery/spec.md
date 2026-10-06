# official-link-discovery Specification

## Purpose

Discovers the official web links for every project — the national portal
(內政部國土管理署都市更新入口網) view page and the Taipei City 都市更新審議服務平台
case_id(s) it cross-references — by crawling the portals and joining on the same
land-identity core the merge step uses, so the pipeline can attach authoritative
records to each project without manual curation.
## Requirements
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

### Requirement: Extract the city-platform case links from the view page

The system SHALL parse each resolved view page's 縣市政府案件連結 block and SHALL
record every `gis.uro.taipei/r_progress_detail.aspx?case_id=<id>` URL it embeds.

#### Scenario: One view page embeds multiple city case_ids
- **WHEN** a view page lists separate 事業計畫 and 權利變換 case_ids (e.g. 10110211 and 10810271)
- **THEN** all of them are recorded against that project

#### Scenario: View page has no city link
- **WHEN** a view page has no 縣市政府案件連結 block
- **THEN** only the national-portal link is recorded, and the omission is noted in the crawl log

### Requirement: Join links to projects by land-identity core

The system SHALL attach discovered links to projects and to individual record
nodes by the same land-identity key the merge step anchors on, so each node can
carry the case link for its own approval stage. Date-based node anchoring SHALL
match the node's 核定日期 against the case's approval milestone — which for the
事業計畫/權利變換 tracks is 核定日期/權變核定日期, and for the 事業概要 track is
**概要核准日期** (a 概要 case has no 核定日期; omitting this label silently
degrades 概要-node anchoring to the positional fallback). The date matcher SHALL
accept ROC (`97/1/2`), slash-Gregorian (`2008/01/02`) and ISO (`2008-01-02`)
forms — the PDF pipeline passes raw ROC dates.

#### Scenario: Per-stage city links land on the right node
- **WHEN** a project family contains both a 事業計畫 and a 權利變換 approval
- **THEN** the city case_id for each approval attaches to the corresponding node
- **AND** the shared national-portal link attaches at project level

#### Scenario: 概要 case anchors to its node via 概要核准日期
- **WHEN** a node's date is 2026-03-31 and the family's 概要 case carries
  `概要核准日期 = 2026/03/31` (no 核定日期 — the 概要 track)
- **THEN** the case anchors to that node (previously it fell to the positional
  fallback or stayed unanchored — 延吉段三小段727 shape, operations log §6.14)

#### Scenario: ROC gazette dates anchor correctly in the PDF pipeline
- **WHEN** the PDF pipeline passes the node date as a ROC string (`97/1/2`) and
  the case's 核定日期 is `2008/01/02`
- **THEN** the matcher normalizes both to ISO and anchors the case
  (previously every PDF-pipeline anchoring silently degraded to positional)

#### Scenario: Unresolvable projects are counted
- **WHEN** discovery completes over all projects
- **THEN** the review report lists the number and identities of projects with no resolved link

### Requirement: Emit links into the graph document

The system SHALL include a `links` object in the emitted project graph JSON
carrying the national-portal URL and the city-platform case URLs, without
breaking consumers of the existing schema.

#### Scenario: Link field present on projects with a resolution
- **WHEN** projects.json is generated after discovery
- **THEN** each resolved project carries a `links` object with its twur URL and any city case URLs
- **AND** projects with no resolution carry an empty `links` object

### Requirement: Fetch failures never abort the crawl

The system SHALL retry each HTTP fetch on connection errors up to 3 times with exponential backoff (2s, 4s, 8s), and SHALL mark the affected project unresolved and continue with the next project when all retries fail, so a single connection reset never aborts the whole discovery run.

#### Scenario: Connection reset is retried then succeeds
- **WHEN** a view-page fetch fails with a connection error twice and succeeds on the third attempt
- **THEN** the project resolves normally and the crawl continues

#### Scenario: Exhausted retries mark one project unresolved
- **WHEN** all retries for a project's view page fail
- **THEN** that project is marked unresolved with the error recorded in the crawl log
- **AND** discovery proceeds to the next project

### Requirement: Resume discovery from cache

The system SHALL cache fetched pages and per-project discovery outcomes, and SHALL skip projects whose results are already cached, so an interrupted run resumes from the first uncached project instead of restarting from the beginning.

#### Scenario: Interrupted run resumes
- **WHEN** a previous run completed links for the first N projects and was interrupted
- **THEN** the next run makes no HTTP requests for those N projects
- **AND** it begins fetching from project N+1

#### Scenario: Completed projects keep their links on resume
- **WHEN** discovery resumes and a project already has a cached result
- **THEN** the cached result is used as-is and re-emitted into the graph document

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

#### Scenario: A parcel-less case naming the same area is kept
- **WHEN** the search for 青年段一小段 parcel 711 returns 09112120 / 09112121, whose names
  declare the area 崇仁新村 and no 地號, and the searched record's name carries 崇仁新村
- **THEN** both remain in `city_case_ids`

#### Scenario: A parcel-less case naming a different area is rejected
- **WHEN** a case's name declares no 地號 and shares no place run with the searched record
- **THEN** it is dropped and named in `search_rejected`

#### Scenario: A declared conflicting parcel is never corroborated
- **WHEN** a case's name carries a 地號 other than the searched one, even while sharing a
  place run with the searched record
- **THEN** it is dropped, because a conflicting 地號 is positive evidence of a different unit

#### Scenario: Own-family cases survive the guard
- **WHEN** the search for 寶清段一小段 parcel 57-13 returns 10212211 (擬訂…57-13地號等1筆…) and 10212212/10212214/11412018 (…57-13地號等1筆…)
- **THEN** all four remain in `city_case_ids`

#### Scenario: Foreign same-section case rejected
- **WHEN** the search for 正義段四小段 parcel 115 returns case 11102211 (擬訂…正義段四小段**133地號**1筆…)
- **THEN** 11102211 is dropped — its name lacks parcel 115

#### Scenario: Sibling R13 概要 case rejected
- **WHEN** the search for 南港段一小段 parcel 520-2 returns 概要 cases on 522等45筆 / 467等41筆 / 403-2等28筆 / 561等5筆 (§6.7)
- **THEN** the four siblings are dropped; 09407070/71/73 (520-2等18筆) remain

#### Scenario: Notation drift tolerated
- **WHEN** the searched parcel is 263-19 and a case name writes 263之19
- **THEN** the case is kept (drift-tolerant comparison, same rule as the national strict matcher)

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

### Requirement: Capture per-case schedule from the search response

Every discovered case's lifecycle status SHALL be observable per case_id: the viewer SHALL be able to display each case's schedule (已核准 / 已駁回 /
自行撤回 / 已失效 / 審查中 / 施工中), and a project whose every case is
已駁回 / 自行撤回 / 業已失效 SHALL be distinguishable as never-approved (the
national portal will never list it). To provide this, the pipeline SHALL
retain the search response's per-case `schedule` (`case_schedules`) alongside
`candidate_names`, and for cases discovered outside the parcel search SHALL
derive it from `get_project168_top.ashx` `phase`/`NAME` outcome.

#### Scenario: Rejected and withdrawn 概要 attempts keep their status
- **WHEN** a project's parcel search returns 11207021 (已駁回) and 11302031
  (自行撤回) for the same 概要 unit (民生段140-9 shape)
- **THEN** both case_ids are retained with their schedules and the viewer can
  render 擬訂臺北市松山區民生段140-9地號等3筆土地事業概要案 — 已駁回 / — 自行撤回

#### Scenario: Schedule explains a missing national-portal page
- **WHEN** every case of a project is 已駁回 / 自行撤回 / 業已失效 (never
  approved), and the project therefore has no twur link
- **THEN** the viewer and ledger classify the project as never-approved rather
  than as an unexplained no-match

### Requirement: Report link data that a run failed to attach

The system SHALL report link-derived data that is absent from an emitted dataset, naming the fields and the affected counts, and SHALL name the run step that attaches them. Absence is a fault of the run when **no** project in the dataset carries it, because that is indistinguishable from a run that collected nothing.

Partial coverage is **not** a fault: the portals do not cover every project, so a dataset in which some projects carry link data and others do not is the expected state. Partial coverage SHALL be reported as a count so a regression against a previous emission is visible, and SHALL NOT be raised as a fault.

#### Scenario: No project has link data

- **WHEN** an emitted dataset carries no link field on any project and none on any approval
- **THEN** the run reports a fault naming the fields and the number of projects
- **AND** reports that the viewer cannot render the views that depend on them

#### Scenario: The report names the step that did not attach the data

- **WHEN** link data is reported missing
- **THEN** the report names the run step that attaches it, so the cause is identifiable from the output alone

#### Scenario: Some projects have link data and some do not

- **WHEN** an emitted dataset carries link data on some projects and not others
- **THEN** both counts are reported
- **AND** no fault is raised, because the portals do not cover every project
- **AND** the dataset is not described as fully covered

#### Scenario: Every project has link data

- **WHEN** every emitted project carries the link fields the capability requires
- **THEN** no fault and no partial-coverage note is reported on their account

### Requirement: A human-verified portal link may be recorded as configuration

The system SHALL accept a portal view id recorded against a project by a person who
verified it, and SHALL apply it when discovery found no link for that project. The record
SHALL be stored outside the working tree's derived data, be version-controlled, and carry
the evidence it was verified against: where the page was seen, what its title said, when it
was verified, and why automated matching could not claim it.

A recorded link SHALL fill a gap and SHALL NOT displace a link discovery found on its own.
Where both exist, discovery's answer is kept, so a recorded link can never silently replace
what the portal actually returned for a project.

An applied recorded link SHALL be completed from the portal page itself rather than from
hand-entered values, so milestones and case identifiers come from the same source as any
discovered link.

A recorded link SHALL be reachable whenever discovery runs, and SHALL NOT depend on a
per-project cache entry existing. The per-project cache is derived data and is not
version-controlled, so a record consulted only from inside a cache read can never satisfy
a rebuild from an empty cache.

Applying a recorded link SHALL NOT suppress the rest of discovery. City-platform search,
milestones, implementation and rewards SHALL still run for the project, and the result
SHALL be written to the per-project cache in the ordinary shape, so an applied record
yields a complete result rather than a link with every other field empty.

#### Scenario: A verified link is recorded

- **WHEN** a person confirms a portal page for a project that discovery could not match
- **THEN** the record is stored with the page location, its title, the date, and the reason automated matching failed
- **AND** the record is version-controlled, so the decision survives a fresh clone

#### Scenario: The record fills a gap

- **WHEN** a project has no portal link and a recorded link exists for it
- **THEN** the recorded link is applied
- **AND** the project's milestones and case identifiers are read from that portal page

#### Scenario: The record does not displace a discovered link

- **WHEN** a project already has a portal link found by discovery and a recorded link also exists
- **THEN** the discovered link is kept
- **AND** the recorded link is not applied to it

#### Scenario: A recorded link survives a fresh clone

- **WHEN** the emitted dataset is rebuilt on a machine that has no per-project cache
- **THEN** the recorded link is still available, because it is configuration rather than a cache artefact
- **AND** the record is applied even though no cache entry for the project exists

#### Scenario: The record applies with no portal index available

- **WHEN** the national-portal index is empty or could not be built
- **THEN** a recorded link is still applied
- **AND** the national-portal step is not skipped wholesale, since skipping it would strand the record exactly when it is needed

#### Scenario: Applying the record does not suppress discovery

- **WHEN** a recorded link is applied to a project
- **THEN** city-platform search still runs for that project
- **AND** the result carries the city case identifiers and their milestones
- **AND** a cache entry is written in the ordinary shape, so a later run resumes from it

#### Scenario: An unexplained record is refused

- **WHEN** a record names a view id but carries no evidence of where it was verified
- **THEN** it is not applied
- **AND** the record is reported as incomplete, because an unattributed link cannot be audited

#### Scenario: A record naming a project that does not exist

- **WHEN** a recorded link names a project absent from the emitted dataset
- **THEN** it is reported rather than silently retained, since the identity may have moved

### Requirement: A repeated discovery run does not re-raise a flag it already raised

Where discovery compares a record's published stage against the platform case it anchored to
and finds them inconsistent, the disagreement SHALL be flagged. Raising that flag SHALL be
idempotent: re-running discovery over unchanged input SHALL NOT add a second copy of a flag
the record already carries.

A flag that has already been raised is evidence about the record, not an event that occurred
again. Counting occurrences instead of recording the finding makes an emitted dataset a
counter of how many times the pipeline has run, which is not a property of the gazettes.

#### Scenario: The disagreement is flagged on first observation

- **WHEN** discovery compares a record's published stage with the stage of the platform case it anchored to and they differ
- **THEN** the record carries a flag describing the disagreement

#### Scenario: A second run does not flag it again

- **WHEN** discovery runs again over the same records and the same anchored case
- **THEN** the record still carries exactly one copy of that flag
- **AND** no additional copy is added

#### Scenario: The flag text is unchanged by repetition

- **WHEN** a flag has already been raised for a disagreement
- **THEN** repeating the comparison produces the same flag text and adds nothing
- **AND** the flags a record carries are unchanged in content and count

#### Scenario: Distinct disagreements are still all reported

- **WHEN** a record carries flags for two different conditions
- **THEN** both appear, once each
- **AND** deduplication does not collapse flags that differ in text

### Requirement: Emitted review flags carry no duplicates

The emitted dataset SHALL NOT contain the same review flag string more than once on a single
record. Where duplicates exist from earlier runs, the next emission SHALL collapse them,
preserving the order in which the flags were first raised, and no distinct finding SHALL be
lost.

#### Scenario: A record emitted with duplicates

- **WHEN** a record's flags were accumulated by earlier runs and contain the same string more than once
- **THEN** the emitted record carries that string once
- **AND** the flags appear in the order they were first raised

#### Scenario: Nothing is lost by collapsing

- **WHEN** duplicates are collapsed during emission
- **THEN** the set of distinct flags a record carries is unchanged
- **AND** the count of records carrying at least one flag is unchanged

