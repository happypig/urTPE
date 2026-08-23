# Two Portals — Field Notes & Alignment Map

*Exploration summary: Taipei City ashx API vs National Portal (twur.nlma.gov.tw) for project 中山區-中山段一小段-254地號等13筆*

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

- **143 & 144 are name-twins**: identical case name → same application resubmitted after withdrawal
- Portal shows **one row per revision ordinal** (1st, 2nd…) with paired 事業/權變 dates
- Taipei splits by **application attempt** (each gets own case_id + full process trace)

---

## 3. Date Alignment — The 1-Day Offset

| Milestone | Portal (gazette) | Taipei (ashx) | Delta | Meaning |
|---|---|---|---|---|
| 事業計畫核定 | 101.08.28 (2012-08-28) | 2012/08/27 | +1 day | gazette 公告日 vs 會議核定日 |
| 權變核定 (原案) | 101.08.28 | 2012/08/27 | +1 day | same |
| 1st變更 事業 | 105.08.24 | 2016/08/23 | +1 day | same |
| 1st變更 權變 | 105.08.24 | 2016/08/23 | +1 day | same |
| 2nd變更 事業 | 106.04.14 | 2017-04-13 | +1 day | same |
| 2nd變更 權變 | 106.04.13 | 2017/04/13 | 0 | coincidence / same day |

**Rule**: portal date = gazette publication date (next business day after committee approval). Taipei date = committee approval date. Store both; they are semantically different.

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

---

## 5. Known Data Bugs & Quirks

| Bug | Location | Impact |
|---|---|---|
| **Chimera merge** | `links.py:489 all_taipei_milestones.update(ms)` | Last-write-wins across cases; 141's 核定 2012/08/27 overwritten by 142's 2016/08/23 → viewer card shows wrong anchor date for node 1219 |
| **Missing `jud_ok_date2` mapping** | `STAGE_FIELD_MAP` | `jud_ok_date2=2012/04/16` filled but unmapped → silently dropped |
| **`uro_chk_date2` inconsistency** | `top.ashx` | Case 144 has approval in `second.ashx` (2017/04/13) but `top.ashx` leaves it empty |
| **No withdrawal date** | Both | 143 自行撤回 has only 申請權變 2016/09/22; withdrawal date nowhere published |
| **Portal cross-link error** | view/136 | 縣市政府案件連結 points to `case_id=10202065` (辛亥段, 大安區) — wrong project |
| **Partial portal crawl** | `build_portal_index` | WAF resets → only 110/709 projects indexed; this project missing → no `twur` link |

---

## 6. Join Strategy (Design Sketch)

```
STEP 1: Fix provenance (per-case timelines)
  Taipei: retain [{case_id, name, schedule, milestones: [{label, date}]}]
  Portal: parse view page → {view_id, revisions: [{ordinal, biz_date, land_date}], occupancy_date, basic_data}

STEP 2: Anchor by date (±1 day, track-compatible)
  141 ↔ node 1219 (核定 2012-08-27 vs 101.08.28)
  142 ↔ node 1037 (核定 2016-08-23 vs 105.08.24)
  144 ↔ node 991  (核定 2017-04-13 vs 106.04.13)

STEP 3: Leftover cases → name-twin fallback
  143 name = 144 name = node 991 name → attach as ghost before 144
  position by its 申請權變 2016/09/22, badge 自行撤回

STEP 4: Merge post-approval
  Portal 使用核發 2016/08/29 → attach to 1st-revision chain (after 142's 核定)
  Portal 基本資料 → project-level enrichment
  Portal `資料更新日期` → freshness signal
```

---

## 7. Current Viewer State (projects.data.js)

```json
"links": {
  "taipei": ["09811141","09811142","09811143","09811144"],
  "milestones_taipei": { "核定日期": "2016/08/23", ... },  // CHIMERA
  "twur": ""
}
```
- Per-node links assigned positionally (wrong for revisions: 1037 gets 141, 991 gets 142)
- No portal data at all
- No 建照核發 on node 1219 (was overwritten)

