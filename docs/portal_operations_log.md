# Portal Operations Log — dated sessions, incidents & campaigns

*Companion to `docs/facts_2_portals.md` (reference) — this file is the append-only operational record. Anchors §6.x / §16-§19 are preserved here so citations like "see §6.7" or "§18 rule 1" keep resolving. New sessions append at the bottom.*

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

**Applied in `STAGE_FIELD_MAP`** (2026-08-24): `jud_ok_date` relabeled `概要審議會通過日期` → `審議通過日期`, and `jud_ok_date2 → 權變審議通過日期` added (regression test `test_stage_field_map_jud_ok_labels`). Note: labels are baked into caches at fetch time — existing caches keep the old label until the bulk discovery refresh. `概要核准日期` mapping candidate `outline_ok_date` is now **evidence-backed** (filled 2001/01/11 on lapsed 概要 case 08909160, live-probed 2026-08-25) — still intentionally not added pending a UI-label confirmation on a 概要-track case detail page.

### 6.3 Withdrawal Date — `[RESOLVED]`: Not Published

Checked all 4 ashx endpoints for case 09811143 `[live-probed]`: `second.ashx` (36 timeline fields → only `Plan_App_Date2`=2016/09/22), `top.ashx` (`phase='C'`, NAME 自行撤回, no date), `third.ashx` & `fourth.ashx` (all empty / no date). Platform records *that* it was withdrawn, never *when*. Best anchor: application date 2016/09/22 + 撤回 badge.

### 6.4 Occupancy Permit — Taipei side exists, in `third.ashx` `[live-probed]`

