## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Crawl the national portal for each project's view page

The system SHALL resolve each project's national-portal page by looking up the project's land-identity core in the cached bulk portal index, and SHALL record the resolved `twur.nlma.gov.tw/zh/urban/rebuild/view/<id>` URL when a unique case matches. It SHALL NOT issue a per-project search request in the steady state (index already built).

#### Scenario: Land-identity core resolves a unique case
- **WHEN** the join looks up the core `玉泉段二小段40地號等29筆` in the portal index
- **THEN** it resolves exactly one case and records its view URL

#### Scenario: Initial-vs-latest stage mismatch does not break matching
- **WHEN** the project's anchor name is a later-stage approval (變更…) but the portal names the initial approval (擬訂…)
- **THEN** the join still succeeds because matching uses the land-identity core, not the full title

#### Scenario: No portal case exists
- **WHEN** the core has no entry in the portal index
- **THEN** the project is recorded as unresolved with no link attached

#### Scenario: Ambiguous core matches multiple portal cases
- **WHEN** the core matches more than one portal index entry
- **THEN** the project is flagged for review rather than guessed
- **AND** no link is attached