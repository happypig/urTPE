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

**Blocked on (was):** reconciliation diff providing a trustworthy per-gazette change set.
That blocker is gone — the change set is durable output. **Blocked on now:** nothing
structural. What is missing is a *consumer*: no code reads `change_sets/*.json`, so the
cascade's input exists and its sweep does not. A second gate also stands, and it is
measured rather than asserted: see the trigger below.

`docs/sync_architecture.md` §3 already designs this (PDF as heartbeat, portals as
decoration, liveness-based refresh policy). Three findings from this exploration revise it:

- **The 28 h national-portal sweep is the scarce resource.** It should consume the
  reconciliation diff — projects that gained a node — rather than re-scan all projects.
  Measured baseline: 709 projects, 292 with portal coverage, 58 with 使用核發.
  **The change set this needs now exists as durable output**, written per publication by
  `gazette-ingest-cadence`; before that it was console text that no later run could read.

- ~~**`coverage.py` cannot see a total re-key.**~~ **RESOLVED** in `no-silent-data-loss`.
  `urtpe/coverage.py` now reports `total_rekey` as its own outcome and `coverage_guard`
  raises on it. Verified against a wholesale re-key: the guard raises, where it previously
  computed regressions over `set(before) & set(after)`, found that intersection empty, and
  passed while every cache was orphaned. The same blind spot, and the reason this item was
  called the most valuable thing in this file, applied to reconciliation itself — which is
  why a total re-key is now a requirement of `gazette-reconciliation` too. The portal
  cascade itself remains unbuilt.

- **The recno model in `sync_architecture.md` §2 no longer holds.** It argues from the
  `1150820 → 1150827` transition, where all 1,421 matched records shifted by exactly
  `+5`. The `1150827 → 1151002` transition is **not affine**: records move in both
  directions, one measured case moving up past 13 others. So recno is a coordinate in a
  mutable list, not a rank with an offset. The document's conclusion (`project_id`/land-core
  are the only cross-PDF keys) stands and is reinforced; its supporting arithmetic does
  not, and it should be revised.

**Trigger to un-park:** reconciliation is trusted in production and has produced
a reliable change set across at least two consecutive ingestions.

