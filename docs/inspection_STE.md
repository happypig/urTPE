# Project inspection — 2026-10-26

This document records the result of an inspection of the whole project. The
inspection looked at commit `20a2c92` and at the live viewer. Nothing is fixed yet.
Each finding gives its location and its fix.

**Update 2026-10-30.** A second session inspected the same repo. We merged its five
findings into this document. They are marked **[peer]**. The "Consolidated fix plan"
section at the end tells you what to do, in what order. Read that section first. It
replaces the older "Suggested order of work".

## Method

The inspection did three things:

1. Read the core modules. This includes `cli.py`, `lock.py`, `tripwire.py`,
   `coverage.py`, `archive.py`, `extract.py`, `links.py`, `emission.py`,
   `viewer.py`, `reconcile.py`, `poller.py`, `corpus.py`, `io.py`, `merge.py`,
   and `graph.py`.
2. Run the standing checks. See the table below.
3. Probe each suspicious spot with a small script. Record the result.

## Standing checks

All checks pass.

| Check | Command | Result |
| --- | --- | --- |
| Test suite | `python -m pytest` | 705 passed, 1 skipped, 75 s |
| Deploy freshness | `python scripts\check_deploy.py` | all 4 artifacts fresh |
| Viewer render path | `node scripts\viewer_smoke.js` | all checks passed |
| Silent-failure baseline | `python scripts\baseline_silent_failures.py` | items 1–4 caught; item 5 "yes" by design (D5) |

The gates that are wired all work. No data-corruption defect was found. One real
gap exists: the emission check is not wired. See P1.

# Part 1 — Pipeline findings

## P1 — The emission gate exists, but no code calls it

Priority 1. Fix this first.

`urtpe/emission.py` is a check for one failure. A rebuild without `--links` makes
a dataset with no link data. The run reports success. The viewer then shows the
missing data as "no data" (`urtpe/emission.py:4`).

The problem: `urtpe/cli.py:15` imports the module, but no code calls it. The
function `emission_faults` does not appear in any code path in `urtpe/`. Today, a
run without `--links` gives `links: {}` on all 694 projects and exits 0. The check
runs only when a person runs `scripts/baseline_silent_failures.py` by hand. The
unused import shows that someone planned this wiring and then lost it.

Fix:

1. Call `emission_faults(doc["projects"])` in `_run_locked`.
2. Put the call after `build_graph_document`, before `write_json`.
3. Report the faults in `review_report.txt`. Also print them.
4. Keep it as a warning. Do not refuse the run. `--links` stays advisory by
   design (D5).

## P2 — Should fix soon

### P2.1 — The lock has a race window

`urtpe/lock.py:69` does read, then check, then write. No step is atomic. Two runs
that start together both read "no lock". Then:

- On POSIX, both runs win. Two writers hold the lock at the same time.
- On Windows, one run crashes. `os.replace` gives `PermissionError` because both
  use the name `.lock.part`.

A two-thread probe reproduced the crash. Both outcomes break the contract: two
holders, or exit 1 instead of exit 5.

Fix: create the lock file with `os.open(path, O_CREAT | O_EXCL)`. This call is
atomic on both platforms. Map `FileExistsError` to a liveness re-check, then to
`LockHeld`. Remove the tmp-and-replace code.

### P2.2 — `--fresh` deletes state that is hard to rebuild

`urtpe/links.py:1791` calls `shutil.rmtree(self.cache_dir)` when you pass
`--fresh`. This deletes:

- `portal_index.json`. This file is the only path to the ~110 oldest portal
  entries.
- `no_match_ledger.json`.
- The 724 per-project `result.json` directories.

The coverage guard then refuses the run. But the delete has already happened. The
five `.link_cache_backup_*` directories exist because of this type of incident.

Fix: rename the cache to `.link_cache_backup_<date>`. Do not delete it.

### P2.3 — `data/taipei_case_ids.json` is necessary, but git does not track it

`discover_project_links` reads this file when the portal index has no match
(`urtpe/links.py:625`). The flag `--add-mapping-file` writes it. The content is a
curated, human-verified mapping. It is the same category as the tracked file
`data/twur_overrides.json`. But git does not track it, and the code hardcodes a
path relative to the current directory (`urtpe/cli.py:32`, `urtpe/links.py:415`).
A clone loses the file. No error appears.

