## MODIFIED Requirements

### Requirement: A unit's sibling cases are found by walking the id stems of its held cases

City case ids are a filing day's 7-digit stem plus one digit, so the cases of one
unit sit in one or two adjacent stems. For every project, the system SHALL walk the
7-digit stem of each case it holds and probe, by the case header, each id between
the lowest and the highest held digit of that stem that (a) the project's cache does
not hold, (b) no other project holds, and (c) an earlier walk did not already probe.
It SHALL NOT probe an id outside the held minimum and maximum of a stem, and it
SHALL NOT probe another stem. The walk SHALL run only from a command, never from the
emission path, and the emission path SHALL issue no request because of it.

A probed case SHALL join the project only on positive evidence: the city's own case
name carries a land core that matches the unit's land core at the link threshold, or
the name declares the unit's own district and 段/小段 text, one of the unit's own
parcels, and a declared count that passes the count rule (the name's `等N筆`, or one of its `原N筆`, equals the unit's count at any approval). A case with no name, or a
name with no parcel, SHALL NOT join. A case that
joins SHALL be added in place, append-only, with its name, header and milestones.
The §8 view-page gate SHALL decide a city name by the same rule.

#### Scenario: A sibling of the unit joins
- **WHEN** a unit holds cases `…201` and `…208` of one stem, `…203` is a case whose
  name carries the unit's own parcel in the unit's own section with the unit's declared
  count, and no project holds `…203`
- **THEN** the walk adds `…203` to the unit's cases with its name, header and
  milestones

#### Scenario: A case of another unit is refused
- **WHEN** the probed case's name carries a land core of another section or another
  unit
- **THEN** the case is not added, and the walk records that it probed the id

#### Scenario: A name with an unequal declared count is held back
- **WHEN** the probed case's name declares one of the unit's own parcels in the unit's
  own section, but its declared count (and any `原N筆`) is none of the unit's counts at any
  approval, and its land core does not match at the link threshold
- **THEN** the case is not added by the walk

#### Scenario: A count of an earlier approval joins
- **WHEN** the probed case's name declares the unit's own parcel in its own section and a count that the unit declared at an earlier approval
- **THEN** the walk adds the case

#### Scenario: A case with no parcel in its name is refused
- **WHEN** the probed case has a name that declares no parcel, or no name at all
- **THEN** the case is not added, even though the §8 gate would not reject such a
  name on a view page

#### Scenario: Ids outside the held range are not probed
- **WHEN** a stem's held digits are 3 and 6
- **THEN** the walk probes digits 4 and 5 only, and issues no request for 0–2 or 7–9

#### Scenario: An id another project holds is skipped
- **WHEN** an id in the unit's stem range is held by another project
- **THEN** the walk issues no request for it and does not add it to this unit

#### Scenario: The anchor-drift unit finds its siblings
- **WHEN** the unit is 大安區-懷生段二小段-16 and the city holds `09503201`,
  `09503202` and `09503207` with names that carry the unit's own parcel
- **THEN** all three join the unit

## ADDED Requirements

### Requirement: A case the search refused is admitted only by the count rule

The system SHALL offer a command that admits a case recorded in a project's `search_rejected` when its city name passes the same acceptance rule as the §8 gate, no project holds the id, and the project has not recorded it in `view_rejected`. The command SHALL run as a dry run unless told to apply, SHALL list the ids it would admit without a request, SHALL take the single-writer lock to apply, and SHALL copy each changed cache to a backup first. An admitted case SHALL join the cache in place with its header and milestones. A case the rule refuses SHALL stay in `search_rejected` unchanged. A second run SHALL change nothing.

#### Scenario: A held-back predecessor is admitted

- **WHEN** 文山區-華興段一小段-8地號等4筆 records `09708111` (`…華興段一小段18-1地號等13筆…`) in `search_rejected`, 13 is a count the unit declared at its 2013 approval, and no project holds the id
- **THEN** the command admits `09708111` into the project's cases

#### Scenario: A held or refused case is left alone

- **WHEN** an id in `search_rejected` is held by another project, or its name fails the rule
- **THEN** the command leaves it in `search_rejected` and adds nothing

#### Scenario: The dry run changes nothing

- **WHEN** the command runs without being told to apply
- **THEN** it lists the ids it would admit, issues no request and writes no file

#### Scenario: A second run changes nothing

- **WHEN** the command has applied and runs again
- **THEN** it admits nothing and issues no request
