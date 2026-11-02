# Project inspection — 2026-10-26 · consolidated 2026-11-01

An evaluation of the whole project, started at commit `20a2c92` and extended across
three sessions and the completed `restore-2026-09-24-gazette` change. This document
is the single execution board: every finding is recorded once, in one of three
states — **done**, **queued** (with its openspec change), or **watch** — and the
"Execution order" section is the sequenced, actionable plan. Evidence sections are
appendices: they hold the verification detail behind each finding and do not need
re-reading to execute the plan.

**Update history:** 2026-10-26 original inspection (pipeline P1–P3, viewer V1–V12) ·
2026-10-30 peer session F1–F5, the audit doc's data-layer findings, the archive
verification · 2026-10-31 the 09-24 restoration executed · 2026-11-01 TAB-2 session
G1–G5.

## State of the board

| Check | Result at last full run |
| --- | --- |
| Test suite | 842 passed, 1 skipped (843 collected) |
| Deploy freshness | all 4 artifacts fresh (`scripts\check_deploy.py`) |
| Viewer render path | `node scripts\viewer_smoke.js` passes |
| Silent-failure baseline | items 1–4 caught; item 5 "yes" by design (D5) |
| Archive | 7 publications, chain whole, 09-24 restored |
| Acquisition | **weekly scheduled task `urtpe-poll` live** (Mondays 06:30); channel verified healthy 2026-11-01 (`reuploaded`) |
| Emission | 2026-10-15, 1,442 raw / 1,442 clean / 694 projects, 0 residuals (188 recovered 2026-11-01) |

## Execution order — the integrated plan

Execute top to bottom. Each item names its finding, its form (direct commit or
openspec change), and its gate.

### Wave 0 — done (recorded so the board is complete)

| Item | Finding | Commit |
| --- | --- | --- |
| Docs tracking | F5 (uncommitted docs; AGENTS.md citation resolves) | `0bc6ed0` |
| Dead-code cleanup | F3 + F4 (three functions + tests deleted, orphan-skip block removed) | `d6c77b3` |
| Archive verification | the quarantined 09-24 identity + the 10-30 re-upload | `601b9bb` |
| 09-24 restoration | Openspec change D (re-file, dual-path ingest, chain repair, calendar correction, P3.7 superseded digests, forward re-emission) | `9ad2a9d`, `bb93106`, archived `9028780` |
| TAB-2 findings folded | G1–G5 verified and recorded | `4886252` |

### Wave 1 — unblock the recovery follow-ups (no gate, no user decision)

1. **G3 — regenerate the stranded-count report.** — **DONE 2026-11-01.** The three
   numbers were three different reference payloads, all correct for their moment:
   doc 23 (aliases.unmatched, measured vs the 8/11 baseline), `aliases.orphaned` 27
   (built 2026-10-07 vs the 10-01 payload, pre-forward-re-emission), plan note 32
   (stale 10-26 reading). Regenerated against the current tree: the forward
   re-emission's `--links` re-cached everything under current ids, so
   `build_project_aliases.py` (prev = the pre-restore 10-15 payload at `532236e`,
   current = live) now reports **1 orphaned/unmatched — 永昌段46-4, the transient
   residual family**; the remaining 32 dirs-without-live-projects are
   old-generation caches from identities that left the list long ago (the known
   portal-history churn, documented in the regenerated
   `docs/stranded-cache-dirs.md`). The doc now says **1**, agreeing with the
   aliases file. `data/project_aliases.json` regenerated (committed).
2. **Rerun the 10-15 ingestion when gis.uro recovers** — **DONE 2026-11-01.**
   API probe passed (family returned 15 members instantly), ingestion exit 0:
   **RECOVERED includes 編號 188** (`R089213-02`, api 10403071, date exact) —
   all four recovery rows back (188/1005/1131/1206), **INCOMPLETE: 0**,
   tripwire PASS, 1,442 records / 694 projects, partition total, smoke test
   passing, links 686/8/0. G2's R-form evidence is back in the payload, as
   predicted. Both G1 and G2 are now live observations again — Wave 5's
   change D′ is fully evidenced.

