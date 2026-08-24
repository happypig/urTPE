## Purpose

Fetches missing national portal data for projects lacking twur links by performing targeted searches on the national portal, parsing 推導歷程 milestones, and writing results to per-project caches — all within a time-bounded, sequential, polite fetch loop that logs failures and continues.

## ADDED Requirements

### Requirement: Targeted portal search by land core

The system SHALL search the national portal list endpoint for each project lacking a twur link, using the project's section and first parcel as keywords in a `?title=` query parameter.

#### Scenario: Single unique view_id found
- **WHEN** the search for "中山段一小段254" returns exactly one `/view/` link
- **THEN** the system records that view_id and proceeds to fetch the view page

#### Scenario: Multiple view_ids found
- **WHEN** the search returns multiple `/view/` links
- **THEN** the system picks the first match and logs a warning "multiple matches"

#### Scenario: No view_ids found
- **WHEN** the search returns zero `/view/` links
- **THEN** the system logs "no match" and skips to the next project

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

The system SHALL process projects in descending order of their anchor 現況 date (most recent first) to maximize 使用核發日期 discoveries.

#### Scenario: Ordering applied
- **WHEN** the candidate list is built from `viewer/projects.data.js`
- **THEN** projects without twur are sorted by their 現況 node date descending before processing begins

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