## MODIFIED Requirements

### Requirement: The viewer links to the release-diff report, and the report links back

The release-diff report SHALL be reachable from the site's pages, and the
report SHALL carry a link back into the viewer's pages. The reachability runs
through the about page: the viewer's header SHALL carry a link to the about
page (the 關於 requirement above), and the about page SHALL link the report;
the report's back link SHALL point at the about page (`../viewer/about.html`),
which links the viewer in turn. The chain is therefore:
report → 關於 → viewer and viewer → 關於 → report, every hop a relative path,
so the chain works from the published site, from a `file://` page, and from a
clone — the viewer's normal way of being opened is `file://`, and an absolute
URL would break it there.

The three documentation pages — the release-diff report, the coverage report
and the ETL write-up — SHALL each carry a 關於 link at their header's right
edge, present in the page's markup rather than added by script, so a reader
who lands on a report directly (from a search result or a shared link) can
still reach the license, the data sources and the contact.

In every header that carries site links — the viewer's, the dashboard's and
the three documentation pages' — the 關於 link SHALL be the last (rightmost)
link, with the page's other site links to its left.

#### Scenario: The viewer header carries the link

- **WHEN** the viewer page is loaded
- **THEN** its header carries a link labelled 關於
- **AND** the link's target is a relative path to the about page

#### Scenario: The 關於 link is the rightmost site link

- **WHEN** the viewer's, the dashboard's or a documentation page's header is read
- **THEN** the 關於 link is the last site link in the header
- **AND** the viewer's 政策儀表板 and the dashboard's 專案歷史圖 links sit to its left, unchanged

#### Scenario: The about page links the report

- **WHEN** the about page is opened
- **THEN** it carries a link labelled 歷次公報差異 to the release-diff report
- **AND** the link's target is a relative path to the report

#### Scenario: The report links back to the viewer

- **WHEN** the release-diff report is opened
- **THEN** it carries a 關於 link at its header's right edge
- **AND** the link's target is a relative path to the about page
- **AND** the about page links the viewer's index, so the viewer stays one hop away
- **AND** the report carries no direct 回專案歷史圖 link

#### Scenario: The documentation pages carry the link

- **WHEN** the coverage report or the ETL write-up is opened
- **THEN** its header carries a 關於 link at the right edge
- **AND** the link's target is a relative path to the about page

#### Scenario: The links work from a local file

- **WHEN** the viewer is opened from `file://` with no server running
- **THEN** the 關於 link reaches the about page
- **AND** the about page's report link reaches the report
- **AND** the report's 關於 link reaches the about page

#### Scenario: The link survives a data load failure

- **WHEN** the payload fails to load
- **THEN** the 關於 link is still present in the page's header
- **AND** the about page, needing no data, still renders its report link
