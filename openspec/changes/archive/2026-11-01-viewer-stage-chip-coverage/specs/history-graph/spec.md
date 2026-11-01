# history-graph Delta

## MODIFIED Requirements

### Requirement: List items surface the construction stage

Each project item in the left-hand list SHALL display a two-character
construction stage badge — 建照， 開工， or 使照 — derived from whichever of
the three construction milestones carries the latest date (使照 falls back to
the national 使用核發日期). A project with none of the three dates but a known
case state (`case_schedules` holding 審查中 or 自行撤回/已駁回/已失效) SHALL
display a grey status chip naming that state (審查中 or 撤回) instead of
showing nothing — silence must not read as "not started" when the platform
says otherwise. Only a project with neither construction dates nor any case
schedule SHALL show no badge. The badge is a read-only status chip; it adds no
interaction. Badge colours: 建照 orange, 開工 red, 使照 green, status chip grey.

#### Scenario: Latest milestone wins the badge
- **WHEN** a project has 建照核發日期 2018/12/21 and 使照核發日期 2024/04/24
  (no 開工)
- **THEN** the list item shows the 使照 badge (the latest construction event),
  rendered green

#### Scenario: In-review without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and its
  `case_schedules` include 審查中
- **THEN** the list item shows the grey 審查中 chip

#### Scenario: Withdrawn without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and every
  case in its `case_schedules` is 自行撤回 / 已駁回 / 已失效
- **THEN** the list item shows the grey 撤回 chip

#### Scenario: No construction dates and no case schedule shows nothing
- **WHEN** a project carries none of the three construction dates and no
  `case_schedules` entry
- **THEN** its list item shows no stage badge
