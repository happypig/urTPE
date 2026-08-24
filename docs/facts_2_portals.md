# Two Portals — Field Notes & Alignment Map (v2)

*Exploration summary: Taipei City ashx API vs National Portal (twur.nlma.gov.tw) for project 中山區-中山段一小段-254地號等13筆*

> This is the consolidated, single-source-of-truth version. All findings and the §14 parser fix are folded in; resolved items are marked `[RESOLVED]`, code claims carry the verified file:line, and empirical API values are tagged `[live-probed]` (not re-verified this pass).

---

## 0. Decision Summary

| Decision | Status |
|---|---|
| 推動歷程 parser silent-failure root cause | `[RESOLVED]` — applied, backfilled, verified in `viewer/projects.data.js` |
| `jud_ok_date2` field | `[RESOLVED]` — label identified; **mapping added to `STAGE_FIELD_MAP`** (2026-08-24, incl. `jud_ok_date` label fix; regression-tested) |
| Join approach | Portal = gazette date; Taipei = committee date. **±1 day is a heuristic, not a rule** (Δ=0 observed). |
| Do we need both sources? | Yes — they cover disjoint lifecycles (Taipei pre-approval depth; Portal post-approval breadth + revision rollup). |
| 3 top forks (see §7) | Portal crawl recovery · `Report_Date` semantics · Phase-D confirmation |
| Curated fallback wrong view (河堤段263-19 → 板橋 view/1042) | `[RESOLVED]` — mapping fixed to view/262; cache + view.html refreshed (see §6.6) |
| Per-node case links (positional mislink / missing links) | `[RESOLVED]` — date-aligned anchoring in `attach_links_to_projects`, positional fallback kept (see §6.6) |
| Fetch-script loose parcel match (`parcel in html`) | `[RESOLVED]` — strict parcel+地號 + title section/parcel/count match (see §6.6) |
| third.ashx integration (開工/使用執照 into data model) | **`[RESOLVED]`** — OpenSpec change `add-taipei-implementation-data`: fetch/cache + emission + viewer all done (schema v2; bulk pass 2026-08-24: 691 caches with per-case payloads, 689 projects emit `implementation`, 254 family shows 開工 2013/09/10 / 使照 2016/08/29) |
| Parcel-count mismatch in land-core join (portal 11筆 vs Taipei 13筆) | **Open — needs OpenSpec change** (touches land-identity semantics) |
| Portal coverage for older projects | **Regressed — restore pending** — targeted fetch had reached 292/709 twur (41%), 58 使用核發; the 2026-08-25 bulk discovery refresh dropped it to 109/709, 1 使用核發 (see §18); full pre-refresh state preserved in `data/.link_cache_backup_20260824` |
| Bulk refresh wiped targeted-fetch links (2026-08-25) | **`[RESOLVED]`** (2026-08-25 02:17) — `scripts/restore_national_links_2026_08_25.py` merged the 3 national fields back into the 183 regressed caches from the backup, viewer re-emitted: 292/292/58 verified; root cause + guard rules in §18 |
| Portal discovery consolidation (CLI vs fetch script) | **Decided** — library-first: move targeted search into `urtpe/links.py`, opt-in `--links-targeted` CLI flag, script stays as overnight wrapper; full design in `docs/sync_architecture.md` §4; needs OpenSpec change |
| PDF + portals sync model | **Decided** — event-cascade with PDF as heartbeat; liveness-based refresh (freeze phase-E, refresh C/D); `project_id`/land-core are the only cross-PDF keys (recno shifts every gazette); full design in `docs/sync_architecture.md`; needs OpenSpec change (`portal-sync`) |
| Cache concurrency (2026-08-24 incident) | **`[RESOLVED]`** — 47 wiped caches repaired, poison URL-caches deleted; **single-writer rule** now in force (see §17) |

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
| **Curated fallback wrong view** | `data/taipei_case_ids.json` (河堤段263-19 → view/1042 = 新北市板橋區 project, bogus case_id "10421234") | Wrong twur link + wrong national milestones cached/emitted for the project | **`[RESOLVED]`** — mapping → view/262, cache/view.html refreshed (see §6.6) |
| **Per-node positional mislink** | `links.py` `attach_links_to_projects` (`city_case_ids[0]/[1]` by track keyword) | 10204032 (核定 2016/07/05) attached to recno 772 (2019-08-01) instead of recno 1042; 金華段513-3 cases attached to no node at all — violates official-link-discovery "Per-stage city links land on the right node" | **`[RESOLVED]`** — date-aligned anchoring (see §6.6) |
| **Fetch-script loose parcel match** | `scripts/fetch_remaining_national_portal.py` `find_matching_view` (`parcel in html`) | Substring collisions (263-19 vs 209-19) and same-parcel different-project matches (444等7筆 vs view/264 444等**17**筆) | **`[RESOLVED]`** — strict parcel+地號 + title tuple match (see §6.6) |
| **Parcel-count mismatch join miss** | land core includes `等N筆` count; portals disagree (金華段513-3: portal 11筆 vs Taipei 13筆, same case — 實施者 江陵 confirmed on view/265) | Project with an existing portal page gets no twur link | **Open — needs OpenSpec change** |
| **third.ashx fetch/cache vs emission gap** | fetch+cache **done** (691 caches carry per-case `implementation`/`rewards` after the 2026-08-24 bulk pass); `graph.py` emits `implementation`/`rewards` + 開工日期/使照核發日期 milestones; `viewer/app.js` renders 執行階段/獎勵資料 cards | ~~開工/使用執照 absent from data model & viewer~~ | **`[RESOLVED]`** — `add-taipei-implementation-data` (schema v2) |
| **Cache concurrency wipe (2026-08-24 ~21:23)** | 4 writers raced `data/.link_cache` (2 dry-run parents + 2 orphaned CLI children); torn reads → spurious cache misses → live re-discovery read 75/126 corrupt URL-caches (orphan mechanism corrected 2026-08-25 — see §17 #1) | 47 caches wiped to empty `national_milestones`; 62 `view.html` rewritten corrupt | **`[RESOLVED]`** — repaired 47/47, all 126 URL-caches deleted, **single-writer rule** in force (see §17) |
| **Bulk refresh regression (2026-08-25 ~01:05)** | `links.py:565-585` resolves view_id from `portal_index.json` (110 entries, WAF-capped §9) + fallback JSON (3 entries); the targeted campaign's ~180 extra mappings lived only inside the deleted `result.json` | twur/`national_milestones` 292→109; 使用核發 58→**1**; viewer emitted regressed state | **`[RESOLVED]`** — restored 183 caches from `.link_cache_backup_20260824`, re-emitted, verified 292/292/58; guard rules in force (see §18) |

---

## 6. Resolved Findings & Implementation Notes

### 6.1 Provenance & Join *(replaces v1 §6 + §12 — single strategy)*

```
STEP 1: Fix provenance (per-case timelines)
  Taipei: retain [{case_id, name, schedule, milestones: [{label, date}]}]
  Portal: parse view page → {view_id, revisions: [{ordinal, biz_date, land_date}], occupancy_date, basic_data}

STEP 2: Anchor by date (match ±1 day, same-day fast-path)
  141 ↔ node 1219 (核定 2012-08-27 vs 101.08.28)
  142 ↔ node 1037 (核定 2016-08-23 vs 105.08.24)
  144 ↔ node 991  (核定 2017-04-13 vs 106.04.13)

STEP 3: Leftover cases → name-twin fallback
  143 name = 144 name = node 991 name → attach as ghost before 144
  position by its 申請權變 2016/09/22, badge 自行撤回

STEP 4: Merge post-approval
  Portal 使用核發 2016/08/29 → attach to 1st-revision chain (after 142's 核定)
  Case 141 implementation (third.ashx): Eng_Start_Date 2013/09/10 → node 1219 chain (post-核定)
    Ulic_Date 2016/08/29 → matches portal 使用核發, attach after 1st revision
    Base_Area/Landkind* → project-level metadata enrichment
  Cases 142/144: implementation fields empty (tracking on final case only)
  Portal 基本資料 → project-level enrichment | Portal `資料更新日期` → freshness signal
```

**Implementation status (2026-08-24)**: STEP 1 (Taipei half) + STEP 2 are now implemented —
`DiscoveryResult.case_milestones` retains per-case timelines, and
`attach_links_to_projects` anchors each node's case by 核定日期/權變核定日期
(exact, then ±1 day), falling back to the legacy positional heuristic for old
caches (see §6.6). Portal-side revision/basic_data parsing (STEP 1 Portal half)
and STEP 3 ghost nodes / STEP 4 merge remain open.

### 6.2 `jud_ok_date2` Label — `[RESOLVED]` (mapping applied 2026-08-24)

From live `#data2` tab (案件詳細 > 階段辦理過程) `[live-probed]`, case 141:

| API field | UI label | Value |
|---|---|---|
| `jud_ok_date` | **審議通過日期** | 2012/04/16 |
| `jud_ok_date2` | **權變審議通過日期** | 2012/04/16 |
| `comm_hold_date` | 召開審議會日期 | 2011/04/25 |
| `comm_hold_date2` | 權變召開審議會日期 | 2011/04/25 |

**Applied in `STAGE_FIELD_MAP`** (2026-08-24): `jud_ok_date` relabeled `概要審議會通過日期` → `審議通過日期`, and `jud_ok_date2 → 權變審議通過日期` added (regression test `test_stage_field_map_jud_ok_labels`). Note: labels are baked into caches at fetch time — existing caches keep the old label until the bulk discovery refresh. `概要審議會通過日期`/`概要核准日期` likely map to `outline_ok_date` variants — still **unverified field names, intentionally not added**.

### 6.3 Withdrawal Date — `[RESOLVED]`: Not Published

Checked all 4 ashx endpoints for case 09811143 `[live-probed]`: `second.ashx` (36 timeline fields → only `Plan_App_Date2`=2016/09/22), `top.ashx` (`phase='C'`, NAME 自行撤回, no date), `third.ashx` & `fourth.ashx` (all empty / no date). Platform records *that* it was withdrawn, never *when*. Best anchor: application date 2016/09/22 + 撤回 badge.

### 6.4 Occupancy Permit — Taipei side exists, in `third.ashx` `[live-probed]`

| Field | Label | Case 141 value | Matches |
|---|---|---|---|
| `Eng_Start_Date` | 開工日期 | **2013/09/10** | — |
| `Ulic_Date` | 使用執照日期 | **2016/08/29** | Portal `使用核發` 105.08.29 ✓ |
| `Report_Date` | (成果報備日期?) | empty | — |
| `Exe_Way` | 實施方式 | **權利變換** | ✓ |

Only the *completed* case (141) has these; revision cases (142, 144) empty because implementation tracking belongs to the final approved case.

### 6.5 Phase Taxonomy — `[RESOLVED]` model, partial validation

`top.ashx` `phase` + `NAME` `[live-probed]`. A/B/D **observed values are inferred, not confirmed** — only C and E were seen. Treat A/B/D labels as hypotheses pending a real case.

| Phase | NAME example | Meaning | UI tab | Confidence |
|---|---|---|---|---|
| A | (not seen) | 單元劃定 | 單元劃定 | inferred |
| B | (not seen) | 事業概要 | 事業概要 | inferred |
| C | 權利變換計畫階段─實施者自行撤回 | 計畫審議中 (含撤回) | 事業計畫 / 權變計畫 | seen |
| D | (not seen) | 核定後、執行前 (公告/備查) | — | inferred |
| E | 執行階段_更新案完成成果備查 | 施工/實施階段 | 執行 | seen |

### 6.6 Session 2026-08-24 — Wrong-Match Bugs + Per-Node Link Fix `[RESOLVED]`

Probing 6 projects for 建築執照/開工/使用執照 across both portals surfaced five bugs
(root causes traced and fixed same day; full inventory in v1 §16).

**Definitive national 推動歷程 vocabulary** (109 cached view pages + live view/136):
only 事業計畫/權利變換計畫 申請·核定日期, 第一次變更…核定日期, **使用核發日期**
(completed cases only), 備註. The national portal **never** publishes 建築執照 or
開工日期 — "all three dates on both portals" is unsatisfiable by design; the only
cross-portal overlap is 使用執照 ↔ 使用核發日期 (dates matched exactly on the two
projects where both sides have them: 河堤段263-19 2021/10/25, 金華段513-3 2019/09/10).

**Fixes applied** (all conformance repairs — no OpenSpec delta needed, same
precedent as §8):

- `data/taipei_case_ids.json`: 河堤段263-19 → view_id 262 + real case_ids.
- `scripts/repair_cache_2026_08_24.py`: 河堤段263-19 result.json corrected
  (view/262, true milestones incl. 使用核發 110.10.25, refreshed view.html —
  parser output on the live page matches exactly); both 河堤段 and 金華段 caches
  gained `case_milestones` (per-case 核定日期) for date anchoring.
- `urtpe/links.py`: `DiscoveryResult.case_milestones` retained in discovery;
  `attach_links_to_projects` date-aligned anchoring (positional fallback for
  old caches without `case_milestones`).
- `scripts/fetch_remaining_national_portal.py`: strict `view_page_matches()`
  (`<parcel>地號` context + `parse_name_id` title section/parcel/count);
  candidates now carry land count.
- Tests: 2 regression tests (date-aligned attach; positional fallback). Suite
  121 passed. Viewer regenerated: 697 resolved / 12 unresolved; verified in
  `data/projects.json` — 河堤段 twur → view/262, recno 1042→10204032 /
  772→10707031; 金華段 recno 1040→10011041 / 797→10011042.

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
| `scripts/fetch_remaining_national_portal.py` | Targeted portal fetch — strict match added (§6.6) | done |
| `scripts/repair_cache_2026_08_24.py` · `scripts/probe_third_6projects.py` | One-off cache repair / third.ashx probe (6 projects) | done |
| `scripts/repair_wiped_caches.py` | §17 incident repair — re-fetched 47 wiped caches fresh | done |
| `scripts/restore_national_links_2026_08_25.py` | §18 regression restore — merged national fields back into 183 caches from backup, offline | done |
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
| `get_project168_top.ashx` | **Case header** | `phase`, `NAME`, `plan_app_date`, `uro_chk_date*`, `Exe_Way` |
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
| 成果報備日期 | `third.ashx` | `Report_Date` | (empty for 141) |
| 實施方式 | `third.ashx` | `Exe_Way` | 權利變換 |
| 基地面積 | `third.ashx` | `Base_Area` | 1,604.00 |
| 土地使用分區1 | `third.ashx` | `Landkind1` | 第四種商業區(特)(原商三) |
| 土地使用分區2/3 | `third.ashx` | `Landkind2/3` | (empty) |
| 使用分區1-3面積 | `third.ashx` | `Landkind*_Area` | 1,604.00 / 0.00 / 0.00 |

Additional `third.ashx` settlement stats: `Old_Doors`=50, `Settle_Old_Doors`=0, `Settle_Doors`=0, `New_Parkings`=103, `New_Parkings2`=85, `Sidewalk_Length`=60, `Sidewalk_Area`=230.81, `Urban_Renew_Fee`=1,242,782,140, `pc_afterUpdTotalValue`=2,761,323,189, `Land_Owners_Pir`=54, `Bui_Owners_Legal`=54.

`fourth.ashx` rewards: `F0`=8,982.01 (基準容積), `F`=10,829.58 (允建容積), `F3`=538.92 (都市更新獎勵), `F5`=1,308.65, `F5_3`=230.81 (人行步道面積); reward flags (GREENBUILD_DESIGN, SEISMIC_DESIGN…) all empty here.

---

## 12. Top Priorities (not "open questions")

1. **Portal coverage convergence** — `[OPERATIONAL]` restore done (§18, 2026-08-25 02:17: 292/292/58 verified in the emitted viewer); resume the targeted-fetch batches — ~373 candidates still queued, ~2-3 overnight windows at 06:30 deadline. No code work needed.
2. ~~**third.ashx emission layer**~~ — **`[DONE]`** via OpenSpec change `add-taipei-implementation-data` (2026-08-24): `graph.py` emits `implementation`/`rewards` + 開工/使照 milestones, `viewer/app.js` renders 執行階段/獎勵資料 cards, `schema_version` → 2, bulk pass refreshed 691 caches (689 projects emit implementation; 18 unresolved = pre-existing Taipei-search misses).
3. **Portal discovery consolidation** — library-first: move `search_portal`/`view_page_matches`/cache-write from the fetch script into `urtpe/links.py`; expose opt-in `--links-targeted`; script becomes the unattended overnight wrapper. Rationale: the loose-parcel-match bug (§6.6) is the precedent for dual-implementation drift. **Full design: `docs/sync_architecture.md` §4.** Needs OpenSpec change (modifies `official-link-discovery`).
4. **PDF + portals sync model** — event-cascade with PDF as heartbeat: new/changed projects trigger per-project refresh; liveness policy (freeze phase-E/completed, refresh phase C/D, targeted queue for twur-less); `project_id`/land-core as the only cross-PDF keys (recno shifts every gazette — node anchoring must be re-derived per sync). **Full design: `docs/sync_architecture.md`.** Needs OpenSpec change (new `portal-sync` capability).
5. **Parcel-count mismatch normalization** — land-core join should tolerate portal-vs-Taipei count drift (金華段 11 vs 13 筆) without weakening uniqueness; touches land-identity-fallback / official-link-discovery semantics.
6. **`Report_Date` semantics** — empty for 141; confirm whether it ever fills as 成果報備日期.
7. **Phase-D confirmation** — find a real phase-D case; hint: phase data may already sit in the cached `top.ashx`-derived structures — a local scan might confirm D without network.
8. **`fourth.ashx` reward flags** — map non-empty values to labels (site JS needed); rewards now cached per case.
9. ~~**`regenerate_viewer` hardening**~~ — **`[RESOLVED]`** (2026-08-25): child stdout/stderr → append-mode log file `data/.link_cache/regen_log.txt` (orphan can always write + stays observable), timeout 300 s → 1800 s, regen-start marker flushed before spawn. Verified live: regeneration succeeded, full child output captured in the log. No spec delta (emission contract unchanged).
10. **Freshness-signal hygiene** — `viewer/projects.data.js` `generated_at` is preserved from the loaded file under `--from-js` (shows 2026-08-23 despite 8/24 writes) — not a reliable freshness signal; rely on file mtime or a sync manifest (§12.4's ledger).
11. ~~**`jud_ok_date2` mapping**~~ — **done** (2026-08-24); removed from active list.
12. **Withdrawal date source** — any external system (紙本? 內部系統?) publishes 撤回日. Likely a dead end; deprioritize.

---

## 16. Targeted Fetch Campaign — `fetch_remaining_national_portal.py` (2026-08-24)

The OpenSpec change `fetch-remaining-national-portal` (archived
`2026-08-24-fetch-remaining-national-portal`, spec synced to
`openspec/specs/fetch-remaining-portal/spec.md`) produced a time-bounded,
sequential fetcher. It replaced the dead bulk-crawl path (§9) with per-project
targeted search: `?title=<section>&city_id=2` → candidate view_ids → fetch each
→ strict parcel+地號/title match (`view_page_matches`, §6.6) → parse 推動歷程 →
merge into `data/.link_cache/<project>/result.json` → auto-regenerate viewer.

### Run log

| Run | Window | Deadline | Processed | Updated | Failed | 使用核發 found |
|---|---|---|---|---|---|---|
| 06:30 run | ~4.5 h | 06:30 | 62 | 62 | 0 | 13 |
| 17:00 run | ~10.5 h | 17:00 | 109 | 109 | 0 | +45 (→58) |

Both runs: 100% success rate, 3-5 min random intervals (180-300 s), retries via
`fetch_url` backoff, failures logged to `data/.link_cache/fetch_failures.json`
(none triggered), viewer auto-regenerated at deadline.

### Cumulative coverage

| Metric | Pre-campaign | After 06:30 | After 17:00 | Coverage |
|---|---|---|---|---|
| Projects with `twur` | 118 | 183 | **292** | 41% of 709 |
| Projects with `milestones_national` | 109 | 183 | **292** | 41% |
| Projects with `使用核發日期` | 0 | 13 | **58** | 8% |

`twur` ≡ `milestones_national` since the 06:30 run: the earlier 9-project gap
(118 vs 109) was corrupted caches (gzip bodies saved as replacement-mangled
text by the pre-gzip-fix code path, §8); the backfill re-fetched and repaired
them.

### Remaining work

- **~373 candidates left** (482 at campaign start − 109 processed in 17:00 run).
  At the observed ~10 projects/hour, roughly 2-3 more overnight batches.
- **Campaign paused (2026-08-24 evening)** — blocked only by the single-writer
  rule while the cache-healing CLI (§17.5) finishes; resume with deadline
  flipped to 06:30.
- **`update_project_cache` now also persists the matched `view.html`** — caches
  are self-contained for future re-parses (parser fixes no longer require
  re-fetching). The CLI's `save_project_cache` already had this behavior.
- Expected no-match tail: projects predating the portal, renamed/re-parceled
  units, and genuinely absent cases — the strict matcher correctly rejects
  ambiguous hits (e.g. 桃源段四小段154, 長安段一小段721 in the 15-sample probe).
- Script deadline is a constant pair (`DEADLINE_HOUR`/`DEADLINE_MINUTE`,
  currently 17:00); flip to 06:30 for overnight runs.
- Dry-run mode (`--dry-run`: first 3 candidates, no sleeps) and
  `--max-projects N` available for sampling before a long batch.

### Observations from live runs

- 使用核發日期 yield concentrates in projects with 現況 ≤ ~2023 (construction
  completed); the newest-first ordering front-loads 申請/核定/變更 milestones
  and the occupancy dates arrive as the queue reaches older cohorts.
- Multi-revision rollups are common on older cases (up to 第四次變更 observed,
  e.g. view/327 with 12 milestones incl. 使用核發 112.05.31).
- No WAF resets encountered at 3-5 min intervals across ~171 sequential
  project fetches (each = 1 search + 1-5 view-page probes).

---

## 17. Cache Concurrency Incident (2026-08-24 ~21:23) — Root Cause, Repair, Rules

### What happened

Four processes wrote `data/.link_cache` concurrently: two `--dry-run` invocations
of the fetch script and the two `urtpe.cli --from-js --links` regeneration
subprocesses they spawned. Shell-timeout kills orphaned the CLI children (the
parent dying does not kill the child on Windows), producing:

1. **Orphaned children kept running** — `regenerate_viewer` spawns the CLI with
   `subprocess.run(capture_output=True)`; when the shell timeout killed the
   dry-run parents, the CLI children survived (Windows does not kill child
   trees) and kept working. *Correction (2026-08-25):* the earlier "pipe
   deadlock" read was wrong — the CLI's progress output is a few hundred bytes
   and can never fill the 64 KB pipe. The observed "CPU 0, no sockets" state
   was an orphan sitting in `time.sleep`/network waits during **live discovery
   over ~283 cache misses** (~5-6 s each ≈ 25-30 min of legitimate work). One
   orphan completed at 29 min and wrote the viewer correctly; the second was
   killed prematurely under the wrong diagnosis. The real orphan hazards are
   (a) it keeps writing caches with nobody supervising, and (b) under
   concurrent writers it participates in the race — hence the kill-the-tree
   and single-writer rules below.
2. **Torn reads → spurious cache misses** — while siblings mid-write `result.json`,
   `load_project_cache` hit partial JSON → `JSONDecodeError` → cache miss →
   `discover_project_links` re-ran **live**.
3. **Poisoned re-discovery** — the live path's `fetch_view_page` read the URL-cache
   files in the cache root: **75 of 126 were gzip bodies saved as
   replacement-mangled text** (pre-gzip-fix era, §8's sibling). The parser read
   garbage → `{}` milestones → `save_project_cache` overwrote good caches.

### Damage

| Measure | Count |
|---|---|
| `<project>/{result.json, view.html}` pairs rewritten | 62 |
| …wiped (`national_milestones` emptied) | **47** |
| …survived with milestones intact | 19 |
| Corrupt URL-cache files (removed) | 75 of 126 |

Viewer `projects.data.js` (written 21:45 by the completing CLI, which had
cache-hit the good state before the race) was **never damaged**: 292/292/58
intact. `data/projects.json` went stale until the next clean emission.

### Repair (verified)

- `scripts/repair_wiped_caches.py`: re-fetched view pages fresh for all 47
  twur'd-but-empty caches → **`repaired: 47 · still-empty: 0`**; post-check:
  0 caches with `twur_view_id` + empty milestones.
- Deleted all 126 URL-cache `*.html` files (poison source gone; fresh fetches
  on any future cache miss parse correctly).

### Silver lining — unplanned bulk refresh

The surviving orphaned CLI (PID 315812, started 23:14) kept running live
discovery over the ~283 unreadable caches with the **fixed parser and the new
`STAGE_FIELD_MAP`** — an unplanned bulk refresh. Progress observed: 471 → 657/709
cache hits (~190 caches/hr), 52 remaining at last check. Its eventual emission
carries corrected `審議通過日期`/`權變審議通過日期` labels and freshened Taipei
timelines for the re-discovered cohort. *(Caveat: this same run, relaunched after
all 709 `result.json` were backed up + deleted, also produced the §18 regression —
the Taipei-side gains are real, but national coverage collapsed. See §18.)*

### Rules going forward

1. **Single-writer rule**: never run the fetch script and any `urtpe.cli`
   discovery concurrently — one writer on `data/.link_cache` at a time. The
   fetch script's auto-regeneration at deadline is the sanctioned hand-off.
2. **Kill order**: if a fetch/CLI process must be stopped, kill the whole tree
   (parent + children); a killed parent with a live child is the worst state.
3. **Hardening (§12.9) — `[RESOLVED]` (2026-08-25)**: `regenerate_viewer` now
   redirects child stdout/stderr to `data/.link_cache/regen_log.txt` (append)
   instead of `capture_output` pipes and raises the timeout 300 s → 1800 s.
   Not deadlock-class (see corrected #1) — the point is that an orphaned child
   can always finish writing, stays observable in the log, and legitimate slow
   regenerations don't time out into silent "viewer not refreshed" states.
4. **Corruption signature**: a cache/view file starting `\x1f\xef` (mangled gzip
   magic) is unrecoverable text-mangled binary — delete and re-fetch, never parse.

---

## 18. Bulk Discovery Refresh Regression (2026-08-25 ~01:05) — Root Cause, Damage, Rules

### What happened

The cache-healing refresh (§17.5 continuation) went further than repairing the
47 wiped caches: **all 709 `result.json` were backed up to
`data/.link_cache_backup_20260824`, then deleted**, and discovery re-ran
(`urtpe.cli --from-js viewer/projects.data.js -o data --viewer --links`) keeping
only the URL page caches — intent: re-derive everything with the fixed parser
and corrected `STAGE_FIELD_MAP` without re-hitting the network.

Timeline: first attempt started 2026-08-24 21:21, died silently ~23:11 (no
stderr; logs empty/truncated); relaunched 23:14 (PID 315812) over the full 709;
completed ~01:05; `viewer/projects.data.js` regenerated 01:05:55 on the
regressed state.

### Root cause — a "cache" that was actually the source

The Taipei path reconstructs fully from kept inputs (search API by
section + parcel). The national path cannot:

- `discover_project_links` (`urtpe/links.py:565-585`) resolves a view_id ONLY
  via `portal_index.json` (**110 entries** — WAF-capped newest-first crawl,
  §9) or the fallback JSON (**3 entries**).
- The targeted-fetch campaign's ~180 additional land-core → view_id mappings
  were written **directly into each project's `result.json`** and existed
  nowhere else.
- Page caches don't help: `fetch_view_page` needs the view_id to build the URL
  before it can hit its cache. No mapping → no URL → cache miss that can never
  resolve.

Deleting the `result.json` files therefore didn't discard cheap derived data —
it discarded the only copy of an expensive lookup table.

### Damage

| Measure | Pre (backup 20260824) | Post (regenerated) |
|---|---|---|
| Projects with `twur_url` / `national_milestones` | 292 | **109** |
| Projects with `使用核發日期` | 58 | **1** |

183 projects lost national links + milestones (57 of them carried 使用核發).
The refresh's Taipei-side gains (corrected labels, freshened timelines) are
real but ride on top of this loss.

### Recovery (done 2026-08-25 02:17)

`scripts/restore_national_links_2026_08_25.py`: for each backup cache with a
twur link whose live counterpart lost it, merged back exactly
`twur_view_id` / `twur_url` / `national_milestones` — preserving the refresh's
Taipei-side gains (`case_milestones`, `implementation`, `rewards`, corrected
labels). No network. Result: **restored 183 · already-ok 109 · missing 0**,
live totals **709 scanned · twur 292 · national_milestones 292 · 使用核發 58**.
Viewer re-emitted (`--from-js --viewer --links`, cache-only) and parsed back:
292 / 292 / 58 across 709 projects — pre-refresh state fully recovered.
Keep `.link_cache_backup_20260824` until the §12.3 consolidation makes the
index self-sufficient (never delete as scratch).

### Rules going forward

1. **Reconstructibility precondition**: before deleting/regenerating a cache,
   enumerate every field and prove it is reconstructible from the inputs being
   kept. If not, the "cache" is a source — back it up *and* diff coverage after.
2. **Fold campaign outputs into the index at write time**: targeted-fetch
   mappings must land in `portal_index.json` (or a dedicated mapping store), so
   the index reflects reality instead of lagging it — merges naturally into the
   §12.3 library-first consolidation (`--links-targeted`).
3. **Regression guard on destructive jobs**: snapshot coverage counters
   (twur / national_milestones / 使用核發 / Taipei resolved) before and after;
   any decrease aborts the job and alerts. A silent 292→109 drop ran unnoticed
   for hours here.
4. **Single-writer rule unchanged** (§17): one writer on `data/.link_cache` at
   a time — this incident was single-writer yet still destructive; concurrency
   is not the only hazard.

---

## 19. Bulk-Refresh Sequencing Decisions & Outcome (exploration 2026-08-24/25)

The pre-change exploration for `add-taipei-implementation-data` produced a sequencing
plan for the full discovery refresh. Decisions, rationale, and where each landed:

| # | Suggestion | Rationale | Outcome |
|---|---|---|---|
| 1 | Fix `STAGE_FIELD_MAP` before any bulk pass | labels are baked into caches at fetch time; fix-then-fetch = one pass instead of two | ✅ round 1 + round 2 landed in the change (tasks 1.2/2.1) — round 2 (comm_hold relabel, `outline_ok_date`/`jud_ok_date0`/`comm_hold_date0`) came from the DOM label map |
| 2 | Bundle third/fourth.ashx integration before the bulk pass | the detail-page DOM handed over the full 86-field label map for free; avoids a second ~1,400-case sweep | ✅ became `add-taipei-implementation-data` (21/21 tasks, schema v2) |
| 3 | Discovery refresh BEFORE the `fetch_remaining` campaign | the fetch script is cache-first — twur-first would freeze positional node links in place | ⬜ pending — now safe to start: refreshed caches carry `case_milestones`, which `update_project_cache` preserves |
| 4 | Count normalization before the campaign COMPLETES | strict matcher rejects count-drift pages (金華段 11 vs 13 筆); rejects are logged and retried, so the campaign may start early | ⬜ OpenSpec change pending |
| 5 | Never run discovery and `fetch_remaining` concurrently | both write the same `result.json` (last-write-wins = lost updates) | ⬜ standing rule (reinforced by §17 single-writer) |
| 6 | No 3–5 min interval for discovery; keep `delay=1.0s` | national exposure is 0–1 *cached* view fetch per project; WAF evidence is list-endpoint-only | ✅ recorded as design D8 of the change |
| 7 | Back up caches before the refresh | a failed view fetch mid-run could blank previously-good national data | ✅ done — `data/.link_cache_backup_20260824` (709 files); this backup is what makes §18's recovery possible |
| 8 | "National-side refresh risk is low — view pages are cached" | held for the **Taipei** path; wrong for the **national** path | ❌ superseded by §18 — see correction below |

**Correction to #8**: the exploration assumed national view pages were reconstructible
from the URL page cache. They are — but only *given the view_id*, and the targeted
campaign's land-core→view_id mappings lived solely in the deleted `result.json`
files: a **source mislabeled as a cache** (§18 root cause). Net effect of the refresh:
Taipei-side gains are real (corrected labels, `case_milestones` in 691 caches,
implementation/rewards payloads) but national coverage regressed 292→109 twur /
58→1 使用核發. The lesson is generalized in §18 rule 1 (reconstructibility
precondition) — read #8 together with §18, never alone.

**Unblocked by the refresh**: the chimera-merge fix (§5, still open) can now be
computed at emit time from `case_milestones` (691 caches carry it) — no network
needed.

### The sequence, current state

```
✅ map round 1+2 → ✅ third/fourth integration → ✅ bulk refresh (691 caches, schema v2)
                                                          │
                                                          ▼
⬜ §18 recovery FIRST: merge the 183 lost national links from
   .link_cache_backup_20260824 (no network) + regenerate + post-check 292/292/58
                                                          │
                                                          ▼
⬜ fetch_remaining campaign (twur coverage, ~600 candidates, overnight windows)
   │  may START anytime (single-writer §17; never concurrent with discovery)
   ▼
⬜ count-normalization OpenSpec change — must land before the campaign COMPLETES
   (strict matcher rejects count-drift pages; rejects retry, so start ≠ finish)
```

---

*Sources: interactive exploration (wmux browser + live API probes) 2026-08-23; code claims cross-checked against `urtpe/links.py`, `tests/fixtures_links.py`, `scripts/`, `viewer/projects.data.js` on 2026-08-24. §6.6 additions (wrong-match bugs, per-node date-aligned linking, fetch-script strict match, third.ashx 6-project probe) from the 2026-08-24 session. §16 fetch-campaign results (06:30 + 17:00 runs) from the 2026-08-24/25 targeted-fetch batches. §17 incident (concurrency wipe, repair, single-writer rule) and the third.ashx cache-layer discovery from the 2026-08-24/25 evening session. §18 regression (bulk refresh vs partial portal index; coverage counts re-measured live from `data/.link_cache_backup_20260824` vs `data/.link_cache`) discovered during the 2026-08-25 overnight refresh monitoring. §19 sequencing decisions from the pre-change exploration for `add-taipei-implementation-data` (2026-08-24/25).*
