## Why

A latent bug of the same class as the already-fixed `ymd` bug: `stage_index` is
**read** on every `--from-js` rebuild but never **written** into the emitted
nodes. `urtpe/cli.py:126` and `scripts/run_links_from_js.py:52` read
`node["stage_index"]` with a `-1` default; `build_project_graph` never emits the
key; so on a rebuild from emitted state every node loads as `-1`, and the
section-branch grouping at `urtpe/graph.py:108`
(`stage_groups.setdefault((r.stage_index, r.track), ...)`) collapses every stage
of a track into one group — 區段 branch edges can never form on a rebuild.
Verified on the payload: 0 section edges, 1 node corpus-wide carries
`area_section`. Latent today; fires the first time the city publishes 甲/A/B區段
rows — and when it fires, the graph silently loses the 区段 dimension, the exact
silent-corruption shape the domain invariants warn about.

The maintainer affected: anyone rebuilding from emitted state (the `--from-js`
path the AGENTS.md trap section calls "input and output"), and the viewer, whose
区段 lane grouping depends on the edges.

## What Changes

- `build_project_graph` emits `stage_index` on every node.
- `_load_projects_from_js` and `scripts/run_links_from_js.py` derive
  `stage_index` from the stage text when the emitted key is missing, so every
  already-deployed `projects.data.js` repairs on load (the pattern of the `ymd`
  fix documented at `urtpe/cli.py:83`).
- Round-trip guarantee: emit → load → emit is lossless for `stage_index`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `history-graph`: the emitted node payload SHALL carry `stage_index`, and a
  rebuild from emitted state SHALL reconstruct section-branch edges identically
  to the original build. (The existing "Node order survives a rebuild from
  emitted state" requirement covers ordering; this adds the edge-identity
  guarantee.)

## Impact

- `urtpe/graph.py` — `build_project_graph` emits the key.
- `urtpe/cli.py` — `_load_projects_from_js` derives on load.
- `scripts/run_links_from_js.py` — same derivation.
- No emission-format break: the new key is additive; the viewer ignores unknown
  keys.
