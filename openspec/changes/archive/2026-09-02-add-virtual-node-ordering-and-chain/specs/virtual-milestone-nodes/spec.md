## MODIFIED Requirements

### Requirement: Stage-key clusters group base/split case files

Nodes SHALL cluster by 第N次 (stage) within the family — not by date. Undated members SHALL join their stage's dated cluster, rendered after the dated members and tagged (未核定). The cluster date SHALL be the real member's date, else the minimum dated member's date (±1-day splits span the band). Clusters with ≥2 members SHALL render a soft band spanning their rows plus a count chip (e.g., 變更(第四次) · 4 案 · 1 未核定); single-member groups render bare. Members SHALL order base(real) first, then splits by 區段, then undated. **Tie-break (2026-08-31 decision, viewer change design.md D12)**: dated members SHALL order row-by-row by **effective case_id ascending** — a real node's key is its anchored case_id (`links.taipei[0]`), a virtual node's key is its own `case_id`; real nodes without an anchored case carry an empty key and sort first (`""` < any case_id, keeping the order strictly ascending). The 區段 ordering applies only between members whose case keys are equal or both empty. **Family-wide interleave (Amendment 3, 603 exploration)**: the case_id ordering extends across the family — undated virtual attempts interleave between their case_id neighbors instead of being pushed to the tail, reproducing the 相關連結 case_id order in the graph.

#### Scenario: Undated 權變 sibling joins its stage cluster
- **WHEN** 變更(第四次) has dated base + 西區 + 東區 nodes and an undated 權利變換 sibling (09403244)
- **THEN** the sibling joins the 變更(第四次) band tagged (未核定) and the chip reads 變更(第四次) · 4 案 · 1 未核定

#### Scenario: Undated stage with no dated mate stays its own group
- **WHEN** an undated stage has no dated cluster of the same 第N次 (e.g., 變更(第三次) 權變)
- **THEN** it renders as its own bare (未核定) group at the timeline end

#### Scenario: ±1-day splits span one band
- **WHEN** a stage's split cases were approved a day apart (擬訂-北區 11-04 / 擬訂-南區 11-03) with no real member
- **THEN** both render inside one band whose date label is the minimum dated member's date

#### Scenario: Undated virtual attempts interleave by case_id (603 shape)
- **WHEN** the family 吉林段四小段603 holds real nodes anchored 09511211/09511214/11007261/11501016 and undated virtuals 09511212/09511213 (自行撤回) + 11007262 (已駁回)
- **THEN** the family-wide row order is 09511210 → 09511211 → 09511212 → 09511213 → 09511214 → 11007261 → 11007262 → 11501016 — matching the 相關連結 case_id order, with the withdrawn attempts between their dated neighbors and 已駁回 11007262 before 已核准 11501016

#### Scenario: Same-date virtuals attach after their anchored milestone (date-band adjacency)
- **WHEN** same-date virtual nodes exist (e.g. A區/B區 splits of one anchored milestone)
- **THEN** they attach immediately AFTER their same-day anchored milestone — date-band adjacency takes precedence over pure case_id order, with case_id ordering members within the date band

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
