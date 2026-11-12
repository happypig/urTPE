# Proposal: joined-node-section-callouts

## Why

30 nodes carry 2+ city case ids; 28 of them are area splits (the city filed
-A區 and -B區 cases for one approval, and the pipeline binds both to the one
recno — the 民生134-6 / 敦化363-1 shape). The list shows one row; the graph
shows one node. But:

- the 北 badge links **only `cases[0]`** (`viewer/app.js`) — the second case
  is invisible on the graph;
- the node's implementation snapshot takes the **first** case with a payload
  (`urtpe/links.py`'s per-record loop breaks on first hit), so 敦化363-1
  node 537 shows -A區's 使照 (2025-04-29) and hides -B區's (2025-05-06,
  cached at `implementation["10906102"]`);
- a callout value can wrap under the 160 px gutter cap (739 of 1,426 callouts
  on the 675-project payload).

**The user's rules** (items 4, 4a–4d, 5; decisions 2026-11-12): the cases are
already joined on the recno — the badge covers both, the callout shows both
per section with the differences visible, the [A區]/[B區] label renders
beside the badge AND the callout sections, and a callout row never wraps —
the gutter grows to the content.

## What Changes

- **The payload carries implementation keyed by case id** on joined nodes
  (decided: 在負載中按案例發出): the per-record snapshot gains
  `implementation_by_case` when the node anchors 2+ cases with payloads. The
  single `implementation` snapshot stays (the D5 pick — existing consumers
  unchanged).
- **The viewer renders one callout box per section** on a joined node, with
  the [A區]/[B區] label on the box header; the diff marker compares within a
  section across nodes.
- **The 北 badge renders one badge per case**, each linking its own case
  page, with the area suffix label beside it.
- **The callout never wraps**: `CALLOUT_GUTTER_CAP` goes; the gutter takes
  the widest box; the D2 wrap-height model (`implValueLines`, the two-line
  case) retires — the height model exists to predict wrapping that no longer
  happens.
- The 14 projects whose area cases sit on distinct recnos are not this
  finding: their per-node badges already follow their own cases.

## Capabilities

### Modified Capabilities

- `case-record-join`: the joined-node emission requirement — a node anchoring
  2+ cases with implementation payloads carries `implementation_by_case`.
- `viewer-related-links`: the node badge requirement — one 北 badge per
  anchored case, each linking its own page, with the area suffix label.
- `history-graph`: the callout requirement — per-section boxes on joined
  nodes; one line per row (the gutter takes the widest box; the cap and the
  wrap-height model are retired).

## Impact

- Code: `urtpe/links.py` (the per-case snapshot), `urtpe/cli.py` (the loader
  round-trip), `viewer/app.js` (the badges, the area labels, the per-section
  callouts, the sizing), `viewer/app.css` (the section header).
- Payload: `implementation_by_case` on 30 nodes (small); one re-emit.
- Tests: the per-case emission pinned in pytest; the harness's callout
  checks re-targeted (no-wrap by construction).
