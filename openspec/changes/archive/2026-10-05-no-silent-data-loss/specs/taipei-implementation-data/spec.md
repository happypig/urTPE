## Purpose

Defines how the viewer behaves when a field it reads is absent from the dataset, and
how the absence of implementation and reward data is reported rather than absorbed.

## ADDED Requirements

### Requirement: The viewer degrades rather than blanking

The viewer SHALL render every project that the dataset contains. An approval or project
lacking an optional field SHALL cost only the view that field feeds; it SHALL NOT leave
the detail pane showing its empty state, and it SHALL NOT prevent any other project
from being rendered.

#### Scenario: One approval lacks a link set

- **WHEN** an approval carries no link data and the viewer reads that field while rendering its project
- **THEN** the project renders, omitting only the element that field feeds
- **AND** every other project still renders

#### Scenario: No project has link data

- **WHEN** the whole dataset lacks link data
- **THEN** every project still renders its published fields
- **AND** the milestone cards, portal badges and execution-stage labels are omitted rather than shown empty

#### Scenario: A field the viewer reads is absent from every record

- **WHEN** a field the viewer reads is absent from every approval in the dataset
- **THEN** the viewer still lists and renders every project
- **AND** the absence is detectable by a check over the dataset rather than only by opening the page

### Requirement: Report implementation and reward data that a run failed to attach

The system SHALL report implementation and reward fields absent from an emitted dataset.
Their absence SHALL be reported as a fault of the run, since the viewer renders cards
from them and their absence is otherwise indistinguishable from having none.

#### Scenario: No approval carries an implementation snapshot

- **WHEN** an emitted dataset carries no implementation snapshot on any approval and no implementation object on any project
- **THEN** the run reports the absence with both counts
- **AND** states that the implementation and reward cards cannot render

#### Scenario: Snapshots are present for some approvals only

- **WHEN** some approvals carry a snapshot and others do not
- **THEN** the run reports both counts rather than treating the populated set as the whole
