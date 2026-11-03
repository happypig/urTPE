## MODIFIED Requirements

### Requirement: Ghost landcore extraction handles single-段 sections and 概要-track dates

The orphan landcore extraction SHALL accept single-段 sections (`民生段140-9地號等3筆`) as well as 段小段 sections — village-renewal and older units use single-段 names, and rejecting them silently drops every orphan of the family (民生段140-9 shape: two 概要 orphans, one 已駁回 one 自行撤回). The extraction SHALL also accept, measured city shapes the single regex missed: a 、-list before 地號 (`長安段三小段709、711地號等2筆` — the land core keys on the first parcel), an `(原NNN)` suffix inside the parcel or the count (`105(原90)地號等13筆(原24筆)`), and spaces before 地號 or 筆 (`1-1 地號等11 筆`). The extraction SHALL NFKC-normalise the name before matching (the 擬訂臺北市 prefix with the compatibility form U+F963 of 北 breaks the 臺北市 split — Appendix A). An orphan case_name that still yields no land core SHALL be named in the run report, not dropped silently; a parcel-less name (崇仁新村) stays excluded from the similarity gate by design and is not reported as unparseable. The ghost's `node_date` SHALL fall back through the approval-date labels in track order: `核定日期` → `權變核定日期` → `概要核准日期`.

#### Scenario: Single-段 orphan cases become ghosts
- **WHEN** a project's 案名 land core is `松山區民生段140-9地號等3筆` (single-段) and two orphan 概要 cases carry candidate_names with the same land fragment
- **THEN** both orphans pass the similarity gate and render as virtual nodes with their harvested names

#### Scenario: 概要 ghost carries its approval date
- **WHEN** an orphan 概要 case has `概要核准日期 = 2026/03/31` and no 核定日期
- **THEN** the ghost's `node_date` is `2026-03-31` (previously empty, leaving the virtual node undated and mispositioned — 延吉段三小段727 shape)

#### Scenario: A 、-list orphan name extracts its first parcel
- **WHEN** an orphan case_name reads `變更臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫案-A區`
- **THEN** the extraction yields a land core with first parcel 201-2, and the case passes the similarity gate against the 華中段一小段 anchor (09305081 shape)

#### Scenario: An (原NNN) orphan name extracts without the suffix
- **WHEN** an orphan case_name reads `擬訂臺北市南港區中南段105(原90)地號等13筆(原24筆)土地都市更新事業計畫案`
- **THEN** the extraction yields the land core without the `(原…)` parts (105地號等13筆)

#### Scenario: Spaced 地號/筆 extract
- **WHEN** an orphan case_name reads `擬訂臺北市北投區奇岩段四小段1-1 地號等11 筆土地都市更新事業計畫案`
- **THEN** the extraction yields the land core `奇岩段四小段1-1地號等11筆`

#### Scenario: A compatibility 北 still extracts
- **WHEN** an anchor name carries the compatibility form of 北 (U+F963) after 臺 (三興972 shape)
- **THEN** the extraction recovers the land core (NFKC before matching)

#### Scenario: An unparseable orphan name is named, not dropped silently
- **WHEN** an orphan case_name still yields no land core after NFKC and the learned shapes (e.g. a 號-without-地號 name)
- **THEN** the run report names the project and the case_id with its name
