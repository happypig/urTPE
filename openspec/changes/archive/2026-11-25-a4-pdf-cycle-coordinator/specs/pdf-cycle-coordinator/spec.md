## Purpose

Runs the existing acquisition, ingest, refresh, rebuild, verification and report-publication commands in one fixed order, stops at the first refusal, and records where each run stopped, so a new gazette reaches a checked emission without a person starting a chain of commands by hand.

## ADDED Requirements

### Requirement: The cycle runs the existing steps in a fixed order and commits only the report

The system SHALL provide a coordinator that runs these steps in this order: poll the gazette page, poll the 168 list, detect a gazette to ingest, ingest it, refresh the caches whose cases await approval, rebuild the payload from itself, run the post-ingest check, run the test suite and the viewer smoke run, and then, only after a finished ingest, publish the generated report pages: the release-diff report, the coverage report, the domain model and the ETL page. The coordinator SHALL add no polling, ingest, refresh or publication behavior of its own: each step is the existing command with its existing gates and exit codes.

The coordinator's own use of git SHALL be read-only. It SHALL NOT stage, commit or push the emitted files: after a finished cycle they stay uncommitted for a person to review. The only commit and push a cycle causes is the one the existing publication step makes, and that step stages and commits only those four generated pages.

#### Scenario: A new gazette passes through every step

- **WHEN** a gazette to ingest exists and every step succeeds
- **THEN** the steps ran in the order above, each once, with the report publication last
- **AND** the run ends with a record that names the report publication as the last stage reached and the exit code as 0

#### Scenario: The coordinator's own use of git is read-only

- **WHEN** any cycle ends, whether it finished or stopped early
- **THEN** the coordinator itself made no stage, commit, push or checkout
- **AND** the only git command it ran was a read-only status

#### Scenario: The emission is left for review

- **WHEN** a cycle finishes
- **THEN** the emitted files other than the four generated pages are still uncommitted in the working tree
- **AND** the only paths the cycle caused to be committed are the four generated pages

#### Scenario: Nothing to ingest causes no write to the emitted dataset

- **WHEN** no archived gazette is newer than the emitted dataset
- **THEN** no ingest, refresh, rebuild or report publication runs
- **AND** no file under the emitted output tree is written
- **AND** the run is recorded with the poll outcomes

### Requirement: Only an archived, verified gazette that the dataset does not yet reflect starts an ingest

The coordinator SHALL start an ingest only for an archived gazette that meets all of these: its publication date is later than the publication date of the emitted dataset; its archived file matches its archive entry; and the coordinator has not recorded its hash as finished or as stopped. The coordinator SHALL decide this from the archive and from its own record, and SHALL NOT decide it from a poller's status word alone, because any earlier poll, including one started by hand or by another scheduled task, consumes a `new_gazette` status. The coordinator SHALL ingest the archived, dated file and SHALL NOT ingest the publisher's live link.

An archived gazette that the dataset already reflects, a re-upload of such a gazette, a failed check and a dry-run answer SHALL NOT start an ingest.

The coordinator SHALL keep an operational record of the hashes it finished and of the hashes it stopped on. A hash that finished SHALL NOT be ingested again, however many later runs start. That record SHALL NOT key on 編號, `recno` or `project_id`.

#### Scenario: A gazette archived by an earlier poll is still ingested

- **WHEN** a poll started by hand or by another task archived a new gazette, and this run's poll then reports the page unchanged
- **THEN** the archived gazette is still found as newer than the dataset and is ingested once in this run

#### Scenario: A verified new gazette is ingested exactly once

- **WHEN** an archived gazette is newer than the dataset, verifies, and is recorded neither as finished nor as stopped
- **THEN** it is ingested once in this run
- **AND** the next run, seeing the same hash as finished, does not ingest it again

#### Scenario: A re-upload of a gazette the dataset reflects never starts an ingest

- **WHEN** the gazette poll reports `reuploaded` for a document whose gazette the dataset already reflects
- **THEN** no ingest runs

#### Scenario: A failed or dry-run poll never starts an ingest

- **WHEN** the gazette poll reports `failed` or `would_download` and no archived gazette is newer than the dataset
- **THEN** no ingest runs

#### Scenario: A gazette that does not verify is refused

- **WHEN** an archived gazette is newer than the dataset but its file does not match its archive entry
- **THEN** no ingest runs
- **AND** the run is recorded as stopped at the detection step with the mismatch as the reason

#### Scenario: A completed cycle is not repeated

- **WHEN** a cycle has finished for a hash and a later run sees the same archived gazette
- **THEN** the later run records that the hash is already done
- **AND** no ingest, refresh or rebuild runs for it

