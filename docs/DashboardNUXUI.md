# Dashboard and viewer UX/UI — exploration notes

Exploration notes for two pieces of work: a new dashboard page, and viewer UI/UX
improvements. This document records what was measured, what was decided, and what
remains open. It is a review document, not a change proposal.

- **Author:** Claude Code, 2026-11-05
- **Dataset:** `viewer/projects.data.js`, **682 projects / 1,444 records**, 統計至
  **2026-10-28**, payload blob `1ddffa1b` (commit `4b67a8f`). §3's figures were measured
  on that blob; §4.1, §4.2, §5 and §6 were re-measured on 2026-11-09 at commit
  `3e0c570`, after the `bind-the-unplaced-by-searching-the-cell-section` change. See
  §14.0.1 for what moved.
- **Status:** nothing implemented. No openspec change is open for the dashboard or the
  viewer UI work. `openspec/changes/` holds `archive/` and one change opened by another
  session, `bind-the-unplaced-by-searching-the-cell-section`.
- **Payload revision:** the figures were re-derived four times on 2026-11-06 as the
  D9g plan landed, and once more on 2026-11-09. The first version was pinned to blob
  `0b3a22b9`; see §14.

---

## 1. The request

Two tasks:

1. Improve the UI of `https://happypig.github.io/urTPE/viewer/index.html`.
2. Add a dashboard for the "staleness" of urTPE projects by city and district.

"Staleness" means **process duration**, not cache age: the long wait from application
through serial approvals, and from approval through 建照, 開工, 使照, and 成果報備.
The dashboard and the viewer are treated as one programme below, because the dashboard
reads the same payload the viewer reads.

**No city dimension exists.** Every project is in Taipei City. The dataset holds
`district` only. A "by city" breakdown is a one-row table today. The dashboard groups by
district, and adds a city row only if the corpus grows.

---

## 2. Definitions the dashboard must keep apart

Two different things get called "stale". They must never merge into one score.

| Name | Question | Source |
| --- | --- | --- |
| **行政時程** | How long does the city take? | Milestone dates in the payload |
| **資料時效** | Is our copy current? | Cache state and awaiting-approval cases |

A project can be slow (行政時程) and fresh (資料時效) at the same time. Most projects are.

---

## 3. Measured: 行政時程

All figures below come from the project-level `links` milestones, taken as the union of
`milestones_taipei`, `milestones_national`, and `milestones_taipei_case`. Dates are
normalised to ISO at read time: ROC `112.12.20` → `2023-12-20`, slash `2011/11/27` →
`2011-11-27`.

### 3.1 The funnel

"Ever reached" counts projects where the milestone exists in any bucket. "Stands here"
counts projects that reached the stage and have not reached the next one. A project that
reached a stage in one bucket and the next stage in a **different** bucket has moved on,
so the two tests are made per bucket and not on a merged dictionary.

| Stage | Ever reached | Stands here | Median days waiting | n waiting |
| --- | --- | --- | --- | --- |
| 核定 | 681 | 147 | 874 | 147 |
| 建照 | 534 | 27 | 337 | 27 |
| 開工 | 510 | 177 | 1,120 | 177 |
| 使照 | 334 | 283 | **2,014** | 283 |
| 成果報備 | 51 | 51 | **5,224** | 51 |

Waiting days are measured from the stage date to 2026-10-28, the gazette date.

**The 核定 row uses the LATEST of its approval dates; every other row uses the earliest.**
Appendix A says "the earliest date over the stage's fields", and that is what the other
four rows use. The 核定 row is the exception, and it is not a small one: the earliest
reading gives a median of 1,546 days and the latest gives 874. The document's 874 is
the latest reading. `scripts/probe_wait_date_rule.py` tests every row under both rules
and marks which one reproduces the figure.

**The dominant wait is 開工 → 使照.** 283 projects reached 使照 and stopped there. The
median wait since is 2,014 days, about 5.5 years. **The current viewer shows none of
this.** It renders the per-project graph, but no aggregate duration anywhere.

### 3.2 Stage-to-stage durations

Each row uses the earliest "from" date and the earliest "to" date per project.

| Transition | n | Median (d) | p75 (d) | Max (d) |
| --- | --- | --- | --- | --- |
| 申請 → 核定 | 681 | 379 | 896 | 7,690 |
| 核定 → 建照 | 534 | 330 | 1,566 | 6,715 |
| 建照 → 開工 | 507 | 169 | 262 | 2,246 |
| 開工 → 使照 | 333 | **1,169** | 1,442 | 3,704 |
| 核定 → 使照 | 334 | 1,657 | 2,716 | 7,846 |
| 使照 → 成果報備 | 51 | 339 | 466 | 1,197 |
| 申請 → 成果報備 | 51 | **2,163** | 2,680 | 3,352 |

**Read every median with its p75 and its max.** 核定 → 建照 has a median of 330 days and
a p75 of 1,566 days — nearly five times larger. A dashboard that shows only the median
hides that spread. The 7,690-day 申請 → 核定 outlier is 21.1 years.

`scripts/probe_dashboard_durations.py` computes both tables and prints them at the
current payload and at the revisions this document cites, so a figure that moves can be
told from a rule that was always this.

### 3.3 申請 → 核定 by track

Track comes from the project's current node.

| Track | n | Median (d) | p75 (d) | Max (d) |
| --- | --- | --- | --- | --- |
| 事業計畫 | 263 | 385 | 890 | 7,544 |
| 權利變換 | 218 | 360 | 783 | 7,544 |
| 事業計畫、權利變換 | 187 | **414** | 994 | 7,690 |
| 事業概要 | 13 | 347 | 439 | 573 |

Combined-track projects wait longest. 事業概要 has only 13 members, so its median is
not a stable figure.

### 3.4 By district

| District | Projects | n 申請→核定 | Median (d) | p75 (d) | 使照, no 成果報備 | No 建照 | Not 核定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 大安區 | 86 | 86 | 367 | 866 | 34 | 18 | 0 |
| 中山區 | 83 | 83 | 296 | 740 | 38 | 15 | 0 |
| 士林區 | 63 | 63 | 462 | 974 | 26 | 6 | 0 |
| 北投區 | 58 | 58 | 446 | 1,036 | 29 | 16 | 0 |
| 南港區 | 57 | 57 | 386 | 999 | 18 | 9 | 0 |
| 松山區 | 54 | 54 | **574** | 910 | 20 | 10 | 0 |
| 中正區 | 53 | 53 | 356 | 768 | 25 | 13 | 0 |
| 文山區 | 50 | 50 | 285 | 717 | 22 | 12 | 0 |
| 信義區 | 51 | 51 | 470 | 1,180 | 15 | 16 | 0 |
| 大同區 | 48 | 47 | 277 | 519 | 20 | 12 | 1 |
| 內湖區 | 40 | 40 | 347 | 658 | 18 | 9 | 0 |
| 萬華區 | 39 | 39 | 390 | **1,206** | 18 | 12 | 0 |
| **Total** | **682** | **681** | | | **283** | **148** | **1** |

District medians span 277 to 574 days. 萬華區's p75 is 1,206 days, the widest spread of
any district. **Never show one number per district.**

**The "not 核定" column fell from 8 to 1.** Those 8 projects had no approval date at
all, and 7 of them were among the 7 the
`bind-the-unplaced-by-searching-the-cell-section` change gave case ids. Only 大同區's
one project still has no approval.

`scripts/probe_dashboard_by_district.py` computes both tables and prints them at the
current payload and at the revisions this document cites.

### 3.5 成果報備 is a dead field

`成果報備日期` exists on 51 projects. Every date falls in a ten-year band:

| 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 5 | 1 | 3 | 9 | 7 | 4 | 8 | 9 |

**No project has a 成果報備 date after 2015-12-17.** The city stopped publishing the
field. The dataset carries no evidence of when the city stopped.

**This changes the dashboard design.** A funnel ending at 成果報備 would show 283
projects waiting for a date the city no longer publishes. That reads as 283 stalled
projects. It is false.

The dashboard must show 成果報備 as a **historical cohort** — a labelled chart of the 51
projects that have it, with the date range stated — and must not use it as a funnel
step.

**Corrected from an earlier draft of these notes.** The field was first identified as
`報核`. No key named `報核` exists in the payload or in any of the 727 caches; the
payload contains the string zero times. The field is `成果報備日期`. The earlier label
was wrong, and the earlier wording "報核 died after 2015" was an accident that landed
on the right years.

### 3.6 使用核發日期 is the national portal's own completion date

