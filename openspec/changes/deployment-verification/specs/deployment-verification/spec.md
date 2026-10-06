# deployment-verification Specification

## Purpose

Allow an analyst to tell, without opening a browser, whether the published site is the
build this repository currently holds — and to keep the published address written down in
one place, with its capitalisation pinned to the repository name so it cannot silently
become a URL that serves a "Page not found" document.

The site is a static `file://` bundle published to GitHub Pages from a branch of this
repository. Nothing serves it, no CI publishes it, and no browser test renders it, so
"what is deployed" and "what is committed" are otherwise two facts nobody ever compares.

## ADDED Requirements

### Requirement: The deploy target is recorded in one place

The system SHALL record the published site's owner, repository, base URL and artifact list
in exactly one tracked file, and the documentation and the checking script SHALL both read
that record rather than restating the address. A published address known only from a
browser tab, or restated in two places, is a URL that will eventually be wrong somewhere
with nothing to notice.

#### Scenario: The target is recorded

- **WHEN** an analyst asks where the site is published
- **THEN** the answer is one tracked file naming owner, repository, base URL and artifacts
- **AND** the documentation cites that same base rather than its own copy

### Requirement: The recorded address matches the repository name exactly

The recorded base URL's final path segment SHALL equal the repository name taken from the
git remote, compared **case-sensitively**. GitHub Pages paths are case-sensitive, so
`/urtPE/` and `/urTPE/` are different sites and only one of them exists; the wrong one
answers with a "Page not found" document that a browser will happily keep rendering from
cache.

This SHALL be verifiable without a network request, because a check that needs the network
cannot run in the offline test suite and therefore would not have run before the mistake.

#### Scenario: The capitalisation is right

- **WHEN** the repository is named `urTPE` and the recorded path is `/urTPE/`
- **THEN** the recorded target is accepted

#### Scenario: The capitalisation is wrong

- **WHEN** the repository is named `urTPE` and the recorded path is `/urtPE/`
- **THEN** the target is rejected
- **AND** the report names capitalisation as the cause, because a 404 from Pages is
  otherwise indistinguishable from an unbuilt site and sends the investigation the wrong way

### Requirement: A deployed build is compared to the committed build

For every artifact the system SHALL compare the bytes served at the canonical URL against
the bytes of the same path in the repository's `HEAD`, by digest of the exact bytes. An
artifact whose digests match SHALL be reported fresh; one that is served but differs SHALL
be reported stale; one that is absent SHALL be reported missing. The three states SHALL be
distinguishable, because "stale" and "missing" call for different responses and collapsing
them would let a stale build pass as a healthy one.

The comparison SHALL read the committed bytes without altering them. Line-ending rewriting
on the way out would report every artifact as stale.

#### Scenario: Everything is current

- **WHEN** every listed artifact is served with bytes identical to its `HEAD` blob
- **THEN** each is reported fresh and the check exits successfully

#### Scenario: A build is published from an older commit

- **WHEN** an artifact is served but its digest differs from the `HEAD` blob
- **THEN** that artifact is reported stale
- **AND** the check exits non-zero, since a site showing superseded data reads as current

#### Scenario: An artifact is not reachable

- **WHEN** an artifact cannot be fetched at the canonical URL
- **THEN** it is reported missing with the reason
- **AND** the check exits non-zero

#### Scenario: A listed artifact is not in the repository

- **WHEN** the recorded artifact list names a path the repository does not track
- **THEN** that is reported
- **AND** the check does not pass silently on a file git does not know about

### Requirement: Network checks stay out of the offline suite

The test suite SHALL NOT require network access. Checks that must reach the published site
SHALL be a runnable command, not a test case, so the suite's offline guarantee is preserved
and a network outage cannot be mistaken for a code regression.

#### Scenario: The suite runs without a network

- **WHEN** the test suite runs with no connectivity
- **THEN** it completes successfully
- **AND** the published-site check remains available as a separate command

### Requirement: Stated dataset counts are checkable

A count stated in project configuration SHALL be verifiable against the emitted payload
rather than maintained by hand, so a dataset that grows cannot leave a stale figure in the
context an analyst or an assistant reads before proposing a change.

#### Scenario: The stated count matches the payload

- **WHEN** configuration states a record count
- **THEN** that count equals the records count in the emitted graph payload

#### Scenario: The payload moves and the stated count does not

- **WHEN** the emitted payload's record count changes
- **THEN** the disagreement is reported rather than left to be discovered by a reader