#### Scenario: Older archived gazettes are never ingested

- **WHEN** the record is empty and the archive holds gazettes that are all older than or equal to the dataset's publication date
- **THEN** none of them is treated as a gazette to ingest

### Requirement: The first refusal stops the cycle

The coordinator SHALL stop at the first step that exits non-zero, up to and including the test and smoke steps. It SHALL NOT retry past a refusal, SHALL NOT start a later step, and SHALL NOT pass `--allow-reconcile-block` or `--no-archive` to any command. A refusal by the ingest (exit 2, 3 or 4) SHALL leave the emitted files as that command left them: the coordinator SHALL NOT repair, restore or overwrite them.

A cycle that stopped at a step SHALL be recorded with that step as the failed stage. A later gazette, or a later successful step in another run, SHALL NOT make the failed stage read as successful. The hash of a cycle that did not finish SHALL NOT be recorded as finished.

A stop caused by a refusal or a failed step SHALL wait for a person: later scheduled runs SHALL record that the hash awaits diagnosis and SHALL NOT run it again. A person SHALL restart it with an explicit request naming the hash, which restarts at the failed stage. A stop caused only by a held lock or a dirty working tree is transient: the next scheduled run SHALL try again.

#### Scenario: An ingest refusal stops everything after it

- **WHEN** the ingest exits 2, 3 or 4
- **THEN** no refresh, rebuild, check, test or publication step runs
- **AND** the record names the ingest as the failed stage with that exit code
- **AND** the hash is not recorded as finished

#### Scenario: A failed refresh is not hidden by a rebuild

- **WHEN** the refresh step exits non-zero
- **THEN** the rebuild does not run
- **AND** the record names the refresh as the failed stage

#### Scenario: No bypass flag is ever passed

- **WHEN** the coordinator starts any command
- **THEN** the command line holds neither `--allow-reconcile-block` nor `--no-archive`

#### Scenario: A later gazette does not mask an earlier failure

- **WHEN** a cycle stopped at a step, and a newer gazette is later acquired
- **THEN** the record of the earlier cycle still names its failed stage
- **AND** the earlier hash is still not recorded as finished

#### Scenario: A stopped gazette is not retried on its own

- **WHEN** a hash is recorded as stopped at a refusal and a later scheduled run starts
- **THEN** the run records that the hash awaits diagnosis
- **AND** it runs none of that hash's steps again

#### Scenario: A person resumes a stopped cycle by name

- **WHEN** a person asks the coordinator to resume a stopped hash
- **THEN** the cycle restarts at the failed stage and not at the first step

#### Scenario: A transient stop is retried by the next run

- **WHEN** a cycle stopped only because a lock was held or the working tree was dirty
- **THEN** the next scheduled run tries the same gazette again without a person's request

### Requirement: The report is published only after a finished ingest, and a failed publication never undoes the ingest

After the test and smoke steps have succeeded, the coordinator SHALL record the gazette's hash as finished, and only then run the report publication step. The report publication step SHALL NOT run on a run that did not finish an ingest. A failure of the publication step, including its refusal when the report generator's source has uncommitted changes, SHALL be recorded as a failed publication with the step's own exit code, SHALL leave the hash finished, and SHALL NOT start the ingest again. A later run SHALL NOT publish again for a finished hash. A person SHALL retry a failed publication by running the publication step by hand.

#### Scenario: The report is published after a finished ingest

- **WHEN** an ingest finished and the test and smoke steps succeeded
- **THEN** the hash is recorded as finished
- **AND** the report publication step runs as the last step

#### Scenario: The report is not published on any other run

- **WHEN** a run found nothing new, found the hash already done, was refused, stopped at a step, found a lock held, found a dirty working tree, or found a hash awaiting diagnosis
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

### Requirement: The coordinator never holds the emitted tree's lock, and a held lock stops the cycle

The coordinator SHALL NOT hold the single-writer lock over the emitted output tree across the commands it starts: each command that writes takes its own lock. Before the first step that writes the emitted files or the cache, the coordinator SHALL check that no other writer holds that lock. If a writer holds it at the start, or any command exits 5 because it does, the coordinator SHALL stop, record the exit 5 and the step, and write nothing for that step.

The coordinator SHALL NOT assume the cache is unchanged between two steps, because another writer, such as the nightly sweep, may run between them.

Two cycles SHALL NOT run at once. The coordinator SHALL use a lock of its own, over a different location from the emitted output tree, so that a second cycle that starts while one is running stops and records that it did, and so that the commands a cycle starts are never blocked by it.

