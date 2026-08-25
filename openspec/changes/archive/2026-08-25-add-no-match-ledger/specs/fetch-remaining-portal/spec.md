## MODIFIED Requirements

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

## ADDED Requirements

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