`milestones_national.使用核發日期` exists on 292 projects. Excluding the corrupted record in
§3.7, the 291 real dates span 2004-03-30 to 2024-12-31. It is not the same event as
the city's `使照核發日期`:

| Relation | Count |
| --- | --- |
| Both present, same date | 268 |
| Both present, different date | 21 |
| 使用核發日期 only | 3 |
| 使照核發日期 only | 45 |

**The two fields agree on 268 of 289 projects where both exist.** They are the same
event seen by two portals, and the city is authoritative. A dashboard that shows both
as separate funnel steps would double-count. Use 使照核發日期 for the 行政時程 funnel,
and offer 使用核發日期 as a cross-check.

**The dates must be normalised before they are compared.** The national portal writes
ROC (`112.12.20`) and the city writes Gregorian (`2023/12/20`). Comparing the raw
strings says all 289 differ, and it says the 268 that agree differ. `scripts/probe_dashboard_national_dates.py`
normalises first and reports the 268.

### 3.7 Two data defects found while measuring

**ROC year 291.** `大同區-橋北段一小段-574-1地號等41筆` carries
`milestones_national.使用核發日期 = "291.08.02"`. ROC 291 parses to the year 2202. The
true value is `111.08.02` = 2022-08-02, and the same project carries
`使照核發日期 = 2022/08/02` and `links.permit.date = 2022-08-02`. **This is the only
ROC date above ROC 115 in the whole payload.** It corrupts the 申請 → 使用核發 duration
for that project to 70,461 days, which is what made the 70,461-day outlier appear in an
earlier draft.

**The current node is not a status.** The `is_current` node carries only the
*administrative* milestones of its own approval (核定日期 on 453 projects, 申請計畫日期
on 452, 審議通過日期 on 416, 建照核發日期 on 132). It carries no 開工日期, no 使照核發日期,
and no 成果報備日期 at all. So a "current node" funnel reports 0 projects at 開工 and 0
at 使照, while 510 and 334 projects have reached those stages. **Read construction
stages from the project level, never from the current node.**

---

## 4. Measured: 資料時效

### 4.1 Awaiting approval — 99 projects

Computed from the payload with the pipeline's own predicate: a case carries an
application date and no approval date, and is neither terminal (自行撤回 / 已駁回 /
已失效) nor superseded.

| | Count |
| --- | --- |
| Projects awaiting an approval | **99** of 682 (15%) |

By district: 大安區 14, 南港區 12, 信義區 11, 中山區 10, 中正區 9, 北投區 8, 文山區 8,
松山區 7, 大同區 6, 內湖區 5, 士林區 5, 萬華區 4.

**The payload computes this exactly.** The payload and the cache layer agree: the
same rule, read from each, gives the same 99 and the same 12 districts. The rule is
`urtpe.links.cached_cases_awaiting_approval`, and the payload carries every field it
reads — `case_milestones`, `case_schedules`, `case_headers`, `superseded_by`.

**The figure was 97 until 2026-11-09.** The
`bind-the-unplaced-by-searching-the-cell-section` re-emit gave 7 projects their city
case ids, and 2 of them now carry a case that awaits an approval:

| Project | Case | Application | Approval |
| --- | --- | --- | --- |
| 中正區-臨沂段三小段-412地號等12筆 | 11410026 | 申請計畫日期 2025/10/14 | none |
| 信義區-吳興段二小段-163-2地號等2筆 | 11510019 | 申請計畫日期 2026/10/15 | none |

A project with no case id had no case that could carry an application, so it could not
await. Binding the case is what made it countable, and the count moved because the
population was measured again — not because the rule changed.

`scripts/probe_awaiting_over_history.py` walks the payload history and reports the
figure at each revision: 85 up to `a46f643`, 97 from `c084833` to `eafb9dd`, 99 from
`3e0c570`.

### 4.2 Unverified projects — 0

**This set is empty.** It held 6 projects until 2026-11-09, and the
`bind-the-unplaced-by-searching-the-cell-section` change emptied it: the 6 were exactly
the projects the city's parcel search did not match, and the widened land-core
comparison plus the portal's title search gave every one of them a city case id.

The 6, now bound:

| Project | Case id |
| --- | --- |
| 中正區-河堤五小段-399地號等3筆 | 11005053 |
| 信義區-吳興一小段-330地號等43筆 | 10611051 |
| 信義區-吳興段二小段-163-2地號等2筆 | 10405235, 09102220, 09102221 |
| 大安區-復興段一小段-3地號等2筆 | 10111171, 10111173 |
| 大安區-懷生段一小段-928地號等1筆 | 10002141 |
| 萬華區-萬華段一小段-519-2地號等35筆 | 10011301, 10903061 |

**The unverified column has nothing to show.** §5's Option B predicate now selects 0
projects. The option is not wrong — it is empty, because the defect it was measuring
has been fixed. A column that is always empty is not a column.

**The 60 that carry a city case id but no national link** are a different population,
and they are not unverified. Every one of them has a case the city confirms. What they
lack is a page on the national portal — and the portal's index holds only the ~110
newest entries, because the crawl is WAF-capped. `scripts/probe_dashboard_link_shapes.py`
counts every shape:

| Link shape | Count |
| --- | --- |
| National link **and** city case id | 622 |
| National link only | 0 |
| City case id only | **60** |
| Neither | **0** |

**Call the 60 something else.** They are 資料無國土署頁面 — the national portal has no
page for them — not 資料未驗證. The city confirmed them; the portal simply does not
cover them.

### 4.3 The ledger is not a freshness signal

`data/.link_cache/no_match_ledger.json` holds 74 entries. Each carries `last_probed`,
`twur_class`, and `view_ids_checked`.

| Check | Result |
| --- | --- |
| Ledger entries that are payload projects | 50 of 74 |
| Ledger entries whose own cache is stale | 6 of 74 |
| Cache-stale payload projects | 6 |
| Of those 6, present in the ledger | 6 |
| Ledger entries with `twur_class == "no-cases"` | 6 |

The ledger tracks **search misses**, not cache age. It contains 44 projects that are not
stale. A ledger lookup marks 50 projects where the true answer is 6.

**The `no-cases` class is an exact match for the stale set.** All 6 stale projects have
`twur_class == "no-cases"`, and no ledger entry with any other class is stale. But this
is a coincidence of the current corpus, not a rule. The mtime is the definition.

**Corrected from an earlier draft of these notes.** The first recommendation was to copy
the ledger into `viewer/`. That produces a wrong column. The ledger must not be the
source.

### 4.4 The payload proxy — it was exact, and it is now empty

