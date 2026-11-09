## ADDED Requirements

### Requirement: The viewer links to the release-diff report, and the report links back

The viewer's header SHALL carry a link to the release-diff report, and the
report SHALL carry a link back to the viewer. The two links SHALL be relative,
so the pair works from the published site, from a `file://` page, and from a
clone — the viewer's normal way of being opened is `file://`, and an absolute
URL would break it there.

The viewer's link SHALL be present in the page's markup rather than added by
script, so a reader who lands on a payload that fails to load can still reach
the report.

#### Scenario: The viewer header carries the link

- **WHEN** the viewer page is loaded
- **THEN** its header carries a link labelled 歷次公報差異
- **AND** the link's target is a relative path to the release-diff report

#### Scenario: The report links back to the viewer

- **WHEN** the release-diff report is opened
- **THEN** it carries a link back to the viewer
- **AND** the link's target is a relative path to the viewer's index

#### Scenario: The links work from a local file

- **WHEN** the viewer is opened from `file://` with no server running
- **THEN** the link to the report reaches the report
- **AND** the report's back link reaches the viewer

#### Scenario: The link survives a data load failure

- **WHEN** the payload fails to load
- **THEN** the link to the release-diff report is still present in the page

### Requirement: Each release links to the document the city published for it

The release-diff report's per-release table SHALL link a release to the
document the city published for that release, and SHALL say in words when no
such link is known.

A release SHALL link to its own version-specific publisher URL when the
archive index records one. The publisher serves one PDF link at a time and
repoints it on every publication, so the live link names the newest document
rather than any particular one; a release with no recorded URL SHALL NOT be
given the live link, because that would send a reader to a different gazette
while appearing correct.

The newest release SHALL link to the live publisher PDF and SHALL carry the
publisher's 資料更新 stamp beside the link, so the address is dated.

#### Scenario: The newest release links to the live PDF

- **WHEN** the report lists the release the publisher currently serves
- **THEN** that release's row links to the publisher's PDF
- **AND** the publisher's 資料更新 stamp appears beside the link

#### Scenario: An older release links to its own URL

- **WHEN** the archive index records a version-specific publisher URL for a release that is not the newest
- **THEN** that release's row links to that URL
- **AND** it does not link to the live URL

#### Scenario: A release with no recorded URL says so

- **WHEN** no publisher URL is recorded for a release
- **THEN** that release's row carries no publisher link
- **AND** the report states that the URL for that release is unknown
- **AND** the row does not link to the live PDF, which serves a different document

#### Scenario: The link column distinguishes the two kinds of URL

- **WHEN** a report carries both a live-publisher link and a version-specific link
- **THEN** a reader can tell which is which from the link's label
