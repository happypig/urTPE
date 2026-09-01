## MODIFIED Requirements

### Requirement: Stage-key clusters group base/split case files

Nodes SHALL cluster by 第N次 (stage) within the family — not by date. Undated members SHALL join their stage's dated cluster, rendered after the dated members and tagged (未核定). The cluster date SHALL be the real member's date, else the minimum dated member's date (±1-day splits span the band). Clusters with ≥2 members SHALL render a soft band spanning their rows plus a count chip (e.g., 變更(第四次) · 4 案 · 1 未核定); single-member groups render bare. Members SHALL order base(real) first, then splits by 區段, then undated. **Tie-break (2026-08-31 decision, viewer change design.md D12)**: dated members SHALL order row-by-row by **effective case_id ascending** — a real node's key is its anchored case_id (`links.taipei[0]`), a virtual node's key is its own `case_id`; real nodes without an anchored case carry an empty key and sort first (`""` < any case_id, keeping the order strictly ascending). The 區段 ordering applies only between members whose case keys are equal or both empty.

#### Scenario: Attempt twins order by case_id, not platform search order
- **WHEN** a cluster holds two same-stage, same-date virtual nodes (吉林段三小段1021: 09902261 and 10201171, resubmitted 擬訂 概要 pairs)
- **THEN** they render in case_id ascending order (09902261 above 10201171) — application-attempt order, stable across portal loads
- **AND** the order does not depend on the platform search-response order

#### Scenario: Real node outranks a later virtual, is outranked by an earlier one
- **WHEN** a cluster's real node anchors case 09811141 and a virtual orphan is case 09506200 (an earlier withdrawn attempt of the same stage)
- **THEN** the virtual renders above the real node (09506200 < 09811141 — the earlier attempt precedes the gazette approval)

#### Scenario: Case-less real node sorts first
- **WHEN** a cluster's real node has an empty `links.taipei` (no platform linkage, e.g. 民生段140-9 node 65) alongside case-keyed members
- **THEN** the case-less real node renders first in the cluster (empty key = ascending order)

## ADDED Requirements

### Requirement: Virtual nodes chain row-by-row within a cluster

Consecutive virtual nodes within a stage cluster (the case_id-ascending row order above) SHALL be connected by a **dashed virtual revision edge** directed along the row (earlier attempt → later attempt), rendering the platform's application-succession sequence. Same-date pairs in *different* stage clusters SHALL NOT be chained (parallel tracks — e.g., a 擬訂 概要案 cluster and a 擬訂 事業計畫案 cluster on one date are not revisions of each other). Only pairs involving at least one virtual node SHALL gain an edge from this rule; real↔real pairs remain covered by the existing revision edges without duplication. Chain edges SHALL use a dashed line style consistent with the virtual nodes' dashed circles.

#### Scenario: Attempt pair is chained
- **WHEN** a cluster holds virtual nodes 09902261 and 10201171 (withdrawn 概要 → resubmitted 概要, 吉林段三小段1021)
- **THEN** a dashed edge connects them in row order (09902261 → 10201171)

#### Scenario: Cross-stage same-day pairs are not chained
- **WHEN** a family has a 擬訂 事業概要案 virtual cluster and a 擬訂 事業計畫案 virtual cluster on the same date (吉林段四小段676: 09601260 / 09601262)
- **THEN** no edge connects the two clusters' virtual nodes

#### Scenario: Real↔real pairs are not duplicated
- **WHEN** a cluster's row order places two real members consecutively
- **THEN** no chain edge is added between them (their revision edge from graph.py remains the single connector)
