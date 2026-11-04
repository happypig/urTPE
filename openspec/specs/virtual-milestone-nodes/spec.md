# virtual-milestone-nodes Specification

## Purpose
Orphan case_ids with harvested case_names and landcore similarity ≥ 0.7 stop being side-annotations and become **virtual milestone nodes**: first-class, dashed-styled members of the project timeline, placed chronologically in their 事業種類 column. This retires the ghost-anchor column for named orphans — "there's no orphan node anymore".
## Requirements
### Requirement: Candidate case_names persisted at discovery time

The discovery pipeline SHALL persist the `case_name` returned by the platform search API for every candidate case_id (kept or rejected) into the discovery result, instead of discarding kept-case names. Landcore similarity for orphan anchoring SHALL compute from these harvested names when available, taking precedence over the attribution and twin-bridge proxies.

#### Scenario: Kept orphan's name survives discovery
- **WHEN** the platform search returns case_name for a kept candidate case_id that no node anchors
- **THEN** the discovery result carries {case_id: case_name} and the emitted ghost payload includes that name

#### Scenario: Harvested name gates virtual anchoring
- **WHEN** an orphan's harvested case_name yields landcore similarity ≥ 0.7 to the project anchor
- **THEN** the orphan qualifies for virtual milestone rendering without relying on attribution or twin-bridge signals

### Requirement: Landcore-similar orphans render as virtual milestone nodes

A named, landcore-similar orphan SHALL render inside the project timeline as a virtual milestone node: dashed circle, dashed connecting edges, placed at its 核定日期 row within its 事業種類 column, labeled with its stage (擬訂 / 變更 / 變更(第N次)) and 事業種類 without a recno, and belonging to the project family identity. Its link badges SHALL use the same 北/國 badge anatomy as PDF milestone nodes (badge strip above the label); named virtual nodes SHALL NOT carry a 孤 badge — provenance SHALL live in the node tooltip only. The ghost's `node_date` SHALL read only the case's OWN track approval (board D2a, user decision 2026-11-05): a 概要-track case falls through 核定日期 → 權變核定日期 → 概要核准日期; a plan-track case (事業計畫 / 權利變換 / combined) falls through 核定日期 → 權變核定日期 and NEVER reads 概要核准日期, which the city echoes from the family's 概要 approval into every descendant case — a dead plan case dated with its sibling's approval is a fabricated event (measured: 18 of 25 same-date pairs were echoes; 吉林717's triple all carried the 概要's 2007/01/30). A plan-track case with no own approval renders undated, tagged (未核定).

#### Scenario: Virtual node placed chronologically in its track column
- **WHEN** orphan 09907221's harvested name gives stage 擬訂, track 事業計畫, and its milestones give 核定日期 2019/01/31
- **THEN** the graph renders it as a dashed node in the 事業計畫 column between its date neighbors, labeled 擬訂 + 事業計畫 without recno, with the standard 北 link badge above the label

#### Scenario: Named virtual nodes carry no visible orphan marker
- **WHEN** a virtual node renders from a harvested name
- **THEN** no 孤 badge appears on it — differentiation is the dashed circle/edges, and the tooltip carries the orphan provenance

#### Scenario: A dead plan case carries no approval date
- **WHEN** a plan-track orphan's milestones hold no 核定日期/權變核定日期 but carry 概要核准日期 2007/01/30 (the family echo, 吉林717 shape)
- **THEN** the ghost's `node_date` is empty — the node renders undated, tagged (未核定), and does not share the 概要's date row

#### Scenario: A 概要 case keeps its own approval date
- **WHEN** a 概要-track orphan's milestones hold 概要核准日期 2026/03/31 and no 核定日期
- **THEN** the ghost's `node_date` is `2026-03-31` (its own approval)

#### Scenario: Virtual node construction dates stay in the shared column
- **WHEN** a virtual node's case owns execution dates
- **THEN** those dates render once in the execution column, connected to the virtual node by slanted solid source edges per the edge-semantics rules

#### Scenario: Nameless orphans keep the interim anchor column
- **WHEN** an orphan qualifies only via attribution or twin-bridge (no harvested name yet)
- **THEN** it remains a dashed anchor (with 孤 badge) in the ghost column until its name is harvested