Fix:

1. Add a `.gitignore` negation for the file.
2. Resolve the path from the repo root, or from `--outdir`.
3. Share one constant between `cli.py` and `links.py`.

## P3 — Housekeeping

Fix these in any order.

4. **The exit-code table is not complete.** Reconcile-block exits 2
   (`urtpe/cli.py:356`). "No records parsed" exits 1 (`urtpe/cli.py:231`). An
   unhandled exception exits 1. `AGENTS.md:30` gives only 0, 3, 4 and 5. Add
   code 2 at minimum.
5. **The tripwire page check can never fire.** `urtpe/cli.py:276` passes
   `tables_found=pages`. So the check at `urtpe/tripwire.py:90` always sees equal
   values. Real no-table detection lives in `TableStructureError`. Pass real
   counts, or remove the parameter. `AGENTS.md` currently lists this as a
   tripwire check. That is not correct.
6. **The portal-index crawl gives no completeness signal**
   (`urtpe/links.py:442`). A WAF-blocked crawl saves a smaller index with no
   warning. This index is the only path to the older identities. Fix: print a
   warning when the new index is much smaller than the old one.
7. **A corrected re-upload makes `verify()` fail forever.** `store()` replaces
   content with the same `gazette_id`. Then every older index entry fails its
   digest check on every future run. Fix: record superseded digests. Or accept
   the noise in code, with a comment that cites this finding.
8. **`AGENTS.md` is wrong about the viewer test.** It says "no browser test
   exists". But `scripts/viewer_smoke.js` tests the real render path, and it
   passes. Fix: say the test exists, and say a person must run it by hand.
9. **Uncommitted work names a file that git does not track.** The modified
   `AGENTS.md` describes `docs/dataset_completeness_audit.md`. Git does not
   track this file. Fix: commit both files together. Otherwise a clone gets an
   `AGENTS.md` that points at nothing.
10. **`FALLBACK_MAPPING_FILE` is defined twice.** `urtpe/cli.py:32` hardcodes the
    path. It must use the constant in `urtpe/links.py:415`. Also `.corpus_cache/`
    never deletes old member-set keys.

# Part 2 — Viewer findings

The live viewer at `https://happypig.github.io/urTPE/viewer/index.html` was
inspected in Chrome. The inspection used DOM reads and small scripts, plus three
screenshots.

The deployed build matches `HEAD`. The page works:

- Search works. All four filters work. Combined filters work.
- The detail pane works. The counter tracks the filters.
- No `undefined` or `NaN` text appears.
- The render path does not blank. The smoke test result also holds on the live
  build.
- Links open with `rel="noopener"`.
- The recovered rows (編號 188, 1005, 1131, 1206) show their provenance,
  including the A/B併案 flag.

## V1 — Two projects have a broken identity: `project_id` contains `等?筆`

Priority 1 in the viewer findings.

Two project ids are wrong:

- `松山區-寶清段一小段-51-13地號等?筆`
- `萬華區-崇仁新村青年段一小段-711-3地號等?筆`

Both anchors (編號 838 and 1375) have `land_count: null`. So `slug_for` printed
`?` (`urtpe/merge.py:124`). These ids go into `.link_cache/` directory names, the
alias table keys, and every future diff. A `?` in a directory name is legal, but
it is hostile. Also the identity is not the land core that the domain model
needs. The second node of each project holds the true count (1 and 2).

Fix:

1. When the anchor count is missing, take the count from another member of the
   family. Do this before you make the slug.
2. Add a review flag when no member has a count.

## V2 — The record table shows raw JSON and `null` in cells

The 20-column detail table prints:

- `地號清單` as `["336","336-1","339",…]`
- `地號別名` as `{}`
- `原地號數` as `null`

Fix:

1. Join the parcel list with `、` as prose.
2. Remove empty dict cells.
3. Show a missing count as an em dash (—).

The table is the "say what was read" surface. Raw encodings work against it.

## V3 — 195 cards show no stage chip

