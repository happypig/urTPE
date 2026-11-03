# Project inspection — 2026-10-26 · consolidated 2026-11-03

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
G1–G5 · 2026-11-03 Batch B, the §37/§38 residuals collected for batch treatment ·
2026-11-03 Batch C, the post-viewer-UX gaps collected after waves 1–5 landed.

## State of the board

| Check | Result at last full run |
| --- | --- |
| Test suite | 851 passed, 1 skipped (852 collected) at `2b96e5b` |
| Deploy freshness | all 4 artifacts fresh (`scripts\check_deploy.py`) |
| Viewer render path | `node scripts\viewer_smoke.js` passes |
| Silent-failure baseline | items 1–4 caught; item 5 "yes" by design (D5) |
| Archive | 7 publications, chain whole, 09-24 restored |
| Acquisition | **weekly scheduled task `urtpe-poll` live** (Mondays 06:30); channel verified healthy 2026-11-01 (`reuploaded`) |
| Emission | 2026-10-15, 1,442 raw / 1,442 clean / 693 projects, 0 residuals |
| Batch B | 8 findings queued, 0 executed (§37/§38 residuals) |
| Batch C | 7 findings queued, 0 executed (post-viewer-UX gaps; C6 rule decided, C7 added) |
| Batch B + C plan | reviewed 2026-11-03: 15 steps (S0–S13 + R); C8, C9 added 2026-11-04 |
| openspec | 4 changes done but unarchived; 3 fail `openspec validate` (fixed by S0) |

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

### Post-wave — `fix-graph-timeline-order` then `refresh-awaiting-approval-caches` — **DONE 2026-11-02** (archived; §29–§33)

### Post-wave — `fix-row-order-tiebreak-and-view-badges` — **DONE 2026-11-02** (archived; §34). 30 same-case row inversions fixed viewer-side (tie-break by node date before recno — 37 same-case groups remain, all date-ascending); the refresh selector widened to plan-change applications (177 candidates, 2 approval dates recovered: 314's 11507024 → 2026/09/17, 303's 11505020 → 2026/09/30); `refresh_project` re-absorbs the view page (140 caches backfilled with `view_verified_case_ids`); the 國 badge renders on view-verified nodes (view/621 ↔ 10105152). Residual watch: the 17 drift families whose older node's gazette date matches no approval (±2–7 days) — their render order is fixed, their binding is not; a matcher-tolerance decision is recorded in the archived design's Open Questions.

### Post-wave — `refresh-case-status-and-drop-withdrawn-fields` — **DONE 2026-11-02** (archived; §36). The 13 "still awaiting" cases checked against 基本資料/data1/data2: 8 badge errors corrected (in-review cases read 已核准 by `schedule_from_top`), 3 closed cases (2 自行撤回, 1 駁回) no longer selected (selector 176 → 91), 南港671-6 correctly stays 審查中 (立農163-2 was recorded here as correctly 審查中 — wrong, see the next entry and §37); the refresh now re-derives case status from the case header and drops dates the city withdrew (6 removed, 0 conflicts); the viewer hides 已核定 like 已核准. Residual watch: status is re-derived only for refresh-selected projects — 4 cached 審查中 on since-approved cases and 3 cached 已核准 with no dates wait for a corpus-wide status pass; a cleared status is removed (not stored as ""), so a project whose last non-terminal status clears would read never-approved (measured 3 → 3 this run).

### Post-wave — `supersede-headerless-cases-and-discover-new-ids` — **DONE 2026-11-02** (archived; §37). A `無` case header clears an in-review/approved status; re-filed cases are recorded as superseded (立農163-2 11211211 → 11409026, now with no 審查中 chip; 虎林38 10806141 → 11510017); the refresh repeats discovery's parcel search and appended 4 case ids (incl. 虎林38's real pending case 11510017). The 2 `無` cases with a non-exact successor (雅祥227-4 11009142, 吉林705-3 10410012) were matched by `match-superseding-case-on-application-dates` (§38, the maintainer's decision: match on application dates). Residual watch: new-case discovery covers selected projects only; 4 stranded cache dirs are re-selected every run.

### Post-wave — `match-superseding-case-on-application-dates` — **DONE 2026-11-02** (archived; §38). A re-filed case is matched to its successor on the application dates, not on every date. Measured before the change: the relaxed rule matches exactly 4 cases, each with one candidate. Live run: 89 projects, 0 failures, 4 superseded, 0 `無` without a successor, 0 ambiguous. Re-emission: 1,442 records / 693 projects, never-approved 3, `links.taipei` 1997, orphan nodes 596 — all unchanged. Residual watch: §37 residuals (b)–(e) stand.

### Batch B — the §37/§38 residuals, collected 2026-11-03 — **QUEUED, not started**

Every item below is a residual that §37 or §38 left open. The viewer-UX waves
(`docs/viewer-UX.md`) changed how the viewer draws a case. They did not close any
item here. Measured at `2b96e5b`, on the payload emitted 2026-11-02
(1,442 records / 693 projects) and the 726 cache dirs.

| ID | Finding | Evidence now | Form | Gate |
| --- | --- | --- | --- | --- |
| B1 | New-case discovery covers refresh-selected projects only | the 336 project (大安區-通化段四小段-336地號等26筆) has 3 case ids, all 已核准; the selector skips it; its cache has no `case_headers` | openspec change | — |
| B2 | A superseded case keeps its undated node in the graph | 4 of the 5 superseded cases carry an orphan node with an empty `node_date`: 10410012, 10806141, 11009142, 11211211 | openspec change | B1 |
| B3 | A `fresh=True` re-discovery drops `case_headers` and `superseded_by` | `discover_project_links` never writes either field; only `refresh_project` does | openspec change | — |
| B4 | 4 stranded cache dirs are re-selected every run | the selector returns 89 candidates; 北投區-關渡段二小段-55, 士林區-天山段二小段-264, 大同區-延平段一小段-314, 文山區-華興段四小段-44-2 report "not searched" every run | direct `fix:` commit | — |
| B5 | Status is re-derived only for selected projects | 1 cached 審查中 sits on a case that has an approval date (大同764 09605032, 核定 2007/07/06); 3 cached 已核准/已核定 have no approval date (臨沂318 10409104, 學府125 10611122, 直興373 10405293) | openspec change | B1 |
| B6 | A cleared status is removed from `case_schedules` | a project whose last open status clears would read as never-approved; measured 3 never-approved projects, unchanged | openspec change | B5 |
| B7 | A view-verified case may belong to another project | 4 of 189 view-verified ids have a label whose land core is another project (similarity < 0.7): 10202065, 10906092, 09608220, 09807161. Under §8 decision 1 (the city name decides) 10906092 is accepted and 09511211 is rejected instead — see C3. **DONE 2026-11-04** — see C3 | done (= C3) | — |
| B8 | 3 nameless 孤 anchors carry another project's milestones | 10202065 (中山254), 09511211 (大安557, 施工中), 09807161 (龍泉169). **DONE 2026-11-04**: all 3 rejected and offered to their owners; the corpus has 0 nameless orphans | done | — |