| Predicate on project `links` | Matches then (682 projects) | Matches now |
| --- | --- | --- |
| `twur` empty | 60 | 60 |
| `taipei` empty | 7 | **0** |
| `case_milestones` empty | 7 | **0** |
| **`twur` empty AND `taipei` empty`** | **6** | **0** |

The last row was an exact proxy for the stale set, and it was measured against 25
payload revisions that held at 6. The
`bind-the-unplaced-by-searching-the-cell-section` change gave the 6 their city case
ids, so the predicate now selects 0.

`scripts/probe_option_b_over_history.py` walks that history and reports the count at
each revision: 6 at every revision from `fbece0c` to `eafb9dd`, then 0 at `3e0c570`.

**The proxy drifted because the population moved, not because the proxy was wrong.**
That is the property §5.2 wanted — a predicate that tracks the definition without a
pipeline change — and it also means the predicate is only as good as the population it
reads.

**A note on dates, from the peer.** Any predicate that compares against the gazette
must read `published_date` from the payload, never a hard-coded date. **A hard-coded
date is exactly the constant that broke the waiting figures** in §3 between revisions —
the gazette moved 2026-10-15 → 2026-10-28 and every "waiting since" number shifted by
13 days. The build script must take the gazette date as an input from the payload.

---

## 5. Open decision 1 — the source of the unverified column

**The question changed on 2026-11-09.** The unverified set was 6 projects and the
column had something to show. The `bind-the-unplaced-by-searching-the-cell-section`
change gave all 6 a city case id, so the set is now empty. Every option below is
re-read against the current payload.

| Option | Correct? | Cost | Risk |
| --- | --- | --- | --- |
| **A** — copy `no_match_ledger.json` into `viewer/` | **No.** Marks 50, truth is 0 | Low | Wrong column |
| **B** — payload predicate `twur` empty AND `taipei` empty | Yes, and it selects **0** | **None** | An always-empty column |
| **C** — emit the cache mtime into the payload | **No** — the mtime is the write time, and the cache pass rewrites 622 of 682 | Medium | Would read as fresh for all 682 |
| **D** — omit the column | n/a | None | Loses nothing — the set is empty |

**Option D is now the only one with something to deliver.** B is correct and free, but a
column that is empty for all 682 projects is a column with no information. The
recommendation has moved from B to D, and the reason is a measurement, not a preference.

**The 60 need a different question.** They carry a city case id and no national link.
They are not unverified — the city confirmed them. The national portal's index holds
only the ~110 newest entries because the crawl is WAF-capped, so "no portal page" is
mostly "the crawl did not reach this one". If the dashboard wants to show them, the
column should be named for what it is (資料無國土署頁面), and the crawl would have to run
again before the count meant anything.

### 5.2 The write-time risk, measured

Add a `cache_written_at` field. The pipeline already computes the value — it is thrown
away at `urtpe/cli.py:526-534`, where the stale count is printed and discarded.

The field must reach the payload through three places:

1. `DiscoveryResult` — add `cache_written_at: str = ""`
2. `build_graph_document()` in `urtpe/graph.py` — copy it into the project graph
3. The `--from-js` round trip at `urtpe/links.py:3030-3061` — read it back

**Point 3 is the trap.** `viewer/projects.data.js` is both input and output. A field
missing from that round trip is dropped silently on the next run. The archived
`supersede-headerless-cases` change left a comment at `urtpe/links.py:3051` about
exactly this failure mode.

**The risk in Option C, measured 2026-11-06 and re-measured 2026-11-09.** The cache
mtime is the **write** time, not the **fetch** time. The measurement:

| | Count |
| --- | --- |
| Cache directories | 727 |
| With a `result.json` | 727 |
| With a `view.html` (a page was fetched at some point) | 643 |
| `result.json` newer than `view.html` — rewritten with **no** fetch | **642** |
| `result.json` and `view.html` written together | 1 |
| No `view.html` at all | 84 |

The `result.json` mtimes cluster on 2026-11-06 (662) and 2026-11-04 (58), with **7
written on 2026-11-09** — the refresh the
`bind-the-unplaced-by-searching-the-cell-section` change ran. **No cache carries
2026-08-29 any more.** Six did before that refresh, and they were exactly the
unverified projects; the seventh was 臨沂段三小段.

`refresh_project()` re-fetches the city's case milestones, headers, implementation and
rewards, then calls `save_project_cache()` — which writes `result.json` and leaves
`view.html` alone. It never touches the national portal page. So **642 of the 727 caches
have a `result.json` mtime that says nothing about when their data was fetched.**

The lag is not noise. It runs from 29.0 days to 72.2 days, with a median of 70.7 days.
The 642 rewritten caches carry a `result.json` written on 2026-11-06 over a
`view.html` fetched on 2026-08-27.

**A `view.html` mtime is not a fetch time either.** Under that rule **642 of 727**
caches are stale. The `view.html` files cluster on 2026-08-27 (396), 2026-08-29 (166)
and 2026-08-30 (75), with only 6 fetched since. The national portal was not crawled
again after the Batch D pass, which re-fetches the city's cases but never the
national page. That would flag the whole corpus.

**This kills Option C as stated.** A `cache_written_at` field carries the write time,
and the write time is now meaningless: the Batch D cache pass rewrote 642 caches
without fetching a single national page. Every one of them would read as fresh.

`scripts/probe_cache_write_vs_fetch.py` produces this table.

### 5.3 The signal that actually works — it is now empty

**The 6 were the ones the refresh pass did not touch.** They were exactly the caches
with no `view.html` and no rewrite. The 2026-11-09 refresh reached all 6 of them, plus
臨沂段三小段, and they now carry 2026-11-09.

So the "unverified" signal has nothing left to mark. That is the good outcome: the
defect it was measuring is fixed. It is also the reason the column cannot be built
from it.

### 5.4 Recommendation

**Option D, not B.** The recommendation moved on 2026-11-09. Option B is still correct
and still free, but the predicate `links.twur` empty AND `links.taipei` empty now
selects **0** of 682 projects. A column that is empty for every project carries no
information, and shipping one would be a column that always reads the same.

Option C is still out: the cache mtime is the write time, and the cache pass rewrites
642 of 727 without fetching anything.

**The 60 are the population that remains**, and they need a different question and a
different name — 資料無國土署頁面, not 資料未驗證. The city confirmed every one of them.
The national portal's index holds only the ~110 newest entries because the crawl is
WAF-capped, so most of the 60 are projects the crawl never reached rather than
projects the portal does not have. If the dashboard wants to show them, the portal
crawl must run again before the count means anything.

### 5.5 The write-time check, if the pipeline ever wants it

The pipeline must record the **fetch** time, not the write time. Two options:

1. Store a `fetched_at` field inside `result.json` and update it only on a real
   request. The field survives the rewrite, because the rewrite preserves the
   `DiscoveryResult` fields it does not touch.
2. Use `case_headers` presence as the proxy. A cache the refresh pass reached has
   `case_headers`. **This proxy is no longer coarse: 726 of the 727 caches carry
   `case_headers` and 1 does not.** It was 628 of 726 lacking them before the
   whole-corpus refresh, and it was far too coarse then. It is a *precise* proxy now,
   and it selects the same project the unverified predicate would — a project with
   no case id has no case whose header the refresh could have read.

**Option 1 is still the one that works.** It says what the question asks — when was
this fetched — while `case_headers` says only that some case was read at some point.
It is a bigger change than Option C and it is not needed for the dashboard. It
belongs on the list only if a future feature needs a per-project freshness date.

**A practical path exists either way.** The dashboard can ship with the 99 awaiting
projects. The unverified column has nothing to add — the set is empty. The 99 need no
pipeline change.

---

## 6. Measured: the viewer's list performance

Measured in Chrome against the live site, `https://happypig.github.io/urTPE/viewer/index.html`,
dispatching real `input` events against the `#filter` element and forcing layout with
`list.offsetHeight` so paint cost is included.

**Re-measured 2026-11-09 on the 682-project payload**, so the figures below are the
current ones. The method changed in one way that matters: the queries are now measured
**interleaved** — each round measures every query in turn — so a drift in the machine's
load hits all of them alike. Measuring one query to completion and then the next lets
load drift masquerade as a difference between queries.

### 6.1 Render cost scales with rows built, not with the query

| Query | Rows built | Median (ms) | p75 (ms) | Max (ms) |
| --- | --- | --- | --- | --- |
| `zzzzz` | 1 (the empty-state row) | 5.8 | 8.4 | 75.8 |
| `大安區通化段四` | 2 | 1.7 | 2.4 | 16.2 |
| `大安區` | 86 | 13.0 | 16.9 | 70.7 |
| (empty) | 682 | **107.3** | 146.5 | 763.4 |

Medians of 25 interleaved rounds after 5 warm-up rounds.

**The absolute numbers move with the machine's load.** A separate non-interleaved run
on the same payload and the same browser measured the full render at 294 ms, and
another at 344 ms — the same code, the same 682 rows, three different figures. The
**ratio** is the finding, and it is stable: a full render costs about 8× what the
86-row render costs, and about 60× what the 2-row render costs. **Quote the shape,
not the milliseconds, unless the number was measured on the machine that will show
it.**

### 6.2 Where the time goes in a full render

| Step | Time |
| --- | --- |
| Build and insert 682 DOM rows | 96 ms |
| **Force layout and paint** | **765 ms** |

`list.scrollHeight` is **34,294 px** against a `list.clientHeight` of 920 px. The
browser does not virtualize, so it paints all 682 rows and discards most of them
off-screen. **Paint is the cost, not JavaScript.**

The split varies between runs — one instrumented run measured 66 ms of build-and-insert
against 278 ms of layout, another 96 ms against 765 ms — but layout and paint are the
larger part in every run. The rows are built one at a time with `appendChild` into the
live list at `viewer/app.js:897-910`, so each append touches a node the browser must
lay out.

### 6.3 Typing costs less than one full render

Typing `大安區通化段` one character at a time costs 263.5 ms for 6 keystrokes, against
a full 682-row render. **Typing costs less than one full render**, because each
keystroke narrows the list and so renders fewer rows.

**This is why a debounce is a weaker win than it first appears.** The cost tracks the
row count. As the reader types, the list narrows, so most keystrokes render *fewer*
rows. A debounce mainly helps the worst case: clearing the box, or a query that matches
all rows.

### 6.4 The real fix is a windowed list

If the list renders only the rows near the viewport, a full render costs what the
86-row render costs — about 13 ms. Then debounce matters much less.

