# Project inspection — 2026-10-26

An evaluation of the whole project after commit `20a2c92`. This document records the
findings. Nothing is fixed yet; each finding names its location and its fix.

**2026-10-30 update:** consolidated with a second session's independent findings
(stage_index latent bug, dead code, vestigial orphan-skip, one test flake, uncommitted
docs). The merged, prioritized execution plan is in "Consolidated fix plan" at the
end of this document; it supersedes the per-part ordering. Findings from that session
are marked **[peer]**.

## Method

- Read the core modules: `cli.py`, `lock.py`, `tripwire.py`, `coverage.py`,
  `archive.py`, `extract.py`, `links.py`, `emission.py`, `viewer.py`, `reconcile.py`,
  `poller.py`, `corpus.py`, `io.py`, `merge.py`, `graph.py`.
- Run the standing checks (table below).
- Probe each suspicious spot with a small script, and record the result.

## Standing checks (all pass)

| Check | Command | Result |
| --- | --- | --- |
| Test suite | `python -m pytest` | 705 passed, 1 skipped, 75 s |
| Deploy freshness | `python scripts\check_deploy.py` | all 4 artifacts fresh |
| Viewer render path | `node scripts\viewer_smoke.js` | all checks passed |
| Silent-failure baseline | `python scripts\baseline_silent_failures.py` | items 1–4 caught; item 5 "yes" by design (D5) |

The gates that are wired all work. No data-corruption defect was found. The one real
gap is the unwired emission check.

## P1 — the emission gate exists but is never called

`urtpe/emission.py` is the check for one specific failure: a rebuild without `--links`
emits a dataset with no link data, reports success, and the viewer presents absence as
"no data" (`urtpe/emission.py:4`). The module is imported at `urtpe/cli.py:15`, but no
code path calls it — `emission_faults` appears nowhere in `urtpe/`. A no-`--links` run
today produces `links: {}` on all 694 projects and exits 0.

The check runs only when someone runs `scripts/baseline_silent_failures.py` by hand.
The dead import suggests the wiring was intended and then lost.

Fix: call `emission_faults(doc["projects"])` in `_run_locked` after
`build_graph_document`, before `write_json`. Report the faults in `review_report.txt`
and print them. Keep it a warning, not a refusal — `--links` stays advisory by
design (D5).

## P2 — should fix

### 1. The lock acquire has a race window

`urtpe/lock.py:69` does read → check → write with no atomicity. Two runs that start
together both read "no lock". On POSIX both win. On Windows the loser crashes with
`PermissionError` from `os.replace` on the shared `.lock.part` name. A two-thread
probe reproduced the crash. Either way the contract breaks: two holders, or exit 1
instead of exit 5.

Fix: create the final lock with `os.open(path, O_CREAT | O_EXCL)`. That call is atomic
on both platforms. Map `FileExistsError` to a liveness re-check and then `LockHeld`.
Drop the tmp-and-replace dance.

### 2. `--fresh` destroys durable state

`urtpe/links.py:1791` calls `shutil.rmtree(self.cache_dir)` on `--fresh`. That deletes
`portal_index.json` (the only reachability path for the ~110 oldest portal entries),
`no_match_ledger.json`, and the 724 per-project `result.json` directories. The coverage
guard then refuses the run, but the wipe has already happened. The five
`.link_cache_backup_*` directories exist because of this class of incident.

Fix: rename the cache to a timestamped `.link_cache_backup_<date>` instead of
deleting it.

### 3. `data/taipei_case_ids.json` is load-bearing but untracked

`discover_project_links` falls back to this file when the portal index misses
(`urtpe/links.py:625`), and `--add-mapping-file` writes it. The content is a curated,
human-verified mapping — the same category as the tracked `data/twur_overrides.json`.
But git does not track the file, and the path is hardcoded relative to the CWD
(`urtpe/cli.py:32`, `urtpe/links.py:415`). A clone loses it with no error.

Fix: add a `.gitignore` negation for the file. Resolve the path from the repo root or
`--outdir`, and share one constant between `cli.py` and `links.py`.

## P3 — housekeeping

4. **The exit-code table is incomplete.** Reconcile-block exits 2 (`urtpe/cli.py:356`);
   "no records parsed" exits 1 (`urtpe/cli.py:231`); an unhandled exception exits 1.
   `AGENTS.md:30` documents only 0, 3, 4 and 5. Add code 2 at minimum.
