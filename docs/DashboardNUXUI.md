# Dashboard and viewer UX/UI — exploration notes

Exploration notes for two pieces of work: a new dashboard page, and viewer UI/UX
improvements. This document records what was measured, what was decided, and what
remains open. It is a review document, not a change proposal.

- **Author:** Claude Code, 2026-11-05
- **Dataset:** `viewer/projects.data.js`, 681 projects / 1,442 records, 統計至 2026-10-15,
  generated 2026-11-05T10:31:05+08:00
- **Status:** nothing implemented. No openspec change is open. `openspec/changes/` holds
  only `archive/`.

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
counts projects that reached the stage and have not reached the next one.

| Stage | Ever reached | Stands here | Median days waiting | n waiting |
| --- | --- | --- | --- | --- |
| 核定 | 669 | 155 | 890 | 155 |
| 建照 | 514 | 23 | 387 | 23 |
| 開工 | 495 | 168 | 1,094 | 168 |
| 使照 | 328 | 278 | **2,010** | 278 |
| 成果報備 | 50 | 50 | **5,190** | 50 |

Waiting days are measured from the stage date to 2026-10-15.

**The dominant wait is 開工 → 使照.** 278 projects reached 使照 and stopped there. The
median wait since is 2,010 days, about 5.5 years. **The current viewer shows none of
this.** It renders the per-project graph, but no aggregate duration anywhere.

### 3.2 Stage-to-stage durations

Each row uses the earliest "from" date and the earliest "to" date per project.

| Transition | n | Median (d) | p75 (d) | Max (d) |
| --- | --- | --- | --- | --- |
| 申請 → 核定 | 669 | 386 | 897 | 7,544 |
| 核定 → 建照 | 514 | 326 | 1,575 | 6,684 |
| 建照 → 開工 | 491 | 170 | 263 | 2,246 |
| 開工 → 使照 | 327 | **1,164** | 1,445 | 3,704 |
| 核定 → 使照 | 328 | 1,658 | 2,685 | 7,846 |
| 使照 → 成果報備 | 50 | 342 | 466 | 1,197 |
| 申請 → 成果報備 | 50 | **2,229** | 2,685 | 3,352 |

**Read every median with its p75 and its max.** 核定 → 建照 has a median of 326 days and
a p75 of 1,575 days — nearly five times larger. A dashboard that shows only the median
hides that spread. The 7,544-day 申請 → 核定 outlier is 20.7 years.

### 3.3 申請 → 核定 by track

Track comes from the project's current node.

| Track | n | Median (d) | p75 (d) | Max (d) |
| --- | --- | --- | --- | --- |
| 事業計畫 | 260 | 372 | 818 | 7,544 |
| 權利變換 | 217 | 390 | 809 | 7,544 |
| 事業計畫、權利變換 | 181 | **445** | 1,015 | 4,639 |
| 事業概要 | 11 | 347 | 397 | 573 |

Combined-track projects wait longest. 事業概要 has only 11 members, so its median is
not a stable figure.

### 3.4 By district

| District | Projects | n 申請→核定 | Median (d) | p75 (d) | 使照, no 成果報備 | No 建照 | Not 核定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 大安區 | 86 | 84 | 392 | 927 | 32 | 21 | 2 |
| 中山區 | 83 | 83 | 314 | 790 | 38 | 15 | 0 |
| 士林區 | 63 | 63 | 509 | 974 | 26 | 8 | 0 |
| 北投區 | 58 | 58 | 366 | 1,009 | 29 | 17 | 0 |
| 南港區 | 57 | 55 | 379 | 804 | 17 | 15 | 2 |
| 松山區 | 54 | 53 | **570** | 886 | 20 | 14 | 1 |
| 中正區 | 53 | 50 | 363 | 788 | 24 | 14 | 3 |
| 文山區 | 50 | 50 | 318 | 849 | 22 | 13 | 0 |
| 信義區 | 51 | 49 | 470 | 1,089 | 15 | 17 | 2 |
| 大同區 | 47 | 46 | 262 | 537 | 20 | 11 | 1 |
| 內湖區 | 40 | 40 | 348 | 658 | 18 | 9 | 0 |
| 萬華區 | 39 | 38 | 398 | **1,246** | 17 | 13 | 1 |
| **Total** | **681** | **669** | | | **278** | **167** | **12** |

