## MODIFIED Requirements

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

The page SHALL state the corpus's scope in the same breath as its size: the
graph holds **approved** cases only (680 projects / 1,444 records at the
2026-10-28 gazette), and the applications still under review are by design
absent from it — 臺北市報核 1,480 事業計畫 of which 630 were approved, and the
national portal's statistics table names 433 報核中 for 臺北市 (統計至
2026/09/30). The page SHALL link the two official statistics pages the scope
statement is read from, so a reader comparing the site's 680 against an
official total can see which population each number names. A scope statement
without its sources would read as an excuse rather than a measurement.

The page SHALL link the release-diff report (歷次公報差異) and the coverage
report (資料覆蓋度報告) by their published relative paths, with one abstract
sentence each on what the report establishes, and SHALL carry the maintainer's
contact address.

The viewer's header and the dashboard's header SHALL each carry a link to the
about page, in the page's markup rather than added by script, so the link is
reachable even when the page's data fails to load.

Every published page that carries site links in its header SHALL carry the
same 關於 control: the navlink chip the viewer and the dashboard wear
(terracotta text, hairline border, 8px radius), as the header's last element,
so the header closes at the right edge on every page. The rule covers the
domain-model page (`docs/domain-model.html`) too: its header SHALL carry the
chip, so a reader who lands on it from a search result can still reach the
license, the data sources and the contact.

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

#### Scenario: The scope statement names its official sources

- **WHEN** the about page states that the graph holds approved cases only
- **THEN** the statement carries the site's own count (projects and records) and the gazette date it names
- **AND** the city's 報核 figure (1,480 事業計畫, 630 核定實施) and the national portal's 報核中 figure (433, 統計至 2026/09/30) are each linked to the official page they come from
- **AND** the in-review pool is stated as absent by design, not as a gap

#### Scenario: The page works from a local file

- **WHEN** the about page is opened from `file://` with no server running
- **THEN** every link on the page resolves to its target
- **AND** the page makes no external request to render

#### Scenario: Both headers carry the link

- **WHEN** the viewer page or the dashboard page is loaded
- **THEN** its header carries a link labelled 關於 whose target is a relative path to the about page
- **AND** the link is present in the page's markup, not added by script

#### Scenario: The domain-model header carries the chip

- **WHEN** the domain-model page is opened
- **THEN** its header carries the navlink chip labelled 關於 whose target is a relative path to the about page
- **AND** the chip is the header's last element

#### Scenario: The link survives a data load failure

- **WHEN** the viewer's or the dashboard's payload fails to load
- **THEN** the 關於 link is still present in the page's header
