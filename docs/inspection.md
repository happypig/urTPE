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
| Batch C | 6 findings queued, 0 executed (post-viewer-UX gaps) |

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
| B7 | A view-verified case may belong to another project | 4 of 189 view-verified ids have a label whose land core is another project (similarity < 0.7): 10202065, 10906092, 09608220, 09807161 | openspec change | — |
| B8 | 3 nameless 孤 anchors carry another project's milestones | 10202065 (中山254), 09511211 (大安557, 施工中), 09807161 (龍泉169) | openspec change | B7 |

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

### Batch C — the post-viewer-UX gaps, collected 2026-11-03 — **QUEUED, not started**

The viewer-UX waves 1–5 landed (`91699bb`…`370ddb2`): §5 centered, §1+§6 the
gutter, §7 the [無]/[NA] labels, §2 the 國 binding, §3+§4 the event/orphan
placement. This batch collects what those waves left open, measured at `370ddb2`
on the same payload (1,442 records / 693 projects, `published_date 2026-10-15`)
and the 726 cache dirs. Wave 3b (`docs/viewer-UX.md` §8) never ran — no
`reject-foreign-view-cases` change exists in `openspec/changes/` or the archive —
so C3 re-lists it here as the batch's gate.

| ID | Finding | Evidence now | Form | Gate |
| --- | --- | --- | --- | --- |
| C1 | `nationalBoundTo` binds without an exact date — the code guesses, the §2 spec says never | 1,720 national approval labels: exact 963, no-node 327, drifted 430 (the shipped code binds all 430; the spec binds 0 of them). 331 of the 430 are off by exactly 1 day (公告 vs committee date); 343 have a node within ±1 day; 9 have 2–3 candidate nodes and the code picks the first | direct `fix:` commit + spec delta to the §2 requirement | — |
| C2 | The offline `view_verified_case_ids` backfill has never run | 642 caches hold `view.html`; 587 parse to ≥1 case id, 758 ids in all. 435 projects would gain ids (557 new; 143 projects / 189 ids carry ids today). 553 of 557 new ids pass the land-core check; 4 fail it (C4's artefacts, not foreign ids); 10 names are parcel-less; 9 have no city name in the payload | openspec change (the refresh writes caches → the single-writer rule) | C3, C4 |
| C3 | Wave 3b (`docs/viewer-UX.md` §8, `reject-foreign-view-cases`) never ran | the 5 foreign ids of Batch B7/B8 are all still in the payload: 10202065 (中山254), 10906092 (吉林898), 09608220 (犁和102), 09511211 (吉林603 **and** 大安557 — shape B), 09807161 (龍泉169). Each grants a wrong 國 badge through §2 decision 2 | openspec change | — |
| C4 | 11 project anchors yield no land core from their own 案名 | the anchor names print 號 not 地號 (大業401, 美仁831-3, 陽明291), a 松山→松化 typo (敦化510), compatibility-char corruption (三興972, 桃源424-8 print 擬訂臺北市 with U+F963 北), or a multi-parcel list (長安709, 仁愛679, 懷生316, 南港531-4, 華中247); 實踐641 and 崇仁711-3 name no parcel at all. `extract_landcore_from_case_name` returns "" for all 11 | openspec change | — |
| C5 | 使照 disagreement between the two portals is not flagged | 282 projects hold 使用核發/使照核發 from both portals: 260 agree, 22 differ (吉林811 2013-09-11 vs 2013-11-12; 榮星306 year; 虎林310 month). 13 projects hold it national-only, 32 city-only. 橋北574-1's national value `291.08.02` converts to 2202-08-02 — the only out-of-range ROC year in the payload | openspec change | — |
| C6 | The 北 positional fallback binds 71 nodes on 51 projects, unmarked | re-run of the pipeline's own `_match_case_by_date` over the payload: 1,356 nodes match by date, 71 do not (榮星53: 4 nodes dated 2005–2010 all bound to case 09001121, approved 2007-11-20), 15 have no case. The user has not decided between marking the fallback and leaving orphan nodes | openspec change, after the user decides | — |

**C1 in detail.** `openspec/changes/bind-national-badge-to-named-node/design.md`
decision 1 says: "If none equals, leave the label unbound. Never guess."
`viewer/app.js:130` (`nationalBoundTo`) scores a node 2 for an exact date and 1
otherwise, then takes the best score — so a label with no exact match still
binds its first stage+track candidate. The drift profile (331 of 430 off by
exactly 1 day) matches the 公告-vs-committee offset that
`urtpe/links.py:1856` (`_match_case_by_date`) already tolerates for the 北
badge. Fix: score 1 only when the node date is within ±1 day; leave unbound
when 2+ nodes qualify. This changes 394 of 430 bindings from "first
candidate" to "nearest date", and unbinds the 9 multi-candidate labels and 78
far-drift ones. The §2 spec requirement needs a delta: its 國-binds-by-date
tie-break scenario must name the tolerance and the never-guess rule the code
must follow. The 327 no-node labels stay unbound (their stage+track node does
not exist — mostly 權變 labels on 事業-only families).

**C2 in detail.** Method: parse every cached `view.html` with the pipeline's
own `extract_case_ids_from_view`, match each dir to its payload project by
dir name (= project_id), and subtract the ids the project already holds. The
538 passing ids checked clean with `compute_landcore_similarity ≥ 0.7`
against the project's own anchor name. The 9 ids without a city name come
from caches whose `candidate_names` lack them — the refresh supplies the name
when it runs. C3 must land first (§8 decision 2 moves foreign ids to their
own project), and C4 first among those, so the similarity check can decide
every id.

**C4 in detail.** The 11 anchors break into three shapes:

| Shape | Projects | What the name prints |
| --- | --- | --- |
| 號 without 地號 | 大業401, 美仁831-3, 陽明291 | `401號等10筆` — the regex wants `地號` |
| Typo / compatibility chars | 敦化510 (松化區), 三興972 + 桃源424-8 (U+F963 北 inside 擬訂臺北市) | the PDF's own glyphs |
| Multi-parcel list before 地號 | 長安709 (`709、711地號`), 仁愛679, 懷生316, 南港531-4, 華中247 | the regex stops at the first 、 list |
| Update-unit name, no parcel | 實踐641, 崇仁711-3 | `木新路三段95巷南側地區…` / `崇仁新村土地…` |

The payload's project_id is still correct for all 11 (the slug comes from the
land column, not the name), so nothing downstream is wrong today — but C2's
similarity check cannot decide the 5 ids whose projects sit in this list
(10712281, 10312101, 10510181, 11501039, 10812201 measure 0.0 against a
corrupted or missing own-core; each city name actually names the project's
own section+parcel, so these are artefacts, not foreign ids), and the
parcel-less names are exactly the case the `orphan-case-anchoring` spec's
parcel-less rule anticipates. Fix: normalise compatibility chars (NFKC)
before extraction — that recovers 三興972 and 桃源424-8 — and teach the
extractor the 號 form and the 、-list form. The 松化 typo is the PDF's own
glyph; no extractor change recovers it.

