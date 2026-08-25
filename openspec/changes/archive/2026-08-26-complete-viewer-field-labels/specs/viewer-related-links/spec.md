# viewer-related-links — Delta: links migrate onto the graph

## REMOVED Requirements

### Requirement: Render a 相關連結 section in the detail pane

**Reason**: the standalone link list is superseded by outbound links living
directly on the graph — every portal-sourced node labels with a hyperlink to
its source (Taipei case detail page / national view page), which removes the
extra section while keeping every destination reachable where the data sits.

**Migration**: readers find case links on the approval nodes' 北 badge and on
the construction-event labels; the national view link sits on the 現況 node's
國 badge. No data loss — the same URLs, attached to the nodes they describe.

### Requirement: Embed milestone timelines inline

**Reason**: milestone timeline cards render independently of the removed link
section (unchanged behavior, see `viewer-milestone-timeline`); only their
co-location with the link list is dissolved.

**Migration**: none — the cards keep rendering in the detail pane as before.

## ADDED Requirements

### Requirement: Graph nodes carry outbound portal links

The viewer SHALL make portal-sourced graph elements reachable in place:
each approval node with an anchored Taipei case SHALL expose its 北 badge as a
hyperlink to that case's detail page; the 現況 node SHALL expose an 國 badge
hyperlink to the project's national view page when one exists; and each
construction-event node SHALL label as a hyperlink to its source portal —
Taipei case page (pink) when Taipei-sourced, national view page (green) when
national-mapped. The standalone 相關連結 section SHALL be retired behind an
explicit debug toggle that defaults to hidden.

#### Scenario: Approval node links to its anchored case
- **WHEN** a record anchors to Taipei case 09804142
- **THEN** that node's 北 badge opens
  `r_progress_detail.aspx?case_id=09804142` in a new tab

#### Scenario: Current node links to the national view
- **WHEN** the project has a national view URL
- **THEN** the 現況 node's 國 badge opens the twur view page in a new tab

#### Scenario: Link section hidden by default, available for debugging
- **WHEN** the detail pane renders
- **THEN** no 相關連結 list appears unless the user explicitly enables the
  除錯 toggle, which reveals the full link list (with 案名 annotations) for
  debugging purposes