### Requirement: 區段 labels extracted from case_name tails

Real and virtual nodes SHALL extract the trailing 區段 token from their anchored case_name (`-東區/-西區/-北區/-南區`, bare `北/南` directionals, `甲/乙區段`) and render it in the track sub-line (e.g., 事業計畫（西區）, 權利變換（西區）). A base case whose name carries no token SHALL show no 區段 label, with base provenance in the tooltip.

#### Scenario: Split virtual node shows its 區段
- **WHEN** orphan 10211110's case_name ends with `-西區`
- **THEN** the virtual node's sub-line reads 事業計畫（西區）

#### Scenario: Real split node shows its 區段 too
- **WHEN** a real record's case_name ends with `-西區` (e.g., 變更(第五次)權利變換計畫案-西區) and the PDF provided no separate area
- **THEN** the real node's sub-line shows the 區段 token as well

### Requirement: Stage-key clusters group base/split case files

Nodes SHALL cluster by 第N次 (stage) within the family — not by date. Undated members SHALL join their stage's dated cluster, rendered after the dated members and tagged (未核定). Clusters SHALL render bare without a soft band or count chip (the viewer's callout gutter reserves that space; see viewer-graph-layout). The cluster date SHALL be the real member's date, else the minimum dated member's date (±1-day splits span the band). Clusters with ≥2 members SHALL render a soft band spanning their rows plus a count chip (e.g., 變更(第四次) · 4 案 · 1 未核定); single-member groups render bare. Members SHALL order base(real) first, then splits by 區段， then undated. **Date-first ordering (2026-11-05 decision, superseding the 2026-08-31 case_id-first rule — board D2b)**: dated members SHALL order row-by-row by their **own-event date** ascending — a 概要-track member reads 概要核准日期 → 申請概要日期 → 申請計畫日期; a plan-track member reads 核定日期 → 權變核定日期 → 申請計畫日期 → 申請權變日期 → 申請概要日期, never the echoed 概要核准日期. When two members share the same own-event date (or both have none), they SHALL order by **effective case_id ascending** (the D12 attempt order survives as the tie-break: a real node's key is its anchored case_id, a virtual node's its own). The 區段 ordering applies only between members whose case keys and dates are both equal. **Family-wide interleave**: all members flatten into one row sequence by the same own-event key — an undated virtual attempt whose application date is known orders at that date, not at the tail.

#### Scenario: Undated 權變 sibling joins its stage cluster
- **WHEN** 變更(第四次) has dated base + 西區 + 東區 nodes and an undated 權利變換 sibling (09403244)
- **THEN** the sibling joins the 變更(第四次) cluster tagged (未核定); no soft band and no count chip render (the callout gutter reserves that space)

#### Scenario: Undated stage with no dated mate stays its own group
- **WHEN** an undated stage has no dated cluster of the same 第N次 (e.g., 變更(第三次) 權變)
- **THEN** it renders as its own bare (未核定) group at the timeline end

#### Scenario: ±1-day splits span one band
- **WHEN** a stage's split cases were approved a day apart (擬訂-北區 11-04 / 擬訂-南區 11-03) with no real member
- **THEN** both render inside one band whose date label is the minimum dated member's date

#### Scenario: Rows read chronologically
- **WHEN** a family holds a 2016 approval and a 變更 dated 2019 whose case_id sorts lower
- **THEN** the 2016 row renders first (date order), not the lower case_id

#### Scenario: Same-day members keep attempt order
- **WHEN** two members share one own-event date (a genuine same-day serial, or an echo removed by D2a)
- **THEN** they order by case_id ascending within that date

#### Scenario: An application-dated dead attempt sits at its application date
- **WHEN** a withdrawn plan case applied 2013/11/18 and never won approval, and the family's later approval is dated 2019
- **THEN** the attempt renders at 2013/11/18 tagged (未核定), before the 2019 approval

