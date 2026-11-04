## MODIFIED Requirements

### Requirement: Viewer renders orphan ghost node with dotted construction-chain edges

The viewer SHALL render ghost/orphan nodes in the history graph with an "orphan" badge. Each orphan SHALL take its own timeline row, interleaved with the recno nodes by the case_id order (an undated orphan carries its stage cluster's effective date). A dated nameless 孤 anchor joins the timeline by date like a named orphan; an undated nameless anchor renders no row (the right-most ghost column is removed — wave 5 §4; the 3 nameless anchors were §8 defects removed by wave 3b). "Between 2 consecutive recnos" and "nearest recno" mean RENDERED ROWS in the timeline, not dates: an undated orphan has no date of its own, so a date-based test never fires for it (corpus: 30 orphans row-between but undated, 7 dated). A named orphan whose row sits between 2 consecutive recno rows of the same swimlane SHALL shift 32px right of that swimlane's track line. Each orphan whose schedule is NOT a dead end (已失效 / 自行撤回 / 已駁回) SHALL connect with a dotted edge (class `edge orphan`) to the recno row directly above it — its branch-off point — or to the recno row directly under it when no recno row sits above. A dead-end orphan connects only upward, to its branch-off row; when no recno row sits above it, it renders with no dotted edge (user decision 2026-11-05, board D4b — an edge pointing down out of a closed case draws a flow that never happened; measured 160 such edges, against 78 up-edges that stay). Example: 11012301 (applies 2021-12-29, withdraws, no date) renders between 734@2019-12-18 and 393@2022-12-29 in the 事業計畫、權利變換 swimlane, shifts 32px right, and its dotted edge goes to 734 — the revision it was filed against — not to the later 393; the live path keeps its solid edge 734 → 393 (dead-end branch vs ongoing path).

#### Scenario: Orphan ghost node appears in graph by date with badge

- **WHEN** a project has a ghost node for case_id 09907221
- **THEN** the graph shows a node with an "orphan" badge at its date row among the recno nodes

#### Scenario: Orphan dotted edge to the recno row directly above

- **WHEN** an orphan renders between recno nodes dated 2023-03 and 2023-08 in its swimlane
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2023-03 recno node directly above it

#### Scenario: Undated orphan branches from the recno row directly above, not the later recno it was filed against

- **WHEN** an undated orphan (case_id 11012301) renders between recno 734 (2019-12-18) and recno 393 (2022-12-29) in the same swimlane
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to recno 734, not to recno 393

#### Scenario: Orphan dotted edge to recno row directly under when no recno row sits above

- **WHEN** a live orphan (schedule not 已失效 / 自行撤回 / 已駁回) renders earlier than every recno node in its swimlane (earliest recno dated 2022-01)
- **THEN** a dotted edge (class `edge orphan`) connects the orphan to the 2022-01 recno node directly under it

#### Scenario: A dead-end orphan above every recno row renders no dotted edge

- **WHEN** an orphan whose schedule is 已失效 / 自行撤回 / 已駁回 renders earlier than every recno node in its swimlane (e.g. 北安段一小段25's 09609061 已失效)
- **THEN** no dotted edge connects it to any recno row (no edge points out of a closed case)
- **AND** the node still renders its row, badge and schedule text

#### Scenario: Orphan shifts 32px right only when between 2 recno rows in same swimlane

- **WHEN** a named orphan's row sits between 2 consecutive recno rows of the same track column (dated or undated)
- **THEN** its node renders 32px right of that column's track line