### 6.5 One measurement is missing

The off-screen paint test failed three times (empty result, internal error, then a
timeout that hung the renderer). It was abandoned. The row-count scaling and the
build-versus-paint split identify the mechanism, but **no direct off-screen figure was
obtained.**

---

## 7. Measured: viewer accessibility and state gaps

Checked by search across `viewer/app.js` (1,648 lines):

| Capability | Occurrences |
| --- | --- |
| `tabindex` | 0 |
| `keydown` / `keyup` | 0 |
| `role=` | 0 |
| `aria-` | 0 |
| `location` / `pushState` / `replaceState` / `hash` | 0 |

**The viewer has no keyboard path and no URL state.**

- List items are `div` elements with an `onclick` handler at `viewer/app.js:910`. They
  are not focusable and cannot be activated by keyboard.
- The URL never changes. A reader who finds a project cannot share a link to it.
- `prefers-color-scheme` does not appear in `viewer/app.css` at all.

### 7.1 Dark mode needs tokens first

`viewer/app.css` (391 lines) defines **7 CSS variables** in `:root` but contains **62
hardcoded colour literals**. A `prefers-color-scheme` block can only override the 7
tokens; the 62 literals stay light. `docs/domain-model.html` and
`docs/graph-tabs-decision.html` both have such a block, so there is a precedent to copy.

### 7.2 The smoke harness cannot check a windowed list

`scripts/viewer_smoke.js` (329 lines) stubs `getBoundingClientRect()` to return all
zeros, and provides no `scrollTop`, `clientHeight`, or `offsetHeight`. A windowed list
needs those values.

**Nothing checks that file automatically.** `AGENTS.md` states it runs by hand and
reaches no network. A windowed list without harness support ships with no automated
check at all.

---

## 8. Open decision 2 — the scope of Part 1

### 8.1 The four candidate items, ranked

| Item | Value | Effort | Needs a list refactor? |
| --- | --- | --- | --- |
| **Windowed list** | High — fixes the full render and 34,294 px of scroll | Medium | It is the refactor |
| **URL state** | High — makes links shareable | Medium | No |
| **Keyboard and focus** | Medium | Medium | Partly |
| **Dark mode** | Medium | Medium | No, but needs 62 tokens first |
| **Debounce** | **Low** | One line | No |
| **Clear-all button** | Low | Small | No |

### 8.2 Why URL state and keyboard are one change

A URL that points at a project must be reachable. The list items are `div`s, not links
or buttons, and carry no `tabindex`. **A keyboard user cannot select a project, so a
shared URL cannot open one.** Making the URL addressable and making the list keyboard
operable are the same work.

### 8.3 Recommended scope

**Part 1 = URL state + keyboard access to the list, as one change.** Then the windowed
list. Then debounce.

1. Make each list item focusable and give it a role.
2. Handle Enter and Space to select.
3. Write the selection into the URL with `history.replaceState`.
4. Read the URL on load and select that project.
5. Add a windowed list.
6. Add a 250 ms debounce on top.

**Dark mode waits for Part 2**, after the colour tokens exist.

### 8.4 The dashboard needs a windowed list too

If the dashboard lists projects for drill-down, it inherits the same full-render cost.
The dashboard must render only visible rows.

---

## 9. Decided: paths and wiring

- **Pages:** `viewer/dashboard.html` + `viewer/dashboard.js`
- **`viewer/deploy.json`** must gain both, so `scripts/check_deploy.py` compares them
  against the served bytes. It currently lists 4 artifacts:
  `viewer/index.html`, `viewer/app.js`, `viewer/app.css`, `viewer/projects.data.js`.
- **`?v=` cache-bust token.** `viewer/index.html` loads
  `projects.data.js?v=202610280223` and `app.js?v=202610280223`. The dashboard needs
  its own matching token, or browsers serve a stale `dashboard.js` after a deploy.
- **A link from the viewer header**, and one back from the dashboard.
- **The dashboard reads `projects.data.js` directly.** No new data file, no pipeline
  change for the 行政時程 content.
- **A build script computes the aggregates.** The dashboard must not embed hand-written
  figures. Three payload re-emits on 2026-11-06 each moved the durations while the
  project count stayed the same — see §14.4. The aggregates are derived at build time
  and written into a data file the page reads, or computed in the page from the payload.
  **Either way, the numbers come from the payload, never from a human typing them.**
- **The unverified column needs no pipeline change.** Under Option B it is
  `links.twur` empty AND `links.taipei` empty, both already in the payload. **The whole
  dashboard is viewer-side.** The column has since emptied (§4.2), so the recommendation
  is Option D — but the pipeline independence holds either way, and it is why the
  dashboard can be a viewer-side change.

## 10. Decided: dashboard content

1. **行政時程 and 資料時效 are separate sections with separate names.** They never
   merge into one "stale" score.
2. **Every median appears with its p75 and its max.** One number per district hides a
   3,704-day spread.
3. **成果報備 appears as a historical cohort**, never as a funnel step, because the
   city stopped publishing it after 2015.
4. **Construction stages read from the project level**, never from the current node.
5. **使照核發日期 is the funnel's completion stage.** 使用核發日期 is a cross-check, not
   a second funnel.
6. **Per-project drill-down** from any aggregate cell.
7. **n is always shown next to every figure.** A median over 13 projects is not a
   district finding.

---

## 11. Separate, small: the compatibility-ideograph defect

CJK compatibility ideographs appear in the data in two places. They are **two separate
problems**. Neither is harmless: the corpus's 6 records break the identity reader, and
the one live case name breaks the track reader.

### 11.1 The corpus: 6 records, 3 projects — the identity reader breaks

**6 of 1,444 records** carry U+F901 (更), U+F963 (北), and U+FA26 (都) — all three in
each affected record's `name` and `name_raw`.

Measured over every text column of `clean.tsv`:

| column | rows carrying a compatibility ideograph |
| --- | --- |
| `name` | **6** — recnos 8, 121, 179, 611, 613, 615 |
| `name_raw` | **6** — the same rows |
| `land` (the 地號 cell) | **0** |
| every other text column | **0** |

| Project | 編號 |
| --- | --- |
| 信義區-三興段一小段-972地號等9筆 | 121, 611 |
| 北投區-桃源段四小段-424-8地號等15筆 | 8, 615 |
| 南港區-南港段三小段-274地號等16筆 | 179, 613 |

`parse_name_id()` in `urtpe/cleanse.py:31` returns `('', '', '', None)` on all 6,
because the regex cannot match a compatibility 北 or 都. The identity after folding:

| 編號 | As-is | After folding |
| --- | --- | --- |
| 8, 615 | `('', '', '', None)` | `('北投區', '桃源段四小段', '424-8', 15)` |
| 121, 611 | `('', '', '', None)` | `('信義區', '三興段一小段', '972', 9)` |
| 179, 613 | `('', '', '', None)` | `('南港區', '南港段三小段', '274', 16)` |

**Exactly those 6 rows change, out of 1,444.** So the corpus's own land core for these
3 projects is empty today.

**It costs nothing today, and the reason is not the one I wrote.** §11.3 said the index
core "falls through to the crude string-strip fallback at `urtpe/links.py:503`". That is
true, but the fallback builds the core from the **portal's** title, not from the corpus's
案名. The portal's titles for these 3 units carry no compatibility form, and the crawled
index holds **no core for these 3 units at all** — so the lookup misses either way.

Their portal links came from the cached view pages instead: **view/793** (北投),
**view/791** (信義), **view/253** (南港), each with `status: resolved`.

**So the defect is latent rather than live.** The reader is broken, and only the data
around it happens to route around it. That is the same population `land-identity-fallback`
covers, and the same reason that fallback exists. A change at the cleansing boundary is
still the right place to fix it.

**These 6 do not touch the track reader, and the reason is stronger than "the district
comes from another column".** The real reason: **no track keyword carries a
compatibility ideograph.** The reader tests four literals — 事業概要, 事業計畫, 權利變換,
都市更新計畫 — and none of the four contains one. The corpus's 北 / 都 / 更 are therefore
never compared against anything.

Measured: **0 of the 1,444 rows change track after folding.**

### 11.2 The live case name: 1 occurrence, and it breaks the track reader

**U+F9DD (利) appears once**, in `links.candidate_names["11507018"]` for
大安區-復興段三小段-3地號等2筆. It is the **compatibility form**, not the unified
利. Three checks agree:

