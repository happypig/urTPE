# Design — fix-graph-timeline-order

## Context

The graph layout (`viewer/app.js`, `renderDetail`'s SVG block) assembles a
`timeline` array: approval members sorted by `effectiveCaseKey`, execution events
from `buildConstructionChain` sorted by string date, spliced before the first
member whose date is later. Two facts defeat it: `buildConstructionChain` emits
exec dates as `2023/04/27` (slash) while node dates are ISO, so the string
comparison orders `/`-dates after every `-`-date of the same year; and the
y-pitch mapping draws the array with the newest member at the smallest y
(measured live: node 1/2026 at y=371, node 453/2022 at y=540). Dataset-wide:
316 of 490 construction-bearing projects have exec dates between two approvals —
all currently mis-ordered.

## Goals / Non-Goals

Goals:

1. Exec dates normalised to ISO at `buildConstructionChain` exit.
2. The interleave comparison runs on ISO strings (chronological).
3. The drawn order ascends top-to-bottom.
4. Display of exec dates keeps the established form; the payload stays verbatim.

Non-Goals:

- Re-anchoring the stale provenance (the 669-bindings re-emission, recorded in
  `docs/inspection.md`).
- Touching the record table, the list, or any non-graph layout.
- Changing `compareClusterMembers` / the D12 case_id order *within* a stage
  cluster (that order is spec'd separately; this change orders the timeline's
  rows, not the members' internal sequence).

## Decisions

### D1 — Normalise in `buildConstructionChain`, not at the comparison site

`buildConstructionChain` already converts ROC dot dates to slash-western; extend
that normalisation one step to full ISO (`2023/04/27` -> `2023-04-27`) so the
event's `date` field is ISO from the moment it exists. The interleave code then
needs no change - its string comparison becomes chronological automatically.
Alternative rejected: normalising inside the sort comparator - three comparison
sites each carrying a conversion is the kind of drift the `ymd` bug taught this
repo to avoid.

### D2 — Display converts from ISO at the label site

The row label renders `建照核發日期：2023/04/27` today. After D1 the field is
ISO; the label site applies the existing `fmtDate` reverse form (ISO -> the
established slash display) so the visible text is unchanged for existing users.
Alternative rejected: displaying ISO - changes what users read for no spec'd
reason (the delta requires "the viewer's established rendering").

### D3 — Ascending draw: fix the y-assignment, not the array order

The `timeline` array is built oldest-member-first; the y-pitch assigns row 0 the
smallest y. Measured output has the newest at the smallest y, meaning the pitch
or the SVG mapping inverts the array (or the array is built newest-first via the
case-key sort). The fix: make the drawn order match the array order (ascending),
by assigning y in array order - first row, smallest y. The exact inversion point
is found by the red test before touching code. Alternative rejected: sorting the
array descending to compensate for an inverted draw - that would re-break the
interleave the moment the inversion is also fixed.

### D4 — The red test drives a purpose-built fixture through the real smoke harness

The fixture (already used by `viewer-stage-chip-coverage`, rebuilt from the real
payload) gains a project whose exec dates fall between two approvals - exactly
the 336 shape. A Node probe through the smoke harness's DOM stub captures the
rendered SVG row order top-to-bottom and asserts: 2022 node, 建照, 開工, 2026
node. Structural source tests pin D1 (ISO in `buildConstructionChain`) and the
pitch direction.

## Risks / Trade-offs

- **Changing the graph's reading direction.** Users accustomed to newest-at-top
  will see oldest-at-top. The delta names the ascending order; the record table
  and every list in the app already ascend. Accepted.
- **The `while` splice uses `<` on ISO strings - safe once D1 lands.** Leap-day
  and padded-month edges are covered by the fixture's dates.

## Open Questions

(none)