**Status: 0 of 2 met.** `gazette-ingest-cadence` persisted the change set, but the live
archive at `D:\project\urtpe-gazettes\` has no `change_sets/` directory yet — every
ingestion on record was a first ingest with no predecessor, so `comparable: false`. One
comparable comparison has been produced, against a scratch archive, and it is what sized
the work: `1150827 → 1151002` yields **8** project identities gained, against 77
candidates for a full re-scan. At the sweep's enforced 60–180 s between projects that is
roughly 13 minutes rather than the ~28 h politeness budget, so the cascade's premise holds
up — but one comparison is not two, and it is the sample that crosses a calendar switch
(roc → gregorian, 41 vanished, 18 re-dated), which is the least typical transition
available.

The first comparable reconciliation also required a fix this file did not anticipate.
`GazetteArchive.predecessor_of` required the incoming gazette to be *already archived*,
while `cli.py` resolves the predecessor before archiving the current one — so it returned
None on every ingestion and reconciliation reported "no comparison possible" against a
fully populated archive. Reconciliation had never actually compared two gazettes. Fixed in
`fd7ff89` with `tests/test_predecessor_lookup.py`. Worth recording because the trigger
above looked merely unmet when it was in fact unsatisfiable, and reading a parked trigger
as "not yet" rather than "not ever, as written" is how it survived that long.

## 3. Whether the city re-sorts by date permanently

**Blocked on:** observing further publications. Permanence still needs two more
publications; but the measurement this item said was impossible **has since been taken**.

This item recorded the often-quoted "date-order violations fell from 9 to 1" as
**withdrawn**, on the ground that it "cannot be re-derived until `1151002` is read by the
corrected reader". That reasoning was wrong in a way worth recording: the figure was
withdrawn for want of a read, not for doubt about the number. `1151002` has now been read
by the corrected reader, and **the figure stands: 9, 9, 1**.

| publication | dated records | departures | largest inversion |
|---|---|---|---|
| 1150820 | 1417 | 9 | 1820 days |
| 1150827 | 1422 | 9 | 1820 days |
| 1151002 | 1421 | **1** | 113 days |

The lone `1151002` departure is 編號 109 (2025-08-05) sitting above 編號 110
(2025-11-26): the same unit's 第二次 and 第三次 權利變換. So it is a **re-dated historical
row, not a failure to sort** — the publisher sorts by date and then edits history behind
itself. That is a partial answer rather than a full one: the sorting is real, and so is
the re-dating.

Two traps had to be cleared to get these numbers, and both produce a *healthy-looking*
result when missed:

- `1151002` repeats 編號 1 as a running page head on all 246 pages. A raw table scan reads
  1681 rows for 1436 records, and each head restates the newest date after an older row, so
  the departure count inflates from 1 to **246**.
- `1151002` publishes Gregorian dates (`2026/9/24`) where earlier publications use ROC. A
  single-calendar parser finds no dates and reports **zero** departures.

A metric that returns zero because it parsed nothing is indistinguishable from a metric
reporting a well-ordered publication, which is why the count is now stored beside its
denominator and marked unmeasurable when the denominator is too small. `gazette-ingest-cadence`
records the figure per publication, so the remaining question resolves itself as
publications arrive rather than needing a re-derivation.

**Trigger to un-park (still):** two or more further publications ingested with the
corrected reader. Half-met: the re-measurement that was said to "settle it sooner" is done,
and the trend is recorded per publication.

## 4. ~~Gazette fetching on a schedule~~ — BUILT in `gazette-ingest-cadence`

**Un-parked and built.** The politeness question is answered by measurement rather than by
judgement.

The item left two things open: whether the page honours conditional requests, and the
politeness decision. Probed against the live page on 2026-10-05:

| probe | result |
|---|---|
| page `ETag` | **absent** |
| page `Last-Modified` | **absent** |
| page `Cache-Control` | `no-cache` |
| page size | 86,586 bytes |
| page `資料更新` | `115-09-29 13:55` |
| newest gazette held | `2026-09-24` |
| PDF `ETag` | `"78d49422d74fdd1:0"` |
| PDF `Last-Modified` | `Tue, 29 Sep 2026 05:55:30 GMT` |
| SHA-256 of served PDF | `5066b108…8a92a` |
| SHA-256 of archived `2026-09-24` | `5066b108…8a92a` — **identical** |

So conditional requests are unavailable on the page, and a poll costs its full 86 KB.
That is affordable at weekly cadence, and it is not the interesting finding.

**The important finding is that `Last-Modified` cannot detect a new gazette.** The page
advertised `115-09-29` while the newest gazette held is `2026-09-24`, and the served PDF
was byte-identical to the archived copy: the city **re-uploads the same document under a
later timestamp**. A poller keyed on the timestamp would re-ingest the same gazette every
week, report it as new, and be unable to distinguish that from a genuine re-publication of
an amended document. Detection is therefore by content hash, reusing the archive's existing
SHA-256 rather than introducing a second digest for the same document.

Weekly cadence matches the observed ~2-4 approvals per week with the PDF published weekly
to fortnightly. The interval is a staleness choice only: nothing about detection changes
with it, and a missed gazette is fixed by checking sooner rather than by changing the rule.

Acquisition stays separate from ingestion. The poller archives and never ingests, because
an unattended run that could ingest is one that could overwrite a good dataset with a bad
one, and the single-writer lock serialises writers without deciding which writer is
correct. A detected gazette waits for a person; the automation removes the need to watch,
not the need to decide.

## 5. `gazette_index` as a sync manifest

**Partly taken into `gazette-ingest-cadence`**, which item 2's start made possible.

The `gazette-archival` half landed in `robust-gazette-ingestion` — an append-only index
outside the working tree, carrying publication date, ingest timestamp, record count and
reader version, with SHA-256 on each member. Extending it was deferred "so the manifest is
designed once rather than twice", and that is why this change covers item 2's remainder
and this item together rather than in sequence.

Schema now carries what it previously could not:

- **`reader_version` separates two readers rather than naming one.** The index read
  `table-lines-v1` on all twelve entries, including ingestions made with the reader that
  absorbed page footers and truncated cells — so it could not distinguish a contaminated
  read from a corrected one, which is the manifest's stated purpose. A digest alone is not
  provenance when the reader may have truncated cells, so such an entry now reports
  unverified rather than being treated as sound. The twelve existing entries are left
  unmodified; rewriting append-only history to look correct is the failure this project
  keeps paying for.
- **First ingestion and re-read are distinct events.** Twelve entries described three
  publications, so entry count and publication count had drifted apart and neither could be
  read off the index. Both are now countable separately.
- **Acquisition provenance.** Whether a gazette was fetched or supplied from a path, and
  the publisher's reported timestamp where fetched — recorded as provenance, never read
  back to decide whether a gazette is new, for the reason in item 4.
- **The publication's own ordering**, as a count of departures from descending approval
  date stored beside the number of records a date could be read from, so a zero with too
  small a denominator is recognisable as a parser failure.

**Still open:** the portal-side state proper — per-project portal freshness, so the sweep
can be scheduled from the manifest instead of by re-deriving candidates from the emitted
dataset on every run. `scripts/fetch_remaining_national_portal.py` still enumerates by
absence: it loads `viewer/projects.data.js` and collects every project whose `links.twur`
is empty, re-deriving the list from scratch each time (measured: 709 projects, 632 with a
link, **77 candidates**). It does not read the change set this item now enables, and it
cannot, because the change set has no consumer. Building that consumer is item 2's
remaining work and the two are the same task: the manifest's shape depends on what the
cascade needs to schedule, which is why they are recorded together rather than as one
followed by the other.

## Status — 2026-10-06

Recorded on the way into `gazette-ingest-cadence`, which takes the unbuilt remainder.

| item | was | now |
|---|---|---|
| 1. Cache migration | resolved | resolved |
| 2. Portal sync / event cascade | open | `coverage.py` half **resolved**; cascade still open — its input exists, no consumer reads it, and the two-ingestion trigger stands at 0 of 2 |
| 3. Date-sort permanence | open, figure withdrawn | **measured: 9 / 9 / 1.** Permanence still needs two more publications; recorded per publication |
| 4. Scheduled fetching | open, ETag untested | **built.** No validators on the page, and the timestamp is not a valid signal — detection is by content hash |
| 5. Index as sync manifest | open | **partly built.** Reader identity, re-read events, acquisition provenance, ordering. Portal-side state remains open, and is item 2's remaining work |

Two of the withdrawals in this file were withdrawn for the wrong reason, which is worth
noting because both read as careful and neither was. Item 3's figure was set aside for
want of a read, not for doubt about the number, and it turned out to be exactly right.
Item 1's figures were wrong and had to be replaced. A parked item says what was believed
at the time; this table is what is measurable now.

A third correction belongs beside those two. Item 2's trigger — "a reliable change set
across at least two consecutive ingestions" — read as *not yet met* for as long as it stood,
and it was in fact **unsatisfiable**: `predecessor_of` could not reach a predecessor the
pipeline had not yet archived, so no ingestion ever produced a change set to be trusted.
Fixed in `fd7ff89`. The trigger was not being met slowly; it could not be met at all.

The measurements behind items 3 and 4 are recorded in
`openspec/changes/archive/2026-10-06-gazette-ingest-cadence/design.md` with the probes
they came from.