| Check | Result |
| --- | --- |
| Bytes in `data/projects.json` | `ef a7 9d` at offset 9,439,569 — U+F9DD. The unified 利 is `e5 88 a9` |
| `unicodedata.name(ch)` | `CJK COMPATIBILITY IDEOGRAPH-F9DD` |
| `unicodedata.decomposition(ch)` | `5229` — the compatibility decomposition |

**This one breaks the track reader.** `_tracks()` at `urtpe/cleanse.py:230` matches the keyword
權利變換 literally:

| Title | `_tracks()` |
| --- | --- |
| 事業計畫及權**利**變換計畫案 (unified) | `['事業計畫', '權利變換']` |
| 事業計畫及權<U+F9DD>變換計畫案 | `['事業計畫']` — **the track is lost** |
| The compat title, NFKC-normalised | `['事業計畫', '權利變換']` |

Measured over the whole corpus and the whole link cache, the **track** reader changes
for **one case** — case `11507018` — and it is the same case in every scope. The link
cache stores it twice, in `candidate_names` and in `case_case_names` of the same cache
entry, so the raw entry count is 2 while the distinct-case count is 1:

| Scope | Entries with a compat ideograph | Distinct cases | Track changes after folding | Plan-case outcome changes |
| --- | --- | --- | --- | --- |
| Payload case names (1,987) | 1 | 1 | 1 | **0** |
| Link cache case names (4,192) | 2 (one case, two fields) | 1 | 1 | **0** |
| Corpus rows (1,444) | 6 | — | **0** | — |

**`_PLAN_CASE_RE` at `urtpe/links.py:2536` is NOT affected.** It requires the name to
start with 擬訂, and this case's name starts with 變更, so it matches neither way:

| The live name | `_PLAN_CASE_RE.match()` |
| --- | --- |
| 變更…事業計畫及權<U+F9DD>變換計畫案, as-is | no match |
| The same name, NFKC-normalised | no match |

The regex is genuinely compatibility-blind — a 擬訂 title carrying the compat form
fails as-is and matches after folding — but **no name in the payload or the cache is
that counterfactual**. So the implementation-dates path is not involved.

**But this is not the only reader that changes.** `parse_name_id()` is the second, and
§11.1 covers it: the 6 corpus records yield no identity today.

### 11.3 The fix

**An NFKC normalisation at the cleansing boundary, plus a test.** NFKC folds U+F9DD to
U+5229, U+F963 to U+5317, U+FA26 to U+90FD, and U+F901 to U+66F4. Verified: it makes
`parse_name_id()` succeed on the 6 corpus records, and it restores `_tracks()` on the
compat title.

**The change has TWO readers to fix:**

1. **The track reader**, where a city's case name is compared to a gazette 案名 — the
   one live case, `11507018`.
2. **`parse_name_id()`**, where the corpus's own 案名 yields no identity — the 6 records
   in 3 projects.

**The test-first group must pin six things:**

1. The live case reads **both** tracks after folding.
2. The 6 corpus records are unchanged in track.
3. **The project count does not move** — a normalisation at the cleansing boundary
   changes what the merge's similarity scoring compares, so it can join or split a
   family. Pinning the count catches that. (The record count is a separate concern,
   and the census gate already holds it total and disjoint.)
4. **The live case is checked by name, not by count.** A corpus-only test would pass
   while the live bug survived.
5. **The 6 records parse to their identity after folding**, and the 3 projects' land
   core becomes the folded one. A track-only test would not catch this.
6. **The 3 projects' portal links do not move.** They are already right, and a change
   at the cleansing boundary must not disturb them.

**There is one count, not two.** A family and a project are the same object here:
`urtpe/models.py:73` defines `Project` as *"A merged project family"*, `merge()` builds
one `Project` per cluster, and the emitted count is `len(graphs)` at `urtpe/graph.py:188`.
So **682** is the family count and the project count at once. There is no second count
that could move first.

**Why a corpus-only test is not enough.** The corpus's 6 characters are at index 3 (in
臺北市) and index 24–29 (in 都市更新). The live case's character, U+F9DD, is at index
32 of 38 — **inside 權利變換, which is a keyword**. The difference is *where* the
character sits, not *which* character it is. The corpus's six are never compared
against anything, because no keyword carries one; the live one is compared against a
keyword, and fails.

**This is a pipeline defect, independent of both the dashboard and the UI work.** It
belongs in its own change.

### 11.4 A correction to an earlier draft of these notes

An earlier draft said the single U+F9DD was "a normal 利 in 權利變換計畫案", and listed
three forms instead of four. **That was wrong.** The character is the compatibility form,
and the peer's byte-level check caught it. The distinction matters: a normal 利 is
harmless, and a compatibility 利 silently loses a track.

**A second correction, 2026-11-07.** An earlier revision of §11.2 said the defect broke
**two** readers — the track reader and `_PLAN_CASE_RE` at `urtpe/links.py:2536` — and
that a compatibility 利 could cost a case its plan-case implementation dates. **That was
wrong.** The peer measured it and I verified it: `_PLAN_CASE_RE` requires the name to
start with 擬訂, the live name starts with 變更, and **0 names in the payload or the
link cache would change their plan-case outcome after folding**. The implementation-dates
path is not involved.

I made the same kind of error twice while checking this. First I read a compatibility
利 by eye instead of by codepoint. Then I compared two regex `Match` objects with `!=`,
which is true whenever one side is `None`, and reported 762 names changing when the
correct figure is **0**. Both errors produced a wrong number that looked plausible.
Both were caught by checking the shape of the measurement rather than its output.

**A third correction, 2026-11-07, to the field.** An earlier revision of §11.3 said the
corpus's 6 characters sit in the 臺北市 of the **地號 cell**. **That was wrong.** They
sit in the **`name` column** — the `land` column carries none. The peer measured it over
every text column of `clean.tsv` and I verified it independently.

The conclusion did not move, and the real reason is stronger than the one I gave. I had
said the corpus is harmless because the district is read from the 行政區 column. That is
true, but it is not why the track survives. **No track keyword carries a compatibility
ideograph** — the reader tests 事業概要, 事業計畫, 權利變換 and 都市更新計畫, and none of
the four contains one. So the corpus's 北 / 都 / 更 are never compared against anything.

The peer's framing is the better one: **the difference is where the character sits, not
which character it is.** The corpus's six sit in text no keyword touches. The live case's
sits inside 權利變換, which is a keyword.

**A fourth correction, 2026-11-07, to the scope.** That same revision concluded "**one
reader** is affected". **That was wrong, in the other direction.** The peer found a
second, and I verified it: `parse_name_id()` returns `('', '', '', None)` for all 6
corpus records, and the folded identity is exact for each of the 3 projects. The corpus's
own land core for those 3 projects is **empty today**.

**So the scope is: the track reader breaks for 1 live case, and `parse_name_id` breaks
for 6 records in 3 projects.** The second is latent, not live — the index lookup misses
these 3 units either way, because the fallback builds the core from the portal's title
and the crawled index holds no core for them at all. Their links came from the cached
view pages (view/793, view/791, view/253). A broken reader, with the data around it
routing around it.

**The pattern across all six corrections is the same.** Each one took a partial
measurement and stated it as a scope: a character read by eye, a `Match` compared against
`None`, a field guessed from the neighbouring column, a count of readers taken from the
reader I happened to be looking at, a scope read off one reader, and a denominator taken
from a sample. **A scope is a claim about what was not measured.** Five of the six were
caught by the other session. §14.0.2 carries all six.

---

## 12. Repo housekeeping

- **`AGENTS.md` says "689 tests".** The real count was 1,001 collected on 2026-11-05.
  **It is now 1,116 collected** after the D9g plan. A full run reports the passed and
  skipped counts; the deliberate skip sits at
  `tests/test_idempotent_flags.py:117`. Refresh the count when `AGENTS.md` is next
  touched.
- **`docs/viewer-UX.md` has 8 entries, §1 through §8, and all 8 shipped.** Each has an
  archived openspec change. The status table in that file still reads "design settled"
  and "ready" for several of them, which is stale. New UI work goes in as **§9 onward**;
  the file is append-only and entries must not be inserted above §8.
- **Deploy state as of 2026-11-06: all 4 artifacts FRESH.** The live site carries the
  settled 682-project payload. The §6 performance figures were measured on the
  681-project payload; the corpus has since gained one project, and the viewer's
  render path grew by 7 lines for a badge. Re-measure before quoting a number.
- **The `--from-js` path now carries a partition gate.** A payload missing one node
  used to load as 1,443 members and be written back as a complete dataset. It is
  refused with exit 4 now. This matters for the dashboard: a build script that reads
  the payload can rely on the partition being complete.
