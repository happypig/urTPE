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
shows no state badge. Badge colours: 建照 orange, 開工 red, 使照 green, dead-end state
grey.

Each list item SHALL also be reachable and activatable by keyboard, and the
selection SHALL be written to the URL (viewer-url-writeback-keyboard,
2026-11-12): every item carries `tabindex="0"` and `role="button"`, shows a
visible focus indicator (`:focus-visible`), and Enter or Space activates it
exactly as a click does. Selecting a project — by click or by keyboard —
SHALL write `#project=<encodeURIComponent(project_id)>` into the URL with
`history.replaceState` (one history entry per page load; never a push per
click), so a reader can copy the selection out of the address bar. The
deep-link read half (`openFromHash`, the hash format, the dashboard's
encoding) SHALL NOT change.

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

#### Scenario: In-review without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and its
  `case_schedules` include 審查中 (37 families measured)
- **THEN** the list item shows no state chip (in-review is the default state;
  the grey 審查中 chip is removed)

#### Scenario: Withdrawn without construction dates shows the grey chip
- **WHEN** a project carries none of the three construction dates and every
  case in its `case_schedules` is 自行撤回 / 已駁回 / 已失效, but its current
  recno node's own case has no dead-end schedule (市府段三小段-331,
  雙連段一小段-416-6, 民生段-140-9)
- **THEN** the list item shows no state chip (the grey 撤回 chip is removed —
  the current approval decides, not older cases)

#### Scenario: No construction dates and no case schedule shows nothing
- **WHEN** a project carries none of the three construction dates and its
  current node's case has no `case_schedules` entry
- **THEN** its list item shows no stage badge

#### Scenario: In-review and approved states mark nothing
- **WHEN** a project's cases are 審查中 or 已核准 (37 in-review families
  measured)
- **THEN** its list item shows no state badge (approved/in-review is the
  default state)

#### Scenario: No construction dates and no dead-end current case shows nothing
- **WHEN** a project carries none of the three construction dates and its
  current node's case has no dead-end schedule
- **THEN** its list item shows no stage badge

#### Scenario: A list item is focusable and keyboard-activatable
- **WHEN** a project item renders in the left-hand list
- **THEN** it carries `tabindex="0"` and `role="button"`
- **AND** Enter or Space activates it exactly as a click does

#### Scenario: Selecting a project writes the URL
- **WHEN** a project is selected, by click or by keyboard
- **THEN** the URL hash becomes `#project=<encodeURIComponent(project_id)>`
- **AND** the write is a `replaceState`, so the history stack gains no entry

#### Scenario: The deep link's read half is unchanged
- **WHEN** the page is opened with `#project=<id>` in the hash, or the hash
  changes while the page is open
- **THEN** that project's graph opens, as before

The list SHALL also render only the rows near the viewport
(windowed-list, user decision 2026-11-12): `renderList` renders the visible
range plus a buffer, spacer elements hold the full list height so the
scrollbar never jumps, and scrolling re-renders the window around the new
offset. The window helper SHALL be written so the dashboard's drill-down
list can call it. The deep link (`openFromHash`) SHALL render the window
containing the target row BEFORE scrolling to it — a windowed list whose
target row does not exist yet would silently select without showing.

#### Scenario: The window renders fewer rows than the list holds

- **WHEN** the payload holds 675 projects and the viewport is 920 px
- **THEN** the DOM holds the visible rows plus the buffer, not all 675
- **AND** spacer elements keep `scrollHeight` at the full list height

#### Scenario: Scrolling re-renders the window

- **WHEN** the reader scrolls down past a row height
- **THEN** the window re-renders around the new offset
- **AND** the total scroll height does not jump

#### Scenario: The deep link renders before it scrolls

- **WHEN** the page is opened with `#project=<id>` while the target row is
  outside the current window
- **THEN** the window containing the target row renders first
- **AND** the target row is then scrolled into view, centered

#### Scenario: The helper is callable from the dashboard

- **WHEN** the dashboard's drill-down list needs the same windowing
- **THEN** it calls the same helper rather than re-implementing it
