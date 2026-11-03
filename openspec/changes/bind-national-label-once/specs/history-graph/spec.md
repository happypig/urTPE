## MODIFIED Requirements

### Requirement: 國 badge binds to the recno node a national label names

A national approval label (事業計畫核定日期, 權利變換計畫核定日期,
第一次變更事業計畫核定日期, …) carries a stage (擬訂, 第N次變更) and a
track (事業計畫 / 權利變換). The viewer SHALL bind each label to at most one
recno node, decided once per project, not per node: the label's candidates are
the nodes carrying the label's stage and a matching track (a combined-track
node, 事業計畫、權利變換, matches a label of either track). Binding SHALL
resolve by exact date first; if several nodes share the label's date, or the
label's date matches no node exactly, the ±1-day window (公告-vs-committee
offset) SHALL decide; if 2 or more nodes survive a step, or no node qualifies
at any step, the label SHALL bind nothing and no node gains the 國 badge from
it. Application dates (…申請日期) and 使用核發日期 name no stage and SHALL
never bind. A node SHALL also keep its 國 badge when `links.view_verified_case_ids`
lists its anchored case (the portal's direct assertion). The 現況 rule
(`node.is_current` alone) is removed.

**Reason**: scoring per node badged every candidate of a multi-match label —
19 labels, 41 badged nodes, 16 unearned 國 (C1). Binding per label gives one
owner per label or none.

#### Scenario: 國 binds to the node with matching stage+track

- **WHEN** a national label 事業計畫核定日期 111.08.02 names stage 擬訂 track
  事業計畫 and exactly one recno node carries that stage and track
- **THEN** that node gets the 國 badge

#### Scenario: A single-candidate label binds whatever its date

- **WHEN** a label names stage+track that exactly one node carries, and the
  node's date differs from the label's date by more than 1 day
- **THEN** that node still gets the 國 badge (one candidate cannot tie)

#### Scenario: 國 binds by exact date among several candidates

- **WHEN** two recno nodes share stage 變更 track 事業計畫, dated 111.08.02 and
  112.03.21, and the national label 第一次變更事業計畫核定日期 reads 112.03.21
- **THEN** only the 112.03.21 node gets 國

#### Scenario: The ±1-day window decides among several candidates

- **WHEN** two recno nodes share stage+track, dated 2023-03-20 and 2023-09-01,
  and the label's date converts to 2023-03-21
- **THEN** only the 2023-03-20 node gets 國 (within ±1 day; the other is not)

#### Scenario: A tie that ±1 day cannot break binds nothing

- **WHEN** two recno nodes share stage+track, both dated 2023-03-20, and the
  label's date converts to 2023-03-21
- **THEN** neither node gets 國 from this label (2 survivors after the window)

#### Scenario: view_verified_case_ids still grants 國

- **WHEN** `links.view_verified_case_ids` lists the node's anchored case
- **THEN** that node keeps its 國 badge

#### Scenario: 現況 alone no longer grants 國

- **WHEN** a node is 現況 but its case is not view-verified and no national label
  binds to it
- **THEN** it carries no 國 badge

#### Scenario: application dates and 使用核發日期 bind nothing

- **WHEN** a national label 使用核發日期 or 事業計畫申請日期 is present
- **THEN** it binds to no recno node for the 國 badge
