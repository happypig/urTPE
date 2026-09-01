# Two Portals — Field Notes & Alignment Map (v2)

*Exploration summary: Taipei City ashx API vs National Portal (twur.nlma.gov.tw) for project 中山區-中山段一小段-254地號等13筆*

> **Reference doc** — portal behavior, endpoint map, open issues, priorities. Companions:
> - **`docs/portal_operations_log.md`** — dated session/incident/campaign narratives (anchors §6.x, §16-§19 preserved there; this doc keeps pointer tables)
> - **`docs/cli_enhancement.md`** — forward design for the portal-discovery CLI consolidation (§12 #3)
> - `docs/sync_architecture.md` — sync-model design (§12 #5)
>
> Resolved items are marked `[RESOLVED]`, code claims carry the verified file:line, empirical API values are tagged `[live-probed]` (not re-verified this pass).

---

## 0. Decision Summary

| Decision | Status |
|---|---|
| 推動歷程 parser silent-failure root cause | `[RESOLVED]` — applied, backfilled, verified in `viewer/projects.data.js` |
| `jud_ok_date2` field | `[RESOLVED]` — label identified; **mapping added to `STAGE_FIELD_MAP`** (2026-08-24, incl. `jud_ok_date` label fix; regression-tested) |
| Join approach | Portal = gazette date; Taipei = committee date. **±1 day is a heuristic, not a rule** (Δ=0 observed). |
| Do we need both sources? | Yes — they cover disjoint lifecycles (Taipei pre-approval depth; Portal post-approval breadth + revision rollup). |
| 3 top forks | Portal crawl recovery **`[CONVERGED]`** (§16) · `Report_Date` semantics **`[RESOLVED]`** (2026-08-25) — 成果報備日期 confirmed (§12 #7) · Phase-D **`[RESOLVED]`** (2026-08-25) — `phase='D'` seen, taxonomy corrected (§6.5) |
| Curated fallback wrong view (河堤段263-19 → 板橋 view/1042) | `[RESOLVED]` — mapping fixed to view/262; cache + view.html refreshed (see §6.6) |
| Per-node case links (positional mislink / missing links) | `[RESOLVED]` — date-aligned anchoring in `attach_links_to_projects`, positional fallback kept (see §6.6) |
| Fetch-script loose parcel match (`parcel in html`) | `[RESOLVED]` — strict parcel+地號 + title section/parcel/count match (see §6.6) |
| third.ashx integration (開工/使用執照 into data model) | **`[RESOLVED]`** — OpenSpec change `add-taipei-implementation-data`: fetch/cache + emission + viewer all done (schema v2; bulk pass 2026-08-24: 691 caches with per-case payloads, 689 projects emit `implementation`, 254 family shows 開工 2013/09/10 / 使照 2016/08/29) |
| Per-record implementation snapshots never emitted (viewer callouts dead) | **`[RESOLVED]`** (2026-08-26) — attach flow set `member.implementation` but `build_project_graph` serialized only `node["links"]`; fixed node emission + `--from-js` loader round-trip; regen took carrying nodes **0→1,345/1,419** (see §6.9) |
| Parcel-count mismatch in land-core join (portal 11筆 vs Taipei 13筆) | **Open — needs OpenSpec change** (touches land-identity semantics). Curated-exception recoveries proceed without it (operations log §6.14) |
| Portal coverage for older projects | **`[CONVERGED]`** (2026-08-25) — §18 restore + final targeted run consumed the queue: **302/709 twur (43%), 302 milestones, 63 使用核發 (9%)**. The ceiling is the portal's own bimodal Taipei coverage (2002-03 back-fill + 2022+ live feed; **2004-2021 registry hole ≈ 250-290 projects** — see §16). **Superseded same night** by `fix-targeted-portal-matcher`: the "hole" was mostly matcher false-rejects → **581/709 (82%), 581 milestones, 248 使用核發 (33%)** — see §0 last row + §16.1 |
| Bulk refresh wiped targeted-fetch links (2026-08-25) | **`[RESOLVED]`** (2026-08-25 02:17) — `scripts/restore_national_links_2026_08_25.py` merged the 3 national fields back into the 183 regressed caches from the backup, viewer re-emitted: 292/292/58 verified; root cause + guard rules in §18 |
| Portal discovery consolidation (CLI vs fetch script) | **Decided** — library-first: every portal capability (matcher, ledger, sweep, harvests) moves into `urtpe/links.py`, opt-in CLI flags, scripts become thin wrappers; guardrails-as-code (coverage guard, lockfile, single merge path). **Design: `docs/cli_enhancement.md`** (extends `sync_architecture.md` §4); needs OpenSpec change |
| PDF + portals sync model | **Decided** — event-cascade with PDF as heartbeat; liveness-based refresh (freeze phase-E, refresh C/D); `project_id`/land-core are the only cross-PDF keys (recno shifts every gazette); full design in `docs/sync_architecture.md`; needs OpenSpec change (`portal-sync`) |
| Cache concurrency (2026-08-24 incident) | **`[RESOLVED]`** — 47 wiped caches repaired, poison URL-caches deleted; **single-writer rule** now in force (see §17) |
| Strict-matcher false rejects in targeted fetch (parcel extraction + int-vs-str count) | **`[RESOLVED]`** (2026-08-25, change `fix-targeted-portal-matcher`) — sweep recovered **+252 links (302→554, 78% of 709)**, 使用核發 63→223; the "2004–21 registry hole" was mostly self-inflicted rejection (§16.1) |
| Second cache wipe — §6.8 regen deleted all 709 `result.json` (2026-08-26), §18 mechanism recurred at 5× scale | **`[RESOLVED]`** (recovered 2026-08-28/29; details in operations log §6.10): offline `view.html` backfill +282, sweeps +162, merge-backs held sweep gains → **twur 561/709 (79%), 使用核發 242 (34%), resolved 696/709 (98.2%)**; 148 twur-less = ledger negatives (§16.1 boundary). Remaining lever: §12 #4 count normalization. Root-cause lesson: the §12 #1 coverage guard was still unbuilt — build it before any destructive job |

---

## 1. Sources at a Glance

| Aspect | Taipei `gis.uro.taipei` (ashx) | National `twur.nlma.gov.tw` |
|---|---|---|
| **Access** | JSON APIs: `Get_updcase_list`, `Get_project168_second`, `get_project168_top` | HTML pages: list `/0`, view `/view/{id}` |
| **Granularity** | One **case_id** per application attempt (4 for this project) | One **view_id** per project (view/136 aggregates all revisions) |
| **Lifecycle coverage** | Deep pre-approval (~17 dated events/case) + 建照核發 | Gazette dates for every revision + 使用核發 + rich 基本資料 |
| **Post-approval** | 建照核發 only (dated); `phase`/`NAME`/`schedule` (undated status) | 使用核發 (dated); no process detail |
| **Status tracking** | `schedule`: 已公告/完成成果備查/自行撤回 | `資料更新日期`; free-text `NAME` |
| **Reliability** | Stable, no WAF (so far) | WAF resets crawler; list crawl partial (110/709) |

---

## 2. The Four Taipei Cases vs One Portal View

```
Taipei cases (ashx)                    National portal (view/136)
────────────────────────────────────────────────────────────────────────
09811141 擬訂 事+權  核定 2012/08/27    │
09811142 變更  事+權  核定 2016/08/23    ├──▶ single view aggregates
09811143 變更二 權變  自行撤回 申請2016/09/22    │   all revisions
09811144 變更二 權變  核定 2017/04/13    │
```

- **143 & 144 are name-twins**: identical case name → same application resubmitted after withdrawal. Note **both** carry `變更二` — 143 is the withdrawn attempt, 144 the approved one.
- Portal shows **one row per revision ordinal** (1st, 2nd…) with paired 事業/權變 dates.
- Taipei splits by **application attempt** (each gets own case_id + full process trace).

---

## 3. Date Alignment — The 1-Day Offset *(heuristic, not a rule)*

| Milestone | Portal (gazette) | Taipei (ashx) | Delta | Meaning |
|---|---|---|---|---|
| 事業計畫核定 | 101.08.28 (2012-08-28) | 2012/08/27 | +1 day | gazette 公告日 vs 會議核定日 `[live-probed]` |
| 權變核定 (原案) | 101.08.28 | 2012/08/27 | +1 day | same `[live-probed]` |
| 1st變更 事業 | 105.08.24 | 2016/08/23 | +1 day | same `[live-probed]` |
| 1st變更 權變 | 105.08.24 | 2016/08/23 | +1 day | same `[live-probed]` |
| 2nd變更 事業 | 106.04.14 | 2017-04-13 | +1 day | same `[live-probed]` |
| 2nd變更 權變 | 106.04.13 | 2017/04/13 | 0 | **observed same-day** `[live-probed]` |

**Assessment**: portal date = gazette publication date (next business day after committee approval). Taipei date = committee approval date. Store both — they are semantically different. **But** the "+1 day" generalizes from 5 samples, 1 of which has Δ=0. Treat as an *observed trend*, and match on **±1 day with a same-day fast-path**, not a strict "+1". Do not build an invariant on it.

---

## 4. What Each Source Uniquely Provides

### Taipei ashx (pre-approval depth)

```
17+ dated events per case:
  公聽會 → 申請 → 公告公展 → 公展公聽會 → 幹事會 → 幹事複審 → 聽證 → 審議會 → 核定
  × (事業/權變/概要 tracks) × (attempts 141, 142, 143, 144)
+ 建照核發 (post-approval, 1 month later)
+ 當前狀態: phase E/C, NAME "執行階段_更新案完成成果備查"
```

### National portal (post-approval breadth + revision rollup)

```
Aggregated revision table (all on one page):
  事業/權變 申請+核定 per revision ordinal
  使用核發 105.08.29 ★ ONLY SOURCE
基本資料:
  面積/容積率/建蔽率, 產權結構 (土地54筆/建物54戶, 公私有比例),
  同意比例 (土地92.45%, 建物92.45%),
  更新前後價值 (10.51→27.62 億), 成本/分回,
  社會關懷 (安置50戶, 綠建築銀級, 步道230㎡),
  區段規格 (容積獎勵, 允建容積, 樓層14F/5B, 用途)
資料更新日期: 112.03.17 (last refresh)
```
*Values `[live-probed]` for view/136.*

---

## 5. Known Data Bugs & Quirks *(with status)*

| Bug | Location | Impact | Status |
|---|---|---|---|
| **Chimera merge** | `links.py:535 all_taipei_milestones.update(ms)` *(doc v1 said :489 — corrected)* | Last-write-wins across cases; 141's 核定 2012/08/27 overwritten by 142's 2016/08/23 → viewer card shows wrong anchor date for node 1219 | **Open** — mechanism confirmed in code; fix = retain per-case timelines (see §6.1) |
| **Missing `jud_ok_date2` mapping** | `STAGE_FIELD_MAP` (`links.py:600` starts; **no `jud_ok_date2` entry**) | `jud_ok_date2=2012/04/16` filled but unmapped → silently dropped | **`[RESOLVED]`** — `jud_ok_date2 → 權變審議通過日期` added (see §6.2); old caches keep old labels until the bulk discovery refresh |
| **Wrong `jud_ok_date` label** | `links.py:615 ("jud_ok_date", "概要審議會通過日期")` | Mislabeled; UI calls it 審議通過日期 | **`[RESOLVED]`** — relabeled `審議通過日期` (see §6.2); old caches keep the old label until the bulk discovery refresh |
| **`uro_chk_date2` inconsistency** | `top.ashx` | Case 144 has approval in `second.ashx` (2017/04/13) but `top.ashx` leaves it empty | **Open** `[live-probed]` |
| **No withdrawal date** | Both | 143 自行撤回 has only 申請權變 2016/09/22; withdrawal date nowhere published (see §6.3) | **Open** — best anchor = application date + 撤回 badge |
| **Portal cross-link error** | view/136 | 縣市政府案件連結 points to `case_id=10202065` (辛亥段, 大安區) — wrong project | **Open** `[live-probed]` |
| **推動歷程 parser failure** | `links.py` `ViewPageParser` (old hidden-div-only path) | `milestones_national={}` for all projects | **`[RESOLVED]`** — see §8, verified fixed |
| **Curated fallback wrong view** | `data/taipei_case_ids.json` (河堤段263-19 → view/1042 = 新北市板橋區 project, bogus case_id "10421234") | Wrong twur link + wrong national milestones cached/emitted for the project | **`[RESOLVED]`** — mapping → view/262, cache/view.html refreshed (see §6.6). Provenance of the bad entry: unknown (POC-era hand entry, no audit trail — see §17 addendum) |
| **Per-node positional mislink** | `links.py` `attach_links_to_projects` (`city_case_ids[0]/[1]` by track keyword) | 10204032 (核定 2016/07/05) attached to recno 772 (2019-08-01) instead of recno 1042; 金華段513-3 cases attached to no node at all — violates official-link-discovery "Per-stage city links land on the right node" | **`[RESOLVED]`** — date-aligned anchoring (see §6.6) |
| **Fetch-script loose parcel match** | `scripts/fetch_remaining_national_portal.py` `find_matching_view` (`parcel in html`) | Substring collisions (263-19 vs 209-19) and same-parcel different-project matches (444等7筆 vs view/264 444等**17**筆) | **`[RESOLVED]`** — strict parcel+地號 + title tuple match (see §6.6) |
| **Parcel-count mismatch join miss** | land core includes `等N筆` count; portals disagree (金華段513-3: portal 11筆 vs Taipei 13筆, same case — 實施者 江陵 confirmed on view/265) | Project with an existing portal page gets no twur link | **Open — needs OpenSpec change** |
| **Taipei parcel search over-return** | `search_taipei_cases_api` keeps every `r_progress_detail` case from the search response; the platform matches at **renewal-unit/district level** (R13 街廓), not strict parcel | 南港段一小段520-2等18筆: 7 links for 2 approvals — 4 are sibling R13 cases on different land (522等45筆/467等41筆/403-2等28筆/561等5筆 概要s; 地號清單 verified zero overlap, see §6.7) | **Open** — Taipei twin of §6.6; fix = `case_name` parcel guard (fold into §12 consolidation) |
| **third.ashx fetch/cache vs emission gap** | fetch+cache **done** (691 caches carry per-case `implementation`/`rewards` after the 2026-08-24 bulk pass); `graph.py` emits `implementation`/`rewards` + 開工日期/使照核發日期 milestones; `viewer/app.js` renders 執行階段/獎勵資料 cards | ~~開工/使用執照 absent from data model & viewer~~ | **`[RESOLVED]`** — `add-taipei-implementation-data` (schema v2) |
| **Per-record snapshot emission gap** | `build_project_graph` emitted only `node["links"]`; the `member.implementation` snapshot set by the attach flow never reached the document; `_load_projects_from_js` also dropped project-level `implementation`/`rewards` on re-load | Per-record callouts rendered for nobody — 0/1,419 nodes carried snapshots while 689/709 projects had project-level data; archived change's task 10.2 ("additive optional node field") was checked off but only half-landed | **`[RESOLVED]`** (2026-08-26) — see §6.9 |
| **Cache concurrency wipe (2026-08-24 ~21:23)** | 4 writers raced `data/.link_cache` (2 dry-run parents + 2 orphaned CLI children); torn reads → spurious cache misses → live re-discovery read 75/126 corrupt URL-caches (orphan mechanism corrected 2026-08-25 — see §17 #1) | 47 caches wiped to empty `national_milestones`; 62 `view.html` rewritten corrupt | **`[RESOLVED]`** — repaired 47/47, all 126 URL-caches deleted, **single-writer rule** in force (see §17) |
| **Bulk refresh regression (2026-08-25 ~01:05)** | `links.py:565-585` resolves view_id from `portal_index.json` (110 entries, WAF-capped §9) + fallback JSON (3 entries); the targeted campaign's ~180 extra mappings lived only inside the deleted `result.json` | twur/`national_milestones` 292→109; 使用核發 58→**1**; viewer emitted regressed state | **`[RESOLVED]`** — restored 183 caches from `.link_cache_backup_20260824`, re-emitted, verified 292/292/58; guard rules in force (see §18) |
| **Cross-family milestone pollution (fragment families)** | `search_taipei_cases_api` over-return (§6.7) + last-write-wins merge | 162 construction events across 82 families attribute to cases anchoring nowhere / to other families; 112 events double-display the same dates in 2 graphs; B1b subset (55 events) likely shows **wrong** dates from foreign cases | **Open — needs OpenSpec change** (search strictness + fragment merge candidates; see §6.8) |
| **都市更新計畫案 案名 abbreviation (missing 事業)** | PDF gazette rows c.2009-2011 print `土地都市更新計畫案` (no 事業); platform `CASE_NAME` always writes `土地都市更新事業計畫案` | `_tracks()` fallback assigns track `都市更新計畫` instead of `事業計畫` — 10 nodes / 6 families (長春段775 ×3, 南海段41-4, 河堤段263-19, 奇岩段444, 圓環段103-2 ×2, 金華段513-3 ×2) | **Open — small cleanse normalization** (same class as 權利變換案==權利變換計畫案; platform cross-ref 18/18 spell 事業計畫案, data: `data/_gengxin_plan_crossref.json`) |
| **Virtual-node same-date row order was platform-search-dependent** | 29 families carry ≥2 virtual nodes on one `node_date` (attempt twins 吉林段1021 09902261/10201171; 概要+計畫 same-day 吉林段676; 3-stage 吉林段717) | Cluster tie-break chain leaves same-date/same-stage virtuals tied → JS sort stability resolved them by input order = platform search-response order (load-dependent, unspecified); virtual nodes had no edges at all | **`Decided`** (2026-08-31, design.md D12) — sort row-by-row by **case_id ascending** (real via anchored case_id `links.taipei[0]`; virtual via own `case_id`; case-less real = empty key → first) **+ chain consecutive virtuals row-by-row with a dashed virtual revision edge** (attempt-succession; cross-stage same-day pairs stay unchained) |

---

## 6. Session & Incident Log (moved)

All dated session narratives (§6.1-§6.10: wrong-match fixes, over-return, fragment families, snapshot emission, the coverage audit + 2026-08-26 wipe + 2026-08-28/29 recovery campaign) now live in **`docs/portal_operations_log.md`**. Section anchors (§6.x) are preserved there — citations like "see §6.7" resolve in that file.

| Anchor | One-line summary |
|---|---|
| §6.1-6.5 | Provenance/join strategy, label maps, withdrawal date, occupancy permit, phase taxonomy |
| §6.6 (08-24) | Wrong-match bugs + per-node date-aligned linking + strict portal matcher |
| §6.7 (08-25) | Taipei search over-return (R13 street-block) + parcel guard fix shape |
| §6.8 (08-26) | Cross-family pollution + fragment families + guard implementation |
| §6.9 (08-26) | Per-record snapshot emission fix + `Exe_Way` vocabulary |
| §6.10 (08-28/29) | Coverage audit, second cache wipe (§18 recurrence), full recovery campaign |

---

## 7. Files Touched / To Change *(tracked against actual repo layout)*

| File | Role | Status |
|---|---|---|
| `urtpe/links.py` | Discovery flow, **merge bug fix (#535)**, per-case timeline retention, portal view parsing | per-case retention + date-aligned node linking **done** (§6.6); project-level chimera merge & portal revision parsing open |
| `urtpe/links.py` `STAGE_FIELD_MAP` | Add `jud_ok_date2`, fix `jud_ok_date` label | **done** (2026-08-24, regression-tested) |
| `urtpe/graph.py` | `build_project_graph` — attach merged events to nodes | open |
| `viewer/app.js` | `renderDetail` — event layer rendering, ghost nodes, dual dates | open |
| `tests/test_links.py` · `tests/fixtures_links.py` | Portal view parsing scenarios; **new fixture already added** (#89-108); +2 date-anchoring regression tests (§6.6) | fixture done |
| `viewer/projects.data.js` | Runtime data (**note: lives in `viewer/`, not `content/`**); already carries `milestones_national` | data done |
| `scripts/fetch_remaining_national_portal.py` | Targeted portal fetch — strict match added (§6.6); **no-match ledger** (§16, `add-no-match-ledger`) | done |
| `tests/test_fetch_remaining_portal.py` | +13 no-match-ledger tests (round-trip/quarantine, TTL filtering, clear-on-match/sweep) | done |
| `scripts/repair_cache_2026_08_24.py` · `scripts/probe_third_6projects.py` | One-off cache repair / third.ashx probe (6 projects) | done |
| `scripts/repair_wiped_caches.py` | §17 incident repair — re-fetched 47 wiped caches fresh | done |
| `scripts/restore_national_links_2026_08_25.py` | §18 regression restore — merged national fields back into 183 caches from backup, offline | done |
| `scripts/check_520_parcels.py` | §6.7 one-off probe — 南港段一小段520-2 neighbor parcel/case linkage (evidence for the Taipei over-return bug) | done |
| `docs/final_results_json_api.md` | Update with portal merge findings | open |
| `docs/facts_2_portals.md` (v1) | Superseded by this v2 | closed |

---

## 8. 推動歷程 Parser — Root Cause Found & Applied

**Symptom**: emitted dataset had `milestones_national = {}` for ALL 709 projects, despite 109 projects carrying a resolved `twur` URL and the portal index matching 78/110 cores exactly.

### Causal chain

```
portal index crawl ──▶ 110 entries                 ✅
core lookup        ──▶ 78/110 exact matches        ✅
twur_url assigned  ──▶ 109 projects               ✅
fetch view page    ──▶ 50KB HTML                  ✅
case_id extraction ──▶ works                       ✅
推動歷程 extraction ──▶ {} EVERY TIME              ❌ ROOT CAUSE
```

### The bug (verified live `[live-probed]`)

`ViewPageParser` only extracted milestones from tables inside `data_table_box` divs whose style contained `display:none` (`links.py` `_in_hidden_table` → `_process_tuidui_table`, #176/#219). That assumption came from an older portal design. Current portal serves the milestone table as **visible static HTML** — a live probe of view/1249 found `data_table_box` ×13 but `display:none` ×**0**, so `_process_tuidui_table()` never fired.

### Why it stayed invisible — three masking layers

1. **Status masking** — empty national milestones doesn't change status ("resolved" comes from the Taipei path); no error logged.
2. **Viewer masking** — the 推動歷程 card renders only when non-empty; absence mocked as "no data".
3. **Test masking** — `tests/fixtures_links.py` fixtures were built on the OLD markup (`display:none`) → tests passed green while production yielded nothing.

### Spec conformance

No OpenSpec delta required — `official-link-discovery/spec.md` already mandates attaching "the twur URL and 推動歷程". Broken parser violated existing spec; fixing + refreshing fixtures is an implementation bug fix.

### Fix shape (verified applied)

- Parser now reads visible `項目`/`日期`-headed rows (`_process_row`, `links.py:203-217`), independent of hidden-div detection; legacy hidden path retained (#176).
- New fixture reproducing live `type4_table` markup (`tests/fixtures_links.py:89-108`) with negative assertions (empty 備註 dropped, 資料更新日期 not mistaken for a milestone).
- `scripts/backfill_national_milestones.py` backfills from cached `view.html` (no network) and re-emits viewer data.
- **Confirmation**: `viewer/projects.data.js` now carries populated `milestones_national` (e.g. view/997 `事業計畫核定日期 112.06.08`, view/1212 `事業計畫核定日期 115.01.20`).

---

## 9. Portal Index Coverage Insight (110 entries)

The 110 crawled entries span view_id 987–1252, approval dates 112.05.11–115.06.16 (2023-05 → 2026-06) `[live-probed]`: the crawl walks newest-first and died at the WAF after ~110 rows, so coverage is "recent ~3 years" — everything older (e.g. view/136, 核定 2012) is systematically absent. **Resolution in progress**: the per-project targeted-search path (§16) now covers older cohorts without touching the bulk crawl; the index itself remains as a fast-path cache.

---

## 10. Target Canonical Join Key *(cross-project name normalization)*

| System | Method | Fallback |
|---|---|---|
| **Taipei** | `build_land_core_key(CleanRecord)` → `{district}{section}{parcel}地號等{count}筆` | — |
| **Portal** | `parse_name_id(title)` → same tuple; if regex fails → strip common suffixes | `title.replace("擬訂","").replace("臺北市","")...` |

**Canonical issue**: normalized tuple `(district, section, parcel, count)` from `parse_name_id` on both sides. Avoids string-stripping ambiguity. Store in both indexes for reliable matching.

---

## 11. Complete Taipei Endpoint Map

| Endpoint | Purpose | Key Fields |
|---|---|---|
| `Get_updcase_list.ashx` | Parcel search → case_ids | `details` URL (numeric case_id), `case_name`, `schedule` |
| `Get_project168_second.ashx` | **Process timeline** (pre-approval) | 36 date fields → `STAGE_FIELD_MAP` |
| `get_project168_top.ashx` | **Case header** | `phase`, `NAME`, `plan_app_date`, `uro_chk_date*`, `EXE_NAME` (實施者名稱 — *not* Exe_Way; see §6.9 correction) |
| **`Get_project168_third.ashx`** | **Implementation** (post-approval) | `Eng_Start_Date` (開工), `Ulic_Date` (使用執照), `Report_Date`, `Exe_Way`, `Base_Area`, `Landkind*`, settlement stats |
| `Get_project168_fourth.ashx` | Rewards/容積 incentives | `F`, `F0-F6`, reward flags (`GREENBUILD_DESIGN`, etc.) |

**Full lifecycle coverage**:
```
second.ashx (17 pre-approval events)
    → top.ashx (core header + phase + NAME)
    → third.ashx (開工/使用執照/基地面積/土地分區/安置/停車/費用)
    → fourth.ashx (容積獎勵/綠建築/耐震等獎勵指標)
```

### Project metadata field map (case 141, 開工/使用執照/面積/分區) `[live-probed]`

| Requested field | Source | Field | Value |
|---|---|---|---|
| 開工日期 | `third.ashx` | `Eng_Start_Date` | 2013/09/10 |
| 使用執照核發日期 | `third.ashx` | `Ulic_Date` | 2016/08/29 |
| 成果報備日期 | `third.ashx` | `Report_Date` | (empty for 141; label confirmed via site DOM — §12 #7) |
| 實施方式 | `third.ashx` | `Exe_Way` | 權利變換 |
| 基地面積 | `third.ashx` | `Base_Area` | 1,604.00 |
| 土地使用分區1 | `third.ashx` | `Landkind1` | 第四種商業區(特)(原商三) |
| 土地使用分區2/3 | `third.ashx` | `Landkind2/3` | (empty) |
| 使用分區1-3面積 | `third.ashx` | `Landkind*_Area` | 1,604.00 / 0.00 / 0.00 |

Additional `third.ashx` settlement stats: `Old_Doors`=50, `Settle_Old_Doors`=0, `Settle_Doors`=0, `New_Parkings`=103, `New_Parkings2`=85, `Sidewalk_Length`=60, `Sidewalk_Area`=230.81, `Urban_Renew_Fee`=1,242,782,140, `pc_afterUpdTotalValue`=2,761,323,189, `Land_Owners_Pir`=54, `Bui_Owners_Legal`=54.

`fourth.ashx` rewards: `F0`=8,982.01 (基準容積), `F`=10,829.58 (允建容積), `F3`=538.92 (都市更新獎勵), `F5`=1,308.65, `F5_3`=230.81 (人行步道面積); reward flags (GREENBUILD_DESIGN, SEISMIC_DESIGN…) all empty here. *(Flags populate widely across the corpus — numeric 容積 areas in ㎡, not booleans; official labels captured in §12 #9 / §12.1.)*

---

## 12. Top Priorities *(ordered by dependency — execute top-down)*

> **Dependency graph** (edges explained in each entry):
> ```
> [1] coverage guard ──────▶ protects every destructive cache job
> [2] chimera emit-fix      ── independent, ready (no network)
> [3] consolidation ──┬───▶ [4] count normalization ──▶ re-sweep run
>                     │       (same matcher code moves into links.py)
>                     └───▶ [5] sync model ──▶ absorbs [6] freshness hygiene
> ```
> Name-based references ("§12 consolidation", "§12 count normalization", …)
> survive this ordering.

1. **Coverage regression guard (§18 rule 3)** — snapshot coverage counters (twur / national_milestones / 使用核發 / Taipei resolved) before and after any destructive cache job; any decrease aborts the job and alerts. The §18 drop (292→109) ran unnoticed for hours. Small wrapper, no spec delta. **Do first — protects every future destructive job, including the consolidation's bulk passes.**
2. **Chimera-merge emit-time fix** — `[READY, no network]` the project-level merged `milestones_taipei` is a last-write-wins chimera across cases (§5); `case_milestones` (per-case timelines) now exists in 691 caches, so the merged dict can be **computed correctly at emit time** (graph.py/links.py) instead of carrying the corrupted accumulation — fixes wrong anchor dates in viewer cards (e.g. 141's 核定 2012/08/27 shown as 2016/08/23). Unblocked by the §18-19 refresh; flagged in §19 as the top post-refresh code item.
3. **Portal discovery consolidation** — library-first: move `search_portal`/`view_page_matches`/cache-write from the fetch script into `urtpe/links.py`; expose opt-in `--links-targeted`; script becomes the unattended overnight wrapper. **Includes the Taipei parcel guard (§6.7)**: `search_taipei_cases_api` must verify `<parcel>地號` in the case name (unit-level search over-return). **Includes §18 rule 2 — durable mapping store**: targeted-fetch land-core→view_id mappings must land in `portal_index.json` (or a dedicated store) at write time, so a cache regeneration can never again discard the only copy (the §18 regression mechanism). Rationale: the loose-parcel-match bug (§6.6) and its Taipei twin (§6.7) are the precedent for dual-implementation drift. **Full design: `docs/sync_architecture.md` §4.** Needs OpenSpec change (modifies `official-link-discovery`).
4. **Parcel-count mismatch normalization** — land-core join should tolerate portal-vs-Taipei count drift (金華段 11 vs 13 筆) without weakening uniqueness; touches land-identity-fallback / official-link-discovery semantics. **Ride with/after [3]** (the matcher code moves into links.py); enables the post-normalization **re-sweep run** (no-match ledger `--reprobe-days` re-probes the recovered rejects automatically).
5. **PDF + portals sync model** — event-cascade with PDF as heartbeat: new/changed projects trigger per-project refresh; liveness policy (freeze phase-E/completed, refresh phase C/D, targeted queue for twur-less); `project_id`/land-core as the only cross-PDF keys (recno shifts every gazette — node anchoring must be re-derived per sync). **Depends on [3]'s `--links-targeted`** for the orchestrator's portal lane. **Full design: `docs/sync_architecture.md`.** Needs OpenSpec change (new `portal-sync` capability).
6. **Freshness-signal hygiene** — `viewer/projects.data.js` `generated_at` is preserved from the loaded file under `--from-js` (shows 2026-08-23 despite 8/24 writes) — not a reliable freshness signal. **Fully absorbed by [5]'s sync manifest**; standalone work unnecessary.
7. ~~**`Report_Date` semantics**~~ — **`[RESOLVED]`** (2026-08-25): the site's own DOM labels it 成果報備日期 (`id="detail_Report_Date"`, r_progress_detail.aspx). Empirics agree: fills in 65/2,951 cached third.ashx payloads, and in all 62 co-occurrences postdates 使照核發. Mapping was already correct in `IMPLEMENTATION_MILESTONE_FIELDS` (links.py) — nothing to do.
8. ~~**Phase-D confirmation**~~ — **`[RESOLVED]`** (2026-08-25): live probe hit `phase='D'` on cases 11010082/11008281 (`NAME=事業計畫及權利變換計畫階段─業經本府核定`). The "cached top.ashx-derived structures" hint was wrong in mechanism but right in spirit — no phase survives into caches (top.ashx is never fetched by the pipeline), but milestones predict it: 核定+權變核定 coexistence ⇒ D-shaped (56 of 142 approved-without-開工 projects; 86 B-shaped). Taxonomy corrected in §6.5: D is the combined 事業+權變 track, not "核定後、執行前"; approval does not advance the phase.
9. ~~**`fourth.ashx` reward flags**~~ — **`[RESOLVED]`** (2026-08-25): the flags are numeric 容積 contributions (㎡), not booleans (GREENBUILD_DESIGN×587, TIME_REWARD×590, SCALE_REWARD×547 … across the caches). Full official label map captured from the detail-page DOM — same `id="detail_<field>"` trick that produced IMPL_LABELS, so the archived change's "site JS needed" assumption is dead. All 41 cache keys labeled (map in §12.1); viewer `REWARD_LABELS` completion landed via OpenSpec change `complete-viewer-field-labels` (2026-08-25) — corpus sweep after implementation: 0 unmapped reward rows and 0 unmapped implementation rows across 709 caches (sweep also surfaced 6 unlabeled impl-stat keys, now labeled from the same DOM, incl. the `STATELAND2_OWNER` all-caps variant of `StateLand2_Owner`; national badge label verified as 使用核發日期, 71 projects). Source-position audit (same change, 2026-08-25): the case carrying 開工/使照 anchors to the **first** record in 349/689 (50.7%), to 現況 in only 12 (1.7%), unanchored 122 (17.7%); 建照 winner likewise first-heavy (331/543, 61.0%, vs 現況 4) with merge-rule replication 543/543 — construction data lives on the original 擬訂-era case in half the corpus, which is why viewer provenance labels (`案<id>·編號<n>`) matter and why [2] must not assume final-case ownership.
10. **Withdrawal date source** — any external system (紙本? 內部系統?) publishes 撤回日. Likely a dead end; deprioritize.
15. **Cross-family case pollution & fragment families (§6.8)** — 162 isolated construction events / 82 families; 112 double-displayed; B1b subset (55 events) likely wrong dates from foreign cases. Fix = search strictness (extend §6.7 guard) + fragment merge candidates + one re-merge pass. Needs OpenSpec change (modifies `official-link-discovery` + `case-merging`). Investigation entry: §6.8 (incl. 10106116 verification — data correct).

Converged / done (frozen record, kept for reference):

11. ~~**Portal coverage convergence**~~ — **`[CONVERGED]`** (2026-08-25): restore done (§18, 292/292/58) + final targeted-fetch run consumed the full queue (373 processed, +10 matches → **302/302/63**, 43%/9%; 0 WAF resets at 1-3 min intervals). Remaining coverage lever: §12 count normalization over the ~1,108 strict-rejects.
12. ~~**third.ashx emission layer**~~ — **`[DONE]`** via OpenSpec change `add-taipei-implementation-data` (2026-08-24): `graph.py` emits `implementation`/`rewards` + 開工/使照 milestones, `viewer/app.js` renders 執行階段/獎勵資料 cards, `schema_version` → 2, bulk pass refreshed 691 caches (689 projects emit implementation; 18 unresolved = pre-existing Taipei-search misses).
13. ~~**`regenerate_viewer` hardening**~~ — **`[RESOLVED]`** (2026-08-25): child stdout/stderr → append-mode log file `data/.link_cache/regen_log.txt` (orphan can always write + stays observable), timeout 300 s → 1800 s, regen-start marker flushed before spawn. Verified live: regeneration succeeded, full child output captured in the log. No spec delta (emission contract unchanged).
14. ~~**`jud_ok_date2` mapping**~~ — **done** (2026-08-24); removed from active list.

### 12.1 Official reward-field labels (captured 2026-08-25, r_progress_detail.aspx DOM)

Volume fields use accounting notation; incentive keys are per-incentive 容積
areas (㎡). Complete — covers every key observed in the 691 caches:

```
F=F(㎡)  F0=F0(㎡)  F1..F6=△F1..△F6(㎡)  F4_1..F4_3=△F4-1..△F4-3(㎡)
F5_1..F5_6=△F5-1..△F5-6(㎡)  Park_Area=停車獎勵(㎡)  Park_Cars=停車獎勵部數

TIME_REWARD=時程獎勵                    SCALE_REWARD=規模獎勵
GREENBUILD_DESIGN=綠建築標章之建築設計      SEISMIC_DESIGN=耐震設計
WISDOMBUILD_DESIGN=智慧建築標章之建築設計   ACCESSIBLE_DESIGN=無障礙環境設計
NEWTECH=新技術之應用                    IMENVIRON=改善都市環境
BUILDPLANDES1..4=建築規劃設計(一)..(四)    BUILDSAFE_CONDITION=建築物結構安全條件
CHARITY_BUILD=公益設施                  CULTURAL_MAINTAIN=文資保存及維護
DEVELOP_PUBFACILITY=協助開闢公共設施用地    AGREEMENT_CONSTRUCTION=全體同意採協議合建實施
PROREGENERAT1/2=促進都市更新(一)/(二)      VOLUME_HIGHER_REWARD=高於法定容積部份核計之獎勵
ILLEGAL_FLOORAREA_REWARD=處理違建戶之樓地板面積獎勵  name_reward_no=獎勵上限規定
```

Naming resolution (viewer change `complete-viewer-field-labels`, 2026-08-25):
hybrid — `F`=允建容積, `F0`=基準容積, `F3`=都市更新獎勵, `F5`=其他容積獎勵,
`F5_3`=人行步道面積 keep semantic labels; all other keys use the official
labels above. IMPL_LABELS also gained 開工日期/使照核發日期/成果報備日期 and
six statistic labels (合法建物所有權人數, 公有土地所有權人數, 總銷售金額,
公益設施面積, 捐贈道路成本, 國有土地管理機關2所有人[STATELAND2_OWNER]).

> *Section numbering note: §13-15 were consumed by the v1→v2 consolidation (their content lives in §8, §9, §12); appendices continue at §16 to keep historical v1 references unambiguous.*

---

## 16. Campaign, Incident & Sequencing Records (moved)

The targeted-fetch campaign run/coverage log (§16 incl. §16.1 matcher correction), the cache-concurrency incident (§17), the bulk-refresh regression (§18), and the sequencing decisions (§19) now live in **`docs/portal_operations_log.md`** — anchors §16-§19 preserved there.

> Quick state (2026-08-29, post-recovery): twur/milestones **561/709 (79%)**, 使用核發 **242 (34%)**, resolved **696/709 (98.2%)**; 148 twur-less = ledger-recorded negatives; details in the log.

---

*Sources: interactive exploration (wmux browser + live API probes) 2026-08-23; code claims cross-checked against `urtpe/links.py`, `tests/fixtures_links.py`, `scripts/`, `viewer/projects.data.js` on 2026-08-24. Session narratives and per-incident detail (06.1-6.10, §16-§19) moved 2026-08-29 to `docs/portal_operations_log.md` — see that file's sources footer for the full session provenance.*