5. **The tripwire's page check is inert as wired.** `urtpe/cli.py:276` passes
   `tables_found=pages`, so the check at `urtpe/tripwire.py:90` can never fire. Real
   no-table detection lives in `TableStructureError`. Pass real counts or remove the
   parameter. `AGENTS.md` currently lists this as a tripwire check.
6. **The portal-index crawl has no completeness signal** (`urtpe/links.py:442`). A
   WAF-shortened crawl silently saves a smaller index — the only path to the older
   identities. Warn when the new index is much smaller than the one it replaces.
7. **A corrected re-upload poisons `verify()` forever.** `store()` replaces
   same-`gazette_id` content; every older index entry then fails its digest check on
   every future run. Record superseded digests, or accept the noise in code with a
   comment that cites this finding.
8. **`AGENTS.md` is stale on the viewer test.** It says "no browser test exists". But
   `scripts/viewer_smoke.js` exercises the real render path and passes. Say it exists,
   and say it runs by hand.
9. **Uncommitted work names an untracked file.** The modified `AGENTS.md` describes
   `docs/dataset_completeness_audit.md`, which git does not track. Commit both
   together, or a clone gets an `AGENTS.md` that points at nothing.
10. **`FALLBACK_MAPPING_FILE` is defined twice.** `urtpe/cli.py:32` hardcodes the path
    instead of using `urtpe/links.py:415`. Also `.corpus_cache/` never prunes old
    member-set keys.

## Viewer inspection — 2026-10-26 (live, `https://happypig.github.io/urTPE/viewer/index.html`)

The deployed build was inspected in Chrome, by DOM reads and scripted probes, with
three screenshots. The deployed artifacts all match `HEAD`. The page works: search,
all four filters, cross-filtering, and the detail pane behave; the counter tracks;
no `undefined`/`NaN` text; the render path does not blank (the smoke test holds on
the live build too); links open with `rel="noopener"`; the recovered rows (編號 188,
1005, 1131, 1206) render their provenance including the A/B併案 ambiguity. The
deployment is one release ahead of the repo check expectations — all healthy.

### V1 — two projects carry a broken identity: `project_id` contains `等?筆`

`松山區-寶清段一小段-51-13地號等?筆` and `萬華區-崇仁新村青年段一小段-711-3地號等?筆`.
Both anchors (編號 838, 1375) have `land_count: null`, so `slug_for` rendered `?`
(`urtpe/merge.py:124`). These ids go into `.link_cache/` directory names, the alias
table's keys, and every future diff. A `?` in a directory name is legal but hostile,
and the identity is not the land core the domain model requires. The second node of
each holds the true count (1 and 2). Fix: when the anchor's count is missing, take
it from another member of the family before slugging; add a review flag when no
member carries a count.

### V2 — the record table leaks raw JSON and `null` into cells

The 20-column detail table prints `地號清單` as `["336","336-1","339",…]`,
`地號別名` as `{}`, and `原地號數` as `null`. Three fixes: join the parcel list with
`、` as prose, drop empty dict cells, and render a missing count as an em dash. The
table is the "say what was read" surface; raw encodings undercut it.

### V3 — one stage-chip color encodes nothing: 195 cards show no chip

`開工` red / `使照` green / `建照` amber are fine, but 195 of 694 cards show nothing,
which reads as "not started" and is wrong for 2026-era approvals still in 審查中 or
自行撤回. The data holds `case_schedules` (59 審查中, 130 自行撤回). Fix: add a grey
`審查中`/`撤回` chip, or document that silence means "no construction data", not
"not started". The 未核定 badge logic itself is correct — verified against
`case_schedules` for all three cards it fires on.

### V4 — three date formats inside one detail pane

Node dates render ISO (`2026-10-15`), Taipei milestones render `2011/11/27`, and
national milestones render ROC dots (`100.12.20`). All three appear within one
screen. Normalise to ISO at render time (the source strings stay verbatim in the
data), or label the ROC ones. The comparison across sources is the pane's whole job.

### V5 — a filter that hides the active project leaves the detail pane stale

