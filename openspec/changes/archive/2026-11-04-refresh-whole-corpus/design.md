# Design: refresh-whole-corpus

## Context

Actors: `scripts/refresh_whole_corpus.py` (the new driver),
`urtpe.links.refresh_project` (the standing per-project refresh: parcel
search, per-case milestones + headers, status re-derivation, the §8-gated
view absorb), `urtpe.lock.SingleWriterLock`, `urtpe.coverage.coverage_guard`,
and the emitted payload (`viewer/projects.data.js`, read for keys and anchor
search keys, written once at the end).

Flow today: `refresh_awaiting_caches.py` selects the caches whose cases await
an approval and refreshes those. Everything else froze at first cache: 628
of 726 caches had no `case_headers` (S0's count), the view absorb never ran
for most (C2), and a newly filed case on a fully-approved project is
invisible (B1).

## Decisions

### D1 — Slices under the lock, a checkpoint between slices

The driver slices the sorted project list (about 100 per slice — the user
decision 2026-11-04). Each slice: take the lock, refresh its projects, write
`data/.link_cache/.refresh_checkpoint.json` `{last_pid, finished: [...]}`
with the cache writes, release the lock. A re-run skips finished slices
(the checkpoint is the resume point); `--slice N` re-runs one slice.

### D2 — Emission once, after the last slice

The driver never writes `projects.json` or `viewer/projects.data.js`. After
the last slice (the checkpoint covers every payload project), the operator
runs the standing `python -m urtpe.cli --from-js viewer/projects.data.js -o
data --links` — the same emission path every other change used, so the
emission-fault check and the coverage guard run exactly once over the final
state.

### D3 — Change detection: one cheap signal per source

Per project, in order:

1. **National page**: the cached `view.html`'s 資料更新日期 vs the live page's
   (one request). Later → re-absorb (the standing view absorb). Same/absent
   → skip the absorb's fetch (the parcel search still runs).
2. **City parcel search**: the standing search (one request); a new case id
   or a changed `schedule` marks the project "city moved".
3. **Case headers**: `get_project168_top` per case (one request each);
   compare `NAME`, `uro_chk_date`, `uro_chk_date2` with the cache. A finished
   case (schedule 已完工 / 完成成果備查, or a 使照核發日期 present) skips the
   header fetch unless step 1 or 2 moved the project.

Every skip is counted: the report prints `{skipped_unchanged, fetched, failed}`
per source. "Not fetched because unchanged" is a first-class outcome, never
indistinguishable from "fetched and empty".

### D4 — The refresh calls refresh_project

The driver does not re-implement the per-project logic: it calls
`refresh_project(cache_dir, pid, search_key=...)` (the standing adapters),
then runs `resolve_node_cases` for any node the payload's date matcher
cannot place (S10's resolver, reusing the sweep's probe memo), writing the
finds into the cache. B1/B5/B6/C2/§4.1 all ride on the one call.

### D5 — The coverage guard wraps each slice

The §12 #1 guard aborts on a flag drop or a total re-key before the damage
spreads: each slice runs under `coverage_guard(cache_dir, payload_keys)`.

## Consequences

- ~2,000–2,500 requests (the board's estimate: 622 view pages probed by
  date, ~1,000 unfinished cases' headers, the parcel searches).
- The corpus converges: every cache gains `case_headers`, the view-verified
  list, re-derived statuses; B1's new-case discovery covers every project.
- The next gazette's emission reads the converged state.
