# fetch-remaining-portal Specification

## Purpose

Fetches missing national portal data for projects lacking twur links by performing targeted searches on the national portal, parsing 推導歷程 milestones, and writing results to per-project caches - all within a time-bounded, sequential, polite fetch loop that logs failures and continues.

## Requirements

### Requirement: Targeted portal search by land core

The system SHALL search the national portal list endpoint for each project lacking a twur link, using the project's section and its anchor record's **named first parcel** — the parcel immediately preceding 地號 in the anchor case name — as keywords in a `?title=` query parameter. The parcel keyword SHALL NOT be derived positionally from an enumerated land string.

#### Scenario: Single unique view_id found
- **WHEN** the search for "中山段一小段254" returns exactly one `/view/` link
- **THEN** the system records that view_id and proceeds to fetch the view page

#### Scenario: Multiple view_ids found
- **WHEN** the search returns multiple `/view/` links
- **THEN** the system probes them in returned order under the probe-breadth rule and takes the first strict identity match

#### Scenario: No view_ids found
- **WHEN** the search returns zero `/view/` links
- **THEN** the system logs "no match" and skips to the next project

#### Scenario: Enumerated land string resolves to named first parcel
- **WHEN** the anchor record's land string enumerates parcels before 地號 (e.g., "寶清段四小段599、599-1、601、…、623地號等27筆土地")
- **THEN** the parcel keyword is the named first parcel (599), never the last enumerated parcel (623)

#### Scenario: Anchor parcel used verbatim across runs
- **WHEN** two projects share a section but are named after different parcels
- **THEN** each candidate carries its own anchor parcel and neither can satisfy the other's strict match

### Requirement: View page fetch and 推導歷程 parsing

The system SHALL fetch each resolved view page and extract the 推導歷程 milestone table (visible `type4_table` with 項目/日期 headers) into a milestone dictionary.

#### Scenario: Milestones successfully extracted
- **WHEN** the view page contains a visible `type4_table` with 項目/日期 headers and rows
- **THEN** the system extracts all label/date pairs matching the ROC date pattern and stores them in the project's national_milestones

#### Scenario: Empty or missing milestone table
- **WHEN** the view page has no type4_table or the table has no dated rows
- **THEN** the system records an empty national_milestones dict and does not error

### Requirement: Cache update with twur and milestones

The system SHALL write the discovered `twur_view_id`, `twur_url`, and `national_milestones` into the project's per-project cache file (`data/.link_cache/<project>/result.json`), preserving any existing fields.

#### Scenario: Cache updated successfully
- **WHEN** milestones (possibly empty) and view_id are available
- **THEN** the cache file is written with `twur_view_id`, `twur_url`, and `national_milestones` merged into existing data

### Requirement: Sequential polite fetch with 3-5 min intervals

The system SHALL process projects sequentially, waiting a random interval of 180-300 seconds between each project's fetch attempt.

#### Scenario: Interval enforced
- **WHEN** one project's fetch completes (success or failure)
- **THEN** the system waits a random duration between 180 and 300 seconds before starting the next project

### Requirement: Retry on transient failures

The system SHALL retry failed fetches up to 3 times with exponential backoff (2s, 4s, 8s) on connection errors, timeouts, or HTTP 5xx responses before logging failure and continuing.

#### Scenario: Retry succeeds
- **WHEN** a fetch fails with a transient error and succeeds on a subsequent retry
- **THEN** the system proceeds normally with the successful response

#### Scenario: All retries exhausted
- **WHEN** all 3 retries fail
- **THEN** the system logs the failure with error details and proceeds to the next project

### Requirement: Prioritization by recent 現況 date

The system SHALL build the candidate list from projects lacking twur links, excluding any project recorded in the no-match ledger whose last probe is newer than the re-probe TTL, and SHALL process remaining projects in descending order of their anchor 現況 date (most recent first) to maximize 使用核發日期 discoveries.

#### Scenario: Ordering applied
- **WHEN** the candidate list is built from `viewer/projects.data.js`
- **THEN** projects without twur, and not excluded by the no-match ledger, are sorted by their 現況 node date descending before processing begins

#### Scenario: Recently probed no-match skipped
- **WHEN** a project missing twur has a no-match ledger entry probed within the re-probe TTL
- **THEN** the project is excluded from this run's candidate list and counted in the run summary as skipped

#### Scenario: Stale entry re-enters queue
- **WHEN** a project's only no-match ledger entry is older than the re-probe TTL
- **THEN** the project is included in the candidate list again

### Requirement: Time-bounded execution until 06:30

The system SHALL stop initiating new fetches at 06:30 local time, complete any in-progress fetch, then exit.

#### Scenario: Deadline respected
- **WHEN** the current time reaches or passes 06:30
- **THEN** the system completes the current project's fetch (if any), skips remaining projects, and proceeds to regeneration