- **A separate session was editing `docs/inspection-batchD.md` and adding
  `scripts/check_*.py` files.** These notes do not touch them.

---

## 13. What is needed to proceed

Two answers:

1. **The unverified column** — **Option D** (omit it) is the recommendation as of
   §5.4. Option B is still correct and still free, but it selects 0 of 682 projects, so
   the column would always read the same. Option C is out: the measurement in §5.2 shows
   the cache mtime is the write time, and the cache pass rewrites 642 of 727 caches
   without fetching anything. The 60 that carry a city case id but no national link are
   a different population and need a different name.
2. **Part 1 scope** — the six steps in §8.3, or a smaller slice.

On those answers, the openspec changes open: one for the dashboard, one for the viewer
UI work, one for the compatibility-ideograph fix.

**The dashboard needs no pipeline change** under either option. That means the dashboard
change is viewer-side only, and its test-first group can be a pytest case over a
fixture payload plus a smoke check. It does not need the corpus to be stable, because
every aggregate is computed from the payload at build time.

### 13.1 The openspec gate

Test-first is enforced. Every test-writing task must be fully checked before any
implementation task can be marked complete, or the change declares `> POC: <reason>` as
the first non-heading line of `tasks.md`.

For the viewer work, the test-first group is `scripts/viewer_smoke.js`, which is not a
pytest case. **The harness must gain geometry stubs before a windowed list can be
verified.**

For the dashboard, the test-first group can be a pytest case over a fixture payload,
which is the better shape.

---

## 14. Revision record

### 14.0.1 2026-11-09 — the unverified set emptied, and §4 moved with it

**The 6 unverified projects are now 0, and the awaiting count is now 99.** The
`bind-the-unplaced-by-searching-the-cell-section` change gave the 7 projects with no
city case id their case ids. Everything in §4 that read those 6 was measured against a
population that has since changed.

| Figure | Was | Now | Why |
| --- | --- | --- | --- |
| Unverified projects (§4.2) | 6 | **0** | All 6 gained a city case id |
| Option B predicate (§4.4) | 6 | **0** | It reads `taipei` empty, and none is |
| Awaiting approval (§4.1) | 97 | **99** | 2 of the newly-bound projects carry a case that awaits |
| 核定 ever reached (§3.1) | 674 | **681** | 7 projects gained their approval date |
| 使照 ever reached (§3.1) | 330 | **334** | 4 projects gained their construction date |
| "Not 核定" projects (§3.4) | 8 | **1** | 7 of the 8 were among the newly-bound |
| 使用核發日期 projects (§3.6) | 288 | **292** | 4 projects gained the national date |
| Caches with no `view.html` (§5.2) | 84 | 84 | Unchanged |
| Caches rewritten without a fetch (§5.2) | 642 | 642 | Unchanged |
| Recommendation (§5.4) | Option B | **Option D** | B now selects nothing |

**§3's figures moved for one reason: the 7 projects that had no city case id now have
one.** A project with no case id holds no milestone for that case, so it could not
count toward any stage. The rule did not change — the population did. The full
re-measurement is in §3's tables, and `scripts/probe_dashboard_durations.py` and
`scripts/probe_dashboard_by_district.py` print each table at the current payload and at
the revisions this document cites, so a moved figure can be told from a rule that was
always this.

**One rule in §3 was never stated, and it is not what Appendix A says.** The 核定 row's
"median days waiting" uses the **latest** of 核定日期 / 權變核定日期 / 概要核准日期. The
other four rows use the earliest, which is what Appendix A describes. The difference is
not small: the earliest reading gives a median of 1,546 days and the latest gives 874.
`scripts/probe_wait_date_rule.py` tests every row under both readings and marks which
one reproduces the figure. A build script written from Appendix A alone would get that
row wrong.

**The awaiting count moved for a reason worth stating.** A project awaits when one of
its cases carries an application date and no approval date. 臨沂段三小段's case 11410026
carries 申請計畫日期 2025/10/14 and no approval; 吳興段二小段's case 11510019 carries
申請計畫日期 2026/10/15 and no approval. Before the change those projects held no case
id at all, so no case could carry an application and they could not await. Binding the
case is what made them countable.

**No rule changed** in §4.1. The rule is still `urtpe.links.cached_cases_awaiting_approval`,
and the payload and the cache layer still agree exactly — 99 and 99, over the same 12
districts. What moved is the population, which is the thing the rule reads.

**The three probes that produced these numbers** are checked in:
`scripts/probe_option_b_over_history.py` walks the payload history for the predicate;
`scripts/probe_awaiting_over_history.py` does the same for the awaiting count;
`scripts/probe_awaiting_joiners.py` names the two projects that joined. The history is
the evidence: the awaiting figure was 85 up to `a46f643`, 97 from `c084833` to
`eafb9dd`, and 99 from `3e0c570`.

**One figure held.** The 642-of-727 rewrite count, the 84 caches with no `view.html`,
and the 70.7-day median lag are all unchanged. The refresh wrote 7 caches on 2026-11-09
and the rest still carry 2026-11-06.

### 14.0.2 2026-11-07 — six corrections to §11

**§11 was wrong six times, in four different directions.** All six were found by
measuring the population rather than the sample, and five of the six by the peer. Three
were mine and three the peer's, and the shape is the same in both directions — a scope
overstated and a scope understated.

### 14.0.3 The plan-case claim withdrawn

**The ideograph defect does not cost a case its plan-case implementation dates.**
§11.2 and §11.3 previously said it did, via `_PLAN_CASE_RE` at `urtpe/links.py:2536`.
**That half is not supported** and is withdrawn.

Measured, and verified independently:

| Scope | Names with a compat ideograph | Track changes | Plan-case outcome changes |
| --- | --- | --- | --- |
| Payload case names | 1 | 1 | **0** |
| Link cache case names (4,192) | 2 (one case, two fields) | 1 | **0** |
| Corpus rows (1,444) | 6 | **0** | — |

**The dashboard figures did not move.** Nothing in §3 or §4 depends on this. The
payload blob is still `1ddffa1b`, still 682 projects / 1,444 records.

**Two measurement errors, both mine, both caught by checking the shape.** I read a
compatibility 利 by eye instead of by codepoint, and I compared two regex `Match`
objects with `!=`, which reports 762 names changing where the true figure is 0. A
plausible number is not a verified one.

**A third error, also mine, on the field.** §11.3 said the corpus's 6 characters sit in
the 臺北市 of the **地號 cell**. They sit in the **`name` column**; `land` carries none.
Verified by counting every text column of `clean.tsv`.

The conclusion did not move, and the reason is stronger than the one I gave. I had said
the corpus is harmless because the district is read from the 行政區 column. That is
true, but it is not why the track survives. **No track keyword carries a compatibility
ideograph** — the reader tests 事業概要, 事業計畫, 權利變換 and 都市更新計畫, and none of
the four contains one. The corpus's 北 / 都 / 更 are never compared against anything.

**The difference is where the character sits, not which character it is.** The corpus's
six sit in text no keyword touches, at index 3 (臺北市) and index 24–29 (都市更新). The
live case's sits at index 32 of 38, inside 權利變換 — a keyword. A test that checks only
the corpus passes while the live bug survives, and it passes for a reason the live case
does not share. The test-first group therefore checks the live case **by name**.

### 14.0.4 The scope corrected the other way — two readers, not one

**Having withdrawn the plan-case reader, I then stated "one reader". That was wrong
too.** The peer found the second, and I verified it: `parse_name_id()` returns
`('', '', '', None)` for all 6 corpus records, and the folded identity is exact for each
of the 3 projects.

| 編號 | As-is | After folding |
| --- | --- | --- |
| 8, 615 | `('', '', '', None)` | `('北投區', '桃源段四小段', '424-8', 15)` |
| 121, 611 | `('', '', '', None)` | `('信義區', '三興段一小段', '972', 9)` |
| 179, 613 | `('', '', '', None)` | `('南港區', '南港段三小段', '274', 16)` |

**Exactly those 6 rows change, out of 1,444.** The corpus's own land core for these 3
projects is empty today.

**It costs nothing today, and the reason is not the one I wrote.** The fallback at
`urtpe/links.py:503` builds the core from the **portal's** title, not the corpus's 案名.
The portal's titles carry no compatibility form, and the crawled index holds **no core
for these 3 units at all**, so the lookup misses either way. Their links came from the
cached view pages: **view/793**, **view/791**, **view/253**, each `status: resolved`.

