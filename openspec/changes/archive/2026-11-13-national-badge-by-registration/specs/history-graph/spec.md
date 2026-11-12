## MODIFIED Requirements

### Requirement: 國 badge binds to the recno node a national label names

The pipeline SHALL resolve the 國 badge once, at graph build, and emit the
result per node: a recno node carries `national_badges: true` when the
project's national view page names it by any of three routes
(national-badge-by-registration, user decision 2026-11-12):

1. **registration** — the node's anchored case is listed in
   `links.view_verified_case_ids` (the view page's own 相關連結);
2. **exact name** — the node's 案名 equals the project's `links.twur_name`
   (the view page's own title names the project by its 擬訂 first-plan 案名);
3. **擬訂 section+parcel fallback** — a 擬訂 node whose (section,
   first-parcel) parses from the `twur_name`'s land core (the 權利變換 擬訂
   node's 案名 differs from the title by one word; the unit is the same by
   its own land core, not by a date).

A node qualifying by NONE of the routes SHALL NOT carry the badge — in
particular, the former per-label stage+date binding (a national label's
date matching the node's date) SHALL NOT grant the badge (measured
2026-11-12: 1,186 nodes carry 國 under the binding rule, 735 under this
rule, 451 lose it, 0 gain it). The 現況 rule (`node.is_current` alone)
stays retired. The field is emitted only when the project carries a `twur`
link; a project without a national page emits no `national_badges` on any
node. The viewer SHALL render the badge from the field and SHALL NOT
re-implement the matcher client-side.

**Reason**: a date matching is not the portal naming. The binding route
badged nodes whose cases the view page does not register (文林838-1 node
433: two labels hit its exact date, its case unregistered) — the badge
should mean "the view page names this".

#### Scenario: A registered case's node carries the badge

- **WHEN** the node's anchored case is listed in `links.view_verified_case_ids`
- **THEN** the emitted node carries `national_badges: true`

#### Scenario: The title's own node carries the badge

- **WHEN** the node's 案名 equals the project's `links.twur_name`
- **THEN** the emitted node carries `national_badges: true`

#### Scenario: The 擬訂 section+parcel fallback keeps the 權利變換 擬訂 node

- **WHEN** a 擬訂 node's (section, first-parcel) parses from the
  `twur_name`'s land core, and its 案名 differs from the title by one word
  (大安590 node 884: 權利變換計畫案 vs the title's 事業計畫案)
- **THEN** the emitted node carries `national_badges: true`
- **AND** a 變更 node with the same section+parcel does NOT (the fallback
  is 擬訂-only)

#### Scenario: A stage+date match alone grants nothing

- **WHEN** two national labels' dates hit a node's exact date, and the
  node's case is not registered and its 案名 is not the title (文林838-1
  node 433)
- **THEN** the emitted node carries no `national_badges`

#### Scenario: The current node qualifies only through its own case

- **WHEN** a node is 現況 and its case is not view-verified and its 案名 is
  not the title (大安590 node 90)
- **THEN** the emitted node carries no `national_badges`

#### Scenario: The rule removes only — no node gains a badge

- **WHEN** the rule runs over the corpus (1,186 badged today)
- **THEN** 735 carry the field, 451 lose it, and 0 gain it

#### Scenario: A project without a national page emits no badge field

- **WHEN** the project's `links.twur` is empty
- **THEN** no node of the project carries `national_badges`

#### Scenario: The field survives a rebuild from emitted state

- **WHEN** the payload is reloaded with `--from-js` and re-emitted
- **THEN** every node's `national_badges` is unchanged

The former binding scenarios are retired with their rule; each names what
replaces it:

#### Scenario: 國 binds to the node with matching stage+track

- **WHEN** a national label names a stage+track that exactly one node carries
- **THEN** the label no longer grants the badge by stage+track alone — the
  pipeline resolves the badge by registration, exact name or the 擬訂
  fallback (national-badge-by-registration)

#### Scenario: A single-candidate label binds whatever its date

- **WHEN** a label's single stage+track candidate differs from the label's
  date by more than 1 day
- **THEN** the node's badge comes from the resolved field, not from the
  single-candidate rule

#### Scenario: 國 binds by date tie-break

- **WHEN** two nodes share the label's stage+track and the label's date
  equals one node's date
- **THEN** the date no longer decides the badge — the resolved field does

#### Scenario: The ±1-day window decides among several candidates

- **WHEN** the label's date falls within ±1 day of one node's date
- **THEN** the window no longer grants the badge

#### Scenario: A tie that ±1 day cannot break binds nothing

- **WHEN** several nodes share the label's date
- **THEN** no badge is granted by the tie — the resolved field decides

#### Scenario: view_verified_case_ids still grants 國

- **WHEN** `links.view_verified_case_ids` lists the node's anchored case
- **THEN** the node carries the badge (registration is the first route)

#### Scenario: 現況 alone no longer grants 國

- **WHEN** a node is 現況 but its case is not view-verified and no other
  route names it
- **THEN** it carries no 國 badge

#### Scenario: application dates and 使用核發日期 bind nothing

- **WHEN** a national label 使用核發日期 or 事業計畫申請日期 is present
- **THEN** it grants no badge — labels grant nothing at all now; the
  resolved field does