---

## 8. Open Questions / Next Investigations

1. **Portal crawl recovery** — re-run with retry/backoff (design.md §D3) or use browser automation for missing projects?
2. **`jud_ok_date2` label** — what does the Taipei UI call it? Need to check site JS for label mapping.
3. **Phase taxonomy** — what do `phase` A/B/C/D/E mean? Only saw C (審議中) and E (執行). Map all.
4. **Withdrawal date** — does any other endpoint (施工階段? R_build?) carry 撤回日期?
5. **Occupancy permit in Taipei** — is there an API for `使用核發日期` on the Taipei side?
6. **Cross-project name normalization** — portal names match gazette exactly here; but `build_portal_index` normalizes (strips 擬訂/臺北市). Define canonical comparison.
7. **Schema version** — any merge changes `projects.data.js` schema_version → bump to 2.

---

## 9. Files Touched / To Change

| File | Role |
|---|---|
| `urtpe/links.py` | Discovery flow, merge bug fix, per-case timeline retention, portal view parsing |
| `urtpe/graph.py` | `build_project_graph` — attach merged events to nodes |
| `viewer/app.js` | `renderDetail` — event layer rendering, ghost nodes, dual dates |
| `tests/test_links.py` | Add scenarios for `search_taipei_cases_api`, `fetch_taipei_milestones_api`, portal view parsing |
| `docs/final_results_json_api.md` | Update with portal merge findings |

---

*Generated from interactive exploration (wmux browser + live API probes) — 2026-08-23*

---

## 10. Resolved Open Questions (Follow-up Probes)

### 10.1 `jud_ok_date2` Label — **Taipei UI: "權變審議通過日期"**

From live `#data2` tab (案件詳細 > 階段辦理過程):

| API field | UI label | Case 141 value |
|---|---|---|
| `jud_ok_date` | **審議通過日期** | 2012/04/16 |
| `jud_ok_date2` | **權變審議通過日期** | 2012/04/16 |
| `comm_hold_date` | 召開審議會日期 | 2011/04/25 |
| `comm_hold_date2` | 權變召開審議會日期 | 2011/04/25 |

**STAGE_FIELD_MAP bug**: 
- Current: `("jud_ok_date", "概要審議會通過日期")` → **wrong label**
- Should be: `("jud_ok_date", "審議通過日期")` + add `("jud_ok_date2", "權變審議通過日期")`
- Also `"概要審議會通過日期"` / `"概要核准日期"` appear in UI (empty for this case) — likely map to `outline_ok_date` variants.

---

### 10.2 Phase Taxonomy — **A/B/C/D/E = Top-level Stage Gates**

From `top.ashx` `phase` + `NAME` for all 4 cases:

| Phase | NAME example | Meaning | Corresponds to UI tab |
|---|---|---|---|
| **A** | (not seen) | 單元劃定 | "單元劃定" |
| **B** | (not seen) | 事業概要 | "事業概要" |
| **C** | 權利變換計畫階段─實施者自行撤回 | 計畫審議中 (含撤回) | "事業計畫" / "權變計畫" |
| **D** | (not seen) | 核定後、執行前 (公告/備查) | — |
| **E** | 執行階段_更新案完成成果備查 | 施工/實施階段 | "執行" |

Only C (143) and E (141,142,144) observed. A/B/D would appear for cases in earlier/later lifecycle.

---

### 10.3 Withdrawal Date — **NOT Published in Any Endpoint**

Checked all 4 ashx endpoints for case 09811143 (自行撤回):

| Endpoint | Fields checked | 143 values |
|---|---|---|
| `second.ashx` | 36 timeline fields | Only `Plan_App_Date2` = 2016/09/22 |
| `top.ashx` | `phase='C'`, `NAME='權利變換計畫階段─實施者自行撤回'` | No date |
| `third.ashx` | `Eng_Start_Date`, `Ulic_Date`, `Report_Date` | All empty |
| `fourth.ashx` | Reward/容積 data | No date |