The chips work for three stages: `開工` red, `使照` green, `建照` amber. But 195
of 694 cards show no chip. A user reads this as "not started". That is wrong for
2026 approvals that are in 審查中 or 自行撤回. The data holds `case_schedules`
with 59 審查中 and 130 自行撤回.

Fix: add a grey `審查中`/`撤回` chip. Or write in the docs that no chip means
"no construction data", not "not started".

Note: the 未核定 badge logic is correct. It was checked against
`case_schedules` for all three cards where it fires.

## V4 — Three date formats appear in one detail pane

The pane shows three formats at the same time:

| Source | Example |
| --- | --- |
| Node dates | `2026-10-15` (ISO) |
| Taipei milestones | `2011/11/27` |
| National milestones | `100.12.20` (ROC) |

The job of the pane is to compare across sources. Mixed formats make that hard.

Fix: change all dates to ISO at render time. Keep the source strings verbatim in
the data file. Or label the ROC dates as ROC.

## V5 — A filter that hides the active project leaves the detail pane stale

Do this: select a project. Then search or filter, so the project leaves the
list. The detail pane still shows the excluded project. No message tells you.

Fix: when `activePid` is filtered out, dim the pane header, or clear the
selection. Low harm. But it reads as a bug.

## V6 — The 20-column table has no sticky header

The table is 4,400 px tall. It scrolls horizontally. But `<th>` has
`position: static`. After the first screen, the columns have no names.

Fix: set `position: sticky; top: 0` on `th`. Give it a solid background.

## V7 — The milestone bars show no information

Screenshots show what look like progress bars next to each milestone. In the DOM
they are `<dt>`/`<dd>` rows. Every bar has the same full width. No bar encodes a
date or a duration.

Fix: make the bar extent meaningful. Use the min→max milestone span from the
階段辦理過程 data. Or remove the bar shapes.

## V8 — The list order is 編號 of the newest approval, ascending

`renderList` sorts by the current node's `recno`. This is a gazette position. A
user cannot predict it. A 2008 approval sits above a 2026 one, because its 編號
is lower. Every re-ingestion re-orders the list. `AGENTS.md` says: 編號 is a
coordinate, not an identity.

Fix: sort by anchor date, descending. Newest first. Today 161 開工 cards sit
above the fold by accident, not by design.

## V9 — No keyboard or screen-reader access

Every list item is a `<div onclick>`. There is no `tabindex`, no
`role="button"`, no `aria-expanded` on the filter buttons, and no label on the
search input. The whole list is unreachable by keyboard.

Fix:

1. Give each item `role="button" tabindex="0"`.
2. Add an Enter and Space key handler to items.
3. Add `aria-expanded` to the four dropdown buttons.
4. Add `aria-label` to the search input.

## V10 — The data file is 9.1 MB

`projects.data.js` is 9.1 MB uncompressed. GitHub Pages serves it as 904 KB
gzipped. Desktop is fine. First paint on a phone is slow.

Fixes, cheapest first:

1. Do nothing about gzip. GitHub Pages already compresses.
2. Shorten numeric precision in fields such as `Base_Area`.
3. Split per-project detail into chunks by district. Load on demand.

## V11 — Stage chips and area colours have no accessible name

The stage chip is a colour plus two characters. But its `title` attribute is
`null`. Hover and screen readers get nothing. The base-area colour scale has the
same problem.

Fix: add `title` and `aria-label`. The text must name the stage and the date.

## V12 — Each click re-renders all 694 list items

`el.onclick` calls `renderList()`. This clears `innerHTML` and rebuilds all 694
items. It does this only to move the `.active` class. This takes 73 ms. It is
harmless today. But it adds to the V8 re-sort cost.

Fix: change the class on two nodes only. Do not re-render.

## What was checked and is sound

- Header counts, 統計至 label, and cache-bust `?v=` on both scripts.
- Search matches parcel, district, and implementer. `336地號` gives 1 result.
  `永陞` gives 7.
- All four filters. Combined filtering. Per-button count badge `地區（1）`.
  Panel 全選/清除. The `顯示 N / 694` counter.