**B7 and B8 are `docs/viewer-UX.md` §8 (wave 3b).** They are listed here
because §8 was not started when this batch was collected, and because the 國 badge
of wave 4 reads `view_verified_case_ids` without checking the project's own case
name. Wave 4 landed on 2026-11-03. B7 must land before the badge can be trusted.

**B7 in detail.** Each of the 4 ids lands on two projects. The wrong project
holds it as a nameless 孤 anchor and shows the other project's dates:

| Id | Wrong project (holds the 孤 anchor) | Own project (already holds it on a node) |
| --- | --- | --- |
| 10202065 | 中山254 — 孤, 2020-11-03 | 大安辛亥163 — node 631, 2020-11-03 |
| 10906092 | 中山吉林898 — node 307, 2023-10-18 | 萬華莒光519-3 — no cache dir yet |
| 09608220 | 信義犁和102 — 孤, 2009-01-15 | 信義犁和165 — node 1343, 2009-01-15 |
| 09807161 | 大安龍泉169 — 孤, 2013-11-29 | 內湖康寧262 — node 1160, 2013-11-29 |

A fifth id, 09511211, has the opposite shape: the label is right and the id is
wrong. Both 吉林603 and 大安557 name it, and it is the city's 吉林603 case.
It is the shape B of §8.

**Measured, not guessed.** B5 shrank from the 4 that §36 recorded: one cleared.
B2 shrank from 5 to 4: 萬華894's 11010191 has no orphan node, because its
milestones carry an approval date, so it anchors to a recno node instead.
B7 counts the same 4 defects that `docs/viewer-UX.md` §8 recorded. The ids differ
between the two measurements only in what the id list holds: the payload has 189
view-verified ids in 143 projects, and the cache has 193 in 146 caches. The 4
defects are the same 4 in both.

### Batch C — the post-viewer-UX gaps, collected 2026-11-03 — **C3 DONE 2026-11-04; the rest QUEUED**

The viewer-UX waves 1–5 landed (`91699bb`…`370ddb2`): §5 centered, §1+§6 the
gutter, §7 the [無]/[NA] labels, §2 the 國 binding, §3+§4 the event/orphan
placement. C3 (wave 3b, `docs/viewer-UX.md` §8, `reject-foreign-view-cases`)
landed on 2026-11-04: 146 caches verified under the lock, 4 rejections, 4
offers, 1 label error accepted, 3 not confirmed; the 3 nameless 孤 anchors
are gone (596 → 592 orphan nodes, all named). The C2 ordering hazard is now
live: `refresh_project` runs the gate, so a rejected id stays rejected — the
absorb still merges and never removes, but `view_verified_case_ids` no longer
holds what the gate removed.