**So the defect is latent rather than live.** The reader is broken, and only the data
around it happens to route around it — the same population `land-identity-fallback`
covers, and the same reason that fallback exists. A change at the cleansing boundary is
still the right place to fix it.

### 14.0.5 The scope, settled

**Two readers, and no more:**

1. **The track reader** — 1 live case, `11507018`.
2. **`parse_name_id()`** — 6 records in 3 projects, latent.

**Six pins** for the test-first group, listed in §11.3: the live case reads both tracks
after folding; the 6 corpus records are unchanged in track; the **project** count does
not move; the live case is checked **by name, not by count**; the 6 records parse to
their identity after folding; and the 3 projects' portal links do not move.

**The pattern across all six corrections is the same.** Each took a partial measurement
and stated it as a scope. **A scope is a claim about what was not measured.** Five of the
six were caught by the other session. §14.0.2 carries all six in one table.

**A fifth and sixth correction, 2026-11-07, from the peer.** The peer's sweep of the
board found that its D16 status read "the population is 1 case in 360" — a **sample**
stated as a population. The live case was found by querying the city for 60 units and
reading the 360 names that came back; the population we actually hold is **2,024
distinct city case names in the link cache, of which 1 carries a compatibility
ideograph** — the same case. The finding does not change; its denominator does.

The board's table also still read "1,442 rows" for the corpus, which the D9g ingest
moved to **1,444**, and `scripts/probe_compat_ideographs.py` still prints that
hard-coded string.

**"Small" is a measurement, not a scope.** That is the peer's sentence for the sixth
correction, and it is the shorter form of the same finding.

**The pattern across all six is the same, and it is now the general form.** Three of the
six are mine and three are the peer's, and the shape does not depend on who made it:

| | Correction | What was stated | What was true |
| --- | --- | --- | --- |
| 1 | a character read by eye | "3 compatibility forms" | **4** across the data — 3 in the corpus (U+F901, U+F963, U+FA26) and the live U+F9DD |
| 2 | a match compared against `None` | "762 names would change" | **0** — a `Match` is never equal to `None` |
| 3 | a field guessed from the neighbouring column | "the corpus's characters sit in the 地號 cell" | the **案名** — the 地號 column carries 0 |
| 4 | a reader count taken from the reader in view | "1 reader is affected" | **2** — `parse_name_id` also breaks |
| 5 | a denominator taken from a sample | "1 in 360" | **1 in the 2,024** city case names we hold |
| 6 | a blast radius read as a scope | "the population is 1 case in 360" | **1 live case and 6 corpus rows** |

**A scope is a claim about what was not measured.** Every one of the six was caught by
measuring the population rather than the sample, and five of the six were caught by the
other session.

**The board carries the same six in the same form**, in
`docs/inspection-batchD.md` under "the general form: a scope is a claim about what was
not measured". It is the board's own conclusion, with no attribution to either session,
because the shape does not depend on who made the correction.

### 14.1 2026-11-06, final revision — the settled corpus

Payload blob `d6d62109` → `1ddffa1b`. **The corpus settled.** The 2026-10-28 gazette
was ingested (the tripwire refused it earlier; the empty 核定日期 cell for 編號 3 was
recovered by the `recover-truncated-date-cells` change), and the whole D9g plan landed.

**The corpus moved for the first time.** 681 projects → **682**. 1,442 records →
**1,444**. The gazette date moved 2026-10-15 → **2026-10-28**.

| Figure | Third | Final |
| --- | --- | --- |
| Projects | 681 | **682** |
| Records | 1,442 | **1,444** |
| 核定 ever reached | 673 | 674 |
| 建照 ever reached | 529 | 529 |
| 開工 ever reached | 505 | 505 |
| 使照 ever reached | 330 | 330 |
| 成果報備 ever reached | 51 | 51 |
| Projects stuck at 使照 | 279 | 279 |
| 核定 median wait | 876 d | 874 d |
| 開工 median wait | 1,108 d | 1,120 d |
| 使照 median wait | 2,001 d | 2,014 d |
| 成果報備 median wait | 5,211 d | 5,224 d |
| 申請 → 核定 median | 385 d | 382 d |
| 核定 → 建照 median | 329 d | 329 d |
| 開工 → 使照 median | 1,164 d | 1,164 d |
| 核定 → 使照 median | 1,658 d | 1,658 d |
| 申請 → 成果報備 median | 2,163 d | 2,163 d |
| 事業計畫、權利變換 n | 183 | 184 |
| Districts with no 建照 | 152 | 153 |
| Projects not 核定 | 8 | 8 |
| 大同區 projects | 47 | 48 |

**Waiting days are now measured to 2026-10-28**, the new gazette date. The 13-day
shift explains the +13 d on every "median wait" row.

**What did not change.** The 97 awaiting-approval projects and their district split.
The 6 unverified projects and their names. The ROC year 291. The payload predicate
matching the unverified set exactly. 成果報備 (51 projects, still ending 2015-12-17).
The 開工 → 使照 transition median, still 1,164 days. 大同區 gained the one new project.

**A new gate now protects this.** Proving the partition exposed that the `--from-js`
path had no partition gate: a payload missing one node loaded as 1,443 members and was
written back as a complete dataset. That is fixed and refused with exit 4. **A payload
that reaches the dashboard now carries a gate.**

### 14.2 2026-11-06, third revision — D9c-2a re-emit

Payload blob `e51272a2` → `d6d62109`. The D9c-2a re-emit carried the aliased cases
into the payload.

| Figure | Second | Third |
| --- | --- | --- |
| 核定 ever reached | 672 | 673 |
| 建照 ever reached | 527 | 529 |
| 開工 ever reached | 503 | 505 |
| 使照 ever reached | 329 | 330 |
| Projects stuck at 使照 | 278 | 279 |
| 開工 → 使照 median wait | 1,094 d | 1,108 d |
| 核定 → 建照 median | 329 d | 329 d |
| 申請 → 核定 median | 382 d | 385 d |
| 使照核發日期 only | 42 | 43 |
| Districts with no 建照 | 154 | 152 |
| Projects not 核定 | 9 | 8 |

**What did not change.** The 97 awaiting-approval projects and their district split.
The 6 cache-stale projects and their names. The ROC year 291. The payload predicate
matching the stale set exactly. 成果報備 (51 projects, still ending 2015-12-17). The
開工 → 使照 transition median, still 1,164 days.

**Step 9's ingest did not run.** The tripwire refused it with exit 4 — the 2026-10-28
gazette prints an empty 核定日期 cell for 編號 3 — so the emitted dataset is unchanged.
The cache writes of steps 2, 4 and 6 did land, and the D9c-2a re-emit followed them.

**The next gazette will move the corpus more than a re-emit does.** The refused ingest
read 1,422 records, excluded 23 as publisher-truncated, and produced **676 projects
against today's 681**. So the next successful ingest changes the project count by
5, not 0. Every aggregate in these notes moves again then. This is the third
revision in one day, and the next one will be larger than the first two.

**The −5 is mostly the reader's own exclusions, not new approvals.** The peer measured
the reconciliation offline against `clean.tsv` (the tripwire blocks it inside the CLI):
only 2 approvals are genuinely new — 玉泉段二小段452-2 and 通化段一小段812 — and both
land in projects the payload already holds. The net change comes from the 23
publisher-truncated rows and the 5 families they belong to. The gazette holds 1,442
編號; the reconciliation compares the 1,422 read rows against the predecessor's 1,442.

**編號 3 is not a new approval.** It is the 2026-10-15 approval re-published with an
empty date cell. The current payload already holds it: 大安區-通化段四小段-336地號等26筆,
node recno 1, dated 2026-10-15, bound to city case 11501034, whose 核定日期 reads
2026-10-15. The reconciler names it as a "withdrawn recent approval" only because the
empty date breaks its identity key.

**The 成果報備 and 使照 findings survive that.** Both depend on dates the city
published before 2016, and a new gazette adds approvals, not corrections to old ones.
But the counts will shift, and the dashboard must read them from the payload at build
time.

