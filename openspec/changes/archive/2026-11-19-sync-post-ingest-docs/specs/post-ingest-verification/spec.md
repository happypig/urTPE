## Purpose

Give a maintainer one command that proves an emitted dataset and its viewer
are consistent, applies only existing bounded repairs, and then refreshes
all dependent reports.

## ADDED Requirements

### Requirement: The emitted dataset is checked across every output layer

The system SHALL provide `python scripts/post_ingest_check.py`. Before any
report generation, it SHALL compare the record partition and identifiers in
`raw.tsv`, `clean.tsv`, `merged.tsv`, `projects.json` and
`viewer/projects.data.js`. It SHALL run the viewer smoke harness, the
standing silent-failure check, and the offline deployment-target and
viewer/documentation consistency tests. A check that cannot run SHALL be a
failure, not a skipped success.

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

### Requirement: Recovery is the only automatic PDF-ingest repair

When named publisher-truncated exclusions remain and the archived PDF is
available, the command MAY re-ingest that same PDF with
`--recover-truncated`, `--links` and the existing viewer output. It SHALL do
so at most once per invocation and SHALL recheck the result. A residual
truncated row, a recovery refusal, or an unrelated reconcile refusal SHALL
stop the command. It SHALL NOT pass `--allow-reconcile-block`,
`--no-archive`, or any other bypass flag.

A rebuild that needs graph or viewer repair SHALL use the existing
`--from-js` command with link discovery. It SHALL NOT manufacture missing
records or links in documentation tooling. `--check-only` SHALL perform no
repair and no report generation.

#### Scenario: Named truncated rows are recoverable

- **WHEN** the run report names truncated exclusions and the archived PDF
  can be identified
- **THEN** the command invokes the normal CLI once with recovery enabled
- **AND** the recovered emission must pass every local check before reports
  are generated

#### Scenario: Recovery leaves a residual

- **WHEN** the recovery pass leaves a named residual or refuses ingestion
- **THEN** the command exits non-zero with that outcome
- **AND** it does not update dependent reports

#### Scenario: A read-only check is requested

- **WHEN** the maintainer supplies `--check-only`
- **THEN** no ingest, rebuild, documentation write, report write, commit or
  push occurs

### Requirement: Dependent reports update only after a successful recheck

After every local check passes, the command SHALL synchronise
`docs/etl_process.html` and `docs/domain-model.html`, regenerate
`docs/release-diff.html` and `docs/coverage-report.html`, and report the
paths changed. It SHALL update
the dataset count and publication date in `openspec/config.yaml` through
the same checked measurement path. It SHALL NOT commit or push.

The coverage report SHALL use the latest archived 168-list snapshot rather
than an obsolete copy. Its header-scan evidence SHALL be explicitly bounded
to the scan already held; unexamined cases SHALL remain named as such.
Generation failures SHALL be returned as failures.

#### Scenario: All checks pass

- **WHEN** the command finishes its final successful recheck
- **THEN** both documentation pages and both dependent reports reflect the
  current available evidence
- **AND** the configured approval count agrees with the emitted payload

#### Scenario: A report generator fails

- **WHEN** any dependent report generator returns non-zero or cannot produce
  its required measurements
- **THEN** the command exits non-zero and names the failed generator

#### Scenario: Publication is not implied

- **WHEN** local verification and generation succeed
- **THEN** the command reports the generated paths
- **AND** it performs no git commit, push, or deployment claim

### Requirement: Deployment coverage includes the ETL documentation page

The recorded deployment artifact list SHALL include
`docs/etl_process.html`, so `scripts/check_deploy.py` compares that page
with its committed bytes like the other published pages.

#### Scenario: The ETL page is listed for deployment verification

- **WHEN** the deployment record is read
- **THEN** it contains `docs/etl_process.html`
- **AND** a stale or missing served ETL page makes the deploy check fail