### Requirement: Auto-regenerate viewer on completion

The system SHALL invoke the CLI to regenerate `viewer/projects.data.js` from the updated caches after the fetch loop ends (whether by completion or 06:30 timeout).

#### Scenario: Viewer regenerated
- **WHEN** the fetch loop ends
- **THEN** the system runs `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links` and waits for completion

### Requirement: Failure logging without blocking

The system SHALL log every fetch failure (project_id, view_id, error, timestamp) to stderr and a JSON log file, then immediately continue to the next project.

#### Scenario: Failure logged and queue continues
- **WHEN** a project's all retries are exhausted
- **THEN** the failure is appended to `data/.link_cache/fetch_failures.json` and the next project begins after the polite interval

### Requirement: No-match ledger persistence

The system SHALL record every candidate that completes targeted search without a match into a persistent ledger (`data/.link_cache/no_match_ledger.json`) keyed by project_id with the probe timestamp and the view_ids checked, and SHALL remove a project's entry when that project later gains a twur link.

#### Scenario: No-match recorded
- **WHEN** targeted search finishes for a candidate and no view page satisfies the strict matcher
- **THEN** the ledger gains or updates the project's entry with the current timestamp before processing continues

#### Scenario: Ledger cleared on later match
- **WHEN** a candidate with an existing ledger entry matches a view page and its cache is updated
- **THEN** the project's entry is removed from the ledger

#### Scenario: Ledger survives restarts
- **WHEN** the fetch script exits and a later run starts
- **THEN** previously recorded no-match entries are still honored by candidate selection

### Requirement: Re-probe TTL

The system SHALL treat no-match ledger entries as expired after a configurable time-to-live (default 14 days), after which the project becomes eligible for probing again.

#### Scenario: Expired entry allows re-probe
- **WHEN** candidate selection runs and a ledger entry's probe timestamp is older than the TTL
- **THEN** the project is treated as having no valid exclusion and joins the candidate list

#### Scenario: TTL is configurable
- **WHEN** the script is started with an explicit TTL override
- **THEN** the override replaces the default 14-day window for that run

### Requirement: Run summary reports ledger activity

The system SHALL report per-run counts of candidates processed, matched (updated), and skipped-as-recently-probed when the run ends.

#### Scenario: Summary printed at exit
- **WHEN** the fetch loop ends (completion or deadline)
- **THEN** the printed summary includes processed, updated, and skipped counts derived from ledger filtering

### Requirement: Strict view-page identity match

The system SHALL accept a searched view page as a candidate project's national page only when the page `<title>` parses to the same section, the same named first parcel, and — where both candidate and title carry a land count — an equal land count. All parcel and count comparisons SHALL be type-safe and SHALL tolerate notation drift (`之` ↔ `-` for sub-parcel suffixes, full-width ↔ ASCII digits). A page failing any applicable comparison SHALL be rejected and the next candidate probed.

#### Scenario: Counted candidate matches its own page
- **WHEN** the candidate carries the text count `'27'` and the view title parses to the numeric count `27`
- **THEN** the count comparison passes and the page is accepted when section and parcel also agree

#### Scenario: Differing counts rejected
- **WHEN** both counts are present and differ after normalization (e.g., 等7筆 vs 等17筆)
- **THEN** the page is rejected

#### Scenario: Absent count skips the count check
- **WHEN** either the candidate or the parsed title carries no land count
- **THEN** acceptance is decided by section and parcel alone

#### Scenario: Sub-parcel notation drift tolerated
- **WHEN** the candidate parcel is written `263-19` and the title writes `263之19` (or digits differ only in full-width/ASCII form)
- **THEN** the parcels compare equal

#### Scenario: Wrong parcel or section rejected
- **WHEN** the parsed title's section or parcel differs from the candidate's keywords after normalization
- **THEN** the page is rejected even if the parcel string appears elsewhere in the page body

### Requirement: Configurable view-probe breadth

The system SHALL probe a project's search-result view pages in returned order until one satisfies the strict identity match or the probe limit is reached. The probe limit SHALL default to 8 and be overridable per run. When the limit truncates unprobed results without a match, the system SHALL note the truncation in run output while recording the no-match as usual.

#### Scenario: Match within limit
- **WHEN** one of the probed pages satisfies the strict identity match
- **THEN** probing stops there and the matched view_id is used

#### Scenario: Limit reached without match
- **WHEN** the probe limit is exhausted with no strict match and unprobed results remain
- **THEN** the project is recorded as a no-match and the run output notes how many results were left unprobed

#### Scenario: Probe limit overridden
- **WHEN** the script is started with an explicit probe-limit override
- **THEN** the override replaces the default of 8 for that run
