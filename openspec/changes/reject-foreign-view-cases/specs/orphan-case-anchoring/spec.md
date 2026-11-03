# orphan-case-anchoring spec delta — reject-foreign-view-cases (§8 viewer-UX wave 3b)

## MODIFIED Requirements

### Requirement: Portal-verified orphans bypass the landcore gate

Case_ids listed in `DiscoveryResult.view_verified_case_ids` — extracted from the project's own national view page 相關連結 — SHALL become ghost nodes regardless of landcore similarity **only when the city's own case name for the id confirms the unit**: the land core of the platform's `CASE_NAME` (get_project168_top) SHALL match the project's land core at `LINK_THRESHOLD = 0.7`, or the name SHALL be parcel-less (a settlement-named unit like 崇仁新村 carries no 地號 and is not decidable by land core — it does not reject). A view-verified id whose city name names another project SHALL NOT become a ghost node: it SHALL move to the project's `view_rejected` record with its reason — shape A (the 相關連結 label and the city name both name another project) or shape B (the label is right, the id is wrong — only the city's own case name shows this). A 相關連結 label that names another project while the city name matches SHALL NOT reject the id: the portal's label error is logged in the run report instead. A city name the refresh could not read SHALL NOT reject the id (a missing header is no evidence); the id stays view-verified and, when its label also mismatches, is reported as "label not confirmed".

#### Scenario: Parcel-less portal-verified orphan becomes ghost

- **WHEN** an orphan case_id 09112120 has case_name "擬訂臺北市萬華區崇仁新村土地都市更新事業計畫及權利變換計畫案" (no 地號 → similarity 0.0), no node anchors it, and it is listed in `view_verified_case_ids` (it appears in the project's own view page 相關連結)
- **THEN** a ghost/virtual node is created for it with its harvested case_name, stage/track derived from the name, and `node_date` from its 核定日期 milestone

#### Scenario: Unverified low-similarity orphans remain excluded

- **WHEN** an orphan case_id has a parcel-less case_name, similarity 0.0, and is NOT in `view_verified_case_ids`
- **THEN** no ghost node is created

#### Scenario: A view-verified id whose city name names another project does not become a ghost

- **WHEN** a project's view page lists case_id 09511211 with the label "擬訂臺北市大安區大安段一小段557…" (matching the project's own land core) but the city's own case name for 09511211 is "擬訂臺北市中山區吉林段四小段603…" (similarity 0.0 — shape B)
- **THEN** no ghost node is created for 09511211 on this project
- **AND** the id moves to the project's `view_rejected` with reason "label is right, id is wrong (shape B)"

#### Scenario: A wrong label alone does not reject

- **WHEN** a project's view page labels case_id 10906092 with another project's name (萬華區莒光段三小段519-3) but the city's own case name for it is the project's own unit (中山區吉林段二小段898 — similarity ≥ 0.7)
- **THEN** the id stays view-verified and anchors normally
- **AND** the run report logs the label error for the id

#### Scenario: A missing city name never rejects

- **WHEN** the header fetch returned no row (or the cache holds no CASE_NAME) for a view-verified id whose label names another project
- **THEN** the id stays view-verified
- **AND** the run report marks it "label not confirmed" instead of rejecting it
