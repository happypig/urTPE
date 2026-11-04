## MODIFIED Requirements

### Requirement: Join links to projects by land-identity core

The system SHALL attach discovered links to projects and to individual record
nodes by the same land-identity key the merge step anchors on, so each node can
carry the case link for its own approval stage. Date-based node anchoring SHALL
match the node's 核定日期 against the case's approval milestone — which for the
事業計畫/權利變換 tracks is 核定日期/權變核定日期, and for the 事業概要 track is
**概要核准日期** (a 概要 case has no 核定日期; omitting this label silently
degrades 概要-node anchoring to the positional fallback). The date matcher SHALL
accept ROC (`97/1/2`), slash-Gregorian (`2008/01/02`) and ISO (`2008-01-02`)
forms — the PDF pipeline passes raw ROC dates.

A node the date matcher cannot place SHALL be bound by the 4-step resolver,
in order, never by list position:

1. **案名 match over the cached cases** — tier 1 exact (spaces ignored),
   tier 2 loose (等, `(原N筆)`, 擬定↔擬訂, `案及`→`及`, the area suffix,
   `權利變換案`→`權利變換計畫案`), tier 3 stage-with-ordinal + plan type
   (ignoring `(含釐正圖冊)`). Cases whose schedule is 自行撤回 / 已駁回 / 已失效
   SHALL NOT bind. A 無 case SHALL yield to an approved same-name sibling.
   When every live match in the tier carries a distinct area suffix
   (`-A區` / `-北區` / `(A區段)` …), the node is an area split and **all** its
   cases SHALL bind to the node (one gazette row, several city cases).
2. **Same-day id probe** — the case ids `<first 7 digits>0–9` derived from
   every id the project holds. Case ids are a city-wide daily serial (ROC
   filing date + one digit), so a probed id SHALL be accepted only when the
   city's own `CASE_NAME` matches the node's 案名 **and** the header's
   approval date matches the node's date. An accepted id SHALL join the
   cache (appended to `city_case_ids`, milestones fetched, name recorded).
3. **Header approval date** — a cached case whose header
   (`uro_chk_date`/`uro_chk_date2`) approves on the node's date SHALL bind
   even when the case's data2 milestones carry another case's date. A header
   date within 10 days of the node's date SHALL bind when the case's stage
   equals the node's stage-with-ordinal.
4. **All-parcel search** — the parcel search SHALL run on every parcel of
   the node, not only the first, and a result SHALL be accepted on its 案名
   matching the node plus an approval date matching the node's date.

A node every step misses SHALL be named in the run report and flagged on its
record — never silently unbound, never bound by position. The positional
fallback (binding `city_case_ids[0/1]` by track) SHALL be removed.

#### Scenario: Per-stage city links land on the right node
- **WHEN** a project family contains both a 事業計畫 and a 權利變換 approval
- **THEN** the city case_id for each approval attaches to the corresponding node
- **AND** the shared national-portal link attaches at project level

#### Scenario: 概要 case anchors to its node via 概要核准日期
- **WHEN** a node's date is 2026-03-31 and the family's 概要 case carries
  `概要核准日期 = 2026/03/31` (no 核定日期 — the 概要 track)
- **THEN** the case anchors to that node (previously it fell to the positional
  fallback or stayed unanchored — 延吉段三小段727 shape, operations log §6.14)

#### Scenario: ROC gazette dates anchor correctly in the PDF pipeline
- **WHEN** the PDF pipeline passes the node date as a ROC string (`97/1/2`) and
  the case's 核定日期 is `2008/01/02`
- **THEN** the matcher normalizes both to ISO and anchors the case

#### Scenario: An area split binds every case of the split
- **WHEN** a node's 案名 matches cached cases 11011241 (`…-A區…`) and 11011242
  (`…-B區…`) at the same tier, each carrying a distinct area suffix, and both
  are live (吉林508 recno 259)
- **THEN** both case ids bind to the node in `links.taipei`
- **AND** neither case is left as an orphan node for the date the gazette printed

#### Scenario: A 無 case yields to an approved same-name sibling
- **WHEN** a node's 案名 matches a case whose header reads 無 (no milestones,
  no approval) and another case with the identical name that is approved
  (東湖34 recno 73: 11302181 vs 11502008)
- **THEN** the node binds the approved case 11502008
- **AND** the 無 case does not bind to that node

#### Scenario: A withdrawn case never binds by name
- **WHEN** a node's 案名 exactly matches a case whose schedule is 自行撤回
  (吉林705 recno 1370: 09307103) and another same-name case that is approved
  (09307104)
- **THEN** the node binds 09307104
- **AND** the withdrawn case stays an orphan node with its own city name as label

#### Scenario: A same-day id is accepted only on CASE_NAME and date
- **WHEN** the probe reads a header for id 10203252 whose CASE_NAME names
  中山段一小段111 (a different project — case ids are a city-wide daily
  serial) while the probed node belongs to 犁和302
- **THEN** 10203252 does not bind to the node
- **AND** when a sibling id's CASE_NAME names the node's unit (犁和302's
  10203253, `Uro_Chk_Date2` 2023/12/28 = the node's date), that id binds and
  joins the cache

#### Scenario: A header approval date overrides a copied data2 date
- **WHEN** a cached case's data2 核定日期 reads 2008/05/15 (the plan case's
  date) but its header `uro_chk_date` reads 2013-08-20 and the node's date is
  2013-08-20 (玉泉11 recno 1180 → 09504263)
- **THEN** the node binds 09504263 by the header date

#### Scenario: A bounded header-date drift binds on a matching stage
- **WHEN** a cached case's header approves 2016-11-12, the node's date is
  2016-11-02, and the case's stage equals the node's 變更(第二次) (康寧626
  recno 1019 → 09712204)
- **THEN** the node binds 09712204

#### Scenario: The parcel search runs on every parcel of the node
- **WHEN** a node's parcels are 566 and 567, the first-parcel search returns
  only the newest case, and the parcel-567 search returns the 2016 擬訂 case
  10006032 with an approval date equal to the node's (南港566 recno 1063)
- **THEN** 10006032 binds to the node and joins the cache

#### Scenario: A node no step resolves is reported
- **WHEN** every resolver step misses for a node
- **THEN** the run report names the node's project, 案名 and date
- **AND** the record carries a review flag naming the miss
- **AND** the node is not bound to any case by list position

#### Scenario: Unresolvable projects are counted
- **WHEN** discovery completes over all projects
- **THEN** the review report lists the number and identities of projects with no resolved link
