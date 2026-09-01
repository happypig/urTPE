## Purpose

Orphan case_ids with harvested case_names and landcore similarity ≥ 0.7 stop being side-annotations and become **virtual milestone nodes**: first-class, dashed-styled members of the project timeline, placed chronologically in their 事業種類 column. This retires the ghost-anchor column for named orphans — "there's no orphan node anymore".

## ADDED Requirements

### Requirement: Candidate case_names persisted at discovery time

The discovery pipeline SHALL persist the `case_name` returned by the platform search API for every candidate case_id (kept or rejected) into the discovery result, instead of discarding kept-case names. Landcore similarity for orphan anchoring SHALL compute from these harvested names when available, taking precedence over the attribution and twin-bridge proxies.

#### Scenario: Kept orphan's name survives discovery
- **WHEN** the platform search returns case_name for a kept candidate case_id that no node anchors
- **THEN** the discovery result carries {case_id: case_name} and the emitted ghost payload includes that name

#### Scenario: Harvested name gates virtual anchoring
- **WHEN** an orphan's harvested case_name yields landcore similarity ≥ 0.7 to the project anchor
- **THEN** the orphan qualifies for virtual milestone rendering without relying on attribution or twin-bridge signals

### Requirement: Landcore-similar orphans render as virtual milestone nodes

A named, landcore-similar orphan SHALL render inside the project timeline as a virtual milestone node: dashed circle, dashed connecting edges, placed at its 核定日期 row within its 事業種類 column, labeled with its stage (擬訂 / 變更 / 變更(第N次)) and 事業種類 without a recno, and belonging to the project family identity. Its link badges SHALL use the same 北/國 badge anatomy as PDF milestone nodes (badge strip above the label); named virtual nodes SHALL NOT carry a 孤 badge — provenance SHALL live in the node tooltip only.

#### Scenario: Virtual node placed chronologically in its track column
- **WHEN** orphan 09907221's harvested name gives stage 擬訂, track 事業計畫, and its milestones give 核定日期 2019/01/31
- **THEN** the graph renders it as a dashed node in the 事業計畫 column between its date neighbors, labeled 擬訂 + 事業計畫 without recno, with the standard 北 link badge above the label

#### Scenario: Named virtual nodes carry no visible orphan marker
- **WHEN** a virtual node renders from a harvested name
- **THEN** no 孤 badge appears on it — differentiation is the dashed circle/edges, and the tooltip carries the orphan provenance

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
