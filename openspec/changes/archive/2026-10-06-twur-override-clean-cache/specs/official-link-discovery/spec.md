## MODIFIED Requirements

### Requirement: A human-verified portal link may be recorded as configuration

The system SHALL accept a portal view id recorded against a project by a person who
verified it, and SHALL apply it when discovery found no link for that project. The record
SHALL be stored outside the working tree's derived data, be version-controlled, and carry
the evidence it was verified against: where the page was seen, what its title said, when it
was verified, and why automated matching could not claim it.

A recorded link SHALL fill a gap and SHALL NOT displace a link discovery found on its own.
Where both exist, discovery's answer is kept, so a recorded link can never silently replace
what the portal actually returned for a project.

An applied recorded link SHALL be completed from the portal page itself rather than from
hand-entered values, so milestones and case identifiers come from the same source as any
discovered link.

A recorded link SHALL be reachable whenever discovery runs, and SHALL NOT depend on a
per-project cache entry existing. The per-project cache is derived data and is not
version-controlled, so a record consulted only from inside a cache read can never satisfy
a rebuild from an empty cache.

Applying a recorded link SHALL NOT suppress the rest of discovery. City-platform search,
milestones, implementation and rewards SHALL still run for the project, and the result
SHALL be written to the per-project cache in the ordinary shape, so an applied record
yields a complete result rather than a link with every other field empty.

#### Scenario: A verified link is recorded

- **WHEN** a person confirms a portal page for a project that discovery could not match
- **THEN** the record is stored with the page location, its title, the date, and the reason automated matching failed
- **AND** the record is version-controlled, so the decision survives a fresh clone

#### Scenario: The record fills a gap

- **WHEN** a project has no portal link and a recorded link exists for it
- **THEN** the recorded link is applied
- **AND** the project's milestones and case identifiers are read from that portal page

#### Scenario: The record does not displace a discovered link

- **WHEN** a project already has a portal link found by discovery and a recorded link also exists
- **THEN** the discovered link is kept
- **AND** the recorded link is not applied to it

#### Scenario: A recorded link survives a fresh clone

- **WHEN** the emitted dataset is rebuilt on a machine that has no per-project cache
- **THEN** the recorded link is still available, because it is configuration rather than a cache artefact
- **AND** the record is applied even though no cache entry for the project exists

#### Scenario: The record applies with no portal index available

- **WHEN** the national-portal index is empty or could not be built
- **THEN** a recorded link is still applied
- **AND** the national-portal step is not skipped wholesale, since skipping it would strand the record exactly when it is needed

#### Scenario: Applying the record does not suppress discovery

- **WHEN** a recorded link is applied to a project
- **THEN** city-platform search still runs for that project
- **AND** the result carries the city case identifiers and their milestones
- **AND** a cache entry is written in the ordinary shape, so a later run resumes from it

#### Scenario: An unexplained record is refused

- **WHEN** a record names a view id but carries no evidence of where it was verified
- **THEN** it is not applied
- **AND** the record is reported as incomplete, because an unattributed link cannot be audited

#### Scenario: A record naming a project that does not exist

- **WHEN** a recorded link names a project absent from the emitted dataset
- **THEN** it is reported rather than silently retained, since the identity may have moved