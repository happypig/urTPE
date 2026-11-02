## MODIFIED Requirements

### Requirement: 國 badge binds to the recno node a national label names

A national approval label (事業計畫核定日期, 權利變換計畫核定日期,
第一次變更事業計畫核定日期, …) carries a stage (擬訂, 第N次變更) and a
track (事業計畫 / 權利變換). A node gets a 國 badge when one such label binds to
it: same stage and same track, with a date tie-break when more than one node matches
(民國 date converted to ISO). A combined-track node (事業計畫、權利變換) matches
a label of either track. Application dates (…申請日期) and 使用核發日期 name no
stage and never bind.

A node also keeps its 國 badge when `links.view_verified_case_ids` lists its anchored
case (the portal's direct assertion). The 現況 rule (`node.is_current` alone) is
removed.

**Reason**: 492 of 632 projects with a national link have an empty
`view_verified_case_ids`; the old 現況 rule put 國 on a node the national page does
not name.

#### Scenario: 國 binds to the node with matching stage+track

- **WHEN** a national label 事業計畫核定日期 111.08.02 names stage 擬訂 track
  事業計畫
- **THEN** the recno node carrying stage 擬訂 track 事業計畫 gets the 國 badge

#### Scenario: 國 binds by date tie-break

- **WHEN** two recno nodes share stage 變更 track 事業計畫, dated 111.08.02 and
  112.03.21, and the national label 第一次變更事業計畫核定日期 reads 112.03.21
- **THEN** the 112.03.21 node gets 國

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
