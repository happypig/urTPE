# cache-freshness spec delta — reject-foreign-view-cases (§8 viewer-UX wave 3b)

## ADDED Requirements

### Requirement: The refresh verifies view-verified ids by the city's own case name

The refresh SHALL verify every id in the cache's `view_verified_case_ids` against the city's own case name for that id (get_project168_top `CASE_NAME`, persisted per case), deciding by the land core at `LINK_THRESHOLD = 0.7` against the cache's own land core: match → keep; no match → remove the id from `view_verified_case_ids` and record it in `view_rejected` with its reason (shape A / shape B); the 相關連結 label is compared only for the reason text, and a label mismatch with a matching city name SHALL NOT reject. A missing city name SHALL NOT reject. The verification SHALL run on every cache holding `view_verified_case_ids`, whether or not its cases await an approval, because the defect does not depend on the awaiting state.

#### Scenario: A fully-approved cache is still verified

- **WHEN** a cache holds `view_verified_case_ids` but no case awaits an approval (the awaiting-approval selector would skip it)
- **THEN** the view-verified verification still runs on it

#### Scenario: Shape B rejection is recorded

- **WHEN** the city's own case name for a view-verified id names another project while the label matches (09511211 on 大安區-大安段一小段-557)
- **THEN** the id leaves `view_verified_case_ids`
- **AND** `view_rejected[09511211]` records reason "label is right, id is wrong (shape B)"

#### Scenario: The verification does not depend on the awaiting state

- **WHEN** the refresh runs on a cache whose only defect is a foreign view-verified id
- **THEN** the id is verified and recorded even though no milestone changed

### Requirement: The refresh records CASE_NAME per case

The refresh SHALL persist the header row's `CASE_NAME` (the city's own case name, distinct from the `NAME` state field) into the refreshed cache per case, so the view-verified verification and the offer step can decide offline after the run.

#### Scenario: CASE_NAME reaches the cache

- **WHEN** the header fetch returns a row whose `CASE_NAME` is the city's case name
- **THEN** the refreshed cache carries it for that case id
- **AND** a later `--from-js` reload preserves it

### Requirement: A rejected view-verified id is offered to its own project

After the verification pass, for each rejected id whose city-name land core matches exactly one other project's cache land core at `LINK_THRESHOLD = 0.7`, the system SHALL add the id to that project's `city_case_ids` (appended, never re-ordered — the positional fallback binds by index), fetch its milestones when the target cache does not hold them, and record the move as `adopted_from_view[cid] = source_project_id` on the target cache, with the source recording the rejection. When no other project matches, the id stays only in `view_rejected`. When more than one project matches, the system SHALL NOT guess: the id stays only in `view_rejected` with reason "ambiguous owner" — the same rule `data/project_aliases.json` applies to ambiguous pairs. The move SHALL happen under the same single-writer lock and in the same run that writes the source cache. Matching SHALL use the land core, never 編號 or `project_id` (both churn).

#### Scenario: A rejected id lands on its owning project

- **WHEN** rejected id 10202065's city name (大安區辛亥段一小段163地號等5筆) matches exactly one other cache's land core
- **THEN** 10202065 is appended to that cache's `city_case_ids`
- **AND** the target records `adopted_from_view["10202065"] = "中山區-中山段一小段-254地號等13筆"`
- **AND** the run report names the move for both projects

#### Scenario: An id the target already holds is not duplicated

- **WHEN** the offered id is already in the target cache's `city_case_ids` (09807161 → 內湖區-康寧段二小段-262 already holds it)
- **THEN** the id is not appended twice
- **AND** the target still records `adopted_from_view` and the report names the move

#### Scenario: An ambiguous owner is not guessed

- **WHEN** a rejected id's city-name land core matches two or more other caches
- **THEN** no cache is modified
- **AND** `view_rejected` records reason "ambiguous owner"

#### Scenario: No matching project

- **WHEN** a rejected id's city-name land core matches no other cache
- **THEN** the id stays only in `view_rejected`

### Requirement: The report names every rejection and offer

The run report SHALL name every rejected view-verified id with its reason and shape, every id offered to another project with both project ids, and every label error accepted under decision-table row 4, each with counts, the same way truncated records are named and counted — a rejection that vanished silently would read as a complete dataset.

#### Scenario: The report names the three §8 rejections

- **WHEN** the pass runs over the 2026-11-04 corpus
- **THEN** the report names 10202065, 09511211 and 09807161 as rejected with their shapes
- **AND** names 10906092 as accepted with a label error

#### Scenario: Every offer is named

- **WHEN** an id is offered to another project's cache
- **THEN** the report names the source project, the target project and the id
