## MODIFIED Requirements

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

#### Scenario: Nameless orphans keep the interim anchor column
- **WHEN** an orphan qualifies only via attribution or twin-bridge (no harvested name yet)
- **THEN** it remains a dashed anchor (with 孤 badge) in the ghost column until its name is harvested

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
