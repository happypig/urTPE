# Two Portals — Field Notes & Alignment Map (v2)

*Exploration summary: Taipei City ashx API vs National Portal (twur.nlma.gov.tw) for project 中山區-中山段一小段-254地號等13筆*

> This is the consolidated, single-source-of-truth version. All findings and the §14 parser fix are folded in; resolved items are marked `[RESOLVED]`, code claims carry the verified file:line, and empirical API values are tagged `[live-probed]` (not re-verified this pass).

---

## 0. Decision Summary

| Decision | Status |
|---|---|
| 推動歷程 parser silent-failure root cause | `[RESOLVED]` — applied, backfilled, verified in `viewer/projects.data.js` |
| `jud_ok_date2` field | `[RESOLVED]` — label identified; **mapping still missing in code** (pending) |
| Join approach | Portal = gazette date; Taipei = committee date. **±1 day is a heuristic, not a rule** (Δ=0 observed). |
| Do we need both sources? | Yes — they cover disjoint lifecycles (Taipei pre-approval depth; Portal post-approval breadth + revision rollup). |
| 3 top forks (see §7) | Portal crawl recovery · `Report_Date` semantics · Phase-D confirmation |

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
| **Missing `jud_ok_date2` mapping** | `STAGE_FIELD_MAP` (`links.py:600` starts; **no `jud_ok_date2` entry**) | `jud_ok_date2=2012/04/16` filled but unmapped → silently dropped | **Open** — label resolved (see §6.2), mapping not yet added |
| **Wrong `jud_ok_date` label** | `links.py:611 ("jud_ok_date", "概要審議會通過日期")` | Mislabeled; UI calls it 審議通過日期 | **Open** — see §6.2 |
| **`uro_chk_date2` inconsistency** | `top.ashx` | Case 144 has approval in `second.ashx` (2017/04/13) but `top.ashx` leaves it empty | **Open** `[live-probed]` |
| **No withdrawal date** | Both | 143 自行撤回 has only 申請權變 2016/09/22; withdrawal date nowhere published (see §6.3) | **Open** — best anchor = application date + 撤回 badge |
| **Portal cross-link error** | view/136 | 縣市政府案件連結 points to `case_id=10202065` (辛亥段, 大安區) — wrong project | **Open** `[live-probed]` |
| **推動歷程 parser failure** | `links.py` `ViewPageParser` (old hidden-div-only path) | `milestones_national={}` for all projects | **`[RESOLVED]`** — see §8, verified fixed |

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

### 6.2 `jud_ok_date2` Label — `[RESOLVED]` (mapping pending)

From live `#data2` tab (案件詳細 > 階段辦理過程) `[live-probed]`, case 141:

| API field | UI label | Value |
|---|---|---|
| `jud_ok_date` | **審議通過日期** | 2012/04/16 |
| `jud_ok_date2` | **權變審議通過日期** | 2012/04/16 |
| `comm_hold_date` | 召開審議會日期 | 2011/04/25 |
| `comm_hold_date2` | 權變召開審議會日期 | 2011/04/25 |

**Changes needed in `STAGE_FIELD_MAP`** (verified current state): `jud_ok_date` is mapped to the wrong label `概要審議會通過日期`; should be `審議通過日期`, and add `jud_ok_date2 → 權變審議通過日期`. `概要審議會通過日期`/`概要核准日期` likely map to `outline_ok_date` variants.

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

---

## 7. Files Touched / To Change *(tracked against actual repo layout)*

| File | Role | Status |
|---|---|---|
| `urtpe/links.py` | Discovery flow, **merge bug fix (#535)**, per-case timeline retention, portal view parsing | part done / part open |
| `urtpe/links.py` `STAGE_FIELD_MAP` | Add `jud_ok_date2`, fix `jud_ok_date` label | **pending** |
| `urtpe/graph.py` | `build_project_graph` — attach merged events to nodes | open |
| `viewer/app.js` | `renderDetail` — event layer rendering, ghost nodes, dual dates | open |
| `tests/test_links.py` · `tests/fixtures_links.py` | Portal view parsing scenarios; **new fixture already added** (#89-108) | fixture done |
| `viewer/projects.data.js` | Runtime data (**note: lives in `viewer/`, not `content/`**); already carries `milestones_national` | data done |
| `docs/final_results_json_api.md` | Update with portal merge findings | open |
| `docs/facts_2_portals.md` (v1) | Superseded by this v2 | keðir |

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

The 110 crawled entries span view_id 987–1252, approval dates 112.05.11–115.06.16 (2023-05 → 2026-06) `[live-probed]`: the crawl walks newest-first and died at the WAF after ~110 rows, so coverage is "recent ~3 years" — everything older (e.g. view/136, 核定 2012) is systematically absent. Design fork: resume/repair bulk crawl vs per-project targeted search via the list page's `?title=<keywords>` parameter (mirrors the Taipei parcel-search pattern).

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

1. **Portal crawl recovery** *(highest value — unlocks older projects)* — resume/repair bulk crawl with retry/backoff *or* per-project `?title=<keywords>` targeted search. Recommend the targeted search first: it plates over the WAF and mirrors the working Taipei pattern.
2. **`Report_Date` semantics** — empty for 141; confirm whether it ever fills as 成果報備日期.
3. **Phase-D cases** — find a real phase-D project to confirm the 核定後/執行前 state (A/B/D are currently inferred).
4. **`jud_ok_date2` mapping** (code change, not investigation) — add to `STAGE_FIELD_MAP` and fix the `jud_ok_date` label; this is ready to implement.
5. **`fourth.ashx` reward flags** — map non-empty values to labels (site JS needed).
6. **Withdrawal date source** — any external system (紙本? 內部系統?) publishes 撤回日. Likely a dead end; deprioritize.
7. **Schema version** — confirm whether `schema_version` field actually exists in `viewer/projects.data.js` before bumping; no `schema_version` key was found this pass.

---

*Sources: interactive exploration (wmux browser + live API probes) 2026-08-23; code claims cross-checked against `urtpe/links.py`, `tests/fixtures_links.py`, `scripts/`, `viewer/projects.data.js` on 2026-08-24.*
