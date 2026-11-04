# Proposal: hide-superseded-orphans (S6 — B2)

## Why

A superseded case (the city re-filed it under a new id; the cache records
`superseded_by`) keeps an orphan node with an empty `node_date` in the graph.
Measured (2026-11-04, at the wave-2 payload): 4 of 5 superseded cases carry
such a node — 10410012 (吉林705-3), 10806141 (虎林38), 11009142 (雅祥227-4),
11211211 (立農163-2); the 5th (萬華894's 11010191) anchors by its approval
date and is fine. The node shows a stage and a [無]-shaped schedule with no
date: the graph tells the reader a process exists that the city has replaced.

## What changes

- `attach_links_to_projects`'s orphan gate: an orphan case recorded in
  `superseded_by` SHALL NOT become an orphan node — its successor's case
  carries the live history (the successor itself anchors by date or renders
  as its own named orphan). The gate keeps the case in `city_case_ids`
  (append-only; nothing else keys on the list) — only the node is withheld.
- The viewer needs no change: the node simply stops existing.

## What does not change

- The standing refresh's supersede detection (the cache's `superseded_by`
  is the evidence, untouched).
- Every other orphan path (name-similar, view-verified, attribution,
  twin-bridge) is untouched.

## Capabilities

### Modifications

- `orphan-case-anchoring`: MODIFIED — the "Ghost node for landcore-similar
  orphan case_ids" requirement gains the superseded-case exclusion.

## Risks

- A superseded case whose successor never landed in the cache: the node
  disappears while the successor's node may not exist yet. The supersede
  detection requires the successor to be a cached case with the same header
  case name (cache-freshness's rule), so the successor is always in the
  same cache — its node exists or the family has no row for it (the 擬訂
  row may predate the gazette window); the run report names any such cache.
