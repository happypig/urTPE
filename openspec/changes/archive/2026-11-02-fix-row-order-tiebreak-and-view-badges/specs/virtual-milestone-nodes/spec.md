# virtual-milestone-nodes Delta

## MODIFIED Requirements

### Requirement: Stage-key clusters group base/split case files

Nodes SHALL cluster by 第N次 (stage) within the family — not by date. Undated members SHALL join their stage's dated cluster, rendered after the dated members and tagged (未核定). The cluster date SHALL be the real member's date, else the minimum dated member's date (±1-day splits span the band). Clusters with ≥2 members SHALL render a soft band spanning their rows plus a count chip (e.g., 變更(第四次) · 4 案 · 1 未核定); single-member groups render bare. Members SHALL order base(real) first, then splits by 區段， then undated. **Tie-break (2026-08-31 decision, viewer change design.md D12)**: dated members SHALL order row-by-row by **effective case_id ascending** — a real node's key is its anchored case_id (`links.taipei[0]`), a virtual node's key is its own `case_id`; real nodes without an anchored case carry an empty key and sort first (`""` < any case_id, keeping the order strictly ascending). The 區段 ordering applies only between members whose case keys are equal or both empty. **Family-wide interleave (Amendment 3, 603 exploration)**: the case_id ordering extends across the family — undated virtual attempts interleave between their case_id neighbors instead of being pushed to the tail, reproducing the 相關連結 case_id order in the graph. **Same-key date tie-break (2026-11-02, row-order fix)**: when two or more real nodes share one effective case_id, they SHALL order by **node date ascending** within that key — the recno-string comparison decides only between members whose dates are equal or absent — because 編號 is a newest-first coordinate and a recno tie-break alone renders a newer approval above an older one sharing its case.

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

#### Scenario: Two real nodes sharing one case render chronologically (254 shape)
- **WHEN** real nodes 1232 (2012-08-27) and 1039 (2016-08-23) both anchor case 09811141 (中山區-中山段一小段-254地號等13筆)
- **THEN** node 1232 renders above node 1039 — same-key members order by node date ascending, and the recno tie-break does not invert them

#### Scenario: Three real nodes sharing one case render chronologically (614 shape)
- **WHEN** real nodes 1216 (2013-01-02), 1098 (2015-06-16) and 906 (2018-04-17) all anchor case 09812231
- **THEN** the row order is 1216 → 1098 → 906, ascending by date

#### Scenario: Distinct-case rows keep the case_id interleave
- **WHEN** a family's rows carry distinct case_ids (the 603 shape, or 336's 10011271 → 10011273 → 11501034)
- **THEN** the same-key date tie-break never fires and the order is unchanged from the D12 interleave
