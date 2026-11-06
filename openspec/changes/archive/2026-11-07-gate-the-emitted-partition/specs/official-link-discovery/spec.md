## ADDED Requirements

### Requirement: The city-platform badge and the unplaced-node flag agree

The system SHALL keep the two statements of the same fact in agreement. A
record's city-platform badge is drawn from the case ids bound to that record;
the review flag `節點未能對應平台案件` states in words that the record binds
none. A record that binds no case id and carries no such flag SHALL be
reported, because it renders no badge and names no finding, so the loss is
invisible. A record that binds a case id and still carries the flag SHALL be
reported, because the flag is then stale and reads as a live finding.

The agreement SHALL be checked only for a project link discovery reached. A
project whose own link set is empty was not reached by discovery, so its
records' badges are absent for a reason the coverage report already names.
A run that performed no discovery at all SHALL NOT raise this fault, because
it binds nothing everywhere and the wholesale-absence report already covers
it.

#### Scenario: A record binds nothing and says nothing

- **WHEN** a record of a project link discovery reached binds no city-platform
  case id and carries no `節點未能對應平台案件` flag
- **THEN** the emission check names that record and its project
- **AND** reports that it renders no badge and carries no review finding

#### Scenario: A record binds a case and still carries the flag

- **WHEN** a record of a project link discovery reached binds a city-platform
  case id and still carries the `節點未能對應平台案件` flag
- **THEN** the emission check names that record and reports the flag as stale

#### Scenario: A record that binds nothing and says so is not a fault

- **WHEN** a record of a project link discovery reached binds no city-platform
  case id and carries the `節點未能對應平台案件` flag
- **THEN** no fault is raised on that record's account
- **AND** the flag and the badge agree

#### Scenario: A project discovery never reached is not a fault

- **WHEN** a project's own link set is empty, so discovery found no portal
  record for it
- **THEN** no badge/flag fault is raised on that project's records
- **AND** the project's absence is reported as coverage, which is what it is

#### Scenario: A run without discovery raises no badge/flag fault

- **WHEN** a run completes without link discovery, so no record binds a case id
- **THEN** no badge/flag fault is raised
- **AND** the wholesale-absence report still names the missing link data

## MODIFIED Requirements

### Requirement: Every emission path runs the emission-fault check

The pipeline's emission path SHALL call the emission-fault check
(`urtpe.emission.emission_faults`) on the projects of the document it is about to
write, after link data would have been attached and before any artifact is
written. Wholesale absence of link data (no project carrying any link field)
SHALL be reported as a fault naming the fields, the counts, and the run step that
attaches them; partial coverage SHALL NOT be raised as a fault. The check SHALL
report through the run report and the console. The check is a warning: it SHALL
NOT refuse the run, because `--links` is advisory by design (D5).

The same check SHALL compare each record's city-platform badge against its
`節點未能對應平台案件` flag, and report a disagreement under the same warning
contract. The comparison SHALL cover the records of the projects link discovery
reached; a project whose own link set is empty carries no badge because
discovery found no portal record for it, which the coverage report already
names.

#### Scenario: A run without --links still reports the missing link data

- **WHEN** a run completes without link discovery and every project carries no
  link field
- **THEN** the run reports the wholesale-absence fault, naming the fields and the
  step that attaches them
- **AND** the report appears in `review_report.txt` and on the console
- **AND** the run exits 0 — the report is a warning, not a refusal

#### Scenario: A run with link data reports no emission fault

- **WHEN** a run completes with link discovery and at least one project carries a
  link field
- **THEN** no wholesale-absence fault is reported
- **AND** partial coverage (some projects without portal records) is reported,
  if at all, as a count rather than a fault

#### Scenario: A badge and a flag that disagree are reported

- **WHEN** a record of a project link discovery reached binds a city-platform
  case id but still carries the `節點未能對應平台案件` flag
- **THEN** the run reports the disagreement, naming the record
- **AND** the run exits 0 — the report is a warning, not a refusal
