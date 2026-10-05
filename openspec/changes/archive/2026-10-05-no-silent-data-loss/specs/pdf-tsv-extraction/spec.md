## Purpose

Defines how the reader handles a 地號 cell the publisher truncated at the printed row
height: when the record is excluded and reported, and when — under three independent
checks that must all agree — its parcel list may be completed from another approval of
the same unit elsewhere in the corpus and recorded with its provenance.

## MODIFIED Requirements

### Requirement: Distinguish reader faults from source faults in cell content

The system SHALL classify every fault found in a cell's text by whether the reader or the publisher caused it, because the two demand opposite responses. A fault the reader could have prevented SHALL abort the run and write no output. A fault the publisher introduced SHALL NOT abort the run: the record SHALL either be excluded and named with its page, row and column, or — where every check below is satisfied — completed from another approval of the same unit and recorded with its provenance. In either case the affected count SHALL be reported, so that a gazette missing records is never presented as complete.

A completion is permitted only when all three of the following hold, and each is checked independently:

1. **Same unit.** The candidate is in the same 行政區 and the same 段/小段.
2. **The parcels already read are preserved.** The truncated cell's own text, once whitespace is normalised, is a prefix of the candidate's text, **and** every parcel the truncated cell shows is present in the candidate. The two halves are checked separately and neither implies the other: spacing around `、` and around sub-parcel hyphens varies between publications for the same list (`332 、333` in one, `332、333` in another) and is presentation rather than content, so it is normalised before comparing; and a textual prefix can still end mid-token, so that a parcel already read is bounded differently in the candidate, which containment catches and a prefix test does not.
3. **The count closes.** The completed parcel count equals the count the same row's 案名 declares. If it does not, the count is unexplained and the record stays excluded.

Where all three hold the record is emitted with the completed list and an audit entry naming the source gazette and 編號 it was completed from. Where any one fails the record is excluded as before.

#### Scenario: Page furniture absorbed into a cell

- **WHEN** a page-number footer lies geometrically inside the last row's 地號 cell rectangle and the reader would otherwise emit it as part of the cell's text
- **THEN** the reader identifies it as page furniture and excludes it
- **AND** the cell is emitted with its published text only
- **AND** if it cannot be excluded with certainty, the run is aborted rather than emitting the cell

#### Scenario: Publisher truncates a cell at the row height

- **WHEN** a 地號 cell's text ends in a dangling separator (`、` or `，`) or a half sub-parcel number such as `139-`, because the publisher stopped drawing the list at the printed row height
- **THEN** the record is reported as a source fault naming its page, row and column
- **AND** if no candidate satisfies all three completion checks, the record is excluded from the emitted dataset rather than emitted with an unknown parcel set
- **AND** the run continues and the excluded count is reported
- **AND** no parcel list is inferred from the parcel count declared in the 案名, or from a wider text window

#### Scenario: A truncated cell is completed from another approval of the same unit

- **WHEN** a 地號 cell is truncated and another approval of the same unit elsewhere in the corpus is in the same 行政區 and 段/小段, its text begins with the truncated cell's text modulo whitespace while preserving every parcel the truncated cell shows, and its parcel count brings the truncated cell's total to exactly the count the same row's 案名 declares
- **THEN** the record is emitted with the completed parcel list rather than excluded
- **AND** the run reports that it was completed, naming the source gazette and 編號
- **AND** the completion is auditable after the fact from the run report alone

#### Scenario: A candidate is rejected because the count does not close

- **WHEN** a candidate's text begins with the truncated cell's text but completing from it yields fewer parcels than the same row's 案名 declares
- **THEN** the record is excluded and the count discrepancy is reported
- **AND** the system does not emit a parcel list it cannot reconcile with its own 案名

#### Scenario: A candidate is rejected because it drops an already-read parcel

- **WHEN** a candidate's text begins with the truncated cell's text but a parcel the truncated cell already showed is absent from the candidate
- **THEN** the candidate is a differently-bounded list rather than a continuation
- **AND** the record is excluded

#### Scenario: A candidate from a different 段/小段 is never used

- **WHEN** the only candidate sharing a prefix lies in a different 段 or 小段
- **THEN** the record is excluded
- **AND** no parcel is borrowed across a section boundary

#### Scenario: Publisher's truncation removes only the closing phrase

- **WHEN** a 地號 cell ends mid-enumeration but still shows exactly as many parcels as the same row's 案名 declares
- **THEN** the parcel list is provably whole, only the closing phrase was lost, and the record is emitted normally with no fault reported
- **AND** no parcel is inferred from another record, another gazette, or the declared count

#### Scenario: Publisher's terminal wording variations are not faults

- **WHEN** a 地號 cell ends `地號等共 57筆土地`, `地號等 18 筆土地)`, `地號等 34 筆土 地` (the word 土地 split across a line), or a bare `地號等12筆` with no 土地
- **THEN** the record is emitted normally and no fault is reported
- **AND** the fault detector does not fire on any published wording variation that carries a complete parcel list

#### Scenario: A partial gazette is never presented as complete

- **WHEN** one or more records were excluded as source faults, or completed from another approval
- **THEN** the run report states the number excluded and the number completed alongside the number emitted
- **AND** the emitted dataset is not described as a faithful copy of the publication

## ADDED Requirements

### Requirement: An emission states what the viewer can and cannot render

The system SHALL ensure the dataset it emits carries the fields the viewer reads, and SHALL report any that a rebuild dropped rather than emitting a conforming-looking dataset that cannot be rendered. A dataset missing link-derived fields SHALL be treated as a fault of the run, not as a smaller dataset.

#### Scenario: A rebuild omits link discovery

- **WHEN** a run emits a dataset in which every project carries an empty link set and no approval carries a link
- **THEN** the run reports that link-derived fields are absent, naming the fields and the affected counts
- **AND** the report states that the emitted viewer data cannot render the milestone cards, portal badges and execution-stage labels that depend on them

#### Scenario: A conforming emission is silent about it

- **WHEN** a run emits a dataset in which link-derived fields are present
- **THEN** no fault is reported on their account

#### Scenario: Link-derived fields are present for some projects only

- **WHEN** some projects carry link-derived fields and others do not
- **THEN** the run reports the count that do and does not
- **AND** does not treat the populated minority as conforming the whole
