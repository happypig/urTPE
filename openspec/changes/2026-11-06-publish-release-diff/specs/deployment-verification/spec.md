## ADDED Requirements

### Requirement: Every published page is covered by the artifact list

The recorded artifact list SHALL name every page the repository publishes as
part of the site, including pages that live outside the viewer's own
directory. A published page that is not listed is a page whose served bytes
are never compared against the committed build, so it can serve superseded
content indefinitely while every check passes.

The release-diff report SHALL be listed, so a report that was regenerated and
not pushed — or pushed and not regenerated — is reported as stale.

#### Scenario: The release-diff report is listed

- **WHEN** the deploy record is read
- **THEN** it names `docs/release-diff.html` among the artifacts
- **AND** the deployment check compares that page's served bytes against the committed blob

#### Scenario: A listed artifact is not tracked by git

- **WHEN** the recorded artifact list names a path the repository does not track
- **THEN** that is reported
- **AND** the check does not pass silently on a file git does not know about

#### Scenario: The report is regenerated but not pushed

- **WHEN** the committed report differs from the served bytes
- **THEN** the report is reported stale
- **AND** the check exits non-zero, because the site is showing a superseded report