**Conclusion**: Platform records *that* it was withdrawn (`schedule`/`NAME`/`phase`), but **never *when***. Best anchor: application date 2016/09/22 + 撤回 badge.

---

### 10.4 Occupancy Permit in Taipei — **YES, in `Get_project168_third.ashx`**

| Field | Label | Case 141 value | Matches |
|---|---|---|---|
| `Eng_Start_Date` | 開工日期 | **2013/09/10** | — |
| `Ulic_Date` | 使用執照日期 | **2016/08/29** | Portal `使用核發` 105.08.29 ✓ |
| `Report_Date` | (成果報備日期?) | empty | — |
| `Exe_Way` | 實施方式 | **權利變換** | ✓ |

Only the *completed* case (141) has these filled; revision cases (142, 144) empty because implementation tracking belongs to the final approved case.

---

### 10.5 Project Metadata — **All Available in `third.ashx` + `fourth.ashx`**

User's requested fields **all present** for case 141:

| Requested field | API source | Field | Value |
|---|---|---|---|
| 開工日期 | `third.ashx` | `Eng_Start_Date` | 2013/09/10 |
| 使用執照核發日期 | `third.ashx` | `Ulic_Date` | 2016/08/29 |
| 成果報備日期 | `third.ashx` | `Report_Date` | (empty for 141) |
| 實施方式 | `third.ashx` | `Exe_Way` | 權利變換 |
| 基地面積 | `third.ashx` | `Base_Area` | 1,604.00 |
| 土地使用分區1 | `third.ashx` | `Landkind1` | 第四種商業區(特)(原商三) |
| 土地使用分區2 | `third.ashx` | `Landkind2` | (empty) |
| 土地使用分區3 | `third.ashx` | `Landkind3` | (empty) |
| 使用分區1面積 | `third.ashx` | `Landkind1_Area` | 1,604.00 |
| 使用分區2面積 | `third.ashx` | `Landkind2_Area` | 0.00 |
| 使用分區3面積 | `third.ashx` | `Landkind3_Area` | 0.00 |

**Additional rich fields in `third.ashx`** (settlement stats):
- `Old_Doors`=50, `Settle_Old_Doors`=0, `Settle_Doors`=0
- `New_Parkings`=103, `New_Parkings2`=85
- `Sidewalk_Length`=60, `Sidewalk_Area`=230.81
- `Urban_Renew_Fee`=1,242,782,140
- `pc_afterUpdTotalValue`=2,761,323,189
- `Land_Owners_Pir`=54, `Bui_Owners_Legal`=54

**In `fourth.ashx`** (rewards/容積):
- `F0`=8,982.01 (基準容積), `F`=10,829.58 (允建容積)
- `F3`=538.92 (都市更新獎勵), `F5`=1,308.65
- `F5_3`=230.81 (人行步道面積)
- Reward flags: `GREENBUILD_DESIGN`, `SEISMIC_DESIGN`, etc. (all empty here)

---

### 10.6 Cross-Project Name Normalization — **Canonical Tuple Comparison**

| System | Method | Fallback |
|---|---|---|
| **Taipei** | `build_land_core_key(CleanRecord)` → `{district}{section}{parcel}地號等{count}筆` | — |
| **Portal** | `parse_name_id(title)` → same tuple; if regex fails → strip common suffixes | `title.replace("擬訂","").replace("臺北市","")...` |

**Canonical join key**: normalized tuple `(district, section, parcel, count)` from `parse_name_id` on both sides. Avoids string-stripping ambiguity. Store in both indexes for reliable matching.

---

## 11. Complete Taipei Endpoint Map (Updated)

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

---

## 12. Updated Join Strategy — Implementation Layer

