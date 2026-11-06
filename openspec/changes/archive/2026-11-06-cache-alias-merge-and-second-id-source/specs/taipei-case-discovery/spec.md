## ADDED Requirements

### Requirement: A second id source, confirmed by the case header

The system SHALL discover city-platform case ids from a **second source** when
the parcel search does not return them: the city's 168 list
(`ashx/Get_project168.ashx`), whose entries name the case ids of the 168
fast-track programme.

A case id from that list SHALL enter the project's case ids only when its own
case header (`ashx/get_project168_top.ashx`) confirms it: the header SHALL
return a row that names the case and carries its 案名. A header that returns
nothing SHALL NOT confirm the id, and the id SHALL NOT enter the case list.

The header confirmation exists because the list is a register of cases, not of
the project's cases: an id can name a case in another unit. The 案名 the header
carries is the city's own name for the case, and it is what the resolver's
name step matches against.

The id SHALL be **appended** to the project's case list, never inserted — the
positional fallback binds by index, so the existing ids keep their positions.

#### Scenario: A case the parcel search omitted is confirmed and added

- **WHEN** the parcel search for a project returns no case id, and the 168 list
  names an id whose header returns a row with the case's 案名
- **THEN** the id is appended to the project's case list
- **AND** the id's milestones are read like every other case's

#### Scenario: An unconfirmed id is not added

- **WHEN** an id from the 168 list has no header row
- **THEN** the id does not enter the project's case list
- **AND** the case is named in the refresh report as unconfirmed

#### Scenario: An id the search already returned is not added twice

- **WHEN** the 168 list names an id the parcel search already returned
- **THEN** the id is not appended a second time

#### Scenario: The existing ids keep their positions

- **WHEN** an id is appended to a project's case list
- **THEN** the ids already in the list keep their order
