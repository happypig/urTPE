## Why

Two city case ids that the gazette holds never reach the payload, because the
pipeline has exactly one source of case ids and that source does not index
them.

**The city's parcel search does not index `10708311` or `11412011`** (live
probe, 2026-11-05, `scripts/probe_sibling_search.py`): searching 南港段四小段 /
566 returns `10708312` only; searching 玉成段二小段 / 166 returns `10901211`,
`10901212` and `11412012`, not `11412011`. The guard is not the cause — both
ids are absent with and without it.

The consequence, measured on the 2026-10-15 payload: **16 nodes in 11
projects** carry the flag `節點未能對應平台案件`.

**`10708311` was found once, then lost.** The stranded cache directory
`南港區-南港段四小段-566地號等6筆` (written 2026-11-04) holds
`city_case_ids ['10708312', '10708311', '10006032']`, with full milestones for
`10708311` (核定 2019-11-20) and `10006032` (核定 2016-02-25). The earlier find
came from the all-parcel search step of `resolve_node_cases`.

**The alias was never consulted.** `data/project_aliases.json` maps the live
id `…等1筆` to that old id. But `resolve_cache_dir`
(`urtpe/links.py:1581-1591`) returns the live id's own directory whenever it
exists — and a stub exists there. So the alias is never read, and the richer
directory is shadowed. This is the D6 Finding 5 shape on a different project:
**a stub write is the root cause**, and a fix that merges an aliased
directory into a fresh stub, instead of shadowing it, stops the loss
recurring.

Measured over all 11 alias pairs, the shadowing loses data in **one** project,
and it accounts for **2 of the 16** unplaced nodes (node 744 by the
2019-11-20 approval, node 1063 by the 2016-02-25 approval).

**`11412011` is in no cache at all** — stranded or live — so it still needs a
second id source.

## What Changes

- **(a) An offline cache merge.** The stranded
  `南港區-南港段四小段-566地號等6筆` directory's case ids and per-case
  milestones are merged into the live `…等1筆` directory. No network, no new
  id source. Nodes 744 and 1063 gain their cases.
- **(b) A second id source.** The city's 168 list
  (`Get_project168.ashx`) names case ids the parcel search does not index.
  Each id that the search did not return SHALL be confirmed by its own case
  header (`get_project168_top.ashx`) before it enters `city_case_ids`. The
  header confirms the case exists and names its 案名; a header that reads
  nothing is not a confirmation.
- **(c) A stub no longer shadows an aliased directory.** When a project's
  current cache directory is a stub and an aliased directory holds more, the
  two are **merged** — the stub's own content wins on a conflict, the aliased
  directory's extra content is added — instead of the aliased directory
  being ignored.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `taipei-case-discovery`: a second id source, confirmed by the case header.
- `cache-freshness`: a cache directory is resolved by merging an aliased
  directory into the current one, not by shadowing it.

## Impact

- `urtpe/links.py` — the cache resolution (merge, not shadow) and the second
  id source in the refresh's search step.
- `data/.link_cache/南港區-南港段四小段-566地號等1筆/` — the merge (a).
- `data/projects.json`, `viewer/projects.data.js` — one re-emit.
- The single-writer rule applies to the cache write.