| ID | Finding | Evidence now | Form | Gate |
| --- | --- | --- | --- | --- |
| C1 | `nationalBoundTo` badges **every** candidate of a multi-match label | **Corrected 2026-11-03 (see "C1 in detail").** The §2 date rule is a tie-break: it applies only when 2+ nodes share the label's stage+track. 19 labels have 2–3 candidates (41 nodes). The shipped code scores each node on its own, so all 41 get 國. The spec binds 10 of the 19 (exact date); a ±1-day tie-break binds 17. **16 nodes carry a 國 the spec does not give** (e.g. 文林64 recno 1086 + 693; 潭美579-2 recnos 673, 627, 618) | openspec change (viewer + spec delta) | archive `bind-national-badge-to-named-node` |
| C2 | The offline `view_verified_case_ids` backfill has never run | 642 caches hold `view.html`; 587 parse to ≥1 case id, 758 ids in all. 435 projects would gain ids (557 new; 143 projects / 189 ids carry ids today). Against each cache's own `land_core` field (present on all 726), the 5 ids that scored 0.0 against the 案名 score 0.85–0.95: none of the 557 is foreign. 10 names are parcel-less; 9 have no city name. `refresh_project` already runs this absorb on every project it refreshes (`urtpe/links.py:1667`), so C2 is not separate code: it is the corpus-wide refresh | part of change R | C3 |
| C3 | Wave 3b (`docs/viewer-UX.md` §8, `reject-foreign-view-cases`) never ran | **DONE 2026-11-04** (`ba2700b` pipeline, `f961f6a` re-emit): 146 caches verified under the lock; 4 rejections (10202065 shape A, 09608220 shape A, 09511211 shape B, 09807161 shape A), 4 offers to the owning projects (`adopted_from_view` recorded), 10906092 accepted with a label error, 09112120/09112121 not confirmed (parcel-less = no evidence). The 3 nameless 孤 anchors are gone: 596 → 592 orphan nodes, all named. Full suite 870 passed / 1 skipped; smoke passes | done | — |
| C4 | `extract_landcore_from_case_name` returns "" for 3 name shapes, and the orphan gate (`urtpe/links.py:2162`) then drops the case | 33 cached cases have an unparseable city name. 21 are anchored on a recno node anyway. **12 are dropped**: 4 崇仁新村 (the parcel-less rule, by design) and **8 real cases** — 華中247's 6 A區/B區 cases (09305081/82, 09407301–04), 長安709's 概要 09205060, 南港531-4's 概要 09406102. Shapes: 、-list before 地號 (`709、711地號`), 號 without 地號, `(原NNN)` inside the parcel, compatibility chars (U+F963 北) | openspec change | — |
| C5 | 使照 disagreement between the two portals is not flagged | 282 projects hold 使用核發/使照核發 from both portals: 260 agree, 22 differ (吉林811 2013-09-11 vs 2013-11-12; 榮星306 year; 虎林310 month). 13 projects hold it national-only, 32 city-only. 橋北574-1's national `291.08.02` renders as 2202-08-02 in the 推動歷程 card (`fmtDate`); the 使照 slot and the stage chip use the city's 2022/08/02 | openspec change | user scope decision |
| C6 | The 北 positional fallback binds 71 nodes on 51 projects, unmarked | re-run of the pipeline's own `_match_case_by_date` over the payload: 1,356 nodes match by date, 71 do not, 15 have no case. **Rule decided 2026-11-03 for the area-split ties (see "C6 in detail"):** one approved recno binds every same-date case of its area split. That covers 31 of the 71 nodes (56 cases, 15 projects) and folds their twin orphan nodes into the recno. Examples: 吉林508 (view/1062) recno 259 → 11011241 A區 + 11011242 B區; 榮星53 (view/25) 4 recnos, each → its 北區 + 南區 pair. The other 40 nodes are recorded by type and stay open | openspec change | S0 |
| C8 | The construction dates (建照 / 開工 / 使照) do not follow the case that owns them | **Rule decided 2026-11-04 (the user):** the city keeps 建照核發日期 (data2) and 開工日期 / 使照核發日期 (data3) on the **first 擬訂 plan case** — the one named 擬訂…都市更新事業計畫案 or 擬訂…都市更新事業計畫及權利變換計畫案. Two defects break it. (a) `select_best_payload` (`urtpe/links.py:1971`) keeps one data3 payload per project, chosen by key count, so the plan case's 開工/使照 are dropped when a later case has more statistics: 9 of the 13 "national-only 使照" projects (德惠573 09710240: 開工 2012/07/13, 使照 2015/07/13 cached, not emitted). (b) Discovery misses the 擬訂 plan case itself: 新光101 (09703181), 寶清599 (09303270), 敦化585-11 (10210171) — the parcel search does not return them; they were found by probing sibling case ids. See "C8 in detail" | openspec change | — |
| C9 | A parcel-count shrink (`等N筆(原M筆)`) splits one project in two | 吳興790-6: recno 978 (變更(第三次), 等4筆(原29筆)) scores 0.639 against recno 1157 (等29筆): same section and first parcel, count bridge 0.8, but the parcel sets share 1 of 32 (Jaccard 0.03). **11 project pairs** split this way, and 10 of them share one national page (view/118, 319, 321, 637, 84, 281, 718, 276, 231, 358) and their case ids. See "C9 in detail" | openspec change (`case-merging`) + re-emit + aliases | — |
| C7 | The 相關連結 label of an anchored case shows the gazette 案名, not the city's own case name | `buildRelatedLinkLabels` (`viewer/app.js:563`) labels each case a node anchors with that node's `case_name` (the gazette row). It reads `candidate_names` only for cases no node anchors. 307 anchored cases show a label that differs from their city name: 20 lose an area suffix (吉林508's 11011241 shows without "-A區"), 48 show another stage word (中山202 node 699: gazette 擬訂, case 變更), 8 show other parcel counts (文林176: 等13筆 vs 等14筆), 231 differ in other wording. With C6, one node carries 2+ cases, so the gazette label cannot tell them apart | direct `fix:` (viewer) + a review list for the 48 | — |

**C1 in detail (corrected 2026-11-03).** The first version of this row said
the code "binds 430 labels the design would leave unbound". That was wrong.
In `docs/viewer-UX.md` §2 and in the change's `design.md` decision 1, the
date rule applies only "if more than one node matches". A label with one
stage+track candidate binds it, whatever the date. So the 421
single-candidate drifts comply with the spec. The real defect is in
`viewer/app.js:130`: `nationalBoundTo` asks "does any label match this node?"
per node. It never asks "which node does this label choose?" per label. So
every candidate of a multi-match label gets 國. Measured with the shipped
helpers over the payload: 19 multi-candidate labels, 41 badged nodes, 16
nodes with a 國 that neither the spec nor `view_verified_case_ids` gives.
Fix: bind per label at project level (each label chooses at most one node);
tie-break on the exact date, then ±1 day (the 公告-vs-committee offset that
`_match_case_by_date` at `urtpe/links.py:1856` already allows for 北); leave
the label unbound when 0 or 2+ nodes qualify. The ±1-day step binds 17 of
the 19 labels; the exact-only rule binds 10. The tolerance is a spec change,
so it goes in the delta. Far drift on a single candidate (42 labels ≥120
days) is not a binding bug; it can become a review flag later.

**C2 in detail.** Method: parse every cached `view.html` with the pipeline's
own `extract_case_ids_from_view`, match each dir to its payload project by
dir name (= project_id), and subtract the ids the project already holds.
Check each new id's city name against the cache's own `land_core` field
(not the 案名 — 11 案名 do not parse, see C4). All 557 new ids score ≥ 0.7
or are parcel-less or nameless. **Ordering hazard:** `refresh_project` runs
the view absorb on every project it refreshes, and the absorb merges and
never removes. So any refresh run before C3 lands adds ids with no check, and
any refresh after C3 must skip ids already in `view_rejected`, or it puts
them back.

**C4 in detail (corrected 2026-11-03).** The first version said C4 blocks
C2. It does not: every cache carries a `land_core` field that parses, so C2
and C3 compare against that. C4's real cost is at the orphan gate. A case
whose city name yields no land core fails the similarity test at
`urtpe/links.py:2162`, and unless it is anchored, view-verified or
attributed, it is dropped from the graph without a report. Shapes seen in
the 33 unparseable names:

| Shape | Example | Count of names |
| --- | --- | --- |
| 、-list before 地號 | `長安段三小段709、711地號等2筆` | 華中247 ×6, 長安709, 南港531-4, 仁愛679, 懷生316 |
| `(原NNN)` inside the parcel or count | `105(原90)地號等13筆(原24筆)` | 中南105 ×3, 振興166-2, 陽明19, 永昌142-1 |
| A space before 地號 or 筆 | `1-1 地號等11 筆` | 奇岩1-1 |
| 號 without 地號 | `401號等10筆` | 大業401, 美仁831-3, 陽明291 (anchor names) |
| No parcel at all | `崇仁新村土地…` | 崇仁 ×4 (parcel-less rule, by design) |

The 8 dropped real cases sit in 3 projects. 華中247 loses its whole
A區/B區 history, and its 3 nodes all bind 09305080, a sign of the C6
fallback. Fix: teach the extractor the first three shapes and normalise
compatibility chars (NFKC) before matching; report every name that still
yields no land core.

**C5 in detail.** The national page's 使用核發日期 and the city's 使照核發日期
are the same fact from two offices. 22 disagreements include both plausible
readings: 榮星306 (2022-09-23 vs 2023-09-23) and 虎林310 (2022-11-11 vs
2022-01-11) look like single-digit typos — two sources prove a typo exists,
neither proves which one. The pipeline emits both today with no flag. The
`291.08.02` value is a third shape: an out-of-range ROC year. It renders as
2202-08-02 only in the 推動歷程 card; the 使照 slot prefers the city value.
Fix: a review flag on disagreement (not a repair), plus a range guard in
`fmtDate` and the ROC converters.

**C6 in detail (rule decided 2026-11-03).** `_match_case_by_date` returns
"" for the 71 nodes, and `urtpe/links.py:2073–2081` falls back to
`disc.city_case_ids[0/1]` by track position. The 71 split by cause:

| Type | Nodes | Cause | Example | Disposition |
| --- | --- | --- | --- | --- |
| 1–2. Area-split tie | 31 | The city filed one approval as 2+ area cases (A區/B區, 北區/南區, (A區段)…). The gazette prints one row. All cases share the date, so the matcher refuses the tie | 吉林508 recno 259: 11011241 -A區 已核准 + 11011242 -B區 施工中; 榮星53 (below) | **decided: the area-split rule** |
| Tie, other shape | 5 | 2 cases share the date but are not an area split | 吉林705 recno 1311: 09307101 (事業計畫及擬訂權利變換) vs 09307104 (事業計畫); 玉泉11 recno 1366 and 逸仙294-4 recnos 1233/1234: two cases with the same name; 萬華894 recno 14: 11010191 is superseded by 11507019 | open — a superseded case should yield to its successor (B2) |
| 3. Drift 2–7 days | 5 | The right case exists, outside ±1 day | 瑞安838 recno 590 → should be 10611204 (變更, 2 days off), bound to the 擬訂 case | open — 4 of 5 resolve when the node's 案名 equals exactly one case's city name |
| 4. Drift 8–60 days | 5 | Mostly re-filed cases | 東湖34 recno 73: the bound 11302181 has no approval; the re-filed 11502008 is approved 10 days earlier | open — review flag |
| 5. Drift > 60 days | 24 | The right case is not in the cache | 犁和302 recno 281 (2023 變更) bound to the 2019 擬訂 case | open — discovery (R, B1) |
| 6. No approval date | 1 | No cached case is approved | 玉成253 recno 508 bound to a 審查中 變更 case | open — discovery (R, B1) |

**The rule (types 1–2).** A recno node binds **every** cached case that
matches its date within ±1 day **and** whose city name equals the others'
once the area suffix is removed (`-A區`, `-B區`, `-北區`, `(A區段)` and the
like), with the same stage and track. `node.links.taipei` is already a list,
so the payload shape does not change. Each bound case leaves
`links.orphan_nodes`, so its twin orphan node disappears. The viewer then
shows one 北 badge per case, each labelled by C7.

Worked example, 榮星段六小段53 (view/25), one national row per approval:

| recno | Date | Stage | Binds today | Binds under the rule |
| --- | --- | --- | --- | --- |
| 1416 | 2005-11-03 | 擬訂 | 09001121 (a 2007 case) | 09001120 北區 + 09001123 南區 |
| 1381 | 2007-11-20 | 變更 | 09001121 | 09001121 北區 + 09001122 南區 |
| 1349 | 2008-12-22 | 變更(第二次) | 09001121 (a 2007 case) | 09705130 北區 + 09705132 南區 |
| 1308 | 2010-02-04 | 變更(第三次) | 09001121 (a 2007 case) | 09705131 北區 + 09705133 南區 |

The 2002 事業概要 case 09001125 has no gazette row, so it stays an orphan node.
For 吉林508 the rule binds 2 cases on recno 259. Its two 變更 (A區段)/(B區段)
cases 11508022/11508023 are 審查中 with no approval, so they correctly stay
undated orphan nodes until a gazette row exists.

Corpus effect, measured: 31 nodes, 56 cases, 15 projects; 41 twin orphan
nodes fold into their recno. The other 40 nodes keep the positional fallback
until their types are decided; the open question is whether the viewer marks
a guessed badge or removes it until R finds the case.

**C8 in detail (rule decided 2026-11-04).** The user's rule: 建照, 開工 and
使照 always live on the first 擬訂 plan case (`^擬訂.*都市更新(事業計畫|事業計畫及權利變換計畫)案`).
Measured over all 726 caches:

| Where a construction date sits | Case dates |
| --- | --- |
| On the first 擬訂 plan case | 535 |
| On a later 擬訂 plan case of the same approval (area split: -A區/-B區, 北區/南區) | 14 |
| On another case, as an echo of the plan case's date | 16 |
| On another case, no plan case carries the field | 3 (仁愛114's 08610011 is a pre-2000 name with no 擬訂/案; 永吉44 and 潭美579-2 carry a 權利變換 plan case) |

So the rule holds, with one extension that C6 already needs: in an area
split, each area's 擬訂 plan case carries its own building's dates
(榮星53 北區 09001120 and 南區 09001123; 萬慶6 A區/B區).

The 13 projects whose 使照 came only from the national page, re-checked:

| Project | First 擬訂 plan case | 開工 / 使照 on it | Cause |
| --- | --- | --- | --- |
| 德惠573 | 09710240 | 2012/07/13 / 2015/07/13 | (a) selector chose 09710242 |
| 吳興790-6 (both ids, see C9) | 09712050 | 2014/11/26 / 2017/09/07 | (a) chose 09712053 |
| 永吉44 | 08911251 | 2018/02/08 / 2021/01/19 | (a) chose 09511041 |
| 潭美579-2 | 09809151 | 2017/03/13 / 2020/06/12 | (a) chose 10209171 |
| 玉成158 | 10406103 | 2018/11/21 / 2020/10/26 | (a) chose 10406104 |
| 大龍265-7 | 09603212 | 2011/03/21 / 2012/09/18 | (a) chose 10908271 |
| 興隆377 | 09609171 | 2010/12/24 / 2013/08/12 | (a) chose 09609172 |
| 敦化404 | 10310211 | 2020/09/10 / 2023/01/17 | (a) chose 10905072 |
| 新光101 | **09703181**, not cached | 2009/10/16 / 2012/03/14 (建照 2009/08/31) | (b) discovery missed it |
| 寶清599 | **09303270**, not cached | 2006/10/17 / 2009/03/31 (建照 2006/05/12) | (b) |
| 敦化585-11 | **10210171**, not cached | 2017/02/18 / 2020/01/02 (建照 2016/11/30) | (b) |
| 玉成729 | 10812181 | 2020/11/30 / — | the city has no 使照 yet |

Every recovered 使照 equals the national 使用核發日期 to the day. The three
missing plan cases were found live on 2026-11-04 by probing the case ids next
to the cached ones (`get_project168_top`): the parcel search
(`Get_updcase_list`) returns only the later 變更 cases for these parcels. So
discovery needs a second path for the plan case, for example a sibling-id
probe bounded to the cached batch, accepted only when the city name equals
the project's land core. 大龍265-7 also stops being "out of order": its 2012
使照 belongs to plan case 09603212 (the first phase, 等8筆), and the 2022
建照/開工 belong to the later A區/B區 plan cases.

Fix: take each construction date from the first 擬訂 plan case of its node
(per area in an area split), with that case as `milestones_source`; keep D5's
one-payload rule for the statistics only; fall back to another case's date
only when no plan case carries the field, and flag it.

**C8 (b), corpus-wide (measured 2026-11-04).** The related links (`links.taipei`)
can only list cases discovery found, so a missing plan case is also missing
from 相關連結 and from the graph. Over 693 projects: 663 hold a 擬訂 plan case;
8 hold no city case; 7 start at a 擬訂 事業概要 row (no plan case exists yet —
correct); **15 lack the plan case**. Each was probed live by sibling case ids
(the 10-id batch of every cached case; accepted at land-core similarity ≥ 0.85):

| Project | Found | 核定 (= gazette 擬訂 row) | 建照 | 開工 | 使照 |
| --- | --- | --- | --- | --- | --- |
| 新光段二小段101 | 09703181 | 2009/06/04 | 2009/08/31 | 2009/10/16 | 2012/03/14 |
| 寶清段四小段599 | 09303270 | 2006/04/18 | 2006/05/12 | 2006/10/17 | 2009/03/31 |
| 敦化段三小段585-11 | 10210171 | 2016/09/22 | 2016/11/30 | 2017/02/18 | 2020/01/02 |
| 南港段一小段19-1 | 10111131 | 2019/08/27 | 2021/10/08 | 2022/02/23 | — |
| 南港段一小段601 | 10406241 | 2023/04/13 | — | — | — |
| 玉成段二小段253 | 10405041 | 2022/01/04 | 2022/03/09 | 2022/04/22 | — |
| 敦化段二小段449-12 | 10209291 (等25筆) | 2021/08/19 | 2023/02/01 | 2023/09/20 | — |

The remaining 8:

- **3 not found in the probed batches**, though the gazette has a 擬訂 row:
  玉成段二小段166 (擬訂 2019-07-24), 金華段四小段455-3 (擬訂 2007-05-01, the
  only cached case is a 2020 變更), 南港段四小段566 等6筆 (擬訂 2016-02-25).
  These need another source: the national page's 相關連結, or a name search
  over the section.
- **5 are correct as they are**: the project starts at a 變更 row, so its plan
  case belongs elsewhere — the newer half of a C9 split pair (犁和段一小段102,
  南港段四小段566 等1筆) or a 1筆 unit with only 變更 rows (萬隆段二小段461,
  萬隆段二小段623, 華江段三小段274).

The same probe also found **missing later siblings**, not plan cases:
南港566 等6筆's first 變更 10708311 (核定 2019/11/20) and 玉成166's
變更(第二次) B區 11412011 (核定 2026/02/03). So the parcel search misses any
case, not only the plan case: S12 must look for every name-matching sibling,
and report the cases it finds.

**C9 in detail.** `urtpe/merge.py:40` scores two records by section (.35),
first parcel (.2), parcel Jaccard (.3) and count (.1). A plan change that
shrinks the site (`等4筆(原29筆)`) keeps the first parcel and earns the
count bridge (`orig_count == land_count` → 0.8), but its new parcel set
barely overlaps the old one, so the score stays near 0.64 and the merge
splits the family. The second project then carries the same national page,
the same case ids and the same construction dates as the first, so the
viewer shows one development twice. The 11 split pairs:

| New id (after the shrink) | Old id | National page |
| --- | --- | --- |
| 吳興段二小段-790-6地號等4筆 | …等29筆 | view/118 |
| 中山段二小段-202地號等1筆 | …等12筆 | view/319 |
| 中正段一小段-44地號等1筆 | …等5筆 | view/321 |
| 犁和段三小段-89地號等1筆 | …等16筆 | view/637 |
| 桃源段二小段-251地號等2筆 | …等17筆 | view/84 |
| 立農段一小段-513地號等3筆 | …等17筆 | view/281 |
| 南港段四小段-566地號等1筆 | …等6筆 | — |
| 玉成段三小段-545地號等4筆 | …等8筆 | view/718 |
| 芝蘭段四小段-130地號等1筆 | …等9筆 | view/276 |
| 玉泉段二小段-91地號等7筆 | …等42筆 | view/231 |
| 金華段一小段-719地號等1筆 | …等11筆 | view/358 |

`docs/dataset_completeness_audit.md:184` already listed 吳興790-6 as a land
core with two entries ("second row says `(原29筆)`") and classed the 14 such
cores as under-merges, not losses (the "Watch, do not fix" list). C9 is that
watch item, now measured. Fix: when the first parcel matches and one record's
`orig_count` equals the other's `land_count`, the declared history bridges
the pair; link it (score ≥ 0.7) without the Jaccard term, the way the
empty-parcel rule at `merge.py:73` already redistributes weight. Re-merge,
then run `scripts/build_project_aliases.py`: the newer id merges into the
older family, and its cache dir must migrate.

**C7 in detail.** The label fix is viewer-only: label each case_id with its
own `candidate_names` entry, which the payload already carries, and fall back
to the node's 案名 only when the city name is missing. The 48 stage-word
mismatches are a review list, not a label problem: a 擬訂 node bound to a
變更 case may be bound to the wrong case (中山202 node 699 is one; it was the
§30 headline and its binding was then corrected, so the list needs a
re-measure after S8).

### Batch B + C — the integrated plan (reviewed 2026-11-03)

Both batches were reviewed together against the code and the payload at
`95ea60c`. The review corrected C1, C2, C3, C4 and B7 (see their rows). This
section is the one plan for all 14 findings. Priority uses the
`docs/viewer-UX.md` scale: **P1** the graph tells the reader something false;
**P2** the graph hides data or the pipeline loses state; **P3** polish or a
latent risk.

**Three facts decide the order.**

1. **Every refresh is also a view-page backfill.** `refresh_project` runs the
   view absorb on each project (`urtpe/links.py:1667`), and the absorb never
   removes an id. So no refresh may run before the C3 gate exists. That
   includes §7 task 4.1, which is still open: 628 of 726 caches have no
   `case_headers`.
2. **Specs first.** Four changes are done in code but not archived, and three
   of them fail `openspec validate` (deltas without SHALL/MUST; one delta file
   without a delta header). C1 must modify a requirement that exists only in
   the unarchived `bind-national-badge-to-named-node`. Archive first.
3. **The refresh needs one owner.** B1, B5, B6, C2 and §7 task 4.1 all
   become "refresh more caches". One change with one run is cheaper and safer
   than five runs against a WAF-capped API.

| Step | Priority | Findings | Form | Gate |
| --- | --- | --- | --- | --- |
| S0 | — | housekeeping | fix the 3 invalid deltas; drop the "case_headers stores CASE_NAME" requirement from `show-no-state-case-status` (never built; C3 owns it); check off that change's done tasks and leave task 4.1 to R; archive `callout-gutter`, `bind-national-badge-to-named-node`, `place-events-and-orphans-by-node`, `show-no-state-case-status` | — |
| S1 | P2 | B3 | direct `fix:` — `discover_project_links` keeps `case_headers` and `superseded_by` from the prior cache on `--fresh` | — |
| S2 | P3 | B4 | direct `fix:` — the refresh selector skips cache dirs whose project is absent from the payload, and names them once | — |
| S3 | P1 | C3 (= B7, B8) | **DONE 2026-11-04** — `reject-foreign-view-cases` implemented (`ba2700b`), re-emitted (`f961f6a`), archived (`e5a5986`, 23/23 tasks). Re-checked 2026-11-04: the gate runs after the absorb on every refresh, so a rejected id stays rejected (verified offline on a copy of 中山254: a second refresh keeps 10202065 out of `view_verified_case_ids` and `city_case_ids`). **Residual S3a (P3):** the absorb does not skip `view_rejected`, so each refresh re-fetches the rejected id's milestones and leaves them in `case_milestones` — all 4 rejected ids sit there in the payload today (10202065, 09608220, 09511211, 09807161). They reach no node, orphan, edge or 北 badge; only the 相關連結 label fallback reads `case_milestones`, and that path never sees a rejected id. Fix: the absorb skips `view_rejected` ids and the gate drops their `case_milestones` entry; add the second-refresh test | done; S3a = direct `fix:` |
| S4 | P1 | C1 | openspec change `bind-national-label-once` — per-label binding, exact then ±1-day tie-break, never guess; delta MODIFIES the archived §2 requirement. Viewer only, no re-emit | S0 |
| S5 | P2 | C4 | openspec change `parse-listed-parcel-names` — extractor learns the 、-list, `(原NNN)`, spaced and 號 shapes plus NFKC; unparseable names are reported, not dropped. Re-emit only (no fetch): the 8 dropped cases come back as orphans | S0 |
| R | P2 | B1, B5, B6, C2, §7 4.1 | openspec change `refresh-whole-corpus` — one resumable, rate-limited refresh of all 726 caches: new-case discovery (B1), status re-derivation (B5), cleared status kept as a value (B6), the view backfill (C2, now gated by S3), and the missing headers (§7). Estimate the request count first | S3, S5 |
| S6 | P2 | B2 | openspec change, small — a superseded case's undated orphan node is hidden or chained to its successor | R |
| S7 | P2 | C5 | openspec change — review flag on 使照 disagreement; range guard on ROC years > the current year | user decision |
| S8 | P1 | C6 (types 1–2) | openspec change `bind-area-split-cases` — a recno binds every same-date case of its area split; their twin orphans fold in. Pipeline (`urtpe/links.py:2073`) + re-emit; 31 nodes, 56 cases, 15 projects | S0 |
| S9 | P1 | C7 | direct `fix:` — `buildRelatedLinkLabels` labels each case with its own city name; ships with or before S8, so two cases on one node read apart | — |
| S10 | P2 | C6 (types 3–6) | openspec change — the remaining 40 fallback nodes | user decision, R |
| S11 | P2 | C8 (a) | openspec change `dates-follow-plan-case` — construction dates come from the first 擬訂 plan case (per area); D5 keeps the statistics only. Emit-side, no fetch: recovers 開工/使照 on 8 national-only projects at once | S0 |
| S12 | P2 | C8 (b) | discovery finds the cases the parcel search misses: a sibling-id probe over each cached case's 10-id batch, accepted at land-core similarity ≥ 0.85, every find reported. Measured: 7 missing 擬訂 plan cases + 2 missing 變更 siblings; 3 plan cases need a second source (national 相關連結 or a section name search). Folds into R | S11 |
| S13 | P2 | C9 | openspec change `merge-across-count-shrink` — `(原M筆)` bridges a site shrink; re-merge, aliases, cache migration | S0 |

**Why this order.**

- S0 first, because every later change writes a delta against specs that do
  not exist yet in `openspec/specs/`.
- S1 before any `--fresh` run, because it loses state silently. It is one
  function and one test, so it goes early.
- S3 before R: R refreshes all 726 caches, and without the S3 gate each one
  adds unchecked view ids.
- S5 before R: R's new-case discovery passes new names through the same
  orphan gate. Fix the extractor first, or R drops new cases the same way.
- S4 is independent of the data and can run in parallel with S3.
- B2 waits for R: a full re-discovery changes which cases exist and which are
  superseded.
- S8 (the area-split rule) needs only S0. S9 ships with it, because the
  viewer must label two cases on one node apart.
- S8 runs before R, so R's new-case discovery binds new area splits by the
  same rule.
- S11 is emit-only and needs no network, so it can run right after S0.
  S12 needs network and joins R. S13 changes project ids, so it runs before R,
  or R refreshes 11 caches that are about to merge.
- S7 and S10 wait on the decisions below; S10 also waits on R, because types
  5–6 need cases that only discovery can find.

### Decisions waiting on the user (Batch B + C)

| Entry | Question | Blocks |
| --- | --- | --- |
| ~~C6 / S8~~ | **Decided 2026-11-03** for the 31 area-split ties: one approved recno binds every same-date case of its area split (the user's 吉林508 / 榮星53 examples) | ~~S8~~ unblocked |
| C6 / S10 | The 40 remaining fallback nodes (types 3–6): mark the guessed 北 badge in the viewer, or remove it until R discovers the case? | S10 |
| C5 / S7 | Flag all 22 使照 disagreements for human review, or only the out-of-range year (橋北574-1)? | S7 scope |
| ~~S3~~ | **Resolved 2026-11-04**: the other session implemented and archived the change itself; S3a records the one residual | — |
| R | A full refresh is about 726 projects × their cases against gis.uro. Run it in one sitting, or in resumable slices over several days? | R run |

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

## Appendix G — Batch B measurement (2026-11-03, at `2b96e5b`)

The method and the raw counts behind the Batch B table. Read for detail or audit,
not for execution.

**Baseline.** The payload `viewer/projects.data.js` was emitted 2026-11-02
(`generated_at 2026-11-02T20:31:21+08:00`): 1,442 records / 693 projects,
`published_date 2026-10-15`. The link cache holds 726 dirs. The suite reads
851 passed / 1 skipped (852 collected) at `2b96e5b`.

**B1.** The selector `cached_cases_awaiting_approval` picks a project only when
a cached case carries an application date and no approval date. The 336 project
holds 3 cases, all with a 核定日期, and all cached as 已核准. It is not among
the 89 candidates. Its cache has no `case_headers` key at all. A case filed on it
after 2026-11-02 would not be found by the refresh.

**B2.** 5 caches hold a `superseded_by` entry. 4 of the 5 superseded cases also
appear in `links.orphan_nodes` with an empty `node_date`: 10410012 (吉林705-3),
10806141 (虎林38), 11009142 (雅祥227-4), 11211211 (立農163-2). The 5th,
11010191 (萬華894), has no orphan node: its milestones carry 核定日期
2026/09/10, so the case anchors to recno 14 instead.

**B3.** `discover_project_links` (`urtpe/links.py:554`) writes
`city_case_ids`, `case_schedules`, `case_milestones`, `candidate_names`,
`implementation` and `rewards`. It writes neither `case_headers` nor
`superseded_by`. Only `refresh_project` writes those two. A `--fresh` run
replaces the cache and loses both.

**B4.** `scripts/refresh_awaiting_caches.py --dry-run` returns 89 candidates.
The 4 stranded dirs are among them, and their projects are absent from the
payload, so `load_search_keys` has no anchor for them and the refresh reports
"not searched" every run.

**B5.** A corpus-wide scan of the 726 caches: 1 case has a cached 審查中 and an
approval date (大同764 09605032, 核定 2007/07/06). 3 cases have a cached
已核准/已核定 and no approval date (臨沂318 10409104, 學府125 10611122,
直興373 10405293). §36 recorded 4 and 3.

**B6.** `refresh_project` pops the case from `case_schedules` when the derived
status is empty. A project whose only open status clears keeps only terminal
values, and the viewer then reads it as never-approved. The payload holds 3
never-approved projects, the same count as before the refresh. The invariant
holds by measurement, not by structure.

**B7.** 143 payload projects carry `view_verified_case_ids`, 189 ids in all.
Each id was matched to its label on the project's own `view.html`, the label's
land core was extracted with `extract_landcore_from_case_name`, and the
similarity was computed with `compute_landcore_similarity` against the
project's own anchor land core. 4 ids score below 0.7. Every one of the 189
labels has a land core, so none is undecidable.

Two ids that `docs/viewer-UX.md` §8 listed do not fail this test:

- 09905191 on 文山興安628-1 — the label names 興安段二小段628-1地號等12筆, which
  is the project's own anchor. The cache also holds 09810242, whose name says
  628地號等9筆, and that case sits in another project. The §8 scan read the
  cache's first candidate name, not the anchor.
- 09112120 (崇仁新村) — not a view-verified id in the payload. The city search
  supplied it, and the project's `view_verified_case_ids` is empty. The spec's
  parcel-less rule still needs a test.

**B8.** The payload holds 596 orphan nodes. 3 have no `case_name`, so they have
no stage and no track: 10202065 on 中山254, 09511211 on 大安557 (施工中),
09807161 on 大安龍泉169. All 3 entered through `view_verified_case_ids`, and all
3 belong to another project. The `viewer/app.js` comment that says
"corpus: 0 post-harvest" is stale.

**Order.** B7 must land before B8, and B8 must land before wave 5's orphan
placement is trusted for those 3 nodes. B1 gates B2 and B5, because a full
re-discovery changes which cases exist. B5 gates B6.

## Appendix H — Batch C measurement (2026-11-03, at `370ddb2`)

The method and the raw counts behind the Batch C table. Read for detail or
audit, not for execution. Every number came from one-off scripts over
`viewer/projects.data.js` (emitted 2026-11-02, 1,442 records / 693 projects)
and `data/.link_cache/` (726 dirs); the scripts were deleted after the run.

**C1 (corrected in the 2026-11-03 review).** First pass: `nationalBoundTo`
re-implemented by hand, counted over the 632 twur projects' 1,720 approval
labels: exact-date node exists 963; no stage+track node 327; a stage+track
node exists but no exact date 430 (+1 day 331, −1 day 11, +2..+6 days 43,
−2/−10 days 3, ≥120 days 42). That pass read the §2 date rule as a filter on
every label, which it is not, so "430 the design would leave unbound" was
wrong. Second pass (the review): the shipped `CHINESE_DIGIT`/`nationalLabelKey`,
`trackMatches` and `nationalBoundTo` were extracted from `viewer/app.js` and
run in a VM over the payload. Labels with 2+ stage+track candidates: 19, with
41 candidate nodes. The shipped code badges all 41, because it scores each
node alone. The spec's exact-date tie-break binds 10 of the 19; a ±1-day
tie-break binds 17. Nodes with a 國 that neither the spec nor
`view_verified_case_ids` gives: 16. The pipeline's own `_match_case_by_date`
already applies exact-then-±1-day to the 北 badge, so the tolerance follows
repo precedent.

**C2.** Method: for each cache dir holding `view.html` (642 of 726), parse
case ids with `urtpe.links.extract_case_ids_from_view`; 587 dirs yield ≥1 id,
758 ids in all. Match dir→project by dir name (the dir names are
`project_id` slugs; the `https___twur…view_NNNN.html` flat files are
portal-index pages, not project caches — 0 of them are dirs). Subtract the
project's current `view_verified_case_ids`: 435 projects gain, 557 new ids.
Check each new id's city name (`links.candidate_names[cid]`) with
`extract_landcore_from_case_name` + `compute_landcore_similarity`. Against the
project's newest 案名: 538 pass ≥0.7, 5 score 0.0, 10 are parcel-less names,
9 ids have no city name in the payload (their caches were never refreshed).
The review re-ran the 5 against each cache's own `land_core` field (all 726
caches carry one, and it parses): 10712281, 10312101, 10510181 and 10812201
score 0.95, 11501039 scores 0.85. So the 0.0 came from unparseable 案名 on
the project side, and none of the 557 ids is foreign.

**C3.** The five §8 ids were grepped in the emitted payload directly.
Placements: 10202065 in 中山254's `view_verified_case_ids` (孤 anchor,
2020-11-03); 10906092 in 吉林898 (node 307); 09608220 in 犁和102 (孤,
2009-01-15); 09511211 in **both** 吉林603 and 大安557; 09807161 in 龍泉169
(孤, 2013-11-29). Wave 4 (`00cb177`) landed before wave 3b against the doc's
own ordering rule. **Review update:** after `95ea60c` the change
`reject-foreign-view-cases` was proposed (`4ca6cc2`) (proposal, design, 23 open tasks, three
spec dirs). Its design applies §8 decision 1 and finds 10906092 accepted (its
city name is 吉林898) and 4 ids rejected. The review then counted recno nodes
whose anchored case is one of the 4 rejected ids: 0. So the rejected ids grant
no 國 badge; their harm is the orphan nodes that show another project's
dates. The draft's decision pass runs after the per-case loop, but the view
absorb at `urtpe/links.py:1667` runs after that and merges ids back; the
draft needs the absorb to skip `view_rejected` ids.

**C4.** First pass: ran `extract_landcore_from_case_name` over all 693
projects' newest node case names: 11 return "". The U+F963 finding:
三興972's and 桃源424-8's anchor names print 擬訂臺北市 with the compatibility
form of 北 (U+F963) after 臺 (U+81FA), so the `name.split("臺北市", 1)[1]`
split misses and the fallback pattern grabs `市信義區…`.
`unicodedata.normalize("NFKC", name)` recovers those two; 敦化510's 松化區 is
the PDF's own typo. **Review pass:** every cache carries a parseable
`land_core`, so C4 does not block C2 or C3. The real impact is the orphan
gate at `urtpe/links.py:2162`. Ran the extractor over the city names of every
cached case (`candidate_names` + `search_rejected`): 33 return "". Joined with
the payload: 21 are anchored on a recno node, 0 are orphans, 12 are in
neither. 4 of the 12 are 崇仁新村 (parcel-less, by design). The other 8 are
real cases dropped without a report: 09305081, 09305082, 09407301–09407304
(華中247), 09205060 (長安709), 09406102 (南港531-4).

**C5.** Cross-read `milestones_taipei["使照核發日期"]` against
`milestones_national["使用核發日期"]` (ROC→ISO) over the 632 twur projects:
both present 282 (equal 260, differ 22); city-only 32; national-only 13.
The 22 disagreements were listed and read by eye: 4 are single-day offsets,
2 are year or month typos (榮星306, 虎林310), the rest are 2–12-day offsets
across offices. The out-of-range scan over every national value found one
ROC year above 115: 橋北574-1's `使用核發日期 = 291.08.02` → the viewer's
`1911 + 291 = 2202-08-02`; the city's 使照核發日期 reads 2022/08/02, so the
national page typo'd 111→291. Render check (review): the 使照 slot and the
stage chip read the city value first, so 2202 shows only in the 推動歷程
card, through `fmtDate`.

**C6.** Re-ran the pipeline's own `_match_case_by_date(member_date, disc)`
for every emitted node against its project's `case_milestones`, and compared
its answer with the `links.taipei[0]` the payload actually carries:
1,356 nodes match by date; 71 carry a case the matcher would not choose
(those are the positional fallback of `urtpe/links.py:2067–2081`); 15 nodes
carry no case at all. Distinct projects with a fallback node: 51. The worst
family is 榮星53 — 4 nodes dated 2005-11-03 / 2007-11-20 / 2008-12-22 /
2010-02-04, all bound to case 09001121 whose only approval date is
2007-11-20.


