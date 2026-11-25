## MODIFIED Requirements

### Requirement: The emitted dataset is checked across every output layer

The system SHALL provide `python scripts/post_ingest_check.py`. Before any
report generation, it SHALL compare the record partition and identifiers in
`raw.tsv`, `clean.tsv`, `merged.tsv`, `projects.json` and
`viewer/projects.data.js`. It SHALL run the viewer smoke harness, the
standing silent-failure check, and the offline deployment-target and
viewer/documentation consistency tests. A check that cannot run SHALL be a
failure, not a skipped success.

A consistency test that compares a fact generated from the payload (the
approval count and publication date in `openspec/config.yaml`) with the
payload compares something this command itself updates later. The initial
check, before generation, SHALL therefore leave out those named tests, so a
payload that moves a count does not stop the command on a sentence the
command is about to write. The check after generation SHALL run every test,
including the left-out ones, and a generation that left a fact stale SHALL
still stop the command. A read-only check (`--check-only`) generates nothing,
so it SHALL run every test. Each left-out test SHALL be named in one list,
and every name in it SHALL exist, so the list cannot drift silently.

The command SHALL distinguish publisher-truncated rows named in the run
report from unexplained gaps. An unexplained gap SHALL stop the command.
It SHALL NOT retry a non-zero CLI exit as though it were transient.

#### Scenario: A complete emission passes the local checks

- **WHEN** every record belongs to exactly one project, the viewer payload
  matches `projects.json`, and every standing check succeeds
- **THEN** the command reports each successful check and continues to report
  generation

#### Scenario: The viewer payload belongs to another emission

- **WHEN** `viewer/projects.data.js` differs from `data/projects.json`
- **THEN** the command names the mismatch and does not generate dependent
  reports until a recheck passes

#### Scenario: The record partition is broken

- **WHEN** a cleansed record is absent, duplicated, or unexplained in the
  graph payload
- **THEN** the command names the affected recno and exits non-zero

#### Scenario: A payload that moves the record count passes the initial check

- **WHEN** the emitted payload carries a different record count from the
  sentence in `openspec/config.yaml`, and every other check succeeds
- **THEN** the initial check does not stop on that sentence
- **AND** the command continues to report generation, which updates it

#### Scenario: A generation that leaves a fact stale fails the final check

- **WHEN** report generation finishes and `openspec/config.yaml` still states a
  count or date that differs from the payload
- **THEN** the check after generation fails and the command exits non-zero

#### Scenario: A read-only check runs every test

- **WHEN** the maintainer supplies `--check-only` and the config sentence
  differs from the payload
- **THEN** the command fails on that test and writes nothing
