## MODIFIED Requirements

### Requirement: Ghost node for landcore-similar orphan case_ids

The pipeline SHALL examine each case_id in `links.taipei` that has no corresponding anchor record in the project's nodes. For each such orphan, it SHALL compute the landcore similarity between the orphan's case_name and the project's anchor record. If similarity ≥ 0.7, the pipeline SHALL create a ghost node in the project's graph with `orphan: true`, the orphan's case_id, its milestones, and provenance from `links.milestones_source` or `links.search_rejected`.

A case recorded in `superseded_by` — the city re-filed it under a new id — SHALL NOT become a ghost node: its undated node showed a process the city has replaced (measured: 10410012, 10806141, 11009142, 11211211 carried an empty-`node_date` node each). The case stays in `links.taipei` (the list is append-only and other readers key on it); only the node is withheld. The successor case carries the live history.

#### Scenario: Orphan with matching landcore becomes ghost node
- **WHEN** a project has `links.taipei` containing case_id 09907221, no node anchors 09907221, and the case_name "擬訂臺北市文山區木柵段三小段623地號等39筆土地都市更新事業計畫案" has landcore similarity ≥ 0.7 to the project anchor "文山區木柵段三小段623地號等39筆"
- **THEN** the emitted `projects.json` includes a ghost node with `orphan: true`, `case_id: "09907221"`, and its milestone dates (計畫公聽會日期 through 核定日期, 建照核發日期)

#### Scenario: Orphan with low landcore similarity is excluded
- **WHEN** a project has an orphan case_id whose case_name landcore similarity < 0.7 to the project anchor, and the case_id is NOT portal-verified (absent from `view_verified_case_ids`)
- **THEN** no ghost node is created, and the case_id remains only in `links.taipei` (current behavior)

#### Scenario: A superseded case's undated orphan is withheld
- **WHEN** a project's cache records 10806141 as superseded by 11510017, and 10806141 anchors no node (its undated orphan node carried no date — 虎林38)
- **THEN** no ghost node is created for 10806141
- **AND** 10806141 stays in `links.taipei`
- **AND** the successor 11510017 carries the live history
