# Parked Work

Decided during exploration of `robust-gazette-ingestion`, deliberately not built here.
Each item records its blocking prerequisite and the trigger that would bring it back
into scope. Measurements were taken from the three gazettes in `C:\Users\jeffw\Downloads`
(`1150820`, `1150827`, `1151002`) and are not recoverable from git history.

## 1. Migrate the 5 moved `project_id` cache directories

**Blocked on:** `gazette-reconciliation` shipping (needs the before/after identity sets).

Switching to a table-based reader changes 5 of 709 `data/.link_cache/<project_id>/`
directory names. Measured by running `cleanse_all` + `merge` both ways on `1150827`
and diffing the resulting identity sets:

```
table parser : 712 families
coord parser : 713 families
identical project_id sets: 704 of 709      (2 gained, 3 lost)
```

All 5 are degenerate cases where the positional reader was already broken — notably one
whose identity carries no parcel number at all (`內湖區-東湖段一小段-地號等?筆`) and one
carrying a `-2` collision suffix (`大同區-市府段二小段-220-2地號等54筆-2`).

**Needs:** an alias table mapping former identity → current identity, applied at
cache-load time rather than by renaming directories on disk (renaming would break the
single-writer rule and any in-flight run).

**Trigger to un-park:** reconciliation reports a non-empty `moved_project_ids` set on
the first production ingestion.

## 2. Portal sync / event cascade

**Blocked on:** reconciliation diff providing a trustworthy per-gazette change set.

`docs/sync_architecture.md` §3 already designs this (PDF as heartbeat, portals as
decoration, liveness-based refresh policy). Three findings from this exploration revise it:

- **The 28 h national-portal sweep is the scarce resource.** It should consume the
  reconciliation diff — projects that gained a node — rather than re-scan all projects.
  Measured baseline: 709 projects, 292 with portal coverage, 58 with 使用核發.

- **`coverage.py` cannot see a total re-key.** `coverage.py:46-59` computes
  regressions over `set(before) & set(after)`. When every project identity changes,
  that intersection is empty, so `regressions = {}` and the guard passes — while every
  cache is orphaned. The 2026-08-24 incident (four concurrent writers, 47 caches wiped)
  has the same shape: a check that cannot observe the failure it exists to catch.
  `gazette-reconciliation` reports total re-keying as a distinct outcome (design D6);
  this guard needs the same treatment.

- **The recno model in `sync_architecture.md` §2 no longer holds.** It argues from the
  `1150820 → 1150827` transition, where all 1,421 matched records shifted by exactly
  `+5`. The `1150827 → 1151002` transition is **not affine**:

  ```
  old#1    → +8        old#300   → +5
  old#100  → +6        old#1000  → −13   ◄── moved UP past 13 records
  old#1420 → +10
  ```

  Date-order violations fell from 9 to 1 between the two publications: the old export was
  insertion-ordered (block-insert per gazette batch), the new one re-sorts history by
  核定日期. So recno is a coordinate in a mutable list, not a rank with an offset. The
  document's conclusion (`project_id`/land-core are the only cross-PDF keys) stands and
  is reinforced; its supporting arithmetic does not. This doc should be revised.

**Trigger to un-park:** reconciliation is trusted in production and has produced a
reliable change set across at least two consecutive ingestions.

## 3. Whether the city re-sorts by date permanently

**Blocked on:** observing further publications. Not answerable from the two transitions
available.

Whether the 1151002 date-sort is permanent determines whether the "block-insert per
gazette batch" mental model in `openspec/config.yaml` should be retired outright. It
does not block any work here — content-based reconciliation (design D6) is correct under
either ordering — but it changes what a future reader should assume about the list.

**Trigger to un-park:** two or more further publications ingested; count date-order
violations per publication as the indicator.

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

**Blocked on:** `gazette-archival` landing first.

`docs/sync_architecture.md` §5 item 6 proposes `data/sync_state.json` with per-source
last-sync timestamps and a per-project phase snapshot. `gazette-archival`'s index is a
natural first half of that: publication date, ingest timestamp, record count, reader
version. Extending it with portal-side state is deferred until the portal sync work in
item 2 is un-parked, so the manifest is designed once rather than twice.

**Trigger to un-park:** item 2 begins.