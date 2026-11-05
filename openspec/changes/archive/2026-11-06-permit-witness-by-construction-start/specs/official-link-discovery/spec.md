## MODIFIED Requirements

### Requirement: The building-authority permit record witnesses the 使照 date

The system SHALL treat the building authority's 使用執照摘要 open data
(data.taipei, XML, no key — the 歷年 dataset `0f3f9675-8356-4f1a-9908-1ce8892012fa`
and the current-year dataset `74a8b311-906e-44c4-91fb-7f413842d4e1`) as the
third source for the 使照 date, beside the city platform and the national
page. The system SHALL download both datasets into the archive root keyed by
SHA-256, parse each record's 執照號碼, 發照日期 (ROC `YYYMMDD`), 原核發執照,
開工日期 and 地段號 (`臺北市{區}{段}{號}`), index by (district, section,
parcel-mono), and attach per project the 建字-origin permit(s) whose parcel set
overlaps the project's parcel list most. A download failure SHALL be reported
and SHALL NOT abort discovery: the pipeline emits without the permit witness.
The permit SHALL NOT replace either portal's 使照 date — it is a witness; the
disagreement flag names it.

A permit whose `執照號碼` or `原核發執照` is not a 建字 permit (雜字 — a 雜項
or second building) SHALL NOT witness the 使照. When several 建字 permits
overlap one project (an area split), each area's permit SHALL attach. When
no permit's parcels overlap the project's parcel list, both portal dates
SHALL stay and the disagreement flag SHALL say so — the permit's absence is
never repaired by inference.

When **more than one** permit matches, the system SHALL choose the witness by
the city's **開工日期**: the permit whose `開工日期` equals the city's 開工日期.
The city's 開工 date SHALL be read from the milestone **source map** (the case
that holds each value), not from the merged milestone dict, because the merged
dict can be stale.

The system SHALL **NOT** choose the permit whose 發照日期 equals the city's 使照
date. The permit witnesses that date; matching it would make the witness copy
the value it exists to check, so a disagreement could never be exposed.

When the 開工 date leaves exactly one permit, that permit is the witness. When
it leaves none or more than one, the system SHALL emit **no single permit**:
`links.permit` SHALL be absent and `links.permit.ambiguous` SHALL carry the
candidate list, so an arbitrary permit is never shown as the project's own.

#### Scenario: The permit confirms the national value
- **WHEN** 吉林811's city 使照核發日期 reads 2013/09/11 and the national
  使用核發日期 reads 2013-11-12, and permit 102使字第0298號 (發照日期
  ROC 1021112 = 2013-11-12) sits on 吉林段三小段811
- **THEN** the project carries `links.permit` `{permit_no: "102使字第0298號",
  date: "2013-11-12"}`
- **AND** the disagreement flag names the permit as confirming the national
  value

#### Scenario: The permit confirms the city value on a large gap
- **WHEN** the city and national 使照 dates disagree by months and the
  permit's 發照日期 equals the city's value (虎林310: permit 111使字第0140號,
  ROC 1111111 = 2022-11-11; the city reads 2022/11/11, the national 2022/01/11)
- **THEN** the flag names the permit as confirming the city value

#### Scenario: A 雜字 permit does not witness
- **WHEN** a project's site carries a 建字 permit and a later 雜字 permit, and
  the two portals each copied one of them (奇岩13, 龍泉712)
- **THEN** the 建字-origin permit is the witness
- **AND** the 雜字 permit does not enter the match

#### Scenario: An area split attaches one permit per area
- **WHEN** an area-split project carries two 建字 permits, one per area
  (懷生931 東區/西區)
- **THEN** both permits attach

#### Scenario: No permit overlaps the parcel list
- **WHEN** a project's two portal dates disagree and no permit's 地段號
  intersects the project's parcel list (榮星306, 德惠573 — the permit sits on
  parcels the gazette lists under another number)
- **THEN** both portal dates stay
- **AND** the disagreement flag reads 無執照佐證

#### Scenario: A failed download does not abort discovery
- **WHEN** the data.taipei download fails or times out
- **THEN** the run reports the failure
- **AND** discovery proceeds; no project carries a permit witness

#### Scenario: The 開工 date picks the project's own permit
- **WHEN** a project's parcel carries four permits and the city's 開工日期 is
  2020-05-06, and exactly one of the four carries that 開工日期
  (寶清57-13: the city's 使照 2025-06-25 and 開工 2020-05-06 both name
  114使字第0094號, the last of the four)
- **THEN** `links.permit` names 114使字第0094號
- **AND** `links.permit.date` is 2025-06-25, the project's own 使照

#### Scenario: An unresolved tie is marked ambiguous
- **WHEN** a project's parcel carries several permits and the city's 開工日期
  matches none of them, or matches more than one
- **THEN** the project carries no `links.permit`
- **AND** `links.permit.ambiguous` names the candidate permits
- **AND** no permit is shown as the project's own

#### Scenario: The 使照 date never chooses the permit
- **WHEN** a project's parcel carries several permits and exactly one carries
  the city's 使照 date, but the city's 開工 date matches none of them
- **THEN** the project carries no `links.permit`
- **AND** the candidate list names that permit among the candidates
