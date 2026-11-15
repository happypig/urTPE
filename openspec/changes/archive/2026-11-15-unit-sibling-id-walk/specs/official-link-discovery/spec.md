## ADDED Requirements

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
parcels, and a declared parcel count equal to the unit's. A case with no name, or a
name with no parcel, SHALL NOT join. A case that
joins SHALL be added in place, append-only, with its name, header and milestones.
The §8 view-page gate SHALL use the same land-core and own-parcel test, without the count condition, so its verdicts do not change.

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
  own section, but its declared parcel count differs from the unit's and its land core
  does not match at the link threshold
- **THEN** the case is not added by the walk

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

### Requirement: A probed id that did not join is remembered

The system SHALL record every id the walk probed and did not add, as having no case
or as belonging to another unit, in the project's cache. A later walk SHALL issue no
request for a recorded id. A probe that failed with an error (a failed request) SHALL
NOT be recorded, so the next walk tries it again. A cache written before the record
existed SHALL load with an empty record and SHALL behave as a cache that probed
nothing.

#### Scenario: A second walk issues no request
- **WHEN** a walk has finished for a unit and the same walk runs again with no new
  held case
- **THEN** the second walk issues zero header requests

#### Scenario: A failed request is tried again
- **WHEN** the header request for an id raises an error
- **THEN** the id is not recorded, and the next walk probes it again

#### Scenario: An old cache loads
- **WHEN** a cache written before the record existed is loaded
- **THEN** its record of probed ids is empty and loading raises no error