- Detail pane: version graph with per-track chains, stage bands, construction
  milestones with source badges (國/北), the 20-column record table, 相關連結
  with `rel="noopener"`, and recovery provenance.
- Console: no errors from page code. Three exceptions are browser-extension
  noise.
- No `undefined` or `NaN` text anywhere. No node lacks the `links` key.

# Suggested order of work

This section is old. Read the "Consolidated fix plan" below instead.

1. Wire the emission check (P1). Write tests first, per the openspec gate.
2. Fix the lock (P2.1). It guards every other fix.
3. Make `--fresh` back up instead of delete (P2.2).
4. Track `taipei_case_ids.json` (P2.3).
5. Fix the housekeeping items (P3). Any order.
6. Viewer: V1 first (identity corruption). Then V2 and V4 (wrong text shown).
   Then V3, V5, V6, V7, V8. Then V9 to V12.

# Peer-session findings — 2026-10-30 [peer]

A second session inspected the same repo. We checked each item against the code.
All are real. Here are the five findings, in priority order.

## F1 — `stage_index` is read but never written [peer]

Priority 1. This is a hidden bug.

What happens:

1. `urtpe/cli.py:126` and `scripts/run_links_from_js.py:52` read
   `node["stage_index"]`. The default is `-1`.
2. `urtpe/graph.py` never writes a `stage_index` key into the node. So a rebuild
   with `--from-js` loads every node with `-1`.
3. `urtpe/graph.py:108` groups nodes by `(stage_index, track)`. With `-1` on all
   nodes, one track becomes one group. The 區段 branch edges can never form.

We checked the emitted data. The payload has 0 section edges. Only 1 node in the
whole dataset carries an `area_section`. So the bug is hidden today. It fires the
first time the city publishes 甲/A/B區段 rows.

Fix:

1. Write the `stage_index` key from `build_project_graph`.
2. Also derive the index from the stage text on load, when the key is missing.
   This repairs the data files that already exist. The `ymd` fix at
   `urtpe/cli.py:83` is the pattern to copy.
3. Write the tests first. One test: a family with 甲/A/B `area_section` values on
   different stages must form section edges after a `--from-js` rebuild. Another
   test: emit, load, emit again. The two outputs must be identical.

This fix needs an openspec change.

## F2 — One test failed once, then passed four times [peer]

Do not chase this now.

`tests/test_viewer_degrades.py::test_dropping_an_optional_field_does_not_break_the_render[rewards]`
failed on 2026-10-06. It passed the next four full runs. We re-ran it on
2026-10-30. It passed. Nobody found the cause.

What to do:

1. Add a one-line comment on the test. Note the 2026-10-26 observation.
2. If it fails again, run the file 50 times in a loop. Reproduce first. Then fix.

## F3 — Three dead functions, but 34 green tests say they are alive [peer]

Priority 3. Delete the code, delete the tests.

| Function | Real location | Tests | Decision |
| --- | --- | --- | --- |
| `date_order_report` | `urtpe/ordering.py:107` | 18 refs | delete. No live spec cites it (checked 2026-10-30). |
| `classify_case_outcome` | `urtpe/links.py:1407` | 9 refs | delete with its tests |
| `project_twur_class` | `urtpe/links.py:1422` | 7 refs | delete with its tests |

Note: the peer report said `date_order_report` is in `urtpe/links.py`. That is
wrong. It is in `urtpe/ordering.py:107`.

No production code calls any of the three. The green tests give a false sense of
coverage. Fix: delete each function with its tests.

Dedup check, done before the delete: `date_order_report` deduplicates on 編號 so
repeated page heads do not inflate the count. The wired path keeps this. The reader
deduplicates first (`_dedupe_by_recno`, `urtpe/extract.py:776`). So the records at
`urtpe/cli.py:384` are already deduplicated before `departures_from_descending`
counts. Deleting the function loses nothing.

## F4 — A block that checks for data that never exists [peer]

Priority 4. Trivial cleanup.

`urtpe/cli.py:72-75` skips nodes marked `orphan`, `recno < 0`, or `孤兒節點`. The
emitter never writes these markers. The 969 orphans live in `links.orphan_nodes`.
The viewer makes those nodes itself. So the block never fires.

