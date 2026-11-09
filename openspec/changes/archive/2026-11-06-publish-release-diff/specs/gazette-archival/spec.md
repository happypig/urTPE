## ADDED Requirements

### Requirement: The index records the publisher URL a document was fetched from

An index entry for a document retrieved from the publisher SHALL record the
URL the document was served from. The publisher serves one PDF link at a time
and repoints it on every publication, so the live link names "whatever is
newest" rather than "this document"; the version-specific URL it serves from
names that document and remains a durable address for it afterwards.

The URL SHALL be recorded for every retrieval, including a retrieval that found
the content already held, because the city repointing its link without
changing the document is the event that would otherwise lose the association
between an address and a publication.

The field is additive. An index entry written before the field existed SHALL
remain readable, and a publication whose entries carry no URL SHALL be
reported as having no recorded URL rather than being treated as having one.

#### Scenario: A gazette is archived with its publisher URL

- **WHEN** a gazette is downloaded from `https://www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/<uuid>.pdf`
- **THEN** the appended index entry records that URL
- **AND** the entry's recorded digest still establishes what was retrieved

#### Scenario: An entry written before the field existed still parses

- **WHEN** an index entry carries no publisher URL
- **THEN** the entry is read without error
- **AND** the publication it names is reported as having no recorded URL

#### Scenario: The publisher repoints its link without changing the document

- **WHEN** a check retrieves content it already holds, from a URL it did not previously serve that content from
- **THEN** the recorded outcome and the archive entry name the URL the document was served from
- **AND** the content is still recognised as unchanged by digest

#### Scenario: A document supplied from a local path claims no URL

- **WHEN** a gazette is archived from a path on disk rather than fetched
- **THEN** its entry records no publisher URL
- **AND** it does not claim an address it never retrieved from
