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

The page SHALL wear the site's one design system: the cream palette the
dashboard and the viewer share (`#fff8f4` ground, `#211d1d` charcoal,
`#f3d9bf` hairlines, `#ad4d2a` terracotta links, the sun-highlighter under
headings), inline, with no dark-mode block — the system is light-only by
construction, the same on every published page.

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

#### Scenario: The page wears the site's one design system

- **WHEN** the about page's inline styles are read
- **THEN** they declare the cream palette's tokens (`#fff8f4`, `#211d1d`, `#f3d9bf`, `#ad4d2a`)
- **AND** the page carries no dark-mode block and no slate tokens (`#0f172a`, `#cbd5e1`)

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
