## MODIFIED Requirements

### Requirement: The cycle runs the existing steps in a fixed order and commits only the report

The requirement's name predates this change: since it, the cycle commits and pushes the emission too. The name is kept as the stable identifier.

The system SHALL provide a coordinator that runs these steps in this order: poll the gazette page, poll the 168 list, detect a gazette to ingest, ingest it, refresh the caches whose cases await approval, rebuild the payload from itself, run the post-ingest check, run the test suite and the viewer smoke run, and then, only after a finished ingest, publish the emission and publish the generated report pages: the release-diff report, the coverage report, the domain model and the ETL page. The emission publication SHALL run before the report publication, so the pages are committed and pushed after the data they describe. Each runs its own commit and push: between them the served site MAY show the new data with the old pages, and a lag that remains after a failed second push SHALL be visible to the deployment check and recorded as a failed publication. The coordinator SHALL add no polling, ingest, refresh or report-generation behavior of its own: each step is the existing command with its existing gates and exit codes.

The coordinator's own use of git SHALL stay read-only: one status. The commit and the push are made by two child commands the coordinator starts after the hash is recorded as finished, the emission publisher and then the report publisher; neither is a bypass of any refusal. The emission publisher SHALL stage and commit only the emission paths — the tracked files under `data/`, the viewer's payload and shell pages, and the emission's own count-and-date sentence in `openspec/config.yaml` — in one path-limited commit, and SHALL push `main` afterwards, verified by asking the remote whether it holds the commit. It SHALL commit nothing else: a file another session has staged is neither committed nor discarded by it, and stays staged for that session. Every git command it runs SHALL be unable to prompt for a credential, and a push or a remote check that exceeds its time limit SHALL be reported as a failed publication that names what did not land. A person SHALL be able to run it by hand, to retry a failed publication.

The emission publisher SHALL refuse, without committing, when a tracked file under `urtpe/` or `scripts/` — the code that produced the emission — has an uncommitted change, so an emission is never committed by a commit that does not explain the code that wrote it. It SHALL commit and push only when the new payload's record count is greater than or equal to the committed payload's record count; a lower count SHALL stop the publication before the commit and wait for a person, because the dataset's measured trajectory only grows and a drop names a defect. Every path the dirty-tree check owns, except the two code directories, SHALL be committed by the emission publisher or the report publisher, so a finished cycle leaves none of them modified and the next gazette is not refused on them; and every emission path SHALL be among the paths the dirty-tree check owns, so another session's uncommitted edit to one of them stops the cycle before the ingest and is never swept into an unattended commit.

#### Scenario: A new gazette passes through every step

- **WHEN** a gazette to ingest exists and every step succeeds
- **THEN** the steps ran in the order above, each once, with the emission publication and the report publication last, the emission publication first
- **AND** the run ends with a record that names the report publication as the last stage reached and the exit code as 0

#### Scenario: The coordinator's own use of git is read-only

- **WHEN** any cycle ends, whether it finished or stopped early
- **THEN** the coordinator itself made no stage, commit, push or checkout
- **AND** the only git command it ran was a read-only status
- **AND** every commit and push of the cycle was made by the emission publisher or the report publisher, run as child commands

#### Scenario: The emission is left for review

- **WHEN** a cycle finished but its emission publication did not run, or failed at its commit, its push or the count guard
- **THEN** the emitted files other than the four generated pages are still uncommitted, or committed but unpushed, in the working tree
- **AND** a person reviews them and publishes or repairs them by hand

#### Scenario: Nothing to ingest causes no write to the emitted dataset

- **WHEN** no archived gazette is newer than the emitted dataset
- **THEN** no ingest, refresh, rebuild, emission publication or report publication runs
- **AND** no file under the emitted output tree is written and nothing is committed or pushed
- **AND** the run is recorded with the poll outcomes

#### Scenario: The emission is published unattended

- **WHEN** an ingest finished, the tests and the viewer smoke run passed, the code directories are clean, and the new payload's record count is not lower than the committed payload's
- **THEN** the emission paths are committed in one path-limited commit and pushed, and the remote is asked afterwards whether it holds the commit
- **AND** a push that did not land is reported as a failed publication

#### Scenario: A record-count drop stops the emission publication

- **WHEN** the new payload's record count is lower than the committed payload's
- **THEN** nothing is committed or pushed
- **AND** the run is recorded as a failed publication that names the count guard
- **AND** the hash stays recorded as finished

