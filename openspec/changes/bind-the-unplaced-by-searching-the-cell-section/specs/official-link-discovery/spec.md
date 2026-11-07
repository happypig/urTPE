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

The land-identity comparison SHALL accept the forms the two sides print for the
same unit, and SHALL NOT reject a pair the gazette's own cells agree on:

- **Section forms.** Two sections name the same unit when they carry the same
  小段 suffix and the same 段 name, with a trailing 段 optional on either side.
  The gazette prints 吳興一小段 where the city prints 吳興段一小段.
- **Section reading.** A core's section is cut at both its first 段 and its
  last, and either reading may match. 河堤段五小段 reads as a section name and
  not as section 河堤段 with parcel 五小段399.
- **Parcel set.** The city's declared parcel matches the node when it equals
  the node's first parcel or is one of the node's own parcels. The 吳興街二期
  unit's first parcel is 163-2; the city declares 247.
- **Either cell's core.** A node's land core may be built from the 地號 cell's
  section as well as the 案名's. The gazette's 案名 says 河堤五小段 and its 地號
  cell says 河堤段五小段; the city indexes the cell's form.

The comparison SHALL remain a **superset** of its former strictness: a pair it
accepted before it SHALL accept now. The district and the land count keep
their existing weight, so a count mismatch still costs the count term exactly
as before.

#### Scenario: A node binds to its city's case when the section forms differ

- **WHEN** the node's 案名 is 變更(第三次)臺北市中正區河堤五小段399地號等3筆土地都市更新權利變換計畫案, its 地號 cell says 河堤段五小段, and the city's case 11005053 is named 變更(第三次)臺北市中正區河堤段五小段399地號等3筆土地都市更新權利變換計畫案 with 權變核定日期 2024-10-29
- **THEN** the node binds to case 11005053

#### Scenario: A node binds when the city declares another parcel of the unit

- **WHEN** the node's unit declares parcels 163-2 and 247, its first parcel is
  163-2, and the city's case 10405235 is named 變更(第二次)臺北市信義區吳興段二小段247地號等2筆土地(原吳興街二期整宅地區)都市更新事業計畫及變更權利變換計畫案 with 核定日期 2020-03-19
- **THEN** the node binds to case 10405235

#### Scenario: A node binds when the city's name omits the 段

- **WHEN** the node's 案名 is 擬訂臺北市信義區吳興一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案 and the city's case 10611051 is named 擬訂臺北市信義區吳興段一小段330地號等43筆土地都市更新事業計畫及權利變換計畫案 with 核定日期 2021-09-15
- **THEN** the node binds to case 10611051

#### Scenario: A pair the former comparison accepted is still accepted

- **WHEN** a node's 案名 and a city's case name name the same section, the same
  first parcel and the same land count
- **THEN** the pair still binds
