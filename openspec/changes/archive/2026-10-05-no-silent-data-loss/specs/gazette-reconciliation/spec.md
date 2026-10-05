## Purpose

Defines the additional shape a total re-key is reported under, so that a wholesale
identity change is distinguishable from an ordinary set of moves by every check that
guards the caches — not only by reconciliation.

## ADDED Requirements

### Requirement: A total re-key is reported as a distinct outcome by every guard

A wholesale change of project identity SHALL be reported as its own outcome, distinct
from an ordinary move count and distinct from "nothing changed". Any guard placed over
the caches SHALL observe it, because a guard that cannot see it passes while every cache
is orphaned.

#### Scenario: Every identity changes

- **WHEN** a run leaves no project identity present both before and after
- **THEN** the outcome is reported as a total re-key, naming the count before and after
- **AND** it is not reported as an absence of regressions

#### Scenario: Every cache directory is orphaned

- **WHEN** every cached identity is absent from the new dataset
- **THEN** that is reported as a fault rather than recorded as information
- **AND** the report states that no cached identity survived, so the caches cannot be located by name

#### Scenario: Some identities move

- **WHEN** some identities are present before and after and some are only before
- **THEN** ordinary regressions and the newly absent identities are reported separately
- **AND** the newly absent identities are not reported as regressions on identities that still exist

#### Scenario: A run changes nothing

- **WHEN** the identities before and after are identical
- **THEN** no re-key is reported and no fault is raised

#### Scenario: The guard and the reconciliation agree

- **WHEN** a run re-keys every identity
- **THEN** reconciliation and the cache guard report the same outcome
- **AND** neither reports success while every cache is orphaned