District medians span 262 to 570 days. 萬華區's p75 is 1,246 days, the widest spread of
any district. **Never show one number per district.**

### 3.5 成果報備 is a dead field

`成果報備日期` exists on 50 projects. Every date falls in a ten-year band:

| 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 2 | 4 | 1 | 3 | 9 | 7 | 4 | 8 | 9 |

**No project has a 成果報備 date after 2015-12-17.** The city stopped publishing the
field. The dataset carries no evidence of when the city stopped.

**This changes the dashboard design.** A funnel ending at 成果報備 would show 631
projects waiting for a date the city no longer publishes. That reads as 631 stalled
projects. It is false.

The dashboard must show 成果報備 as a **historical cohort** — a labelled chart of the 50
projects that have it, with the date range stated — and must not use it as a funnel
step.

**Corrected from an earlier draft of these notes.** The field was first identified as
`報核`. No key named `報核` exists in the payload or in any of the 726 caches; the
payload contains the string zero times. The field is `成果報備日期`. The earlier label
was wrong, and the earlier wording "報核 died after 2015" was an accident that landed
on the right years.

### 3.6 使用核發日期 is the national portal's own completion date

`milestones_national.使用核發日期` exists on 287 projects. Excluding the corrupted record in
§3.7, the 286 real dates span 2004-03-30 to 2024-12-31. It is not the same event as
the city's `使照核發日期`:

| Relation | Count |
| --- | --- |
| Both present, same date | 265 |
| Both present, different date | 21 |
| 使用核發日期 only | 1 |
| 使照核發日期 only | 42 |

**The two fields agree on 265 of 286 projects where both exist.** They are the same
event seen by two portals, and the city is authoritative. A dashboard that shows both
as separate funnel steps would double-count. Use 使照核發日期 for the 行政時程 funnel,
and offer 使用核發日期 as a cross-check.

### 3.7 Two data defects found while measuring

**ROC year 291.** `大同區-橋北段一小段-574-1地號等41筆` carries
`milestones_national.使用核發日期 = "291.08.02"`. ROC 291 parses to the year 2202. The
true value is `111.08.02` = 2022-08-02, and the same project carries
`使照核發日期 = 2022/08/02` and `links.permit.date = 2022-08-02`. **This is the only
ROC date above ROC 115 in the whole payload.** It corrupts the 申請 → 使用核發 duration
for that project to 70,461 days, which is what made the 70,461-day outlier appear in an
earlier draft.

**The current node is not a status.** The `is_current` node carries only the
*administrative* milestones of its own approval (核定日期, 申請計畫日期, 審議通過日期,
建照核發日期 on 127 projects). It carries no 開工日期, no 使照核發日期, and no
成果報備日期 at all. So a "current node" funnel reports 0 projects at 開工 and 0 at
使照, while 495 and 328 projects have reached those stages. **Read construction stages
from the project level, never from the current node.**

---

## 4. Measured: 資料時效

### 4.1 Awaiting approval — 97 projects

Computed from the payload with the pipeline's own predicate: a case carries an
application date and no approval date, and is neither terminal (自行撤回 / 已駁回 /
已失效) nor superseded.

| | Count |
| --- | --- |
| Projects awaiting an approval | **97** of 681 (14%) |

By district: 大安區 14, 南港區 12, 中山區 10, 信義區 10, 中正區 8, 北投區 8, 文山區 8,
松山區 7, 大同區 6, 內湖區 5, 士林區 5, 萬華區 4.

**The payload computes this exactly.** Cross-checked against the cache layer: 188 cache
directories hold an awaiting case, of which 181 are payload projects. The 97 are a
strict subset of the 181. The extra 84 hold a case whose approval arrived after the
cache was written, so the payload has no approval date for it yet. That is correct
behaviour, not a gap: a case the city has not approved is a live case, not stale data.

### 4.2 Cache older than the gazette — 6 projects

