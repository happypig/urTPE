## MODIFIED Requirements

### Requirement: Ghost node carries orphan's milestone dates

When a ghost node is created, its `milestones_taipei` and
`milestones_taipei_case` SHALL be populated from the corresponding entries in
`links.milestones_source` that map to the orphan's case_id, and its `case_id`
field SHALL be set for portal linking. The per-case dict is named
`milestones_taipei_case` because it holds the Taipei platform's
per-case milestones (the `Get_project168_second.ashx` data) — the name
`milestones_national` falsely claimed the national portal's data space
(board D1: name wrong, data right). A rebuild from an already-emitted payload
SHALL read an old orphan's `milestones_national` as `milestones_taipei_case`
(load alias), so previously emitted files keep rendering.

#### Scenario: Ghost node shows correct milestones
- **WHEN** `links.milestones_source` maps 14 dates to case_id 09907221
- **THEN** the ghost node's `milestones_taipei` contains those 14 dates with their labels

#### Scenario: The per-case dict is named for its source
- **WHEN** an orphan node is emitted
- **THEN** its per-case milestone dict is `milestones_taipei_case` (Taipei ashx
  data; slash-Gregorian dates), distinct from the project-level
  `milestones_national` (twur 推動歷程, ROC-dot dates)

#### Scenario: An old payload loads under the new key
- **WHEN** `--from-js` loads an emitted payload whose orphan nodes carry
  `milestones_national`
- **THEN** the value loads as `milestones_taipei_case` and the viewer renders
  the node unchanged
