## Purpose

Shows the operator the recent runs of the PDF-cycle coordinator on one local page, so a stopped cycle or a new gazette is visible without reading the record file.

## ADDED Requirements

### Requirement: The page shows the recent cycles from the record

The system SHALL generate a page from the coordinator's cycle record. The page SHALL list the most recent runs, newest first, with for each run: the time, the outcome word, the last stage reached, the failed stage when there was one, and the exit code. A run that stopped SHALL be visibly different from a run that finished or found nothing. The page SHALL show the time of the newest record, and SHALL show a warning when no record is newer than the expected interval, so a stopped schedule is visible.

#### Scenario: A stopped cycle is easy to see

- **WHEN** the newest run stopped at the refresh step with exit 5
- **THEN** that run is shown as stopped, with the refresh as the failed stage and 5 as the exit code

#### Scenario: A quiet day is shown as a quiet day

- **WHEN** the newest run found nothing new
- **THEN** it is shown with that outcome and its time, and not as a failure

#### Scenario: The schedule has stopped

- **WHEN** the newest record is older than the expected interval
- **THEN** the page shows a warning that no run has been recorded since that time

### Requirement: The page is read-only, local and self-contained

The generator SHALL read the cycle record and write only its own output file. It SHALL NOT write under the emitted output tree, the archive or the viewer, SHALL NOT start a cycle, and SHALL make no network request. The page SHALL open from the local file system with no external script or stylesheet. The page SHALL NOT be written to a folder that GitHub Pages publishes, and its output path SHALL be ignored by git, so an operational log is not published by accident.

#### Scenario: Generating the page changes nothing else

- **WHEN** the page is generated
- **THEN** the only file written is the page itself
- **AND** the cycle record is unchanged

#### Scenario: The page is not published

- **WHEN** the repository is committed and pushed to the branch Pages serves
- **THEN** the page is not among the committed files
- **AND** no served path reaches it

#### Scenario: The page works offline

- **WHEN** the page is opened from the local file system with no network
- **THEN** it renders completely
