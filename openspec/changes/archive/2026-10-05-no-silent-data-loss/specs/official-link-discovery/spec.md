## Purpose

Defines the guarantee that discovered link data reaches the viewer, and that a run
which fails to attach it says so instead of emitting a dataset that looks complete.

## ADDED Requirements

### Requirement: Report link data that a run failed to attach

The system SHALL report link-derived data that is absent from an emitted dataset, naming the fields and the affected counts, and SHALL name the run step that attaches them. Absence is a fault of the run when **no** project in the dataset carries it, because that is indistinguishable from a run that collected nothing.

Partial coverage is **not** a fault: the portals do not cover every project, so a dataset in which some projects carry link data and others do not is the expected state. Partial coverage SHALL be reported as a count so a regression against a previous emission is visible, and SHALL NOT be raised as a fault.

#### Scenario: No project has link data

- **WHEN** an emitted dataset carries no link field on any project and none on any approval
- **THEN** the run reports a fault naming the fields and the number of projects
- **AND** reports that the viewer cannot render the views that depend on them

#### Scenario: The report names the step that did not attach the data

- **WHEN** link data is reported missing
- **THEN** the report names the run step that attaches it, so the cause is identifiable from the output alone

#### Scenario: Some projects have link data and some do not

- **WHEN** an emitted dataset carries link data on some projects and not others
- **THEN** both counts are reported
- **AND** no fault is raised, because the portals do not cover every project
- **AND** the dataset is not described as fully covered

#### Scenario: Every project has link data

- **WHEN** every emitted project carries the link fields the capability requires
- **THEN** no fault and no partial-coverage note is reported on their account
