## MODIFIED Requirements

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

## ADDED Requirements

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