**Corroborated by the peer, 2026-11-06.** Three corrections to an earlier draft of
this paragraph: the project count is 676 (not 677 — the figure came from a probe that
skipped the correction ledger, and the ledger's two 吉林676 entries merge one pair); the
−5 frame is exclusions rather than new approvals; and 編號 3 is a re-publication, not a
new approval. Each was checked against the repo and the payload. The board was
corrected at `4f9dfd8`.

### 14.3 2026-11-06, second revision — D9g Batch D re-emit

The D9g Batch D step landed a re-emit while these notes were open. The payload blob
changed from `0b3a22b9` to `e51272a2`. **The project count and record count did not
change: 681 projects, 1,442 records.** Every duration figure did.

| Figure | First | Second |
| --- | --- | --- |
| 核定 ever reached | 669 | 672 |
| 建照 ever reached | 514 | 527 |
| 開工 ever reached | 495 | 503 |
| 使照 ever reached | 328 | 329 |
| 成果報備 ever reached | 50 | 51 |
| 申請 → 核定 median | 386 d | 382 d |
| 核定 → 建照 median | 326 d | 329 d |
| 開工 → 使照 median | 1,164 d | 1,164 d |
| 核定 → 使照 median | 1,658 d | 1,655 d |
| 申請 → 成果報備 median | 2,229 d | 2,163 d |
| 成果報備 median wait | 5,190 d | 5,211 d |
| 事業概要 n | 11 | 13 |
| 使用核發日期 projects | 287 | 288 |
| Districts with no 建照 | 167 | 154 |
| Projects not 核定 | 12 | 9 |

**What did not change.** The 278 projects stuck at 使照 and their 2,010-day median wait.
The 97 awaiting-approval projects and their district split. The 6 cache-stale projects
and their names. The ROC year 291. The `twur` empty AND `taipei` empty predicate
matching the stale set exactly. Every viewer-side measurement in §6 and §7.

**The lesson.** The re-emit added milestone coverage — more projects now carry 建照 and
核定 dates — so the funnel widened at the top and narrowed at "no 建照". A dashboard
built on the old numbers would have understated the first stage and overstated the
third. **The dashboard must compute its figures at build time, not embed them.** This
is the strongest argument for a build script that reads the payload, and against
hand-written numbers in the page.

### 14.4 2026-11-06 — the compatibility-ideograph correction

The peer checked my §11 claim and rejected it. **The peer was right.** I had written
that the single U+F9DD was "a normal 利 in 權利變換計畫案". It is the compatibility form:
`ef a7 9d` at offset 9,439,569 in `data/projects.json`, `unicodedata.name` returns
`CJK COMPATIBILITY IDEOGRAPH-F9DD`, and `unicodedata.decomposition` returns `5229`.

The distinction is not cosmetic. Verified in the repo:

| Reader | Unified | Compatibility |
| --- | --- | --- |
| `_tracks()` at `cleanse.py:230` | `['事業計畫', '權利變換']` | `['事業計畫']` — track lost |
| `parse_name_id()` on the 6 corpus records | — | `('', '', '', None)` |

NFKC fixes both. §11 now separates the two problems: the 6 corpus records (北/都/更
in the district name, harmless to the track reader) and the 1 live case name (利, which
does break the reader).

**Updated 2026-11-07.** This entry originally listed a third reader,
`_PLAN_CASE_RE` at `links.py:2536`, as "no match — dates dropped". **That row was
wrong.** The regex requires the name to start with 擬訂; the live name starts with
變更, so it matches neither way, and **0 names in the payload or the link cache change
their plan-case outcome after folding**. The peer measured it and I verified it
independently. **One reader is affected, not two.** See §11.4.

### 14.5 2026-11-05 — first version

First draft, pinned to payload blob `0b3a22b9`. It recorded the 報核 → 成果報備
correction, the ledger correction, and the ROC 291 defect.

### 14.6 The pattern across all four revisions

| | First | Second | Third |
| --- | --- | --- | --- |
| Payload blob | `0b3a22b9` | `e51272a2` | `d6d62109` |
| Projects | 681 | 681 | 681 |
| Records | 1,442 | 1,442 | 1,442 |
| 核定 ever reached | 669 | 672 | 673 |
| 使照 ever reached | 328 | 329 | 330 |
| Projects stuck at 使照 | 278 | 278 | 279 |

| | First | Second | Third | Final |
| --- | --- | --- | --- | --- |
| Payload blob | `0b3a22b9` | `e51272a2` | `d6d62109` | `1ddffa1b` |
| Projects | 681 | 681 | 681 | **682** |
| Records | 1,442 | 1,442 | 1,442 | **1,444** |
| 核定 ever reached | 669 | 672 | 673 | 674 |
| 使照 ever reached | 328 | 329 | 330 | 330 |
| Projects stuck at 使照 | 278 | 278 | 279 | 279 |
| 申請 → 成果報備 median | 2,229 d | 2,163 d | 2,163 d | 2,163 d |
| 使用核發日期 projects | 287 | 288 | 288 | 288 |

**Four revisions, four sets of durations.** The counts held at 681 for three of them,
then moved to 682 when the gazette was ingested. The durations moved every time.

A reader who quoted the first version's medians would be wrong today by up to 66 days
on 申請 → 成果報備, and by 13 days on every "waiting since" figure — the last shift is
the gazette date moving, not the data.

**The stable findings, across all four revisions.** 97 awaiting-approval projects and
their district split. The 6 unverified projects and their names. The ROC year 291.
成果報備 ending in 2015-12-17. The 使照 bottleneck. The current-node defect. The
payload predicate matching the unverified set exactly.

**None of these moved once.** They do not depend on the milestone coverage the
re-emits change, and the 2026-10-28 gazette added approvals rather than correcting old
ones. That is why they are the findings worth putting in a dashboard.

**Several of them moved on 2026-11-09, and §14.0.1 has the details.** The awaiting
count is 99, not 97. The unverified set is empty, not 6. The 核定 ever-reached count is
681, not 674, and the 使照 count is 334, not 330. All of them moved because the
`bind-the-unplaced-by-searching-the-cell-section` change bound the 7 projects that held
no city case id. The ROC year 291, the 成果報備 cohort ending in 2015-12-17, the 使照
bottleneck and the current-node defect did not move.

**The stability was never a property of the corpus — it was a property of the corpus
being unchanged.** A figure that survives four revisions of a corpus that is itself
moving is worth re-measuring when the corpus moves. That is what §14.0.1 does.

**The design consequence is settled.** Compute at build time. Never embed. Four
revisions in one day is the argument — and the fifth revision, a week later, is the
second half of the argument.

---

## Appendix A — how to reproduce the numbers

Every figure comes from `viewer/projects.data.js` and the cache directory
`data/.link_cache/`. §3's figures were measured at payload blob `1ddffa1b` (commit
`4b67a8f`); §4.1, §4.2 and §5 were re-measured at commit `3e0c570`, which is the
payload after the `bind-the-unplaced-by-searching-the-cell-section` re-emit. The
computation is:

1. Read `viewer/projects.data.js`, strip the `window.PROJECTS = ` prefix and the
   trailing `;`, and parse the JSON.
2. For each project, build a milestone dictionary from the union of
   `links.milestones_taipei`, `links.milestones_national`, and
   `links.milestones_taipei_case`. Keep the first non-empty value per key.
3. Normalise dates: ROC `N.N.N` → `N+1911-N-N`; slash `Y/M/D` → `Y-M-D`; ISO passes
   through.
4. For 申請 → 核定, take the earliest date over
   `申請核定日期`, `權變申請核定日期`, `申請計畫日期`, `申請權變日期`, `申請概要日期`.
   For 核定, take the earliest over `核定日期`, `權變核定日期`, `概要核准日期`.
5. Take the difference in days. Report the median, the p75 (linear interpolation
   between the two nearest order statistics), and the max.
6. For the funnel, "stands here" means the stage milestone exists and the next stage's
   milestone does not.
7. For the waiting-since figures, measure from the stage date to the **gazette date**,
   which is `published_date` in the payload — not a hard-coded date. The gazette date
   moved from 2026-10-15 to 2026-10-28 between revisions.
8. For 資料未驗證, count the projects whose `links.twur` is empty **and** whose
   `links.taipei` is empty. `scripts/probe_option_b_over_history.py` reports the count
   at every payload revision.
9. For 資料未驗證's sibling, the awaiting count, use the pipeline's own rule —
   `urtpe.links.cached_cases_awaiting_approval` — read from the payload's
   `case_milestones`, `case_schedules`, `case_headers` and `superseded_by`.
   `scripts/probe_awaiting_over_history.py` reports it at every payload revision.

**Two cautions.** The ROC year 291 in §3.7 corrupts any duration that includes
`使用核發日期` for that one project. And the "current node" reading in §3.7 counts
construction stages as zero, which is wrong.

**The step-by-step recipe above is the specification for a build script.** See §14.1
for why the figures must not be hand-written.
