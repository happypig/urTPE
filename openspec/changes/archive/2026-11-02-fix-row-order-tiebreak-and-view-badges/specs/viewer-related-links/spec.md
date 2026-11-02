# viewer-related-links Delta

## MODIFIED Requirements

### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place: each approval node with an anchored Taipei case SHALL expose its 北 badge as a hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge hyperlink to the project's national view page when one exists; **any approval node whose anchored case is listed in `links.view_verified_case_ids` — the cases the project's own national view page names in 相關連結 — SHALL also expose the 國 badge**, because the portal itself asserts that case belongs to the unit and the node should lead to the page that names it; and each construction-event node SHALL label as a hyperlink to its source portal — Taipei case page (pink) when Taipei-sourced, national view page (green) when national-mapped. A node qualifying both ways (view-verified and 現況) SHALL render exactly one 國 badge. The standalone 相關連結 section SHALL be retired behind an explicit debug toggle that defaults to hidden.

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
- **AND** node 5 (現況， anchored 11505020, not view-verified) keeps its 國 badge via the
  existing 現況 rule

#### Scenario: A node qualifying both ways renders one badge
- **WHEN** the 現況 node's anchored case is also listed in `view_verified_case_ids`
- **THEN** the node renders exactly one 國 badge

#### Scenario: A node whose case is not view-verified gains no badge
- **WHEN** a non-current node's anchored case is absent from `view_verified_case_ids`
- **THEN** the node carries only its 北 badge

#### Scenario: Link section hidden by default, available for debugging
- **WHEN** the detail pane renders
- **THEN** no 相關連結 list appears unless the user explicitly enables the 除錯 toggle, which reveals the full link list (with 案名 annotations) for debugging purposes
