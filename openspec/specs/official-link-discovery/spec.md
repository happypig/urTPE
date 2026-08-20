# official-link-discovery Specification

## Purpose

Discovers the official web links for every project — the national portal
(內政部國土管理署都市更新入口網) view page and the Taipei City 都市更新審議服務平台
case_id(s) it cross-references — by crawling the portals and joining on the same
land-identity core the merge step uses, so the pipeline can attach authoritative
records to each project without manual curation.

## Requirements

### Requirement: Crawl the national portal for each project's view page

The system SHALL resolve each project's national-portal page by querying the
portal's rebuild-case search (restricted to 臺北市) with the project's
land-identity core, and SHALL record the resolved `twur.nlma.gov.tw/zh/urban/rebuild/view/<id>` URL when a unique case matches.

#### Scenario: Land-identity core resolves a unique case
- **WHEN** the crawler queries the national portal for the core `玉泉段二小段40地號等29筆`
- **THEN** it resolves exactly one case and records its view URL

#### Scenario: Initial-vs-latest stage mismatch does not break matching
- **WHEN** the project's anchor name is a later-stage approval (變更…) but the portal names the initial approval (擬訂…)
- **THEN** the join still succeeds because matching uses the land-identity core, not the full title

#### Scenario: No portal case exists
- **WHEN** the query returns no case for a project core
- **THEN** the project is recorded as unresolved with no link attached

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
carry the case link for its own approval stage.

#### Scenario: Per-stage city links land on the right node
- **WHEN** a project family contains both a 事業計畫 and a 權利變換 approval
- **THEN** the city case_id for each approval attaches to the corresponding node
- **AND** the shared national-portal link attaches at project level

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