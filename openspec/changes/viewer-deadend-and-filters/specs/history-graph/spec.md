## MODIFIED Requirements

### Requirement: List items surface the construction stage

Each project item in the left-hand list SHALL display a two-character
construction stage badge — 建照， 開工， or 使照 — derived from whichever of
the three construction milestones carries the latest date (使照 falls back to
the national 使用核發日期). After the construction badge, the item SHALL
display a dead-end state badge when the project's current (is_current) recno
node's own case carries a dead-end schedule in `case_schedules` — 已失效 /
自行撤回 / 已駁回 — naming that state verbatim (user decision 2026-11-05,
board D4c: the state of the current approval's own case, not the family's; 1
project today, 龍泉段一小段-534's 11201181 已失效). The family-level grey
chips (審查中 / 撤回) and the 未核定 badge are REMOVED: a gazette approval
proves the unit was approved, and an older case's state must not label the
current approval (the 4 撤回/未核定 projects all hold an approved current
node). A project with no construction badge and no dead-end current case
shows no state badge. Badges are read-only status chips; they add no
interaction. Badge colours: 建照 orange, 開工 red, 使照 green, dead-end state
grey.

#### Scenario: Latest milestone wins the badge
- **WHEN** a project has 建照核發日期 2018/12/21 and 使照核發日期 2024/04/24
  (no 開工)
- **THEN** the list item shows the 使照 badge (the latest construction event),
  rendered green

#### Scenario: Dead-end current case shows the state badge after the construction badge
- **WHEN** a project's current recno node's first case is 11201181 and
  `case_schedules[11201181]` is 已失效 (龍泉段一小段-534)
- **THEN** the list item shows the grey 已失效 badge
- **AND** when the project also carries a construction date, the dead-end
  badge renders after the construction badge

#### Scenario: An approved current node shows no dead-end badge despite dead older cases
- **WHEN** a project's current node is an approved 擬訂 事業概要 and an older
  case of the family is 已駁回 or 已失效 (民生段-140-9, 市府段三小段-331,
  雙連段一小段-416-6)
- **THEN** the list item shows no state chip (no 審查中, 撤回 or 未核定 chip
  exists any more)

#### Scenario: In-review and approved states mark nothing
- **WHEN** a project's cases are 審查中 or 已核准 (37 in-review families
  measured)
- **THEN** its list item shows no state badge (approved/in-review is the
  default state)

#### Scenario: No construction dates and no dead-end current case shows nothing
- **WHEN** a project carries none of the three construction dates and its
  current node's case has no dead-end schedule
- **THEN** its list item shows no stage badge
