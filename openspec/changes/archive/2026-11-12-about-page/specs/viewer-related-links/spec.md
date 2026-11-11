## ADDED Requirements

### Requirement: The site carries an about page

The site SHALL carry an 關於 page (`viewer/about.html`) in zh_TW that answers,
in one place: under what license the site's own content may be reused, where
the data comes from and how it was processed, how far the published figures
can be trusted, and how to reach the maintainer.

The page SHALL be static and self-contained: no script, no stylesheet fetched
from the site's directory or elsewhere, and every link relative, so the page
works from the published site, from a `file://` page, and from a clone — the
same constraint the viewer's other pages work under.

The page SHALL state the license of the site's own content (the pages and the
emitted dataset) as CC BY 4.0, and SHALL state in a separate line that the
upstream government data — the gazette PDF and both portals — follows its own
terms.

The page SHALL name the three data sources: the gazette PDF
(臺北市都市更新核定案件一覽表), the Taipei platform (`gis.uro.taipei`), and
the national portal (`twur.nlma.gov.tw`), and SHALL give a concise abstract of
the processing flow from PDF to the per-project history graph the pages
render, including that records the publisher truncated are excluded and named
rather than repaired.

The page SHALL link the release-diff report (歷次公報差異) and the coverage
report (資料覆蓋度報告) by their published relative paths, with one abstract
sentence each on what the report establishes, and SHALL carry the maintainer's
contact address.

The viewer's header and the dashboard's header SHALL each carry a link to the
about page, in the page's markup rather than added by script, so the link is
reachable even when the page's data fails to load.

#### Scenario: The about page answers the four questions

- **WHEN** the about page is opened
- **THEN** it states the CC BY 4.0 license of the site's own content
- **AND** it names the gazette PDF, the Taipei platform and the national portal as the data sources
- **AND** it links the release-diff report and the coverage report
- **AND** it carries the maintainer's contact address

#### Scenario: The license line does not overreach

- **WHEN** the about page states the license
- **AND** it mentions the upstream government data
- **THEN** the CC BY 4.0 statement is scoped to the site's own content
- **AND** the upstream data is covered by a separate line deferring to its own terms

#### Scenario: The page works from a local file

- **WHEN** the about page is opened from `file://` with no server running
- **THEN** every link on the page resolves to its target
- **AND** the page makes no external request to render

#### Scenario: Both headers carry the link

- **WHEN** the viewer page or the dashboard page is loaded
- **THEN** its header carries a link labelled 關於 whose target is a relative path to the about page
- **AND** the link is present in the page's markup, not added by script

#### Scenario: The link survives a data load failure

- **WHEN** the viewer's or the dashboard's payload fails to load
- **THEN** the 關於 link is still present in the page's header

## MODIFIED Requirements

### Requirement: The viewer links to the release-diff report, and the report links back

The release-diff report SHALL be reachable from the site's pages, and the
report SHALL carry a link back to the viewer. The reachability now runs
through the about page: the viewer's header SHALL carry a link to the about
page (the 關於 requirement above), and the about page SHALL link the report;
the report's own back link to the viewer is unchanged.

All links SHALL be relative, so the chain works from the published site, from
a `file://` page, and from a clone — the viewer's normal way of being opened
is `file://`, and an absolute URL would break it there.

The about page's link SHALL be present in the page's markup rather than added
by script, so a reader who lands on a payload that fails to load can still
reach the report.

#### Scenario: The viewer header carries the link

- **WHEN** the viewer page is loaded
- **THEN** its header carries a link labelled 關於
- **AND** the link's target is a relative path to the about page

#### Scenario: The about page links the report

- **WHEN** the about page is opened
- **THEN** it carries a link labelled 歷次公報差異 to the release-diff report
- **AND** the link's target is a relative path to the report

#### Scenario: The report links back to the viewer

- **WHEN** the release-diff report is opened
- **THEN** it carries a link back to the viewer
- **AND** the link's target is a relative path to the viewer's index

#### Scenario: The links work from a local file

- **WHEN** the viewer is opened from `file://` with no server running
- **THEN** the 關於 link reaches the about page
- **AND** the about page's report link reaches the report
- **AND** the report's back link reaches the viewer

#### Scenario: The link survives a data load failure

- **WHEN** the payload fails to load
- **THEN** the 關於 link is still present in the page's header
- **AND** the about page, needing no data, still renders its report link