#### Scenario: A writer holds the lock when the cycle starts

- **WHEN** another run holds the single-writer lock over the emitted tree at the start of a cycle that has a gazette to ingest
- **THEN** the cycle stops before any write step with exit 5 recorded
- **AND** the emitted files and the cache are unchanged

#### Scenario: A writer takes the lock between two steps

- **WHEN** a step exits 5 because another writer took the lock after the previous step finished
- **THEN** the cycle stops at that step with exit 5 recorded
- **AND** the hash is not recorded as finished, so the next run resumes the cycle

#### Scenario: The coordinator leaves the emitted tree's lock free between steps

- **WHEN** the coordinator is between two steps
- **THEN** it holds no single-writer lock over the emitted tree
- **AND** the child command that follows can take it

#### Scenario: A second cycle starts while one runs

- **WHEN** a cycle is already running and a second one starts
- **THEN** the second stops without running any step
- **AND** it records that another cycle was running

### Requirement: The cycle refuses a dirty working tree

Before the first step that writes the emitted files or the cache, the coordinator SHALL check the working tree for uncommitted changes in the paths a cycle owns, which SHALL be a fixed, documented list. The list SHALL name the emitted files, the four generated pages, and the two code directories `urtpe/` and `scripts/`, so that an ingest never runs with uncommitted changes to the code it runs. Only tracked files that changed count: an untracked file SHALL NOT stop a cycle. If anything other than this cycle has changes there, including the output of an earlier cycle that no one has reviewed and committed, the coordinator SHALL stop, record the paths as the reason, write nothing, and leave the next run to try again. Uncommitted changes outside the owned paths SHALL NOT stop a cycle. A run that has nothing to ingest SHALL NOT be stopped by a dirty tree.

#### Scenario: An owned path has uncommitted changes

- **WHEN** a path the cycle owns carries an uncommitted change and a gazette is ready to ingest
- **THEN** the cycle stops before any write step
- **AND** the record lists the dirty paths as the reason
- **AND** nothing is written or discarded

#### Scenario: The previous cycle's output is not yet committed

- **WHEN** a cycle finished and a person has not yet committed its output, and a newer gazette is then ready
- **THEN** the new cycle stops with the dirty paths recorded as the reason
- **AND** the newer gazette waits, untouched, for the next run

#### Scenario: Uncommitted code stops a cycle

- **WHEN** a tracked file under `urtpe/` or `scripts/` has an uncommitted change and a gazette is ready to ingest
- **THEN** the cycle stops before any write step
- **AND** the record lists that file as the reason, and the next run tries again

#### Scenario: An untracked file does not stop a cycle

- **WHEN** the only difference under `urtpe/` or `scripts/` is a new untracked file
- **THEN** the cycle runs as normal

#### Scenario: An unrelated path is dirty

- **WHEN** only paths outside the owned list carry uncommitted changes
- **THEN** the cycle runs as normal

#### Scenario: A quiet day with a dirty tree

- **WHEN** the tree is dirty in an owned path and no gazette is ready to ingest
- **THEN** the run records that nothing was new and does not stop for the dirty tree

### Requirement: Every run is recorded, including the ones that find nothing

The coordinator SHALL append one structured record for every run it starts, whatever the outcome: the time, the poll outcomes, the gazette hash when one was involved, the last stage reached, the failed stage when there was one, the exit code, and the outcome as a word (nothing new, ingested, refused, stopped, already done, awaiting diagnosis, publication failed). A run that found nothing SHALL be recorded as such, so a period with no run is distinguishable from a period with nothing to do.

A dry run SHALL run only read-only steps, SHALL report which steps it would take, including the report publication when a gazette is ready, and SHALL write no record, no archive file and nothing under the emitted output tree.

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
- **THEN** the steps it reports end with the report publication

### Requirement: The cycle runs daily and is the only scheduled publisher of the report pages

The coordinator SHALL run once a day at 04:00 local time from one scheduled task. The nightly sweep SHALL stay its own scheduled task and SHALL stop no later than 03:30, so the two do not overlap. The release-diff report and the generated pages that go with it SHALL have one scheduled publisher only: the coordinator, after a finished ingest. No other scheduled task SHALL publish them.

#### Scenario: The daily run starts after the sweep window

- **WHEN** the scheduled time arrives
- **THEN** the cycle starts at 04:00, after the sweep's 03:30 stop time

#### Scenario: The report has one scheduled publisher

- **WHEN** the schedule is in place
- **THEN** the coordinator is the only scheduled task that publishes the release-diff report and its pages
- **AND** the former weekly task that did so is not scheduled