#### Scenario: The emission publication refuses uncommitted code

- **WHEN** a tracked file under `urtpe/` or `scripts/` has an uncommitted change when the emission publication runs
- **THEN** the step exits non-zero and commits nothing
- **AND** the run is recorded as a failed publication and the hash stays recorded as finished

#### Scenario: The emission is not published on any other run

- **WHEN** a run found nothing new, found the hash already done, was refused, stopped at a step, found a lock held, found a dirty working tree, or found a hash awaiting diagnosis
- **THEN** the emission publisher does not run

#### Scenario: A failed emission publication does not undo the ingest

- **WHEN** the emission publication fails after a finished ingest
- **THEN** the hash stays recorded as finished and the ingest does not run again
- **AND** a person retries the publication by running the emission publication by hand

#### Scenario: A retry after a failed emission push lands

- **WHEN** the emission publication committed but its push failed, and it runs again
- **THEN** it pushes the commit that is ahead of the remote and exits 0 when the push lands

### Requirement: The report is published only after a finished ingest, and a failed publication never undoes the ingest

After the test and smoke steps have succeeded, the coordinator SHALL record the gazette's hash as finished, and only then run the publication steps. The report publication step SHALL NOT run on a run that did not finish an ingest, and SHALL NOT run when the emission publication that precedes it failed, because the pages would describe an emission that did not land. A failure of a publication step, including its refusal when the report generator's source has uncommitted changes, SHALL be recorded as a failed publication with the step's own exit code, SHALL leave the hash finished, and SHALL NOT start the ingest again. A later run SHALL NOT publish again for a finished hash. A person SHALL retry a failed publication by running the publication step by hand.

#### Scenario: The report is published after a finished ingest

- **WHEN** an ingest finished, the test and smoke steps succeeded, and the emission publication succeeded
- **THEN** the hash is recorded as finished
- **AND** the report publication step runs as the last step

#### Scenario: The report is not published on any other run

- **WHEN** a run found nothing new, found the hash already done, was refused, stopped at a step, found a lock held, found a dirty working tree, found a hash awaiting diagnosis, or its emission publication failed
- **THEN** the report publication step does not run

#### Scenario: A failed publication does not undo the ingest

- **WHEN** the report publication step exits non-zero after a finished ingest
- **THEN** the run is recorded as a failed publication with that exit code
- **AND** the hash stays recorded as finished
- **AND** the ingest does not run again

#### Scenario: The publication step refuses because the generator is not committed

- **WHEN** the report publication step exits 2 because the report generator's source has uncommitted changes
- **THEN** the run is recorded as a failed publication with exit 2
- **AND** the hash stays recorded as finished

#### Scenario: A resumed cycle that finishes publishes the report

- **WHEN** a person resumes a stopped hash and every remaining step succeeds
- **THEN** the report publication step runs last

#### Scenario: A later run does not publish again

- **WHEN** a later run sees a hash that finished, whether its publication succeeded or failed
- **THEN** the report publication step does not run for it

### Requirement: Every run is recorded, including the ones that find nothing

The coordinator SHALL append one structured record for every run it starts, whatever the outcome: the time, the poll outcomes, the gazette hash when one was involved, the last stage reached, the failed stage when there was one, the exit code, and the outcome as a word (nothing new, ingested, refused, stopped, already done, awaiting diagnosis, publication failed). A run that found nothing SHALL be recorded as such, so a period with no run is distinguishable from a period with nothing to do. A failed emission publication and a failed report publication are both publication failures; the record names which one by its failed stage.

A dry run SHALL run only read-only steps, SHALL report which steps it would take, including the emission publication and the report publication when a gazette is ready, and SHALL write no record, no archive file and nothing under the emitted output tree.

#### Scenario: A run with nothing new is recorded

- **WHEN** a cycle starts and the polls find nothing new
- **THEN** one record states that nothing was new, with the time

#### Scenario: A gap between runs is visible from the records alone

- **WHEN** no record exists for longer than the expected interval
- **THEN** the gap is detectable from the records without inspecting the publisher

#### Scenario: A dry run writes nothing

- **WHEN** the coordinator runs in dry-run mode
- **THEN** it reports the steps it would take
- **AND** no record, archive file or emitted file is written

#### Scenario: A dry run names the report publication

- **WHEN** the coordinator runs in dry-run mode and a gazette is ready to ingest
- **THEN** the steps it reports end with the emission publication and the report publication, the emission publication first