3. **P2.3 — track `taipei_case_ids.json`** — **DONE 2026-11-01** (`e91788e`).
   `.gitignore` negation added beside `twur_overrides.json`;
   `urtpe/links.py` owns the single `FALLBACK_MAPPING_FILE` constant
   (repo-rooted); `cli.py` imports it (hardcoded copy deleted);
   `tests/test_fallback_mapping.py` pins one-definition / repo-rooted /
   tracked-file-valid / loader-round-trip. config.yaml's approval count
   restored to 1,442 (caught by the deploy-target test).

### Wave 2 — openspec change A′: `wire-standing-checks` — **DONE 2026-11-01** (archived `2026-11-01-wire-standing-checks`)


P1 (wire `emission_faults` into `_run_locked`, warning not refusal — the spec
already requires the report at `official-link-discovery/spec.md:253`) bundled with
the census-equality gate the audit surfaced (PDF rows vs emission, merge-partition
totality — the audit's Appendix A shows the assertion is three lines). Same test
group, same file. Rationale: a check that exists but never runs is the 2026-08-24
shape.

### Wave 3 — openspec change A: `emit-stage-index` — **DONE 2026-11-01** (archived `2026-11-01-emit-stage-index`)

The highest-value open code bug. Emit `stage_index` from `build_project_graph`;
derive it from stage text in `_load_projects_from_js` when the key is absent, so
already-deployed `projects.data.js` files repair on load. Test first: a fixture
family with 甲/A/B `area_section` across distinct stages must form section edges
after a `--from-js` rebuild; assert emit→load→emit losslessness.

### Wave 4 — openspec change B: `land-core-slug-fallback` — **DONE 2026-11-01** (archived `2026-11-01-land-core-slug-fallback`); id map: 寶清段51-13 `等?筆`→`等1筆`, 崇仁新村711-3 `等?筆`→`等2筆` (member counts 1 and 2; the ids land in the next scheduled emission)

Two `project_id`s contain `等?筆` because both anchors have `land_count: null`
(`urtpe/merge.py:124`). Fall back to another family member's count before slugging;
review-flag when no member carries a count. Delta touches `case-merging`.
Operational cost of leaving it: the two projects with no `.link_cache` directory are
exactly these two identities — discovery cannot cache them. Note the
alias-migration path for the 31 orphaned dirs (`data/project_aliases.json`), and
fold G3's regenerated numbers in.

### Wave 5 — openspec change D′: `case-record-join-discriminator` — **DONE 2026-11-01** (archived `2026-11-01-case-record-join-discriminator`; new spec `case-record-join`, 2 requirements)

New change, created when Waves 1–4 are done. Two requirements, one delta:

1. **G1 — precedence rule.** `recovery.cases` chose 2 of the 6 cases
   `links.taipei` joins on (the sets overlap; the peer's disjointness claim was a
   truncation artifact — corrected in the appendix). A recorded rule decides which
   wins; `ambiguous-zone` is part of the input, not a tiebreak by itself.
2. **G2 — id-space normalisation.** `recovery.cases` carries both R-form
   (`R089213-02`) and numeric spellings across publications (documented
   `docs/urotpe_api.md` §4); normalise before any join keyed on case id. Absent
   from the current payload (188 is the residual) but returns with item 2 of
   Wave 1.

### Wave 6 — openspec change C: `viewer-stage-chip-coverage` — **DONE 2026-11-01** (archived `2026-11-01-viewer-stage-chip-coverage`; grey 審查中/撤回 chip shipped, fmtCell prose + em-dash cells, fmtDate ISO at all three date sites; both main specs synced)

V3 needs a spec delta (it contradicts `history-graph/spec.md:255` "SHALL show no
badge"). Bundle V2 (raw JSON/`null` in table cells) and V4 (three date formats in
one pane) — same test group, same file.

### Wave 7 — direct `fix:` commits — **DONE 2026-11-01** (`ddab3ba`: P2.1 atomic lock, P2.2 --fresh backup, P3.2 real table counts, P3.3 crawl warning, P3.1/P3.8/P3.11 AGENTS.md, G4 domain docs)

### Post-wave — `fix-graph-timeline-order` then `refresh-awaiting-approval-caches` — **DONE 2026-11-02** (archived; §29–§33)

### Post-wave — `fix-row-order-tiebreak-and-view-badges` — **DONE 2026-11-02** (archived; §34). 30 same-case row inversions fixed viewer-side (tie-break by node date before recno — 37 same-case groups remain, all date-ascending); the refresh selector widened to plan-change applications (177 candidates, 2 approval dates recovered: 314's 11507024 → 2026/09/17, 303's 11505020 → 2026/09/30); `refresh_project` re-absorbs the view page (140 caches backfilled with `view_verified_case_ids`); the 國 badge renders on view-verified nodes (view/621 ↔ 10105152). Residual watch: the 17 drift families whose older node's gazette date matches no approval (±2–7 days) — their render order is fixed, their binding is not; a matcher-tolerance decision is recorded in the archived design's Open Questions.

### Post-wave — `refresh-case-status-and-drop-withdrawn-fields` — **DONE 2026-11-02** (archived; §36). The 13 "still awaiting" cases checked against 基本資料/data1/data2: 8 badge errors corrected (in-review cases read 已核准 by `schedule_from_top`), 3 closed cases (2 自行撤回, 1 駁回) no longer selected (selector 176 → 91), 南港671-6 correctly stays 審查中 (立農163-2 was recorded here as correctly 審查中 — wrong, see the next entry and §37); the refresh now re-derives case status from the case header and drops dates the city withdrew (6 removed, 0 conflicts); the viewer hides 已核定 like 已核准. Residual watch: status is re-derived only for refresh-selected projects — 4 cached 審查中 on since-approved cases and 3 cached 已核准 with no dates wait for a corpus-wide status pass; a cleared status is removed (not stored as ""), so a project whose last non-terminal status clears would read never-approved (measured 3 → 3 this run).

### Post-wave — `supersede-headerless-cases-and-discover-new-ids` — **DONE 2026-11-02** (archived; §37). A `無` case header clears an in-review/approved status; re-filed cases are recorded as superseded (立農163-2 11211211 → 11409026, now with no 審查中 chip; 虎林38 10806141 → 11510017); the refresh repeats discovery's parcel search and appended 4 case ids (incl. 虎林38's real pending case 11510017). The 2 `無` cases with a non-exact successor (雅祥227-4 11009142, 吉林705-3 10410012) were matched by `match-superseding-case-on-application-dates` (§38, the maintainer's decision: match on application dates). Residual watch: new-case discovery covers selected projects only; 4 stranded cache dirs are re-selected every run.

- P2.1: atomic lock acquire via `O_CREAT | O_EXCL` (replaces the tmp-and-replace
  race; Windows loser currently crashes with `PermissionError` instead of exit 5).
- P2.2: `--fresh` renames to `.link_cache_backup_<date>` instead of rmtree.
- P3.1: exit-code table (reconcile-block exits 2; AGENTS.md).
- P3.2: inert tripwire `tables_found` parameter — pass real counts or remove.
- P3.3: portal-index crawl completeness warning (WAF-shortened crawl).
- P3.8: AGENTS.md viewer-test wording (`scripts/viewer_smoke.js` exists, runs by
  hand).
- P3.11: AGENTS.md annotation — the manual-correction ledger (`--ledger`, default
  `urtpe-gazettes/corrections.jsonl`) is designed, spec'd, and unused; the file's
  absence is normal, not a defect (user decision 2026-11-01: annotate, don't
  create).
- G4: `docs/domain_model.md` + `docs/domain-model.html` re-measured on the
  post-restore payload (one `docs:` commit).

### Decisions waiting on the user

- ~~**Poller restart.**~~ **DECIDED + EXECUTED 2026-11-01**: one-off poll now
  (channel healthy — `reuploaded`, gazette 2026-10-15, sha256 matches the held
  member; the 26.3-day stall recorded as the D3 warning) **and** a weekly
  scheduled task `urtpe-poll` created and test-run (Mondays 06:30,
  interactive-only logon — acceptable on this workstation; next run 2026-11-02).
  Recorded in `docs/portal_operations_log.md` §28. Residual item: the task is
  machine-local; if this workstation changes, re-create it there.
- **`corrections.jsonl`** — **DECIDED 2026-11-01: annotate, don't create.** Zero
  demand in 2+ months (the 12 fixes this gazette needed are city-side typos
  handled by `cleanse.py`; the 30 需人工檢視 rows are review flags, not
  corrections). Wave 7 item: one-line AGENTS.md annotation ("designed, spec'd,
  unused — the file's absence is normal").
- **TAB-2's six design decisions** (`docs/graph-tabs-decision.html`) and the
  11 lane-less records — the TAB-2 session's own scope, pending the user.

### Watch, do not fix

- F2 (one-time flake): comment on the test citing the observation; reproduce with
  a tight loop only if it fires again.
- V5–V12 (viewer polish): fix opportunistically, lowest priority.
- Peer-deferred items (no CI, no browser-render test, baseline item 6 numbers):
  recorded as by-design in all sessions.
- **G5:** the TAB-2 planning numbers (474 inverted pairs / 456 ambiguous markers /
  102 multi-track) predate 10-15 and the restore — re-measure before any spec
  cites them.
- API→gazette reverse completeness check (a recovered case id whose gazette row
  is absent would indicate the API holds more than the print).
- 概要-removal policy decision (19 non-概要 deletions, no same-land-core partner;
  64 spurious name-similarity pairs at ≥ 0.75).
- Emission reproducibility — `tests/test_idempotent_flags.py:117` deliberately
  skips the node-payload round-trip; the skip is named, not hidden.
- 08-11 index records 1,414 vs 1,415 mergeable + 4 truncated = 1,419 printed — one
  row unexplained, from the 2026-10-07 ingest.
- 14 two-entry land cores are under-merges, not losses; one bare count change
  (吉林段四小段676), one slug collision, one recovery artefact.
- G2's dual id space until Wave 5 lands: any new consumer of `recovery.cases`
  must handle both spellings.

# Appendices — evidence record

The sections below are the verification trail. Each finding above traces to one of
them. Read for detail or audit, not for execution.

## Appendix A — original pipeline inspection (2026-10-26)

Method: read the core modules (`cli.py`, `lock.py`, `tripwire.py`, `coverage.py`,
`archive.py`, `extract.py`, `links.py`, `emission.py`, `viewer.py`, `reconcile.py`,
`poller.py`, `corpus.py`, `io.py`, `merge.py`, `graph.py`); run the standing
checks; probe each suspicious spot with a small script. Standing checks then: 705
passed / 1 skipped / 75 s; deploy fresh; smoke test passing; baseline items 1–4
caught, item 5 "yes" by design (D5). The gates that were wired all worked; no
data-corruption defect was found.

### P1 — the emission gate exists but is never called

`urtpe/emission.py` checks one failure: a rebuild without `--links` emits a dataset
with no link data, reports success, and the viewer presents absence as "no data"
(`urtpe/emission.py:4`). Imported at `urtpe/cli.py:15`, never called — `emission_faults`
appears nowhere in `urtpe/`. A no-`--links` run produced `links: {}` on all projects
and exited 0. The dead import suggests the wiring was intended and lost. Fix absorbed
into Wave 2 (change A′).

### P2 findings

1. **Lock race.** `urtpe/lock.py:69` does read → check → write with no atomicity.
   Two simultaneous starters both read "no lock"; on POSIX both win, on Windows the
   loser crashes with `PermissionError` on the shared `.lock.part` name (reproduced
   with two threads). Absorbed into Wave 7 (P2.1).
2. **`--fresh` destroys durable state.** `urtpe/links.py:1791` calls
   `shutil.rmtree(self.cache_dir)`: deletes `portal_index.json` (the only path to
   the ~110 oldest portal entries), `no_match_ledger.json`, and the per-project
   `result.json` dirs. The coverage guard refuses afterwards, but the wipe already
   happened — the five `.link_cache_backup_*` dirs exist because of this class.
   Absorbed into Wave 7 (P2.2).
3. **`data/taipei_case_ids.json` untracked.** Read by `discover_project_links`
   (`urtpe/links.py:625`), written by `--add-mapping-file`; curated, human-verified,
   same category as tracked `twur_overrides.json`; CWD-relative path
   (`urtpe/cli.py:32`, `urtpe/links.py:415`). Absorbed into Wave 1 (item 3).

### P3 findings (housekeeping)

4. Exit-code table incomplete (code 2 undocumented) → Wave 7 (P3.1).
5. Tripwire's page check inert as wired (`tables_found=pages`) → Wave 7 (P3.2).
6. Portal-index crawl has no completeness signal → Wave 7 (P3.3).
7. Corrected re-upload poisons `verify()` forever → **resolved** inside change D
   (superseded digests, archived `9028780`).
8. AGENTS.md stale on the viewer test → Wave 7 (P3.8).
9. Uncommitted work names an untracked file → **done** (`0bc6ed0`).
10. `FALLBACK_MAPPING_FILE` defined twice; `.corpus_cache/` never prunes → the
    constant folds into Wave 1 (item 3); pruning remains open, unqueued.

## Appendix B — viewer inspection (2026-10-26, live)

The deployed build matched `HEAD`; search, all four filters, cross-filtering, the
detail pane, the counter, `rel="noopener"` links, and the recovered rows'
provenance all behaved; no page-code console errors; no `undefined`/`NaN` text.
Sound and verified: header counts, 統計至 label, cache-bust `?v=`, search matching
parcel/district/implementer, filter panels with count badges, the version graph
with per-track chains and stage bands, milestones with 國/北 badges, the 20-column
table, recovery provenance.

Findings (all verified live; V1–V4 queued, V5–V12 watch):

- **V1 — broken identity `等?筆`** → Wave 4 (change B).
- **V2 — raw JSON/`null` in table cells** (`地號清單` as `["336",…]`, `地號別名` as
  `{}`, `原地號數` as `null`) → Wave 6 (change C).
- **V3 — 195 cards show no stage chip** (reads as "not started"; data holds
  審查中/自行撤回) → Wave 6 (change C; needs the spec delta).
- **V4 — three date formats in one pane** (ISO / `2011/11/27` / `100.12.20`) →
  Wave 6 (change C).
- V5 stale detail pane on filtered-out active project; V6 no sticky header on the
  20-column table; V7 milestone bars decorative; V8 list sorted by 編號 ascending;
  V9 no keyboard/screen-reader access; V10 9.1 MB payload (904 KB gzipped); V11
  chips/area colours carry no accessible name; V12 73 ms full-list re-render per
  click → all watch.

## Appendix C — peer session F-findings (2026-10-30)

All five verified against the working tree before merging. F1 (`stage_index` read
never emitted — the section-branch grouping collapses when every node loads -1;
0 section edges in the payload, 1 node carries `area_section`) → Wave 3 (change A).
F2 (one-time flake) → watch. F3 (dead code: `date_order_report`
`ordering.py:107` — the peer's `links.py` attribution corrected; the 編號-dedup
guarantee lives in the reader `_dedupe_by_recno` since 2026-10-06, verified before
deletion; `classify_case_outcome`; `project_twur_class`) and F4 (vestigial
orphan-skip at `cli.py:72-75`) → **done** (`d6c77b3`). F5 (uncommitted docs) →
**done** (`0bc6ed0`).

## Appendix D — the 09-24 restoration (executed 2026-10-31)

The audit amendment's two claims, verified against the archive before acting: the
quarantined `skipped since abnormal SN\核定案件-2026-10-02.pdf` **is** gazette
2026-09-24 (sha256 `5066b108…` matches the poller's record; 統計至 115/9/24
Gregorian; 246 pages; 1,681 raw rows = 1,436 real + 245 exact-copy page heads;
1,414 emitted + 22 named truncations); and `核定案件-2026-10-30.pdf` was a
byte-identical re-upload of 10-15 (a missed *check*, not a missed *gazette*).

Executed under openspec change D (archived `2026-11-01-restore-2026-09-24-gazette`,
commits `9ad2a9d`, `bb93106`, archive `9028780`): re-filed with
`restored_from` provenance (refile widened to accept the pre-rebuild index backup
and the poll log as digest evidence — the rebuild had dropped 09-24's entries);
ingested dual-path (tripwire PASS, 1,436/692, **all 22 truncated rows
API-recovered, 0 residual**); the running page head dedupes by content — the
boundary regression test pins this against the v2 positional skip; 08-27→09-24
change set written (+8/+13, roc→gregorian, blocking empty); 10-01 re-ingested
(new approvals 4, matching the 2026-10-07 superseded file exactly; net +7, the
divergence explained; the pre-rename overwrite deviation recorded and the
withdrawn comparison reconstructed into
`2026-10-01.superseded-pre-09-24-restore.json`); calendar boundary corrected in
`AGENTS.md` + `openspec/config.yaml` (ROC through 08-27, Gregorian from 09-24);
P3.7 superseded digests shipped and spec'd; forward re-emission of 10-06 and
10-15 (both exit 0, links 685/8/0, smoke passing, partition census verified).

Two findings from the forward re-emission, both named-not-silent: print
completion refuses the 雙園段505 row (the cut's dangling `579-` tokenizes as
`579` while the candidate's `579-2` is whole — subset check fails despite
prefix+count matching; follow-up recorded, spec-owned by
`truncated-row-recovery`), and 編號 188 degraded to residual (gis.uro began
timing out 4×90 s mid-run; the per-row degrade held) → Wave 1 item 2 reruns when
healthy. Full trail: `docs/portal_operations_log.md` §27; the two scratch runs'
reports preserved as `docs/ingest_0924_review_report.txt` and
`docs/ingest_1001_rereview_report.txt`.

## Appendix E — TAB-2 session G-findings (2026-11-01, verified at `bb93106`)

Post-restore baseline: 2026-10-15, 1,441 records / 693 projects, 1,411
case→record bindings, 981 distinct cases, 971 virtual entries / 951 distinct.

- **G1** (join precedence; the peer's disjointness claim corrected — the sets
  overlap, `links.taipei` carries six ids including both recovery cases) → Wave 5
  (change D′).
- **G2** (R-form/numeric dual id space, real per `docs/urotpe_api.md` §4; absent
  from the current payload because 188 is the residual) → Wave 5 (change D′).
- **G3** (stranded counts: doc 23 / aliases 27 / plan note 32 / live 31−2) →
  Wave 1 item 1.
- **G4** (domain-model docs stale) → Wave 7.
- **G5** (TAB-2 planning numbers predate the restore) → watch.
- Out of scope here: TAB-2's six design decisions
  (`docs/graph-tabs-decision.html`, user decision pending) and the 11 lane-less
  records (a 2b lane-spec requirement, not a defect).

## Appendix F — closed peer questions (2026-10-30)

Suite baseline settled (the peer's 652 was a stale count predating
`33ce713`/`b40bb15`; 706→708 collected as tests landed); no live spec cited
`date_order_report` (deleted; dedup rationale recorded on
`departures_from_descending`); no objection to the `links.py` pair (liveness
coverage confirmed in `tests/test_fetch_remaining_portal.py`). Tasks `99fe037a`,
`2abddaf7`, `494f6747`.