**C5 in detail.** The national page's 使用核發日期 and the city's 使照核發日期
are the same fact from two offices. 22 disagreements include both plausible
readings: 榮星306 (2022-09-23 vs 2023-09-23) and 虎林310 (2022-11-11 vs
2022-01-11) look like single-digit typos — two sources prove a typo exists,
neither proves which one. The pipeline emits both today with no flag. The
`291.08.02` value is a third shape: an out-of-range ROC year the viewer
faithfully converts to 2202. Fix: a review flag on disagreement (not a
repair), plus a range guard on ROC conversion.

**C6 in detail.** The 71 fallback nodes are the same population the
§34 residual watch named ("17 drift families"). `_match_case_by_date` returns
"" for them and `urtpe/links.py:2067–2081` falls back to
`disc.city_case_ids[0/1]` by track position. The badge is then wrong in both
directions the §34 note recorded. Options were put to the user on 2026-11-03
(mark the fallback / use orphans); no decision yet, so the item is queued
with that gate.

**Order.** C3 first (it is already §8, and C1's badge trust and C2's backfill
both depend on it). Then C1 (small, viewer + spec delta). Then C4 (unblocks
C2's decidability), then C2 (the backfill, with C3's move logic in place).
C5 and C6 are independent; C6 waits on the user decision.

### Decisions waiting on the user (Batch C)

| Entry | Question | Blocks |
| --- | --- | --- |
| C6 | Mark the 71 fallback-bound 北 nodes in the viewer, or rebind them to orphan nodes? | C6 |
| C5 | Flag the 22 使照 disagreements for human review, or only the out-of-range ROC years? | C5 (scope) |

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

