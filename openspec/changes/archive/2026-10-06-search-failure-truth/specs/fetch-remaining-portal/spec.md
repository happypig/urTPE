## MODIFIED Requirements

### Requirement: No-match ledger persistence

The system SHALL record every candidate that **completes** targeted search without a match into a persistent ledger (`data/.link_cache/no_match_ledger.json`) keyed by project_id with the probe timestamp and the view_ids checked, and SHALL remove a project's entry when that project later gains a twur link.

A candidate whose search or view-page fetches **failed** has not completed targeted search and SHALL NOT be recorded as a no-match. Such an outcome SHALL be recorded as a distinct class, carrying the same entry shape but no re-probe exclusion, so the project is eligible again on the next run. A transport failure and a genuine negative must be distinguishable from the ledger alone, because the two are the same observation to a reader who did not watch the run.

This covers the whole search, not only the probes taken after it. A search that could not be performed at all is an error, exactly as a run of failed probes is: neither establishes that the portal lacks the case.

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

#### Scenario: A search that could not be run is not a negative

- **WHEN** the portal search request for a candidate raised a transport error, so no candidate view pages were ever obtained
- **THEN** the candidate is not recorded as a no-match
- **AND** an error entry is recorded, with no view ids checked, because nothing was learned about the portal's contents
- **AND** the project is eligible for probing on the next run

#### Scenario: A search that ran and found nothing is a negative

- **WHEN** the portal search request succeeded and returned no candidate view pages
- **THEN** the candidate is recorded as a miss
- **AND** the exclusion applies, because the portal answered and held nothing for that section

#### Scenario: A failed search is distinguishable from an empty one

- **WHEN** one ledger entry records an empty search that failed and another records an empty search that ran
- **THEN** the two are told apart by their recorded outcome rather than by the absence of checked view ids
- **AND** both carry an empty `view_ids_checked` list, so that list alone does not distinguish them