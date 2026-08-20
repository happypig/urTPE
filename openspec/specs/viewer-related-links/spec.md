# viewer-related-links Specification

## Purpose

Shows the discovered official links in the browser viewer's detail pane so an
analyst can jump from a project's history graph to the authoritative case
record on the national portal and the Taipei City platform.

## Requirements

### Requirement: Render a 相關連結 section in the detail pane

The system SHALL render a 相關連結 section in the detail pane, below the record
table, listing the project's national-portal link and each city-platform case
link as clickable outbound anchors with a stable label (e.g. 都市更新入口網,
臺北市都市更新處審議平台).

#### Scenario: Project with both link types
- **WHEN** the selected project has both a national-portal URL and one or more city case URLs
- **THEN** the detail pane shows a 相關連結 section with all links, each opening in a new tab

#### Scenario: Project with no resolved links
- **WHEN** the selected project has an empty `links` object
- **THEN** the detail pane renders no 相關連結 section at all

#### Scenario: Multi-case projects list every case
- **WHEN** a project has two city case_ids (事業計畫 and 權利變換)
- **THEN** both city links are listed, not just the first