**C1.** The shipped `nationalBoundTo` was re-implemented verbatim in the probe
(score 2 exact / 1 otherwise, best score wins, combined track matches either).
Counts over the 632 twur projects' 1,720 approval labels
(`nationalLabelKey` non-null): exact-date node exists 963; no stage+track node
at all 327; stage+track node exists but no exact date 430. The 430 are what
the code binds and the design would not. Their national−node day deltas: +1
day 331, −1 day 11, +2..+6 days 43, −2/−10 days 3, ≥120-day outliers 42 (of
which 9 labels have 2–3 candidate nodes — 大同市府247's three 變更/事業計畫
nodes 2013-03-28 / 2017-07-11 / 2022-10-20 against label 102.04.01). A ±1-day
filter resolves exactly one candidate for 343 of the 430, resolves 0 or 2+
for 87 (unbound under tolerance), and the shipped first-candidate pick
disagrees with the tolerance pick only inside the 43 far-drift rows. The
pipeline's own `_match_case_by_date` already applies exact-then-±1-day to the
北 badge, so the tolerance follows repo precedent.

**C2.** Method: for each cache dir holding `view.html` (642 of 726), parse
case ids with `urtpe.links.extract_case_ids_from_view`; 587 dirs yield ≥1 id,
758 ids in all. Match dir→project by dir name (the dir names are
`project_id` slugs; the `https___twur…view_NNNN.html` flat files are
portal-index pages, not project caches — 0 of them are dirs). Subtract the
project's current `view_verified_case_ids`: 435 projects gain, 557 new ids.
Check each new id's city name (`links.candidate_names[cid]`) with
`extract_landcore_from_case_name` + `compute_landcore_similarity` against the
project's own anchor name: 538 pass ≥0.7, 4 score 0.0 (all four are C4
artefacts on the project side — the city name itself names the project's own
section+parcel; verified by reading the names), 10 are parcel-less names,
9 ids have no city name in the payload (their caches were never refreshed).

**C3.** The five §8 ids were grepped in the emitted payload directly.
Placements: 10202065 in 中山254's `view_verified_case_ids` (孤 anchor,
2020-11-03); 10906092 in 吉林898 (node 307); 09608220 in 犁和102 (孤,
2009-01-15); 09511211 in **both** 吉林603 and 大安557; 09807161 in 龍泉169
(孤, 2013-11-29). No `reject-foreign-view-cases` change exists in
`openspec/changes/` (only `bind-national-badge-to-named-node`,
`callout-gutter`, `place-events-and-orphans-by-node`,
`show-no-state-case-status`) or in the archive (nothing dated 2026-11-03).
Wave 4 (`00cb177`) landed before wave 3b against the doc's own ordering rule.

**C4.** Ran `extract_landcore_from_case_name` over all 693 projects' newest
node case names: 11 return "". Read each name by eye and grouped the shapes
(號-without-地號 3, typo/compatibility-chars 3, 、-list 4, no-parcel update
names 2 — 實踐641's name has no 地號 at all, 崇仁711-3's says 新村). The U+F963
finding: 三興972's and 桃源424-8's anchor names print 擬訂臺北市 with the
compatibility form of 北 (U+F963) after 臺 (U+81FA), so the
`name.split("臺北市", 1)[1]` split in the extractor misses and the fallback
pattern grabs `市信義區…`. `unicodedata.normalize("NFKC", name)` before
extraction recovers 3 of the 11 (三興972, 桃源424-8, and 敦化510 still fails —
its 松化區 is the PDF's own typo, unfixable by normalisation).

**C5.** Cross-read `milestones_taipei["使照核發日期"]` against
`milestones_national["使用核發日期"]` (ROC→ISO) over the 632 twur projects:
both present 282 (equal 260, differ 22); city-only 32; national-only 13.
The 22 disagreements were listed and read by eye: 4 are single-day offsets,
2 are year or month typos (榮星306, 虎林310), the rest are 2–12-day offsets
across offices. The out-of-range scan over every national value found one
ROC year above 115: 橋北574-1's `使用核發日期 = 291.08.02` → the viewer's
`1911 + 291 = 2202-08-02`; the city's 使照核發日期 reads 2022/08/02, so the
national page typo'd 111→291.

**C6.** Re-ran the pipeline's own `_match_case_by_date(member_date, disc)`
for every emitted node against its project's `case_milestones`, and compared
its answer with the `links.taipei[0]` the payload actually carries:
1,356 nodes match by date; 71 carry a case the matcher would not choose
(those are the positional fallback of `urtpe/links.py:2067–2081`); 15 nodes
carry no case at all. Distinct projects with a fallback node: 51. The worst
family is 榮星53 — 4 nodes dated 2005-11-03 / 2007-11-20 / 2008-12-22 /
2010-02-04, all bound to case 09001121 whose only approval date is
2007-11-20.