Select a project, then search or filter so it leaves the list: the detail pane keeps
showing the excluded project with no cue. Fix: when `activePid` is filtered out,
dim the pane header or clear the selection. Low harm, but it reads as a bug.

### V6 — the 20-column table has no sticky header

The table is 4,400 px tall and horizontally scrollable, but `<th>` is
`position: static`. Past the first screenful the columns are unlabelled. Fix:
`position: sticky; top: 0` on `th`, with a solid background.

### V7 — milestones render as plain rows; the bars seen in screenshots are decorative

The screenshot showed what look like progress bars next to every milestone. In the
DOM they are `<dt>/<dd>` rows; every bar has the same full width, so no bar encodes
a date or a duration. Either make the bar's extent meaningful (min→max milestone
span, per the 階段辦理過程 data) or remove the bar shapes.

### V8 — list order is 編號 of the newest approval, ascending

`renderList` sorts by the current node's `recno`. That is gazette position, not
anything a user can predict: a 2008 approval sits above a 2026 one because its 編號
is lower, and every re-ingestion re-shuffles the list. AGENTS.md itself says 編號 is
a coordinate, not an identity. Fix: sort by anchor date descending, newest first.
The current order also puts 161 開工 cards above the fold by accident, not design.

### V9 — keyboard and screen-reader access

Every list item is a `<div onclick>`: no `tabindex`, no `role="button"`, no
`aria-expanded` on the filter buttons, no label on the search input. The whole list
is unreachable by keyboard. Fix: `role="button" tabindex="0"` plus an Enter/Space
handler on items, `aria-expanded` on the four dropdowns, `aria-label` on search.

### V10 — payload: 9.1 MB of JSON, shipped as 904 KB gzipped

`projects.data.js` is 9.1 MB uncompressed. Fine on desktop; slow first paint on a
phone. The `schema_version` 2 document duplicates per-node fields the viewer reads
once. Fixes in order of cost: (a) emit the viewer file with `indent=None` (already
true) and minify numeric precision in `Base_Area` etc.; (b) split per-project detail
into lazy per-district chunks loaded on demand; (c) gzip pre-compression is already
served by GitHub Pages, so no action needed there.

### V11 — construction-stage chips and area colour carry no accessible name

The stage chip is colour + 2 chars (開/使/建 render as short text), but the `title`
attribute is `null`, so hover and screen readers get nothing. Same for the
base-area colour scale. Fix: `title` (and `aria-label`) naming the stage and date.

### V12 — 73 ms list re-render on every click

`el.onclick` calls `renderList()` (all 694 items, `innerHTML=""` first) only to move
the `.active` class. Harmless today, but it compounds with V8's re-sort. Fix:
toggle the class on two nodes instead of re-rendering.

### What was checked and is sound

- Header counts, 統計至 label, cache-bust `?v=` on both scripts.
- Search matches parcel, district, and implementer (`336地號` → 1, `永陞` → 7).
- All four filters, combined filtering, per-button count badge `地區（1）`, panel
  全選/清除, and the `顯示 N / 694` counter.
- Detail pane: version graph with per-track chains, stage bands, construction
  milestones with source badges (國/北), 20-column record table, 相關連結 with
  `rel="noopener"`, and recovery provenance.
- No console errors from page code (three extension-noise exceptions only).
- No `undefined`/`NaN` text anywhere; 0 nodes without a `links` key.

## Peer-session findings — 2026-10-30 [peer]

An independent session working the same repo reported five items. All were verified
against the working tree before being merged here.

### F1 — `stage_index` is read but never emitted [peer] — P1

`urtpe/cli.py:126` and `scripts/run_links_from_js.py:52` read `node["stage_index"]`
with a `-1` default. `build_project_graph` never emits a `stage_index` key, so on a
`--from-js` rebuild every node loads as `-1`. Then the section-branch grouping at
`urtpe/graph.py:108` (`stage_groups.setdefault((r.stage_index, r.track), ...)`)
collapses every stage of a track into one group, and 區段 branch edges can never form
on a rebuild from emitted state. Verified: 0 section edges in the payload, 1 node
corpus-wide carries `area_section` (`"B"`). Latent today; fires the first time the
city publishes 甲/A/B區段 rows.

