# Design: add-virtual-node-ordering-and-chain

## Context

Actors: planners reading the history graph; the viewer's `renderDetail`
(app.js) that orders cluster members and draws edges. Domain events: platform
application attempts (case_ids encode application era — YY序號, e.g.
09506200=2006 → 09811141=2009 → 10201171=2012) that have no gazette record
render as virtual nodes; 29 families hold ≥2 of them on one `node_date`
(census via `viewer/projects.data.js`, 2026-08-31). System boundary: viewer
only (`viewer/app.js` cluster member sort + edge rendering) — no pipeline
changes; `graph.py`'s revision edges are untouched.

Prior art: the decision + amendment are recorded in the viewer change
`viewer-enhancements-and-orphan-case-anchoring` `design.md` D12 (2026-08-31)
and mirrored in `docs/facts_2_portals.md` §5 and
`docs/sorting_connecting_rules.md` §3.3/§6.

## Goals

- Deterministic, load-independent row order for same-date virtual nodes
  (case_id ascending = application-attempt order).
- Attempt-succession chain edges between consecutive virtuals in a cluster.

## Non-Goals

- No pipeline change (edge duplication guard handled viewer-side only).
- No cross-stage chaining (概要/計畫 same-day pairs stay unchained).
- No change to cluster band/chip rendering or the ±1-day band rule.

## Decisions

- **D1 — effective-case_id comparator**: cluster member comparator gains a
  dated-member tie layer keyed by effective case_id ascending (real →
  `links.taipei[0]`, virtual → `case_id`, case-less real → `""` first); the
  區段 locale ordering applies only between equal-or-empty keys. Supersedes
  the blanket "real before virtual" for dated members. Alternative considered:
  keep "real first" — rejected: it hides attempt order (a withdrawn earlier
  attempt should read before the later gazette approval).
- **D2 — chain edges viewer-side**: consecutive virtuals in a cluster connect
  via a dashed `virtual`-style edge along the row; guard: only
  virtual-involved consecutive pairs (never real↔real — those already carry
  `graph.py` revision edges); never across clusters. Alternative: emit chain
  edges from graph.py — rejected: virtual positions exist only in the viewer
  layout, not the pipeline graph.
- **D3 — acceptance anchors**: 吉林段三小段1021 (attempt pair ordering +
  chain) and 吉林段四小段676 (cross-stage non-chaining) are the live fixtures
  for visual verification.

## Open Questions

- Edge style token: reuse `class="edge"` with a `virtual` modifier vs a new
  `virtual-edge` class — decide at implementation (CSS naming only).