| Field | Label | Case 141 value | Matches |
|---|---|---|---|
| `Eng_Start_Date` | 開工日期 | **2013/09/10** | — |
| `Ulic_Date` | 使用執照日期 | **2016/08/29** | Portal `使用核發` 105.08.29 ✓ |
| `Report_Date` | 成果報備日期 — **confirmed** 2026-08-25 via site DOM (`id="detail_Report_Date"`); fills in 65/2,951 cached payloads, always after 使照核發 | empty | ✓ label official (§12 #7) |
| `Exe_Way` | 實施方式 | **權利變換** | ✓ |

Only the *completed* case (141) has these; revision cases (142, 144) empty because implementation tracking belongs to the final approved case.

### 6.5 Phase Taxonomy — `[RESOLVED]`: all five phases seen (2026-08-25)

`top.ashx` returns `phase` + `NAME`; NAME decomposes as `<階段名>─<outcome>`
`[live-probed]`.

| Phase | Stage (= NAME prefix) | Example NAME (case) | Confidence |
|---|---|---|---|
| A | 事業概要階段 | 事業概要業已失效 (08909160) | seen |
| B | 事業計畫階段 | 業經本府核定 (11408005); 本府駁回 (09712201) | **seen 2026-08-25** |
| C | 權利變換計畫階段 | 實施者自行撤回 (09811143) | seen |
| D | 事業計畫【及】權利變換計畫階段 (combined track) | 業經本府核定 (11010082, 11008281); 實施者自行撤回 (11010081) | **seen 2026-08-25** |
| E | 執行階段 | 更新案完成成果備查 | seen |

Outcome suffixes observed: 業經本府核定 · 本府駁回 · 實施者自行撤回 · 業已失效.
單元劃定 appears to have no phase code (or is pre-A).

Corrections to the earlier ladder inference (2026-08-25):

- **D ≠ "核定後、執行前"** — D is the *combined* 事業+權變 reporting track;
  both D confirmations carry `uro_chk_date` AND `uro_chk_date2`.
- **Approval does not advance the phase**: case 11408005 has
  `uro_chk_date=2025/08/14` yet stays `phase='B'`; only entering 執行 moves
  the case to E.
- The tracks are plan-stage labels, not a strict temporal ladder (B and C are
  single-track submissions; D is their combined submission).

Local phase predictor (no network, from cached milestones): 核定日期 +
權變核定日期 both present and no 開工 anywhere ⇒ D-shaped; 核定 only ⇒
B-shaped. Corpus scan (2026-08-25): 142 approved-without-開工 projects split
**56 D-shaped / 86 B-shaped**. Milestone shape is not authoritative (a
B-approved case matches the shape minus 權變核定); the real phase costs one
`top.ashx` call per case — relevant to whether `phase` enters the emitted
graph (defer to [5] sync-model design).

Bonus from the original A-probe: the lapsed 概要 was itself **approved**
(`outline_ok_date = 2001/01/11`) before being superseded by the approved
事業計畫 — and `outline_ok_date` is a real, filled timeline field, evidence
for the §6.2 withheld `概要核准日期` mapping.

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

### 6.7 Session 2026-08-25 — Taipei Search Over-Return (unit-level matching) — Evidence & Fix Shape

The Taipei twin of §6.6: the national portal's loose match was fixed, but the
**Taipei parcel search has the same class of problem one layer earlier** —
`search_taipei_cases_api` keeps every `r_progress_detail` case from the search
response without verifying the case's land matches the project's parcel.

**Case study** (user-spotted): 南港區-南港段一小段-520-2地號等18筆 —
**2 recnos but 7 Taipei links**.

| case_id | case (from `Get_updcase_list.ashx`) | land | schedule | verdict |
|---|---|---|---|---|
| 09407070 | 擬訂…**520-2等18筆**…事業**概要**案 (R13) | own | 已核准 | ✅ own 概要 — no gazette node (概要核准 isn't in this gazette family) |
| 09407071 | 擬訂…**520-2等18筆**…事業計畫及權利變換計畫案 (R13) | own | 完成成果備查 | ✅ → recno 1349 (2008 擬訂) |
| 09407073 | 變更…**520-2等18筆**…事業計畫及權利變換計畫案 (R13) | own | 完成成果備查 | ✅ → recno 1303 (2009 變更) |
| 09407110 | 擬訂…**522等45筆**…事業概要案 (R13) | **other** | 已核准 | ⚠️ sibling land group |
| 09407113 | 擬訂…**467等41筆**…事業概要案 (R13) | **other** | 已駁回 | ⚠️ sibling |
| 09509071 | 擬訂…**403-2等28筆**…事業概要案 | **other** | 已失效 | ⚠️ sibling |
| 09607130 | 擬訂…**561等5筆**…事業概要案 | **other** | 已核准 | ⚠️ sibling |

**地號清單 verification** (viewer `parcels`, parsed from the gazette PDF — the
platform's detail page publishes no parcel list; JS-shell confirmed): both
recnos carry the identical 18-parcel list `508-2…521-3` (508-2, 509, 509-1,
510, 511, 512, 513, 518, 518-1, 519, 519-1, 519-2, 520-1, 520-2, 520-3, 520-6,
521-2, 521-3). **Zero overlap** with 522 / 467 / 403-2 / 561.

**Root cause**: the platform's parcel search matches at the **renewal-unit /
district level** — the four siblings share the **R13 街廓** designation (南港
經貿園區特定專用區; detail page: 本府公告劃定 2002/07/12, 區位 R13-3 西側街廓),
a large designated district containing multiple distinct renewal cases. One
searched parcel drags in every sibling case in the district.

**What saved the nodes**: date-aligned anchoring (§6.6) placed only 09407071/73
on their recnos; the contamination is project-level `links.taipei` only — and
symmetric: the sibling projects' own searches cross-contaminate in reverse.

**Fix shape** (small, no spec delta — same category as §6.6): a `case_name`
parcel guard in `search_taipei_cases_api` — keep only entries whose
`case_name` contains `<parcel>地號` (here: keeps exactly 09407070/71/73, drops
the 4 siblings). Caveat: must tolerate notation drift (520-2 vs 520之2) or it
becomes its own false-reject source. Fold into the §12 consolidation library-first
consolidation, where the function moves into `urtpe/links.py`.

**General rule**: project-level `links.taipei` is the **raw search output** and
can legitimately exceed the recno count — the parcel search returns
*application attempts* (概要/lapsed/withdrawn) that never reached the gazette
(e.g. 龍泉段712: 2 recnos, 3 links — lapsed 概要 08909160; this project: own
概要 09407070 已核准). Node-level anchored links are the authoritative
project↔case binding; expect `len(links.taipei) ≥ len(recnos)` as normal.

**Bonus (§6.5 correction)**: probing this family confirmed **phase A = 事業概要
階段** (08909160 on 龍泉段712, live-probed) — see §6.5.

### 6.8 Session 2026-08-26 — Cross-Family Case Pollution & Fragment Families (isolated construction events)

User-reported: isolated 建照/開工/使照 event nodes (no pink source edge) on
金華段513-3, 南港段一小段19-1, 懷生段249, 正義段115. Investigation extended
§6.7 (unit-level search over-return) one layer deeper — the over-returned
cases don't just pollute `links.taipei`, their **construction milestones win
the last-write-wins merge** and render as events attributed to cases that
anchor to no record (or to another family).

**Verification first (10106116, user-suspected wrong anchoring)** — live
probe: 10106116's own case name is 擬訂…**光華段四小段508-6地號等29筆**…
事業計畫案 (已完工) → belongs to 光華段508-6 recno 1064 ✓; its 建照
2019/08/15 is that family's ✓. 寶清段57-13's 建照 2019/08/06 from 10212211 ✓
(per-case cache: only 10212211 carries it). **Data correct — discrepancy
resolved** (the two families' 建照 dates 2019/08/15 vs 2019/08/06 are
coincidentally close).

**Mechanism** (金華段513-3 case study, user-spotted): family 19-1地號等34筆
records 2019/2024/2026; discovery's parcel search returned 10809251 (擬訂…
**101地號等41筆**…， 核定 2022-10-04) because its 41-parcel land list includes
19-1地號. Its 建照 2023/09/20 + 開工 2024/05/21 won the merge (last-write-wins)
but 10809251 anchors to no record (its own PDF record recno 411 lives in the
**fragment family** 南港段一小段-101地號等41筆) → events render isolated.
The construction dates are arguably **correct** for the development (the 2022
approval covers parcel 19-1) — the family structure is what's fragmented:
the 2022 record's name-core (101地號等41筆) didn't similarity-match the
family (anchor parcel changed 19-1 → 101, count 34 → 41).

**Corpus quantification** (1,353 construction slot values):

| Category | Events | Families/Notes |
|---|---|---|
| Anchored (pink edge renders) | 1,191 (88%) | |
| Resolvable-but-unanchored (isolated render) | **162** | **82 families** |
| ├─ cross-family anchored (fragment confirmed) | 118 | 63 families |
| └─ fully unlinked (case anchored nowhere) | 44 | |
| Double-display (same case wins same slot in 2 graphs) | **112** | e.g. 202地號等1筆 ↔ 202地號等12筆 |

**Fragment shapes** (cross-family fragments classified by
district/section/anchor-stem + parcel overlap):

| Shape | Events | Families | Parcel overlap vs fragment | Reading |
|---|---|---|---|---|
| A: same stem, count drift | 31 | 12 | avg 3.5 (max 18) | same unit, count drift — merge candidates (202地號等1筆 ← 12筆) |
| B1a: same section, parcel changed, overlap > 0 | 11 | 5 pairs | 3–8 | same unit, anchor parcel changed — merge candidates (福和段10-1 ← 165; 犁和段102 ← 165; 玉成段545 ← 560) |
| B1b: same section, parcel changed, overlap = 0 | 55 | 36 pairs | 0 | **foreign-case pollution** — 正義段115/132/243 all take 11102211 (133地號等1筆's case); 長春段35 ← 12-1; 中正段68 ← 66 |
| B1c: same district, section changed | 19 | 13 | 0 | likely pollution (982-8吉林段 ← 133正義段) |
| B2: cross-district | 2 | 1 | **26/26** | 懷生段249: 大安區 vs 中正區 — identical parcels/stem/count, **definite merge miss** (district label conflict) |
| fully unlinked | 44 | — | | winner case anchored nowhere |

**Data-quality risk (B1b)**: foreign cases' construction dates overwrite the
family's own via last-write-wins — 正義段115's graph shows 建照 2024/10/07
from 11102211 (133地號等1筆's case). Open question: does 11102211's land list
include 115/132/243 (one big case → dates shared) or not (search false
positive → wrong dates)? Decides pollution severity.

**Fix direction** (needs OpenSpec change; touches `official-link-discovery`
+ `case-merging`):
1. Taipei case-search strictness — extend the §6.7 `case_name` parcel guard
   to reject cross-family cases (the 44 fully-unlinked + 55 B1b events are
   the pollution tail; §6.7's sibling-概要 case is the same disease).
2. Fragment-family merge candidates — a fragment whose discovered cases all
   anchor inside a main family (A / B1a / B2 shapes) becomes a merge
   candidate, review-flagged 臨界對-style (shape A/B2 are near-certain;
   B1a needs the parcel-overlap threshold).
3. Viewer already renders honestly (案… provenance, no false edges) — no
   viewer change needed for this layer.

**Fix applied** (2026-08-26, OpenSpec change `fix-cross-family-case-pollution`):
- `search_taipei_cases_api` parcel guard implemented (§6.7 extension):
  `urtpe/links.py:_case_name_carries_parcel` + `normalize_parcel_token`
  keep only cases whose `case_name` contains searched parcel (mono part,
  full-width↔ASCII, 之↔- tolerant). `DiscoveryResult.search_rejected`
  captures rejected entries for fragment-detection evidence.
- `detect_fragment_families()` + `_flag_fragment_families()` in
  `urtpe/links.py`: families whose all cases anchor in exactly one other
  family get `review_flags` on anchor records (臨界對-style, no family
  mutation).
- Regen completed (709 caches refreshed, 685 resolved, 24 unresolved).
- **Post-fix corpus metrics**: isolated events **162 → 73** (55%↓),
  families with isolated **82 → 32** (61%↓), double-display **94 → 40**.
- **11102211 verdict**: cache shows it is 133地號等1筆's case — does NOT
  contain 115/132/243 parcels. The B1b pollution was search false positive
  (overlap=0), not a shared big case.
- **Motivating families verified**:
  - 正義段115: 11102211 rejected (kept 10105242, 11008311)
  - 南港19-1: 10809251 rejected (kept own 3 cases)
  - 南港101: own 10809251 wins 建照; fragment-flagged → 19-1
  - 懷生段249: 中正區↔大安區 mutual fragment flags (pair-A, 4 shared)
  - 金華段513-3: 3 own cases (09201072, 10011041, 10011042), 建照 from
    10011041 (no foreign pollution)

### 6.9 Session 2026-08-26 — Per-Record Snapshot Emission Fix + `Exe_Way` Vocabulary `[RESOLVED]`

User question "why can't we have the needed callout?" exposed an emission bug:
`complete-viewer-field-labels` task 10.2 ("additive optional node field") was
checked off, but only the domain half landed — `attach_links_to_projects` sets
`member.implementation` (links.py:974) while `build_project_graph` serialized
only `node["links"]`. The viewer guards callouts on `n.implementation`
(app.js), so 0/1,419 nodes rendered one despite 689/709 projects carrying
project-level data.

**Fixes** (conformance repair — the archived change's spec already mandates
per-record snapshots; same precedent as §8):

- `urtpe/graph.py`: emit `node["implementation"]` when the record carries a
  snapshot (additive optional; schema unchanged).
- `urtpe/cli.py` `_load_projects_from_js`: restore record-level snapshots and
  project-level `implementation`/`rewards`, so a `--from-js` regen is lossless
  even without `--links` (attach overwrites when it runs).
- Tests: node-emission regression in `tests/test_links.py`; loader round-trip
  in new `tests/test_cli.py`. Suite 187 passed.
- Regen (`--from-js --links --viewer`, cache-first): **0→1,345/1,419** nodes
  with snapshots. Unblocks `refine-event-source-edges`, whose proposal wrongly
  assumed this emission had already landed.

**Correction to §11**: live probe of `get_project168_top.ashx` (2026-08-26,
case 10203161) shows its keys are `CASE_ID/CASE_NAME/PLACE/EXE_NAME/NAME/
phase/STYLE/<stage dates>/rm_lastestState` — **no `Exe_Way` field**. The
§11 row's `Exe_Way` was a misread of `EXE_NAME` (= 實施者名稱). 實施方式 lives
only in `third.ashx`.

**`Exe_Way` corpus vocabulary** (scan of all cached third.ashx payloads,
2026-08-26):

| Scope | Coverage | Distinct | Top values |
|---|---|---|---|
| All payloads | 2,682 | 23 | 權利變換 1,749 · 協議合建 423 · 事業計畫及權利變換計畫 176 |
| 現況 (anchor) node's own case | 656/709 projects (53 without payload) | 19 | 權利變換 381 · 協議合建 159 · 事業計畫及權利變換計畫 25 |

Full value set: 權利變換 · 協議合建 · 事業計畫及權利變換計畫 · 事業計畫 ·
權利變換計畫 · 自行興建 · 設定地上權 · 自地自建 · 委託興建 · 聯合開發 ·
臺北市政府自行興建 · 所有權人(臺北市)自行出資 · 依公共工程採購標準編列預算實施 ·
權利變換(變更為協議合建) · 協議合建或權利變換 · plus mixed combos
(部份/部分 權利變換+協議合建).

⚠️ **Not normalized**: the mixed-combo family appears as ~8 spelling variants
(部份 vs 部分 × `、` `,` `，` separators). Anything that groups/filters by
`Exe_Way` must fold these first — relevant to any future way-based viewer
grouping or statistics.

Also confirmed: the 現況 milestone itself carries **no** 實施方式 — `top.ashx`
`NAME` is a stage+status string only (`<階段>─<outcome>`, §6.5); the plan-type
proxy appears solely in case/portal titles (事業計畫 vs …及權利變換計畫;
portal index: 56 / 53 of 110).

### 6.10 Session 2026-08-28 — Coverage Audit + Second Cache-Wipe Regression (§18 recurrence)

A 4-category unresolved/unfetched audit (measured live from `data/.link_cache` +
`viewer/projects.data.js`, 2026-08-28 ~00:58, while the case-name harvest ran —
single-writer rule enforced) returned:

| # | Category | Total | Unresolved/unfetched | Reading |
|---|---|---|---|---|
| 1 | Projects | 709 | 24 (`status != resolved`) | 9 × Taipei read-timeout (transient) + 15 blank-error = the §16.1 count-drift/unparseable cohort; 0 missing cache dirs |
| 2 | Records | 1,419 | 50 | records under the 24 unresolved projects; clears automatically with #1 |
| 3 | 相關連結 case_ids | 1,967 | 288 unnamed | 287 sat in ~108 projects the running harvest hadn't reached (self-healed ~01:08); 1 true orphan `11503006` (中山段一小段639地號等12筆) — search endpoint never returned it (115-era index lag); retry `harvest_case_names.py --pid … --force` later |
| 4 | `twur` links | 709 | **592 missing (117 present)** | **not a backlog — a fresh §18-class wipe, see below** |

Audit mechanics worth keeping: cache lookups must use the sanitized id
(`re.sub(r"[^\w\-]", "_", pid)`, `links.py:_project_cache_dir`) — one project_id
contains a literal `?` (寶清段一小段51-13地號等?筆), so raw-id paths silently
miss.

#### Root cause — §18 recurred, bigger (wipe 2026-08-26, found 08-28)

`scripts/regen_links_2026_08_26.py` (§6.8 re-merge pass) unlinked **all 709
`result.json`**, then re-ran `LinksDiscovery`. Discovery resolves a view_id only
via `portal_index.json` (110 entries) + fallback JSON (3) — the exact §18
mechanism (`links.py:565-585`) — so every targeted-fetch mapping died with its
cache. The same-day viewer emit propagated the regressed state. §6.8's "709
caches refreshed, 685 resolved" was true for the *Taipei* side and masked the
national collapse — status masking again (§8 masking layer 1). The §12 #1
coverage guard still doesn't exist, so the drop ran unnoticed for ~2 days. And
§18 rule 1 / §19 #7 (back up, then diff coverage) were not followed this time:

| Measure | §16.1 peak (08-26 00:19) | Live (08-28) |
|---|---|---|
| `twur_url` / `national_milestones` | 581 (82%) | **117 (17%)** |
| `使用核發日期` | 248 (33%) | **6 (1%)** |

**The peak 581 state exists in no backup** (best: `.link_cache_backup_20260825_matcher` = 302).

#### Recovery assets

- Backups: `backup_20260824` (292-era) · `backup_20260825_matcher` (**302**, best) ·
  `backup_20260826_fix` (109, post-wipe, useless) · `.link_cache_wip_20260827` (9).
- **399 cached `view.html` survive** — the regen deletes only `result.json`. 282
  of the 592 twur-less projects have one → view_id + 推動歷程 re-derivable
  **offline** (§8 backfill precedent). Offline ceiling ≈ 399.
- The no-match ledger (127 negatives) is the genuine-absence set (§16.1);
  previously-*matched* projects are not in it, so a `fetch_remaining` re-run
  re-probes and should re-match the ~464 lost links (~15 h at 1-3 min
  intervals; idempotent, ledger-suppressed skips sleep 15-45 s).

#### Remediation order

1. Wait for any running crawl (single-writer, §17).
2. **Build the §12 #1 coverage guard first** — this is the second unguarded wipe.
3. Offline `view.html` backfill for the 282 (one-off script, no network).
4. Re-run `scripts/run_links_from_js.py` for the 24 unresolved (resumable,
   cache-first); stubborn ones via `--add-mapping-file` (count-tolerance per §16.1).
5. Overnight `fetch_remaining_national_portal.py` for the remainder.
6. Re-emit viewer; re-run this audit — expect 0/0/1-orphan/ledger-tail.

**Progress (2026-08-29, step 4 — unresolved retry)**: 24 unresolved caches backed up
(`data/.link_cache_backup_20260829_retry/`) + deleted + re-discovered via
`run_links_from_js.py` (cache-first, single writer). Result: **1 recovered**
(文山區興安段84 — was blank-error), 3 re-resolved their national side from the
portal index (view/1176, view/1172, view/1083), 11 caches merge-backed with
harvested `candidate_names`/`search_rejected` (monotonic: 685→686 resolved,
twur/milestones/使用核發 unchanged). Remaining 23: **13 search read-timeouts**
(§6.7 endpoint stalls on these sections at night; the same queries served the
08-27 name harvest at ~2.3 s each — retry in a calm window) + **10 blank**
(§16.1 count-drift/unparseable cohort; 3 of them already carry twur+milestones —
only their Taipei side is empty → §12 #4 count-tolerance or `--add-mapping-file`).

**Progress (2026-08-29, steps 3+4 — backfill + sweep)**: offline `view.html` backfill
(`scripts/backfill_twur_from_view_html_20260829.py`) restored **282** twur
(117→399, 0 identity mismatches — every cached page passed strict
re-validation; 使用核發 6→191). Viewer cache-synced pre-sweep. Overnight sweep
(`fetch_remaining_national_portal.py`, 02:45–07:00): **processed 133/180,
updated 119, 0 failures, 0 WAF resets** → **twur/milestones 561/709 (79%),
使用核發 242 (34%)** — near the §16.1 peak. Remainder: 47 unprocessed +
ledger tail re-enters after the 14-day TTL (709−561 = 148 twur-less).

**Post-deadline pass (2026-08-29 ~07:00–08:25, unlogged — pane only)**: a second
sweep window ran the remaining queue to exhaustion — **+43 matches**
(399+119+43 = 561), ledger 127→**147** negatives, viewer re-emitted 08:25:42.
Origin: my §12 playbook reply was pasted into the sweep pane; PowerShell
executed its command lines from the input buffer once the overnight sweep
exited at the 07:00 deadline (the playbook's `run_sweep_until.py 22 30`-style
invocation has no log redirect — hence no sweep-log entries). Later pasted
sweep invocations printed "No candidates to process" (queue exhausted by then).
**Campaign converged**: all 148 twur-less projects are ledger-recorded
negatives (genuine absences / gazette lag), coverage stands at
**561/709 (79%), 使用核發 242 (34%)** — within ~20 of the §16.1 peak.
Further sweeps are no-ops until the 14-day TTL lapses or §12 #4 count
normalization recovers the delta.

**Final audit (2026-08-29 09:00, rerun of the §6.10 snapshot)**: unresolved
projects **24→23** (records 50→49), 相關連結 unnamed **288→3** (orphan
`11503006` + 2 on a no-search ledger-negative), twur missing **592→148** (all
ledger negatives). Residuals are data-boundary, not process gaps.

**Quick wins (2026-08-29 ~15:00, pre-backed-up to
`.link_cache_backup_20260829_quickwins`)**: (a) daytime retry of the 15
timeout caches — **8 recovered** (686→**694 resolved, 97.9%**; the night-stall
theory confirmed — same queries pass in the afternoon), merge-back restored
the 8 sweep-gained twur (561 held); (b) the 3 unnamed case_ids backfilled from
`get_project168_top.ashx` `CASE_NAME` (§11; the search endpoint skips them but
the case-header API doesn't — note `r_progress_detail.aspx` <title> carries
only the site name, useless for extraction) → **category 3 = 0**. Viewer
re-emitted (694/561/242). Remaining: 15 unresolved (7 timeout — keep retrying
in calm windows; 8 §16.1 cohort), 148 twur-less ledger negatives. Also
repaired: a stray `++++…` line had been prepended to `urtpe/models.py`
(14:03, editor slip) breaking all `urtpe` imports — removed, suite 238 passed.

**Category-1 round 2 (2026-08-29 afternoon)**: the afternoon retry had already
cleared every timeout error (remaining 15 all blank-search). New lever —
`scripts/resolve_via_view_links_20260829.py`: for unresolved projects that
carry a twur view_id, pull 相關連結 case links off the portal view page
(cached `view.html` or one fetch), attach per-case `second.ashx` milestones +
`top.ashx` CASE_NAME, resolve. **+2 recovered (長安454 ← case 11407047,
玉成733 ← 11108191/21 milestones) → 696/709 resolved (98.2%)**; the other two
twur'd unresolved (臨沂412/view/1172, 玉成253-1/view/856) already carry their
page's case links but with empty milestone payloads. Viewer re-emitted.
⚠️ **Operational hazard found**: hand-written caches with a wrong key
(`milestones_taipei` vs the dataclass's `taipei_milestones`) are silently
`TypeError`-swallowed by `load_project_cache` (links.py:986) → cache miss →
live re-crawl **clobbers the hand edit** on the next regen. Validate
hand-writes against `DiscoveryResult(**data)` before trusting them.

### 6.11 Session 2026-08-29 — 崇仁新村 Exception Resolution (未解析-1354) `[RESOLVED]`

User-identified exception: 未解析-1354's 案名 (變更臺北市萬華區**崇仁新村**都市更新事業計畫及權利變換計畫案) carries **no 地號** — but the land is user-verified (臺北市萬華區崇仁新村青年段一小段711-3、青年段二小段18地號土地), and it is the same renewal unit as the sibling family 萬華區-崇仁新村青年段一小段-711-3地號等2筆 (recno 1399, 擬訂 2005).

**Two stacked platform mismatches, probed live**:
1. **Section drift** — the PDF-derived section `崇仁新村青年段一小段` returns **0 hits** (village prefix is not part of the platform's section vocabulary); the correct section is plain `青年段一小段`.
2. **Parcel-less case names** — the real cases were found instantly with 青年段一小段/711-3: **09112120** (擬訂崇仁新村…, phase=E 已完工, 22 milestones) + **09112121** (變更崇仁新村…, phase=E, 11 milestones) + 089106 (更新地區劃定) — but their names carry **no 地號**, so the §6.8 parcel guard would reject them on any automated run.

**Resolution** (`scripts/resolve_chongren_exception_20260829.py`): treated as a curated exception — both cases attached to both project caches (09112120→recno 1399, 09112121→recno 1354 via node anchoring; project-level `links.taipei` = raw output per §6.7 general rule), per-case milestones + CASE_NAME + third.ashx implementation attached, every write validated against `DiscoveryResult(**data)` (the §6.10 hazard guard). **未解析-1354 and the 崇仁新村711-3 sibling both resolved → 698/709 (98.4%)**, regen verified: `node links = [['09112121']]` / `[['09112120']]`.

**Generalizable lessons** (candidates for §12 #4 / consolidation):
- 未解析-1354's land cell was empty because the parser couldn't split a two-section land string — the land itself was in the project **name**. A name-derived land fallback for empty land cells would have prevented this class.
- Section-drift (崇仁新村 prefix) + parcel-less names is a shape, not a one-off: the remaining 11 unresolved are likely similar curated-exception candidates.



---

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
| Final run (2026-08-25, post-§18-restore) | ~5-7 h | 07:00 | 373 (full queue) | 10 | 0 | +5 (→63) |
| Matcher-fix W1 (2026-08-25, post `fix-targeted-portal-matcher`) | ~13:00→22:30 | 22:30* | 353 | 252 | 0 | +160 (→223) |
| Matcher-fix W2 (2026-08-25 night, killed early, **no log redirect**) | ~17 min | — | n/a (ledger shows negatives only) | ~1 | 0 | (folded into W3 count) |
| Matcher-fix W3 (2026-08-25/26) | ~23:15→00:19 | queue exhausted | 38 (115 ledger-skipped) | 26 | 0 | (→248) |

\* daytime launch — deadline overridden via `scripts/run_sweep_until.py HH MM`; everything else identical to an overnight run.

Intervals: 06:30/17:00 runs at 3-5 min; final run **calibrated down to 1-3 min
(matches) / 15-45 s (skips)** after a 10-project probe — ~1,491 requests in the
final run with **zero WAF resets**, so the shorter intervals are now standing.
Skips also sleep now (earlier versions bypassed the interval on no-match, a
bulk-crawl-tempo gap). `processed` counts all candidates from the final run on
(earlier runs counted matches only).

### Cumulative coverage

| Metric | Pre-campaign | After 06:30 | After 17:00 | Final (2026-08-25) | Post matcher-fix (2026-08-26) | Coverage |
|---|---|---|---|---|---|---|
| Projects with `twur` | 118 | 183 | **292** | **302** | **581** | 82% of 709 |
| Projects with `milestones_national` | 109 | 183 | **292** | **302** | **581** | 82% |
| Projects with `使用核發日期` | 0 | 13 | **58** | **63** | **248** | 33% |

*(The §18 regression briefly dropped these to 109/109/1 between the 17:00 run
and the final run; the §18 restore brought them back to 292/292/58 before the
final run added +10/+10/+5.)*

*(**Superseded 2026-08-28**: the §6.8 re-merge regen of 2026-08-26 re-ran the
§18 wipe mechanism — live caches now hold **117 / 117 / 6**. Peak-state backups
do not exist; recovery plan in §6.10.)*

`twur` ≡ `milestones_national` since the 06:30 run: the earlier 9-project gap
(118 vs 109) was corrupted caches (gzip bodies saved as replacement-mangled
text by the pre-gzip-fix code path, §8); the backfill re-fetched and repaired
them.

### Remaining work

- **Campaign converged (2026-08-25)** — the full queue was consumed: 373
  candidates processed, 10 new matches, 0 failures. Re-runs are now cheap and
  idempotent (queue ≈ 0; the no-match ledger suppresses re-probing) — useful
  after any matcher improvement to sweep the reject population.

#### Why the ceiling is 302, not 709 — the portal's bimodal Taipei coverage

Year histogram of matched vs unmatched (by 現況 year, final state):

```
            matched  unmatched
2002-03        7      0     ◀ back-filled anchors (view/1-8…)
2004-21      ~10    ~290    ◀ REGISTRY HOLE — approvals never entered
                            into the national registry
2022-26      285     93     ◀ live-feed era (2026 tail = gazette lag)
──────────────────────────
TOTAL        302    407
```

- The 2004-2021 hole (~250-290 projects) is the **portal's genuine boundary**:
  twur.nlma.gov.tw is a separate registry Taipei reports into, not a mirror of
  the city's approved-cases list. Those projects keep complete **Taipei-side**
  data (697/709 have full 階段辦理過程), so the analytical loss is minimal.
- 2026 tail (~15) = gazette lag; a re-run months later picks them up
  (the no-match ledger's `--reprobe-days` makes this automatic).
- Recoverable remainder: §12 count normalization over the strict-reject
  population. Everything else is the portal's recorded boundary.
- **§12 count normalization** — the main remaining coverage lever: a
  recoverable fraction of the ~1,108 strict-rejects in the final run are
  count-drift false rejects (金華段 11 vs 13 筆 pattern).
- **`update_project_cache` now also persists the matched `view.html`** — caches
  are self-contained for future re-parses (parser fixes no longer require
  re-fetching). The CLI's `save_project_cache` already had this behavior.
- Expected no-match tail: projects predating the portal, renamed/re-parceled
  units, and genuinely absent cases — the strict matcher correctly rejects
  ambiguous hits (e.g. 桃源段四小段154, 長安段一小段721 in the 15-sample probe).
  Live-probed 2026-08-25 ~03:15 (通化段六小段218-1, 康寧段三小段821): rejections are
  genuine absences — searched pages contain no trace of the target parcel in
  any notation; no hyphen/之 normalization gap.
- **No-match ledger** (`add-no-match-ledger`, implemented + archived
  2026-08-25 as `2026-08-25-add-no-match-ledger`, spec synced to
  `openspec/specs/fetch-remaining-portal/spec.md`): every
  no-match is recorded to `data/.link_cache/no_match_ledger.json` (atomic
  write, corrupt-file quarantine) and candidates probed within `--reprobe-days`
  (default 14; `0` disables skipping) are excluded at candidate-load time;
  entries clear on match and a run-start sweep drops projects that gained twur
  elsewhere; summary reports processed / updated / skipped. Ledger writes obey
  the single-writer rule like everything else on `.link_cache`. This ends the
  churn where each batch re-probed the same dead heads before reaching untried
  candidates.
- Script deadline is a constant pair (`DEADLINE_HOUR`/`DEADLINE_MINUTE`,
  currently 07:00).
- Dry-run mode (`--dry-run`: first 3 candidates, no sleeps) and
  `--max-projects N` available for sampling before a long batch.

#### §16.1 CORRECTION (2026-08-25/26, post `fix-targeted-portal-matcher`) — the hole was mostly matcher rejects

The ceiling analysis above was **wrong**: it attributed unmatched projects to
portal absence without testing whether the strict matcher could have matched
them. It couldn't — two latent defects rejected nearly everything:

1. **Parcel extraction** read the *last* enumerated parcel from land strings
   ("599、599-1、…、623地號" → `623`), guaranteeing title mismatch; the anchor's
   named first parcel (`599`) is what pages are titled after.
2. **Count comparison** pitted text `'27'` against parsed int `27` — always
   unequal, rejecting every counted candidate even with the right parcel.

Only ~8 of 363 candidates could pass as written. Failures printed as ordinary
no-matches, so the rejection looked like absence. Motivating case:
松山區-寶清段四小段-599地號等27筆 — searchable at view/30, first result, yet
unlinked (§0 row).

Post-fix sweeps across three windows (see run log above; single writer
throughout, 0 failures, viewer regenerated per window — final emit
2026-08-26 00:19):

| Metric | Pre | Post | Δ |
|---|---|---|---|
| Projects with `twur` / milestones | 302 (43%) | **581 (82%)** | +279 |
| 使用核發日期 | 63 | **248** | +185 |

New links by anchor era: **2004–21: 230 · 2022+: 49 · 2002–03: 0** — the
"registry hole" cohort supplied 82% of recoveries. Revised boundary statement:

- 2002–03 back-fill anchors: fully matched since the original campaign.
- 2004–21: partially covered all along; the *genuine* remainder is only what
  post-fix probing still rejects — **127 ledger negatives** recorded tonight.
- 2022+ live feed: near-saturated; residual tail is gazette lag re-picked
  automatically via `--reprobe-days`.

State after W3: **128 projects without twur**, nearly all ledger-suppressed
recent negatives rather than unprobed work; they re-enter after the 14-day TTL
or a forced `--reprobe-days 0` pass. Truncation notes fired on 6 searches where
>8 results existed (W1, `--max-probe` default 8). 寶清段599 was linked via the
production path right after W1's deadline to close this section's motivating
case. Next levers: §12 #4 count normalization over remaining strict-rejects;
§12 #3 consolidation moves this matcher library-first.

#### Post-W3 residue census (2026-08-26 00:19 emit)

The 128 twur-less projects by anchor era (census over `viewer/projects.data.js`):
**2004–21: 95 · 2022+: 33** — even post-fix, the hole cohort dominates the
remainder; these are ledger negatives re-probed once per TTL window, and the
2022+ tail is largely gazette lag rather than absence.

Separately, the **18 Taipei-unresolved** projects (§12 #12; no `links.taipei`
at all) break down by cause: **parcel-count drift** between case name and
gazette (臨沂段三小段412等**12筆(原11筆)** · 復興段一小段3等**2筆(原5筆)** ·
玉成段三小段711-3等**27筆(原24筆)**), and **unparseable land-core keys**
(內湖區東湖段一小段「地號等?筆」; 萬華區崇仁新村 village-style naming → the
literal `未解析-1354` row). 9 of the 18 are *also* twur-less. The same
count-tolerance logic that recovered the portal side (§16.1) applies here —
this census is the evidence base for the §12 #4 / §5 open row.

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
3. **Hardening (§12 hardening item) — `[RESOLVED]` (2026-08-25)**: `regenerate_viewer` now
   redirects child stdout/stderr to `data/.link_cache/regen_log.txt` (append)
   instead of `capture_output` pipes and raises the timeout 300 s → 1800 s.
   Not deadlock-class (see corrected #1) — the point is that an orphaned child
   can always finish writing, stays observable in the log, and legitimate slow
   regenerations don't time out into silent "viewer not refreshed" states.
4. **Corruption signature**: a cache/view file starting `\x1f\xef` (mangled gzip
   magic) is unrecoverable text-mangled binary — delete and re-fetch, never parse.

### Addendum — curated-mapping direct edits (`data/taipei_case_ids.json`)

Raised during the 2026-08-24 session: "is it OK to edit the fallback mapping
directly, without root-causing first, while `fetch_remaining_national_portal.py`
was running until 22:00?" Answer, now on record:

1. **Race safety**: the fetch script NEVER reads `taipei_case_ids.json` — its
   candidates come from `viewer/projects.data.js`. The only reader is discovery
   (`load_fallback_mapping`), which runs inside the script's final
   `regenerate_viewer`. So a mid-run edit cannot race the campaign's writes.
2. **But it is not consequence-free**: the final regenerate re-runs discovery,
   which reads the mapping — a mid-run edit deliberately changes what
   not-yet-cached projects resolve to. In this case that was the point: the
   corrected entry (view/262) stopped the regenerate from re-poisoning the cache
   with view/1042.
3. **Root cause WAS established before editing** — the edit followed the trace
   (wrong twur → `land_core` fallback lookup → stale hand-written entry), it was
   not a blind data patch. The fix order was: trace → fix mapping → repair cache
   (§6.6).
4. **Open provenance gap**: nobody knows where the bad entry came from
   (view/1042 + case_id "10421234" reads like a hand-typed view_id with a
   placeholder; POC-era manual curation, no audit trail — the file has no
   generator or validation).

**Rules for curated-mapping edits**:
- Verify the replacement view_id against the live view page (title + parcel +
  count) before writing — done for view/262 via `view_page_matches`-equivalent checks.
- Record before/after in this doc (§6.6/§16 do).
- The file is hand-curated with no validation: treat every entry as
  guilty-until-verified; the long-term fix is the §12 consolidation library-first
  consolidation (single lookup implementation) so curated entries carry
  provenance comments.

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
Keep `.link_cache_backup_20260824` until the §12 consolidation consolidation makes the
index self-sufficient (never delete as scratch).

### Rules going forward

1. **Reconstructibility precondition**: before deleting/regenerating a cache,
   enumerate every field and prove it is reconstructible from the inputs being
   kept. If not, the "cache" is a source — back it up *and* diff coverage after.
2. **Fold campaign outputs into the index at write time**: targeted-fetch
   mappings must land in `portal_index.json` (or a dedicated mapping store), so
   the index reflects reality instead of lagging it — merges naturally into the
   §12 consolidation library-first consolidation (`--links-targeted`).
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
✅ ~~§18 recovery FIRST~~ done (2026-08-25 02:17): 183 national links merged
   from .link_cache_backup_20260824; post-check 292/292/58 reached (§18)
                                                      │
                                                      ▼
✅ fetch_remaining campaign — [CONVERGED] 2026-08-25 (§0/§12-converged/§16): full queue
   consumed (373 processed), final state 302 twur / 302 milestones / 63 使用核發;
   no-match ledger suppresses re-probing (re-runs are cheap + idempotent)
                                                      │
                                                      ▼
⬜ count-normalization OpenSpec change — remaining coverage lever over the
   strict-reject population (§16 ceiling analysis); strict matcher rejects
   count-drift pages; rejects retry, so start ≠ finish
```

---

*Sources (session provenance for the entries above): §6.6 + §16 (06:30/17:00 runs) from the 2026-08-24 session; §17 concurrency incident from the 2026-08-24/25 evening session (curated-mapping addendum 2026-08-25); §18 regression from the 2026-08-25 overnight refresh monitoring; §19 sequencing from the dd-taipei-implementation-data pre-change exploration (2026-08-24/25); §6.7 over-return + phase-A + no-match-ledger rollout from the 2026-08-25 sessions; §6.8 pollution fix + §6.9 snapshot emission fix from the 2026-08-26 session; §6.10 coverage audit + second wipe + the 2026-08-28/29 recovery campaign (retry → view.html backfill → overnight sweep → post-deadline pass → quick wins → view-link resolve) from the 2026-08-28/29 sessions. All counts measured live from data/.link_cache + iewer/projects.data.js.*

### 6.12 Session 2026-08-29 (evening) — 崇仁新村 national side + viewer label plumbing

User screenshot review of 未解析-1354 surfaced four gaps; two fixed now, two deferred to the family-merge decision:

1. **National side missing** → **fixed (curated exception #2)**: twur title-search 崇仁新村 returns exactly one candidate, **view/18** — title 擬訂臺北市萬華區青年段一小段711地號、二小段18地號**(原崇仁新村)**… (the portal renamed the village to parcel notation); its 相關連結 → our case 09112120; 推動歷程 核定 94.02.24 = recno 1399's node date, 第一次變更核定 97.01.02 = recno 1354's — one unit, one view, both records. Attached view/18 + 7 national milestones (incl. 使用核發 97.01.03) to both caches (scripts/attach_national_chongren_20260829.py, DiscoveryResult-validated). Strict matcher would reject this page (title has 711地號, no 之/hyphen sub-parcel form, no 筆 count) — same exception class as the Taipei side.
2. **相關連結 label showed 里程碑 22 筆 instead of the case name** → **fixed (plumbing, corpus-wide)**: ttach_links_to_projects now emits links.candidate_names (harvested names never reached the viewer before), and uildRelatedLinkLabels consults candidate_names before the case_milestones fallback (structural test added). Suite 238 passed.
3. **Title/left-list shows the literal 未解析-1354** → deferred: proper fix is a family merge — recno 1354's PDF land cell is empty (land embedded in its name tail); a cleanse repair (land-from-name fallback) + PDF pipeline re-run would merge 1354 into the 崇仁新村711-3 family (one project, 2 recnos, both cases node-anchored). Changes project identity — needs a decision (§12 #5 cross-PDF keys).
4. **09112120 not a virtual node in 未解析-1354's graph** → deferred with #3: compute_landcore_similarity = 0.0 (parcel-less case name vs land core; 未解析-1354's own land_core was just 萬華區) → below the 0.7 ghost threshold. Post-merge it becomes a real anchored node — no virtual node needed, and forcing one now would double-display against the sibling family's real node (§6.8).

State after: **resolved 698/709 (98.4%) · twur 563/709 (79.4%) · 使用核發 244 · 相關連結 unnamed 0**. Remaining 11 unresolved: curated-exception candidates (§6.11 shape).

**§6.12 addendum — virtual nodes fixed**: 09112121 (and cross-family 09112120) also missing as virtual nodes — root cause: the ghost gate (attach_links_to_projects) requires landcore similarity ≥ 0.7 via xtract_landcore_from_case_name, which returns empty for parcel-less case names; the lif attributed_case_ids / twin-bridge fallbacks were unreachable when a case name existed (branch-structure hole). Fix: cases listed on the project's own national view page 相關連結 are portal-verified — new DiscoveryResult.view_verified_case_ids field exempts them from the similarity gate (scripts/resolve_via_view_links… writes it going forward; both 崇仁新村 caches marked). Regression test 	est_view_verified_orphan_bypasses_similarity_gate (suite 239). Post-fix: 未解析-1354 renders virtual node 09112120 (擬訂, node_date 2005-02-24); 崇仁新村711-3 renders 09112121 (變更, 2008-01-02) — dates match the portal 推動歷程 exactly. Remaining caveat: each unit renders its sibling's case as a virtual node (cross-family double-display, §6.8) until the family-merge decision (§6.12 item 3) is taken.


### 6.13 Session 2026-08-29 (evening) — 崇仁新村 Family Merge + PDF-Pipeline Date-Anchoring Fix `[RESOLVED]`

User approved the deferred family merge (§6.12 item 3). Root cause of the split: PDF extraction glued recno 1354's 地號 cell onto its 案名 (land cell empty) → land-core unparseable → `slug_for` fell to `未解析-1354` and the record never clustered with its 擬訂 family (recno 1399).

**Fixes**:
1. `urtpe/cleanse.py` — land-from-name recovery: when the 地號 cell is empty, split the trailing `臺北市…地號(土地)?` fragment off 案名 (rfind 臺北市), re-parse it (count inferred from land-token separators: 711-3、青年段二小段18 → 2), flag `地號自案名尾端復原(地號欄黏入案名)`. Unit test `test_land_recovered_from_name_tail_when_land_cell_empty`.
2. **PDF-pipeline date-anchoring bug (corpus-wide)**: `_match_case_by_date` received raw ROC dates (97/1/2) from the PDF pipeline → `_iso_date` can't convert → anchoring silently degraded to positional for EVERY PDF-pipeline run (§6.6's verified anchoring only ever ran via `--from-js`, whose loader restores ISO dates). `_match_case_by_date` now normalizes ROC/ISO/slash-Gregorian. (`--from-js` regens were unaffected — loader restores ISO.)

**Result**: recno 1354 clusters into the 擬訂 family → **one project 萬華區-崇仁新村青年段一小段-711-3地號等2筆, recnos [1399, 1354]**, both cases node-anchored by date (1399→09112120, 1354→09112121), no virtual nodes, no double display; 未解析-1354 label gone (stale cache dir removed; content preserved in `.link_cache_backup_20260829_quickwins`). Coverage guard: 698/563/244 over 709 ≡ 697/562/243 over 708 (de-duplication, rates unchanged 98.4%/79.6%). Suite 240 passed.


### 6.14 Session 2026-08-29 (night) — Category 1/2/4 push plan (pre-OpenSpec)

Remaining after §6.11-6.13: **11 unresolved (16 records) · 146 twur-less (ledger negatives) · 相關連結 unnamed 0**. The 崇仁新村 curated-exception approach (diagnose drift → corrected live probe → independent identity verification → validated attach) has been applied only to 崇仁新村; the other 10 unresolved projects are classified by hypothesis only. Push plan (no OpenSpec change required for curation):

1. **Category 1/2 — diagnose-and-attach over all 11**: derive alternate queries from 案名 parcels / sibling members (anchor-parcel drift: 華中段247 → 201-2、352; count-drift/unparseable → name parcel 東湖段20-9; section drift → 木新路三段); verify identity via case-name tokens, portal 相關連結 cross-refs, or the project's own view page; attach with `DiscoveryResult(**data)` validation. For twur'd cases with empty `second.ashx` payloads (臨沂412, 玉成253-1): diagnose whether the platform holds no timeline (linkage complete → resolve).
2. **Category 4 — 相關連結-identity sweep**: for twur-less projects carrying `city_case_ids`, title-search the national portal by section (the view/18 mechanism), fetch ≤3 candidates, attach when the page's 相關連結 intersects our known case_ids (portal-proven identity, no matcher loosening).
3. OpenSpec change (§12 #4 count normalization + consolidation) remains gated for the *systemic* matcher fixes and the ~1,108 strict-reject re-sweep.

**§6.14 results — BDD/TDD curated resolve (first pass)**: scripts/curated_resolve.py (helpers: classify_failure / derive_queries / ttach_cases, 11 BDD scenarios in 	ests/test_curated_resolve.py, suite 251→255). Live flow over the 11: **+3 resolved (東湖段20-9 +3 cases; 華中段247 +7 cases — anchor-parcel drift confirmed, alternate-query probing found the 201-2、352 family; 實踐段641 +09009032 via byte-identical 案名) → 700/708 resolved (98.9%)**. Remaining 8: 吳興163-2's 5 dropped cases are same-整宅-complex candidates (parcel drift 163-2 vs 247) — **need human verification before attach**; 河堤399 / 吳興330 blank-search; 懷生928 / 萬華519-2 partial title hits need verification.


### 6.15 Session 2026-08-29 (night) — §12 #1 Coverage Guard Landed `[RESOLVED]`

The standing "do first" item from §12 (unbuilt through two wipes) is now code:

- **`urtpe/coverage.py`**: `snapshot(root, project_ids)` reads per-project flags (resolved / twur / national / 使用核發) from sanitized-id caches; `diff` detects flag True→False regressions on the pid intersection (lost/gained pids — family merges — reported informationally, not raised); `coverage_guard(root, project_ids, strict=True)` context manager.
- **CLI wiring**: `urtpe.cli._run` wraps both discovery lanes (fallback + Playwright) in the guard — a cache-wiping job now aborts BEFORE `write_projects_js`, closing the §17/§18 "viewer emitted on regressed state" failure mode.
- **Alert trail**: `data/.link_cache/coverage_alerts.jsonl`, one JSON line per regression event (timestamp + pid → dropped flags).
- **BDD**: 8 scenarios in `tests/test_coverage_guard.py` — snapshot counting, monotonic pass, injected wipe raises with pid+flag, family-merge lost-pid reported-not-raised (崇仁新村 shape), strict=False collects, alert trail only on regression. Suite **259 passed**; verified live on the full 708-project cache-first regen (guard silent on the healthy state).

Remaining §12 order: twur sweep (相關連結-identity) → §12 #2 chimera emit-fix → §12 #3 consolidation (OpenSpec change).

**§6.14 step-2 results — 相關連結-identity sweep pass 1**: 140 attempted, **62 attached, 0 failures** (44% hit rate) → **twur 624/708 (88%)**, 使用核發 pending regen. Log: data/sweep_identity_20260829.log (built-in _Tee — no more unlogged runs). User-spotted miss (吉林段676 → view/75): the portal returned it at position 3-8 depending on load; MAX_PROBE=3 truncated it. Fix: MAX_PROBE → 8 (identity check is 1 GET + regex, cheap). Pass 2 = re-run; also verifies pass-1 attaches under the coverage guard.


**§6.14 step-2 final — identity sweep pass 2 (MAX_PROBE 3→8 fix)**: 78 attempted, **+13 attached** (the view/75-class deep-position matches the user spotted; 0 failures) → **twur 637/708 (89.9%), 使用核發 299 (42%)**, viewer re-emitted under the coverage guard (silent, 0 regressions). Remaining 65 no-match = pages where the portal's 相關連結 genuinely doesn't reference our cases — the §6.11-shape residual (title-search candidates exist but identity unproven); re-probe candidates after the 14-day TTL or via §12 #4.

**§6.14 implementation note**: E1/E2/E3 implemented (openspec §7, tasks 7.1.x-7.3.x, suite 288): 概要-track anchoring + single-段 extraction + ghost node_date fallback; case_schedules captured/emitted (search + schedule_from_top); viewer schedule badges + never-approved reason; ledger annotated with the live classification (15 never-approved excluded from re-probes, 50 recoverable re-enter) — ilter_candidates now skips never-approved beyond TTL.


### 6.15 (cont.) — schedule top-up complete + follow-ups verified (2026-08-30)

Top-up sweep done: **623 caches updated · 1,923 top.ashx calls · 0 errors** (32 min). Viewer re-emitted under the coverage guard. Follow-ups verified:

1. **Curated-resolved names preserved** — all curated projects keep their candidate_names; schedules gained (華中段247: 7/7 mixed 已失效+已核准; 東湖段: 施工中; 實踐641: 施工中). Note: 臨沂412/玉成253-1 have empty city_case_ids — their national pages (view/1172, view/856) carry **no 相關連結 links at all** (correcting the earlier §6.10 note that they "already carry their page's case links"); their Taipei case_ids remain in the manual-lookup bucket.
2. **71 twur-less fully explained**: 15 never-approved (ledger-annotated `twur_class: never-approved`, excluded from re-probes) · 50 recoverable (has-approved/mixed — re-enter after TTL or via 案名-fragment keys) · 6 no-cases. Schedules captured for the population; **21 projects will render the 未核定 chip** in the left list; 641/708 projects emit case_schedules. `schedule_from_top` + `classify_case_outcome` + `project_twur_class` implemented with tests (suite 288).

Final scoreboard: resolved 700/708 (98.9%) · twur 637/708 (89.9%) · 使用核發 299 (42.2%) · 相關連結 unnamed 0 · records 12/1,419 under the 8 unresolved.


**§6.15 addendum — add-coverage-regression-guard change removed (2026-08-30)**: the standalone OpenSpec change was redundant — its scope (snapshot counters, abort + alert on decrease) shipped as task group 6 above (urtpe/coverage.py + CLI wiring + 8 BDD scenarios). One idea from its delta not yet implemented, kept for the consolidation backlog: **labeled snapshot history** — persist every pre/post snapshot pair to data/.link_cache/coverage_snapshots.json with a job label (the current guard only writes the alert line on regression). Cheap to add during 12 #3 consolidation.


**§8 implemented (2026-08-30) — chimera emit fix (facts §12 #2) [RESOLVED]**: attach_links_to_projects now fills each node's links.milestones_taipei from its anchored case's own case_milestones timeline (fallback: project-level merged dict for legacy caches without per-case data). Verified on the §5 motivating family (254): node 1219 emits 核定 2012/08/27 (was 2016/08/23 chimera), node 1037 emits 2016/08/23, node 991 emits its 權變-only timeline (權變核定 2017/04/13 — the case genuinely has no 核定日期). Project-level merged dict + milestones_source provenance unchanged (construction chain unaffected). Corpus effect: the 319 multi-核定 families now render per-node truth. Spec delta: viewer-milestone-timeline Per-node milestone attribution (MODIFIED). Suite 290. Closed the standing §12 #2 item; remaining §12 order: #3 consolidation (OpenSpec change) → #4/#5.


**§6.16 Session 2026-08-31 — Virtual-node ordering + chain edges implemented (add-virtual-node-ordering-and-chain, all 7 tasks) [CLOSED]**

User-designed (D12 in the viewer change design.md): same-date virtuals sort row-by-row by **case_id ascending** (real compared via anchored case_id; empty-key real first) and consecutive virtuals chain with a **dashed virtual revision edge** (attempt succession). Implementation: pure helpers extracted in app.js between D12 markers (ffectiveCaseKey / compareClusterMembers / irtualChainPairs + 
unScenarios), node-tested via a pytest harness (tests/test_virtual_node_ordering.py — 6 JS-executed scenarios + structural assertions in test_viewer_labels.py). Track guard added during verification: 吉林段676's 概要/計畫 same-day pair stays unchained (parallel applications). Live verification on real clusters: 吉林段1021 chains 09902261→10201171 (attempt pair); cross-track pairs skipped per spec. Suite **299 passed**. Hard-refresh renders the ordering + dashed chain edges.


**§6.16 addendum — badge-strip append (2026-08-31 exploration + refinement)**: user-designed variation beyond row ordering — for same-date virtual nodes, only badges carrying 區段標籤 and 排程 append **next to the anchored milestone\'s 北 badge** on the real node strip (virtual circles keep dashed shape + tooltip; no duplicate 北). Distinction via 區段 + status on each appended badge; strip growth bounded by 區段-carrying virtuals. Refinement: **已核准 is the default focus state — its badge is skipped** (only 已駁回/施工中/自行撤回/已失效/審查中 render). Implemented via scheduleBadgeText filter in all three render surfaces (virtual label, real-node label, 相關連結); structural test added. Canonical capture: viewer change design.md D12 Amendment 2 + tasks 7.2.7; spec delta viewer-related-links badge list updated.


**§6.16 addendum 2 — spec-delta sync audit (2026-08-31)**: audit of the D12 exploration capture against the change\'s spec deltas found one unsynced behavior: the badge-strip append (區段 + 排程 same-date virtual badges next to the anchored 北 badge, 已核准 default-skip) existed only in design.md D12 Amendment 2 + tasks 7.2.8 + code. Added as an ADDED requirement to the change\'s virtual-milestone-nodes spec delta (3 scenarios: 區段-carrying append / no-區段 stays on row / 已核准 renders no badge). Ordering + chain-edge requirements are correctly homed in the separate change add-virtual-node-ordering-and-chain.


**§6.16 addendum 3 — duplicate change removed (2026-08-31)**: openspec change split-track-stage-derivation (per-track stage derivation for combined-track nodes) was a duplicate of task group 10 in viewer-enhancements-and-orphan-case-anchoring (same 507-anchor derivation, same spec deltas data-cleansing + viewer-milestone-timeline). Removed; the canonical home is viewer change tasks 10.1-10.4.


**§9 implemented (2026-08-31) — 603 follow-ups (D12 Amendment 3) [CLOSED]**: (9.2) attach emits links.taipei case_id-ascending — corpus 91/564 unsorted normalized at the source; (9.3) renderDetail timeline now family-wide case_id interleave (cluster bands/chips preserved via membership map); (9.4) gazette printing-anomaly review flag — printed 擬訂 vs platform 變更 case → flag 階段與平台案件狀態不一致(公報X/平台Y), stage stays faithful. Verified on 603: 相關連結 order == graph row order (09511210→09511211→09511212→09511213→09511214→11007261→11007262→11501016), node 920 carries the flag. Suite 303. (9.5 accepted.)