Fix: emit `stage_index` from `build_project_graph`, and derive it from the stage
text on load when the key is missing (mirrors the `ymd` fix documented at
`urtpe/cli.py:83`). Openspec change with a test that section edges form when a
區段 family exists.

### F2 — one unexplained test flake [peer] — watch, do not chase

`tests/test_viewer_degrades.py::test_dropping_an_optional_field_does_not_break_the_render[rewards]`
failed once on 2026-10-06, then passed four consecutive full runs (re-run clean
2026-10-30). Root cause never found. Treat as an open stability question. Do not
chase it unless it fires again.

### F3 — dead code with green tests and no production callers [peer] — P3

Three functions, zero production callers, kept alive only by their tests:

| Function | Location | Tests | Decision |
| --- | --- | --- | --- |
| `date_order_report` | `urtpe/ordering.py:107` (not `links.py` — the peer's report had this wrong) | 18 refs | delete — confirmed no live spec cites it (2026-10-30, peer verified; only archived-change prose mentions it) |
| `classify_case_outcome` | `urtpe/links.py:1407` | 9 refs | delete with tests |
| `project_twur_class` | `urtpe/links.py:1422` | 7 refs | delete with tests |

Deleting removes the false sense of coverage the green tests create.

**Dedup guarantee, checked before the delete (peer's one caution):** the archived
tasks document that `date_order_report` deduplicates on 編號 so repeated page heads
do not inflate the departure count. The wired path keeps that guarantee at a lower
layer: `extract_pdf` calls `_dedupe_by_recno` (`urtpe/extract.py:776`, first
occurrence wins), so `records` at `urtpe/cli.py:384` are already deduplicated before
`departures_from_descending` counts. The reader-level dedup is additionally pinned by
the archived change's own test 4.6. Deleting `date_order_report` loses the guarantee
nowhere — it was moved into the reader on 2026-10-06.

### F4 — vestigial orphan-skip block [peer] — P4

`urtpe/cli.py:72-75` skips nodes marked `orphan` / `recno < 0` / `孤兒節點`. The
emitter never writes those markers: 969 orphans live in `links.orphan_nodes` and are
synthesized client-side. Trivial cleanup; batch with F3.

### F5 — uncommitted work in the working tree [peer] — P5

`AGENTS.md` modified; `docs/dataset_completeness_audit.md`, `docs/inspection.md` and
`docs/inspection_STE.md` untracked. Provenance: the two inspection docs are this
session's 2026-10-26 output. Committed together as `0bc6ed0` (2026-10-30), so the
`AGENTS.md` citation resolves.

## Archive findings — 2026-10-30 [peer amendment, independently verified]

While committing step 1, an unattributed amendment to `dataset_completeness_audit.md`
appeared in the shared working tree (describing a quarantined 2026-09-24 gazette).
The peer session disclaimed authorship of the amendment; the user attributed it to a
separate OpenCode session doing `recover-truncated-rows-via-api` work. The claims
were then verified against the archive directly — both hold:

1. **The lost 2026-09-24 gazette exists, quarantined under a wrong name.**
   `urtpe-gazettes/skipped since abnormal SN/核定案件-2026-10-02.pdf` hashes to
   `5066b108…` — byte-identical to the digest the poller logged for gazette
   2026-09-24 on 2026-10-06 — and its 統計至 reads 115/9/24 (2026-09-24), 246 pages.
   The archive holds six indexed publications; the index's 09-24 loss
   (`b1b37b0 docs: record the 09-24 deletion and what it cost`) is recoverable by
   moving this file into place under its correct name.
2. **The poller is stalled, but the newest PDF is not a new publication.**
   Last `poll_log.jsonl` record is 2026-10-06 (24 days quiet). `核定案件-2026-10-30.pdf`
   sits uningested in the archive root, but it is byte-identical to
   `核定案件-2026-10-23.pdf` (sha256 `9b80a6bc…` both) and its 統計至 reads
   115/10/15 = 2026-10-15 — a re-upload of the already-ingested 10-15 gazette. Per
   design D1 (hash decides), it requires no ingestion; running the poller should
   classify it `reuploaded` and write the dated record D3 asks for.

Neither is a step in the fix plan; both belong to the OpenCode session's
`recover-truncated-rows-via-api` scope. Recorded here so the poller stall is not
misread as a missed publication (it is a missed *check*), and so the quarantine's
true identity is on record before anyone restores it.

## Suggested order of work

Superseded by "Consolidated fix plan" below. Kept for reference.

1. Wire the emission check (P1). Tests first, per the openspec gate.
2. Fix the lock (P2.1). It guards every other fix.
3. Make `--fresh` back up instead of delete (P2.2).
4. Track `taipei_case_ids.json` (P2.3).
5. Housekeeping (P3), in any order.
6. Viewer: V1 first (identity corruption), then V2 and V4 (wrong text shown),
   then V3/V5/V6/V7/V8, then V9–V12.

## Consolidated fix plan — 2026-10-30

Merged from both sessions. One baseline question is open with the peer session
(suite count 652 vs 706 at the same commit); it gates nothing below.

### Commit 1 — docs (P5 + F5, one `docs:` commit)

Add `AGENTS.md`, `docs/dataset_completeness_audit.md`, `docs/inspection.md`,
`docs/inspection_STE.md` together, so the citation in `AGENTS.md` resolves.

### Commit 2 — cleanup (F3 + F4, one `chore:` commit)

1. Check whether any spec cites `date_order_report`'s report shape. If none,
   delete it; if one does, keep it as the spec's named entry point.
2. Delete `classify_case_outcome` and `project_twur_class` with their tests
   (≈16 tests gone; explain the count drop in the commit message).
3. Delete the orphan-skip block at `urtpe/cli.py:72-75`.
4. Re-run the suite; confirm the new count and refresh the number in `AGENTS.md`.

### Openspec change A — `emit-stage-index` (F1, test-first)

Highest-value bug in the merged list. Emit `stage_index` from
`build_project_graph`; derive it from stage text in `_load_projects_from_js` when
the key is absent, so already-deployed `projects.data.js` files repair on load.
Test first: a fixture family with 甲/A/B `area_section` across distinct stages
must form section edges after a `--from-js` rebuild; assert emit→load→emit
round-trip losslessness.

### Openspec change B — `land-core-slug-fallback` (V1, test-first)

Two `project_id`s contain `等?筆` because both anchors have `land_count: null`
(`urtpe/merge.py:124`). Fall back to another family member's count before
slugging; review-flag when no member carries a count. Delta touches
`case-merging` (identity derivation is spec'd there).

### Openspec change C — `viewer-stage-chip-coverage` (V3 + V2 + V4, test-first)

V3 needs a spec delta (it contradicts `history-graph/spec.md:255` "SHALL show no
badge"). Bundle V2 (raw JSON/`null` in table cells) and V4 (three date formats in
one pane) — same test group, same file.

### Direct `fix:` commits (no spec delta needed)

- P1: wire the emission check into `_run_locked` (the spec already requires the
  report at `official-link-discovery/spec.md:253`; the gap is wiring).
- P2.1: atomic lock acquire via `O_CREAT | O_EXCL`.
- P2.2: `--fresh` renames to `.link_cache_backup_<date>` instead of rmtree.
- P2.3: track + root-path `taipei_case_ids.json`, one shared constant.
- P3.1–P3.6, P3.8–P3.10: exit-code docs, inert tripwire parameter, crawl
  completeness warning, AGENTS.md viewer-test wording.

### Watch, do not fix

- F2 (one-time flake): comment on the test citing the observation; reproduce
  with a tight loop only if it fires again.
- V5–V12 (viewer polish): fix opportunistically, lowest priority.
- Peer-deferred items (no CI, no browser-render test, baseline item 6 numbers):
  recorded as by-design in both sessions.

### Open with the peer session

All three questions answered 2026-10-30 (task `99fe037a`); the plan below stands
unchanged:

1. Suite baseline: the peer's 652 came from a tree state predating commits
   `33ce713`/`b40bb15`. **706 collected (705 passed, 1 skipped) at `20a2c92` is the
   canonical baseline**, confirmed by both sides.
2. No live spec cites `date_order_report`'s shape — only prose in the archived
   `2026-10-06-gazette-ingest-cadence` change. It is deletable; the dedup guarantee
   it carried moved into the reader (`_dedupe_by_recno`, `extract.py:776`), verified
   above.
3. No objection to deleting `classify_case_outcome` / `project_twur_class`.