Fix: delete the block. Batch this with F3 in one commit.

## F5 — Work in the working tree that git does not hold [peer]

Priority 5. Commit it first. It takes five minutes.

The working tree holds:

- `AGENTS.md`, modified. It cites the audit doc.
- `docs/dataset_completeness_audit.md`, untracked.
- `docs/inspection.md` and `docs/inspection_STE.md`, untracked. This document is
  one of the two.

Fix: one commit with all four files. Then the citation in `AGENTS.md` resolves.

# Consolidated fix plan

This plan merges both sessions' findings. Do the steps in this order.

## Step 1 — Commit the docs (F5)

One `docs:` commit. Add these four files: `AGENTS.md`,
`docs/dataset_completeness_audit.md`, `docs/inspection.md`,
`docs/inspection_STE.md`.

## Step 2 — Delete dead code (F3 + F4)

One `chore:` commit:

1. Delete `date_order_report` with its tests. The dedup guarantee is safe: the
   reader already deduplicates (`urtpe/extract.py:776`).
2. Delete `classify_case_outcome` and `project_twur_class` with their tests.
   About 16 tests go away. Say this in the commit message.
3. Delete the block at `urtpe/cli.py:72-75`.
4. Run the suite. Write the new test count into `AGENTS.md`.

## Step 3 — Openspec change A: `emit-stage-index` (F1)

This is the most valuable bug fix in the plan. Write the tests first. Then make
the two changes in F1. Then apply the openspec flow: proposal, design, tasks,
apply, archive.

## Step 4 — Openspec change B: `land-core-slug-fallback` (V1)

Two project ids contain `等?筆`. Both anchors have `land_count: null`
(`urtpe/merge.py:124`). Write the tests first. Then:

1. Before the code makes the slug, take the count from another member of the
   family.
2. Add a review flag when no member has a count.

This needs a spec delta in `case-merging`. The spec pins how the code derives
`project_id`.

## Step 5 — Openspec change C: `viewer-stage-chip-coverage` (V3 + V2 + V4)

V3 changes spec'd behaviour. The spec at `history-graph/spec.md:255` says:
"Projects with none of the three dates SHALL show no badge". So V3 needs a spec
delta. Bundle V2 (raw JSON in table cells) and V4 (three date formats) into the
same change. They share the test group and the file.

The work:

1. V3: add a grey `審查中`/`撤回` chip. Update the spec scenario.
2. V2: join the parcel list with `、`. Remove empty dict cells. Show a missing
   count as an em dash (—).
3. V4: change all dates to ISO at render time. Keep the source strings verbatim
   in the data file.

## Step 6 — Direct fixes, no spec delta

These are ordinary `fix:` commits with tests:

1. Wire the emission check into `_run_locked` (P1). The spec already asks for
   this report. Only the wiring is missing.
2. Fix the lock race with `O_CREAT | O_EXCL` (P2.1).
3. Make `--fresh` rename to `.link_cache_backup_<date>` instead of delete
   (P2.2).
4. Track `taipei_case_ids.json` in git. Resolve its path from the repo root.
   Share one constant (P2.3).
5. Fix the housekeeping items P3.1 to P3.6 and P3.8 to P3.10.

## Step 7 — Watch, do not fix

1. F2, the one-time flake. See F2 above.
2. V5 to V12, the viewer polish items. Fix them when you touch those files
   anyway.
3. The peer session deferred three items by design: no CI, no browser-render
   test, and the baseline item 6 numbers. Do not treat them as oversights.

## Open questions with the peer session

All answered 2026-10-30. Nothing is open:

1. Test count: the peer's 652 came from an older tree state. **706 collected
   (705 passed, 1 skipped) is the trusted baseline.** Both sides confirmed.
2. No live spec cites `date_order_report`. Delete is safe.
3. No objection to deleting `classify_case_outcome` and `project_twur_class`.

## Rules for every fix

1. Write the test first. This is the openspec gate.
2. Do not bypass a gate. Fix its blind spot, and add the test.
3. Do not key anything durable on 編號. It is a coordinate, not an identity.
4. Do not repair absent data by inference. Exclude and name it.