```
STEP 4 extended: Merge implementation data (third.ashx)
  Case 141: Eng_Start_Date 2013/09/10 → attach to node 1219 chain (post-核定)
            Ulic_Date 2016/08/29 → matches portal 使用核發, attach after 1st revision
            Base_Area/Landkind* → project-level metadata enrichment
  Cases 142/144: implementation fields empty (tracking on final case only)
```

---

## 13. Updated Open Questions

1. **Portal crawl recovery** — re-run with retry/backoff or browser automation?
2. **`Report_Date` meaning** — empty here; does it ever fill as 成果報備日期?
3. **Phase D cases** — find a project in phase D to confirm 核定後/執行前 state.
4. **`fourth.ashx` reward flags** — map non-empty ones to labels (site JS needed).
5. **Schema version bump** — `projects.data.js` → version 2 for merged event layer.
6. **Withdrawal date source** — any other system (紙本? 內部系統?) publishes 撤回日?

---

*Updated 2026-08-23 with live endpoint probes (third.ashx, fourth.ashx, UI label extraction)*

---

## 14. 推動歷程 Parser Silent Failure — Root Cause Found

**Symptom**: emitted dataset has `milestones_national = {}` for ALL 709 projects, despite
109 projects carrying a resolved `twur` URL and the portal index matching 78/110 cores exactly.

### Causal chain

```
portal index crawl ──▶ 110 entries                 ✅
core lookup        ──▶ 78/110 exact matches        ✅
twur_url assigned  ──▶ 109 projects               ✅
fetch view page    ──▶ 50KB HTML                  ✅
case_id extraction ──▶ works                       ✅
推動歷程 extraction ──▶ {} EVERY TIME              ❌ ROOT CAUSE
```

### The bug

`ViewPageParser` only extracts milestones from tables inside `data_table_box` divs whose
style contains `display:none` (`links.py` `_in_hidden_table` → `_process_tuidui_table()`).
That assumption came from an older portal design (hidden div, JS-populated). The current
portal serves the milestone table as **visible static HTML**:

```html
<div class='..._box'>
  <table class='type4_table'>          ← visible; display:none count on page: 0
    <tr><th>項目</th><th>日期</th></tr>
    <tr><td>事業計畫申請日期</td><td>113.05.03</td></tr>
```

Live probe of view/1249: labels present ✓ · `data_table_box` ×13 ✓ · `display:none` ×**0**
→ `_process_tuidui_table()` never fires → `{}`.

### Why it stayed invisible — three masking layers

1. **Status masking**: empty national milestones doesn't change status ("resolved" comes from the Taipei path); no error logged.
2. **Viewer masking**: the 推動歷程 card renders only when non-empty — absence looks like "no data", not breakage.
3. **Test masking**: `tests/fixtures_links.py` fixtures are built on the OLD markup
   (`<div class="data_table_box" style="display:none">`) → tests pass green while production yields nothing.

### Spec conformance

No OpenSpec delta required: `official-link-discovery/spec.md` already mandates attaching
"the twur URL and 推動歷程" from the view page. The broken parser violates the existing spec;
fixing it + refreshing fixtures is a pure implementation bug fix.

### Fix shape (applied)

- Parse visible 項目/日期-headed rows (label `<td>` + ROC-date `<td>` pairs), independent of hidden-div detection; legacy hidden path kept for old cached pages.
- New fixture reproducing live `type4_table` markup + negative assertions (empty 備註 cell dropped, 資料更新日期 row not mistaken for a milestone).
- Backfill `national_milestones` into per-project caches (view.html already cached locally → no network) and re-emit viewer data.

---

## 15. Portal Index Coverage Insight (110 entries)

The 110 crawled entries span view_id 987–1252, approval dates 112.05.11–115.06.16
(2023-05 → 2026-06): the crawl walks newest-first pages and died at the WAF after ~110
rows, so coverage is "recent ~3 years" — everything older (e.g. view/136, 核定 2012) is
systematically absent. Design fork for later: resume/repair bulk crawl vs per-project
targeted search via the list page's `?title=<keywords>` parameter (mirrors the Taipei
parcel-search pattern).