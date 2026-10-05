# Parked Work

Decided during exploration of `robust-gazette-ingestion`, deliberately not built here.
Each item records its blocking prerequisite and the trigger that would bring it back
into scope. Measurements were taken from the three gazettes in `C:\Users\jeffw\Downloads`
(`1150820`, `1150827`, `1151002`) and are not recoverable from git history.

**Figures in this file were measured with the reader as it stood before tasks 14.1–14.7.**
That reader absorbed a page-number footer into a 地號 cell and truncated long cells at
the row height. Any count here derived from those reads is superseded by the corrected
measurements given with each item.

## 1. ~~Migrate the moved `project_id` cache directories~~ — RESOLVED here

**RESOLVED.** `gazette-reconciliation` shipped, and the alias mechanism was a
prerequisite for landing it rather than a follow-up, so it was built in this change:
`scripts/build_project_aliases.py` emits `data/project_aliases.json`, applied at
cache-load time in `links.load_project_cache` rather than by renaming directories on
disk, which would break the single-writer rule and any in-flight run.

Measured against the corrected reader, migrating three publications strands **2** of 709
directories and needs **0** aliases with **0** ambiguous pairs. Both stranded
directories are the projects whose sole record the publisher truncated — so no identity
pairs them, and none should be invented. The originally recorded "5 moves / 704 of 709
unchanged / 5 degenerate ids" came from the old reader and is withdrawn.

The un-parking trigger was met, and the answer turned out to be that the problem was
almost entirely self-inflicted by the reader rather than by identity churn.

## 2. Portal sync / event cascade

**Blocked on:** reconciliation diff providing a trustworthy per-gazette change set.

`docs/sync_architecture.md` §3 already designs this (PDF as heartbeat, portals as
decoration, liveness-based refresh policy). Three findings from this exploration revise it:

- **The 28 h national-portal sweep is the scarce resource.** It should consume the
  reconciliation diff — projects that gained a node — rather than re-scan all projects.
  Measured baseline: 709 projects, 292 with portal coverage, 58 with 使用核發.

- **`coverage.py` cannot see a total re-key.** `coverage.py:51` computes
  regressions over `set(before) & set(after)`. When every project identity changes,
  that intersection is empty, so `regressions = {}` and the guard passes — while every
  cache is orphaned. The 2026-08-24 incident (four concurrent writers, 47 caches wiped)
  has the same shape: a check that cannot observe the failure it exists to catch.
  `gazette-reconciliation` reports total re-keying as a distinct outcome (design D6);
  this guard needs the same treatment. **This is no longer a hypothesis.** During this
  change the orphaned set moved 27 → 2 without the guard noticing either transition, and
  `coverage_guard` records `lost` but never raises on it. It remains unfixed and is the
  most valuable thing in this file.

- **The recno model in `sync_architecture.md` §2 no longer holds.** It argues from the
  `1150820 → 1150827` transition, where all 1,421 matched records shifted by exactly
  `+5`. The `1150827 → 1151002` transition is **not affine**: records move in both
  directions, one measured case moving up past 13 others. So recno is a coordinate in a
  mutable list, not a rank with an offset. The document's conclusion (`project_id`/land-core
  are the only cross-PDF keys) stands and is reinforced; its supporting arithmetic does
  not, and it should be revised.

**Trigger to un-park:** reconciliation is trusted in production and has produced
a reliable change set across at least two consecutive ingestions.

## 3. Whether the city re-sorts by date permanently

**Blocked on:** observing further publications. Not answerable from the transitions
available, and **not answerable from the two that exist** — both were measured on the
contaminated read described above.

Whether the `1151002` date-sort is permanent determines whether the "block-insert per
gazette batch" mental model in `openspec/config.yaml` should be retired outright. It
does not block any work here — content-based reconciliation (design D6) is correct under
either ordering — but it changes what a future reader should assume about the list. The
often-quoted "date-order violations fell from 9 to 1" is **withdrawn**: it cannot be
re-derived until `1151002` is read by the corrected reader.

**Trigger to un-park:** two or more further publications ingested with the corrected
reader; count date-order violations per publication as the indicator. Re-measuring
`1151002` would also settle it sooner.

## 4. Gazette fetching on a schedule

**Blocked on:** nothing technically; needs a decision on automation and politeness.

The gazette page (`uro.gov.taipei/cp.aspx?n=963B15B39CADB94E`) exposes a 資料更新
timestamp, a 資料維護 attribution, and a link to the newest PDF only. Older gazettes are
unreachable — the file path is UUID-based
(`www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/c5ff4f68-….pdf`), so the city
serves one version at a time. This is the argument for D8: archives must be local.

Whether the page honours conditional requests (`ETag` / `If-Modified-Since`) is untested
and determines whether polling is cheap or requires downloading ~2 MB per check. Observed
publication cadence in the sample: roughly 2-4 approvals per week, with the PDF published
weekly to fortnightly.

**Trigger to un-park:** `gazette-archival` and `gazette-reconciliation` are both in
production and stable, so that an unattended run cannot overwrite a bad dataset.

## 5. `gazette_index` as a sync manifest

**Blocked on:** item 2 beginning. The `gazette-archival` half of this landed in
`robust-gazette-ingestion` — an append-only index outside the working tree, carrying
publication date, ingest timestamp, record count and reader version, with SHA-256 on
each member. Extending it with portal-side state is still deferred so the manifest is
designed once rather than twice.

**Trigger to un-park:** item 2 begins.