#### Scenario: Undated virtual attempts interleave by case_id (603 shape)
- **WHEN** the family 吉林段四小段603 holds real nodes anchored 09511211/09511214/11007261/11501016 and undated virtuals 09511212/09511213 (自行撤回) + 11007262 (已駁回)
- **THEN** the family-wide row order reads chronologically by each member's own event date — the withdrawn attempts sit at their application dates between their neighbours, and 已駁回 11007262 before 已核准 11501016 (the echo removed by D2a gives the virtuals their own dates)

#### Scenario: Same-date virtuals attach after their anchored milestone (date-band adjacency)
- **WHEN** same-date virtual nodes exist (e.g. A區/B區 splits of one anchored milestone)
- **THEN** they attach immediately AFTER their same-day anchored milestone — date-band adjacency takes precedence, with case_id ordering members within the date band

#### Scenario: Attempt twins order by case_id, not platform search order
- **WHEN** a cluster holds two same-stage, same-date virtual nodes (吉林段三小段1021: 09902261 and 10201171, resubmitted 擬訂 概要 pairs)
- **THEN** they render in case_id ascending order (09902261 above 10201171) — the case_id tie-break, stable across portal loads
- **AND** the order does not depend on the platform search-response order

#### Scenario: Real node outranks a later virtual, is outranked by an earlier one
- **WHEN** a cluster's real node anchors case 09811141 (approval 2016) and a virtual orphan is case 09506200 (an earlier withdrawn attempt whose own event predates the approval)
- **THEN** the virtual renders above the real node — the earlier attempt precedes the gazette approval, now by its own event date

#### Scenario: Case-less real node sorts first
- **WHEN** a cluster's real node has an empty `links.taipei` (no platform linkage, e.g. 民生段140-9 node 65) alongside case-keyed members
- **THEN** the case-less real node renders first in the cluster (empty key = ascending order)

#### Scenario: Two real nodes sharing one case render chronologically (254 shape)
- **WHEN** real nodes 1232 (2012-08-27) and 1039 (2016-08-23) both anchor case 09811141 (中山區-中山段一小段-254地號等13筆)
- **THEN** node 1232 renders above node 1039 — date order; the case_id tie-break does not invert them

#### Scenario: Three real nodes sharing one case render chronologically (614 shape)
- **WHEN** real nodes 1216 (2013-01-02), 1098 (2015-06-16) and 906 (2018-04-17) all anchor case 09812231
- **THEN** the row order is 1216 → 1098 → 906, ascending by date

#### Scenario: Distinct-case rows keep the case_id interleave
- **WHEN** a family's rows carry distinct case_ids and distinct own-event dates (the 603 shape, or 336's 10011271 → 10011273 → 11501034)
- **THEN** the row order follows the dates (2022 → 2023 → 2026 for 336), with case_id only breaking equal dates

### Requirement: Same-date virtual badges append to the anchored milestone strip

For virtual nodes sharing a real node's date, the virtual's 北 link badge SHALL be kept only when it carries a 區段標籤 **and** a schedule (from `links.case_schedules`) — such badges append **next to the anchored milestone's 北 badge** on the real node's strip (each distinguished by its 區段 label and exceptional schedule). Virtual nodes lacking a 區段 token or schedule keep their badge on their own dashed row. The virtual circle SHALL keep its dashed shape and tooltip (no duplicate 北 on the circle). 已核准 is the default focus state — its schedule badge is omitted; only exceptional schedules (已駁回 / 施工中 / 自行撤回 / 已失效 / 審查中) render.

#### Scenario: 區段-carrying same-day virtual appends to the anchored strip
- **WHEN** a real node anchors case A on date D and a same-date virtual node carries a 區段 label (e.g. A區) with schedule 施工中
- **THEN** the real node's badge strip reads [北 anchored][北 A區 · 施工中] and the virtual circle renders without its own 北 badge

#### Scenario: Virtual without 區段 or schedule stays on its own row
- **WHEN** a same-date virtual node has no 區段 token and no schedule
- **THEN** its badge is not appended to the real node's strip (it renders on its virtual row per the ordering rules)

#### Scenario: 已核准 schedule renders no badge
- **WHEN** a case's schedule is 已核准
- **THEN** no schedule badge renders for it (graph labels and 相關連結) — the default focus state is unmarked

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

