## MODIFIED Requirements

### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place: each approval node with an anchored Taipei case SHALL expose its 北 badge as a hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge hyperlink to the project's national view page when one exists; **any approval node whose anchored case is listed in `links.view_verified_case_ids` — the cases the project's own national view page names in 相關連結 — SHALL also expose the 國 badge**, because the portal itself asserts that case belongs to the unit and the node should lead to the page that names it; and each construction-event node SHALL label as a hyperlink to its source portal — Taipei case page (pink) when Taipei-sourced, national view page (green) when national-mapped. A node qualifying both ways (view-verified and 現況) SHALL render exactly one 國 badge. The standalone 相關連結 section SHALL be retired behind an explicit debug toggle that defaults to hidden.

The 國 badge's route set is the pipeline's resolved one
(national-badge-by-registration, user decision 2026-11-12): the viewer SHALL
render the badge from the node's emitted `national_badges` field — which the
pipeline sets for a node the view page names by registration, exact name, or
the 擬訂 section+parcel fallback — and SHALL NOT re-implement the former
per-label stage+date matcher client-side. A node the payload does not mark
SHALL carry no 國 badge, whatever a national label's date says.

A joined node — one anchoring 2+ city cases — SHALL render one 北 badge per
anchored case (joined-node-section-callouts, user decision 2026-11-12,
item 4b): each badge links its own `r_progress_detail.aspx?case_id=` page,
and the case's area suffix (`[A區]` / `[B區]` — parsed from the case name in
`candidate_names`; the corpus holds A, B, C, D, E, 北, 南, 東, 西) SHALL
render beside its badge (item 4d). A single-case node renders one badge and
no label. Nodes whose cases carry no suffix render no label.

#### Scenario: Approval node links to its anchored case
- **WHEN** a record anchors to Taipei case 09804142
- **THEN** that node's 北 badge opens `r_progress_detail.aspx?case_id=09804142` in a new tab

#### Scenario: Current node links to the national view
- **WHEN** the project has a national view URL
- **THEN** the 現況 node's 國 badge opens the twur view page in a new tab

#### Scenario: A view-verified case's node links to the national view (303 shape)
- **WHEN** 北投區-關渡段二小段-303's `links.view_verified_case_ids` contains 10105152 and
  10803151, the project's twur URL is view/621, and nodes 829 and 669 anchor those cases
- **THEN** nodes 829 and 669 each carry the 國 badge opening view/621 in a new tab
- **AND** node 5 (現況， anchored 11505020, not view-verified, not the title's 案名) carries
  NO 國 badge — the 現況 rule is retired by national-badge-by-registration; a node
  qualifies only through the view page naming it

#### Scenario: A node qualifying both ways renders one badge
- **WHEN** the 現況 node's anchored case is also listed in `view_verified_case_ids`
- **THEN** the node renders exactly one 國 badge

#### Scenario: A node whose case is not view-verified gains no badge
- **WHEN** a non-current node's anchored case is absent from `view_verified_case_ids`
- **THEN** the node carries only its 北 badge

#### Scenario: The viewer reads the resolved field, not a matcher
- **WHEN** the payload marks a node `national_badges: true`
- **THEN** the node renders exactly one 國 badge
- **AND** a node the payload does not mark renders none, even when a national
  label's date matches its date

#### Scenario: Link section hidden by default, available for debugging
- **WHEN** the detail pane renders
- **THEN** no 相關連結 list appears unless the user explicitly enables the 除錯 toggle, which reveals the full link list (with 案名 annotations) for debugging purposes

#### Scenario: A joined node renders one 北 badge per case
- **WHEN** a node anchors 10906101 (-A區) and 10906102 (-B區)
- **THEN** it renders two 北 badges, each linking its own case page
- **AND** each badge carries the case's area label (`[A區]` / `[B區]`)

#### Scenario: A single-case node renders one badge, no label
- **WHEN** a node anchors one case whose name carries no area suffix
- **THEN** it renders one 北 badge and no area label
