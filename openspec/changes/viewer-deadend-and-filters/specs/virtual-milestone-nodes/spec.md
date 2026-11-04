## MODIFIED Requirements

### Requirement: Virtual nodes chain row-by-row within a cluster

Consecutive virtual nodes within a stage cluster (the case_id-ascending row order above) SHALL be connected by a **dashed virtual revision edge** directed along the row (earlier attempt → later attempt), rendering the platform's application-succession sequence. Same-date pairs in *different* stage clusters SHALL NOT be chained (parallel tracks — e.g., a 擬訂 概要案 cluster and a 擬訂 事業計畫案 cluster on one date are not revisions of each other). Only pairs where BOTH members are virtual SHALL gain an edge from this rule; real↔real pairs remain covered by the existing revision edges, and real↔virtual pairs gain no chain edge — a virtual orphan's only recno connector is its dotted orphan edge to the branch-off node (§4, orphan-case-anchoring). A chain edge SHALL NOT start at a virtual node whose schedule is a dead end (已失效 / 自行撤回 / 已駁回, from `links.case_schedules` or the orphan's own schedule): nothing follows a closed case (user decision 2026-11-05, board D4b — measured 36 of 48 chain edges start at a dead end). Chain edges SHALL use a dashed line style consistent with the virtual nodes' dashed circles.

#### Scenario: Attempt pair is chained
- **WHEN** a cluster holds two live virtual nodes in row order (neither schedule is 已失效 / 自行撤回 / 已駁回), e.g. a withdrawn 概要 followed by a 施工中 計畫 re-application (吉林段四小段676: 09601262 自行撤回 → 09703182 施工中)
- **THEN** a dashed edge connects them in row order

#### Scenario: A chain edge does not start at a dead end
- **WHEN** a cluster holds virtual nodes 09902261 (已失效) and 10201171 (已駁回) in row order (吉林段三小段1021)
- **THEN** no dashed edge connects them, although both are virtual and consecutive
- **AND** each node still renders its own schedule badge

#### Scenario: Cross-stage same-day pairs are not chained
- **WHEN** a family has a 擬訂 事業概要案 virtual cluster and a 擬訂 事業計畫案 virtual cluster on the same date (吉林段四小段676: 09601260 / 09601262)
- **THEN** no edge connects the two clusters' virtual nodes

#### Scenario: Real↔real pairs are not duplicated
- **WHEN** a cluster's row order places two real members consecutively
- **THEN** no chain edge is added between them (their revision edge from graph.py remains the single connector)

#### Scenario: Real↔virtual pairs are not chained
- **WHEN** a cluster's row order places a real member next to a withdrawn-orphan virtual member (南海段一小段-687: cluster [變更] holds 393 real and 11012301 virtual)
- **THEN** no chain edge is added between them — the orphan's dotted edge runs to its branch-off node 734, and the live path keeps its solid revision edge 734 → 393