The signal is the `result.json` mtime, because no project cache stores a publication
date. This is the same rule `cache_is_stale_for()` applies at `urtpe/links.py:1629`.

| Project |
| --- |
| 中正區-河堤五小段-399地號等3筆 |
| 信義區-吳興一小段-330地號等43筆 |
| 信義區-吳興段二小段-163-2地號等2筆 |
| 大安區-復興段一小段-3地號等2筆 |
| 大安區-懷生段一小段-928地號等1筆 |
| 萬華區-萬華段一小段-519-2地號等35筆 |

Six of 681 is 0.9%. The viewer shows none of them today.

### 4.3 The ledger is not a freshness signal

`data/.link_cache/no_match_ledger.json` holds 74 entries. Each carries `last_probed`,
`twur_class`, and `view_ids_checked`.

| Check | Result |
| --- | --- |
| Ledger entries that are payload projects | 50 of 74 |
| Ledger entries whose own cache is stale | 25 of 74 |
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

### 4.4 The payload can proxy the stale set exactly — for now

| Predicate on project `links` | Matches | Equal to the stale set? |
| --- | --- | --- |
| `twur` empty | 60 | No — 54 extra |
| `taipei` empty | 7 | No — 1 extra |
| `case_milestones` empty | 7 | No — 1 extra |
| **`twur` empty AND `taipei` empty** | **6** | **Yes, exactly** |

No pipeline change is needed for the dashboard to show these 6. But this is a proxy,
not the definition. It will drift when a project gains a twur link.

---

## 5. Open decision 1 — the source of the cache-stale column

| Option | Correct? | Cost | Risk |
| --- | --- | --- | --- |
| **A** — copy `no_match_ledger.json` into `viewer/` | **No.** Marks 50, truth is 6 | Low | Wrong column |
| **B** — payload predicate `twur` empty AND `taipei` empty | Yes today | **None** | Drifts from the definition |
| **C** — emit the cache mtime into the payload | Yes | Medium | Write time ≠ fetch time |
| **D** — omit the column | n/a | None | Loses 6 projects |

### Option C in detail

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

**The risk in Option C.** `discover_project_links()` returns a cached result without a
network request, but `save_project_cache()` still rewrites `result.json` when
`twur_name` was missing from the cache. The mtime is therefore the **write** time, not
the **fetch** time. A run that rewrites a cache makes it look fresh, and the cache may
still hold old data. **This was not measured.** It needs a check before Option C ships.

### Recommendation

**Option C, after one more check on the write-time issue.** Option B is the fallback and
costs nothing. Option D is defensible: the dashboard ships with the 97 and the 6 follows.

**A practical path exists either way.** The dashboard can ship with the 97 awaiting
projects and add the 6 cache-stale projects later. The 97 need no pipeline change.

---

## 6. Measured: the viewer's list performance

Measured in Chrome against the live site, `https://happypig.github.io/urTPE/viewer/index.html`,
dispatching real `input` events against the `#filter` element and forcing layout with
`list.offsetHeight` so paint cost is included. Medians of 12 runs after 3 warm-up rounds.

### 6.1 Render cost scales with rows built, not with the query

| Query | Rows built | Median (ms) | Max (ms) |
| --- | --- | --- | --- |
| `zzzzz` | 0 | 4 | 29 |
| `大安區通化段四` | 2 | 11 | 20 |
| `大安區` | 86 | 28 | 264 |
| (empty) | 681 | **340** | 1,601 |

### 6.2 Where the time goes in a full render

| Step | Time |
| --- | --- |
| Build 681 DOM rows (detached) | 111 ms |
| Insert into the list | 6 ms |
| **Force layout and paint** | **1,029 ms** |

`list.scrollHeight` is **33,385 px** against a `list.clientHeight` of 920 px. The
browser does not virtualize, so it paints all 681 rows and discards most of them
off-screen. **Paint is the cost, not JavaScript.**

### 6.3 Typing costs less than one full render

Typing `大安區通化段` one character at a time: 86.4, 128.7, 21.5, 11.2, 8.7, 7.0 ms —
**263.5 ms for 6 keystrokes**. One full 681-row render costs 340 ms.

