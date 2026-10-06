## MODIFIED Requirements

### Requirement: No-match ledger persistence

The system SHALL record every candidate that **completes** targeted search without a match into a persistent ledger (`data/.link_cache/no_match_ledger.json`) keyed by project_id with the probe timestamp and the view_ids checked, and SHALL remove a project's entry when that project later gains a twur link.

A candidate whose view-page fetches **failed** has not completed targeted search and SHALL NOT be recorded as a no-match. Such an outcome SHALL be recorded as a distinct class, carrying the same entry shape but no re-probe exclusion, so the project is eligible again on the next run. A transport failure and a genuine negative must be distinguishable from the ledger alone, because the two are the same observation to a reader who did not watch the run.

#### Scenario: No-match recorded

- **WHEN** targeted search finishes for a candidate, every fetch succeeds, and no view page satisfies the strict matcher
- **THEN** the ledger gains or updates the project's entry with the current timestamp before processing continues

#### Scenario: Ledger cleared on later match

- **WHEN** a candidate with an existing ledger entry matches a view page and its cache is updated
- **THEN** the project's entry is removed from the ledger

#### Scenario: Ledger survives restarts

- **WHEN** the fetch script exits and a later run starts
- **THEN** previously recorded no-match entries are still honored by candidate selection

#### Scenario: A failed fetch is not a negative

- **WHEN** every view-page fetch for a candidate raised a transport error
- **THEN** the candidate is not recorded as a no-match
- **AND** the ledger gains or updates an entry identifying the outcome as an error rather than a miss
- **AND** the project is eligible for probing on the next run rather than excluded until its timestamp expires

#### Scenario: A partial failure that still matched is a match

- **WHEN** some probes raise and a later probe returns a page satisfying the strict matcher
- **THEN** the candidate is treated as matched
- **AND** no error class is recorded, because the outcome was determined

### Requirement: Time-bounded execution until 06:30

The system SHALL stop initiating new fetches at a configured local wall-clock time, complete any in-progress fetch, then exit. The stop time SHALL be supplied as a run option and SHALL default to the value below when not supplied.

The default is **06:30**. The previous implementation hardcoded an hour with no option to change it, and its value differed from this requirement; the option removes the disagreement by making the window explicit at launch.

#### Scenario: Deadline respected

- **WHEN** the current time reaches or passes the configured stop time
- **THEN** the system completes the current project's fetch (if any), skips remaining projects, and proceeds to regeneration

#### Scenario: Stop time supplied at launch

- **WHEN** the run is started with an explicit stop time
- **THEN** that time governs the run instead of the default
- **AND** the resolved stop time is reported in the run summary, so the window is visible after the fact

#### Scenario: Stop time already past at launch

- **WHEN** the run starts after the configured stop time on the same day
- **THEN** the stop time resolves to the following day rather than stopping the run immediately

#### Scenario: Malformed stop time

- **WHEN** the supplied stop time cannot be parsed
- **THEN** the run refuses to start and reports the expected format, rather than falling back to a default that may not be what was intended

### Requirement: Re-probe TTL

The system SHALL treat no-match ledger entries as expired after a configurable time-to-live (default 14 days), after which the project becomes eligible for probing again. An entry recording an **error** rather than a no-match SHALL NOT carry this exclusion: it was never a negative, so it must not suppress re-probing for any interval.

#### Scenario: Expired entry allows re-probe

- **WHEN** candidate selection runs and a ledger entry's probe timestamp is older than the TTL
- **THEN** the project is treated as having no valid exclusion and joins the candidate list

#### Scenario: TTL is configurable

- **WHEN** the script is started with an explicit TTL override
- **THEN** the override replaces the default 14-day window for that run

#### Scenario: An error entry does not suppress re-probing

- **WHEN** a ledger entry records an error outcome
- **THEN** the project is eligible regardless of how recently the error was recorded
- **AND** the re-probe interval is governed by the crawl's own politeness policy, not by this entry

### Requirement: Classify ledger negatives by case outcome (never-approved vs recoverable)

A ledger negative (a project the strict title matcher could not match) SHALL be classified by the outcome of its own Taipei cases via `get_project168_top.ashx` (`phase`/`NAME`): a project whose every case is 本府駁回 / 實施者自行撤回 / 業已失效 SHALL be marked **never-approved** — the national portal will never list it — and excluded from future re-probe waves (liveness policy). Projects with at least one 業經本府核定 case SHALL be marked **recoverable** (the portal page should exist; the identity connection failed) and re-enter the targeted queue.

Classification applies to **negatives only**. An entry recording a fetch error has no case outcome to classify, because no case was ever retrieved, and SHALL be left unclassified rather than being forced into `recoverable` or `never-approved`.

#### Scenario: Lapsed-概要 units are marked never-approved

- **WHEN** a twur-less project's only case is phase-A `事業概要階段─事業概要業已失效`
- **THEN** the ledger entry is annotated `never-approved` and excluded from TTL re-probes

#### Scenario: Approved-case units re-enter the queue

- **WHEN** a twur-less project carries a case with `業經本府核定` (e.g. 梨和段二小段261-4, 11409012)
- **THEN** the ledger entry is annotated `recoverable` and re-enters the targeted queue with the case's own 案名 fragments as search keys

#### Scenario: Corpus classification is measurable

- **WHEN** the classification runs over the twur-less population (2026-08-29 baseline: 71 = 15 never-approved · 17 has-approved · 33 mixed/other · 6 no-cases)
- **THEN** the counts are reportable per class so the remaining twur-less tail is explained, not just counted

#### Scenario: An error outcome is not classified

- **WHEN** an entry records a fetch error
- **THEN** no case outcome is assigned
- **AND** the entry is not treated as `recoverable`, because nothing indicates the portal should hold a page