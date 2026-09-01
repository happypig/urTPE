# Proposal: add-virtual-node-ordering-and-chain

## Why

Planners reading the graph see virtual nodes (platform application attempts
with no gazette record) rendered in an **unspecified order**: 29 families carry
≥2 virtual nodes on one `node_date` (attempt twins like 吉林段三小段1021's
09902261/10201171 — resubmitted 概要 pairs; 概要+計畫 same-day pairs like
吉林段四小段676; three-stage same-day sprees like 吉林段一小段717). The
cluster tie-break chain (real first → dated first → 區段 locale) leaves
same-date/same-stage virtuals tied, and JS sort stability resolves them by
**platform search-response order** — load-dependent (the view/75 lesson:
candidate order shifts with portal load) and unspecified. Virtual nodes also
carry **no edges at all**, so an attempt pair (withdrawn → resubmitted)
renders as two disconnected dashed circles with no visual succession.

## What Changes

- **Viewer (cluster sort)**: order cluster members row-by-row by **effective
  case_id ascending** — a real node's key is its anchored case_id
  (`links.taipei[0]`), a virtual node's key is its own `case_id`; real nodes
  without an anchored case carry an empty key and sort first. This supersedes
  the blanket "real before virtual" comparator for dated members and makes the
  order equal application-attempt order (case_ids encode the application era).
- **Viewer (chain edges)**: consecutive virtual nodes within a cluster are
  chained by a **dashed virtual revision edge** directed along the row
  (earlier attempt → later) — the attempt-succession chain. Cross-stage
  same-date pairs sit in different clusters and stay unchained (parallel
  tracks are not revisions). Only virtual-involved pairs gain edges;
  real↔real pairs remain covered by `graph.py`'s revision edges (no
  duplicates).
- Prior decisions recorded in the viewer change's `design.md` D12 (+amendment)
  are the design source; this change implements them.

## Capabilities

### New Capabilities
<!-- none — this change modifies an existing capability -->

### Modified Capabilities
- `virtual-milestone-nodes`: the stage-cluster ordering requirement gains the
  case_id tie-break layer (MODIFIED), and a chain-edge requirement is ADDED.