**This is why a debounce is a weaker win than it first appears.** The cost tracks the
row count. As the reader types, the list narrows, so most keystrokes render *fewer*
rows. A debounce mainly helps the worst case: clearing the box, or a query that matches
all 681.

### 6.4 The real fix is a windowed list

If the list renders only the rows near the viewport, a full render costs what the
86-row render costs — about 28 ms. Then debounce matters much less.

### 6.5 One measurement is missing

The off-screen paint test failed three times (empty result, internal error, then a
timeout that hung the renderer). It was abandoned. The row-count scaling and the
111 / 6 / 1,029 split identify the mechanism, but **no direct off-screen figure was
obtained.**

---

## 7. Measured: viewer accessibility and state gaps

Checked by search across `viewer/app.js` (1,641 lines):

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
| **Windowed list** | High — fixes 340 ms and 33,385 px | Medium | It is the refactor |
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

If the dashboard lists projects for drill-down, it inherits the same 340 ms cost. The
dashboard must render only visible rows.

---

## 9. Decided: paths and wiring

- **Pages:** `viewer/dashboard.html` + `viewer/dashboard.js`
- **`viewer/deploy.json`** must gain both, so `scripts/check_deploy.py` compares them
  against the served bytes. It currently lists 4 artifacts:
  `viewer/index.html`, `viewer/app.js`, `viewer/app.css`, `viewer/projects.data.js`.
- **`?v=` cache-bust token.** `viewer/index.html` loads
  `projects.data.js?v=20261015cb69` and `app.js?v=20261015cb69`. The dashboard needs
  its own matching token, or browsers serve a stale `dashboard.js` after a deploy.
- **A link from the viewer header**, and one back from the dashboard.
- **The dashboard reads `projects.data.js` directly.** No new data file, no pipeline
  change for the 行政時程 content.

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
7. **n is always shown next to every figure.** A median over 11 projects is not a
   district finding.

---

## 11. Separate, small: the compatibility-ideograph defect

6 of 1,442 records carry CJK compatibility ideographs — U+F901 (更), U+F963 (北),
U+FA26 (都), U+F9DD (利). `parse_name_id()` in `urtpe/cleanse.py:31` returns
`('', '', '', None)` on them, so the national portal index core falls through to the
crude string-strip fallback at `urtpe/links.py:503`.

The fix is an NFKC normalisation at the cleansing boundary, plus a test. **This is a
pipeline defect, independent of both the dashboard and the UI work.** It belongs in its
own change.

---

## 12. Repo housekeeping

- **`AGENTS.md` says "689 tests".** The real count is 1,001 collected, 1,000 passed, 1
  skipped. The skip is deliberate, at `tests/test_idempotent_flags.py:117`. Refresh the
  count when `AGENTS.md` is next touched.
- **`docs/viewer-UX.md` has 8 entries, §1 through §8, and all 8 shipped.** Each has an
  archived openspec change. The status table in that file still reads "design settled"
  and "ready" for several of them, which is stale. New UI work goes in as **§9 onward**;
  the file is append-only and entries must not be inserted above §8.
- **Deploy state at the time of writing:** all 4 artifacts FRESH.
- **A separate session was editing `docs/inspection-batchD.md` and adding
  `scripts/check_*.py` files.** These notes do not touch them.

---

## 13. What is needed to proceed

Two answers:

1. **The cache-stale column** — Option C (emit the mtime, after the write-time check),
   Option B (the payload predicate, free), or Option D (omit it).
2. **Part 1 scope** — the six steps in §8.3, or a smaller slice.

On those answers, the openspec changes open: one for the dashboard, one for the viewer
UI work, one for the compatibility-ideograph fix.

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

## Appendix A — how to reproduce the numbers

Every figure comes from `viewer/projects.data.js` at commit `43cb9bf` and the cache
directory `data/.link_cache/`. The computation is:

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
7. For 資料時效, compare each project's `data/.link_cache/<project_id>/result.json`
   mtime against 2026-10-15.

**Two cautions.** The ROC year 291 in §3.7 corrupts any duration that includes
`使用核發日期` for that one project. And the "current node" reading in §3.7 counts
construction stages as zero, which is wrong.
