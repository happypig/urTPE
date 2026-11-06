# Project inspection — Batch D · collected 2026-11-04

Findings from the post-Batch-B+C session (2026-11-04, payload at `47453f9`:
1,442 records / 682 projects, the corpus converged after waves 1–3 of the
Batch B + C plan). Fifteen findings, all measured (D4–D15 added 2026-11-05). The board follows the
`docs/inspection-batchBC.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

**Open items: none** (2026-11-06). The user **agreed** the rule (D9f-1)
and added the 168 list's `MEMO` as a fourth source (D9f-2). Both are
**implemented** (step 9a) and the ingest they unblocked **succeeded**: the
2026-10-28 gazette is ingested, `編號 3`'s date is recovered, and the corpus
stands at **1,444 records / 682 projects**.

The three coverage questions (D18) are **answered and proved**:
`scripts/probe_three_coverage_proofs.py` re-derives every number from the
emitted files. **7** projects carry no case id (so they are in neither list);
**0** recno sit in no project (the partition is total and disjoint); **13**
nodes carry no 北 badge, and **all 13** are named by the flag that says why.
Proving them exposed **two gates that did not hold** — the `--from-js` path
had no partition gate at all (D18b), and the census gate checked the
pre-ledger partition (D18c). Both are **fixed**.

The MEMO is **measured and cannot serve as a date source** — it is empty for
all 33 cases where the PDF and the platform disagree, and it is a different
date (the 核定公告) where it is present — so it joins the rule as a **flag**.

Every step of D9g is done. The consolidated execution order is D9g.

**Working-tree state (2026-11-05).** This board and the `probe_*` scripts are
committed (`87b79d0`, `caa2159`, `43cb9bf`), but not pushed: origin/main is at
`6457de7`. The D9 evidence files (`data/p168_*.json`) are gitignored, so the
scripts are the only reproducible record. D13–D15 came from the peer session
graph-order-issues (HEAD then `16b418a`, after the D5 ingest `28d1eb5`).

## D1 — the orphan `milestones_national` key holds Taipei data (name wrong, data right)

**Finding.** On every orphan node, the payload's `milestones_national` dict
carries **Taipei-platform** milestones, not national ones. The date values are
correct; the key name is false. Verified three ways:

1. **Code path.** `urtpe/links.py:3287` builds the orphan's
   `milestones_national` from `disc.case_milestones[cid]`, and
   `case_milestones` is filled **only** by `fetch_taipei_milestones_api`
   (the `Get_project168_second.ashx` call; the discovery loop, the view
   absorb and the refresh path). No national page data enters it.
   The genuine national data (twur 推動歷程, ROC-dot dates) sits one level
   up at project-level `links.milestones_national`
   (`extract_tuidui_history_from_view`).
2. **Date shapes.** The orphan dicts carry slash-Gregorian dates
   (`2011/03/08`). The real national portal emits ROC dots (`100.03.08`).
3. **Live probe** (2026-11-04): `Get_project168_second.ashx` for
   09906012 / 10202021 / 10012111 reproduces the payload's orphan dicts
   field-for-field (`outline_ok_date` → 概要核准日期， …).

**Corpus effect measured on the trace set** (雅祥492's 09906012 + 10202021,
文德231-3's 10012111, 寶清599's 09303272, 南海段364's 09210162): the date
values are right in every case — `_ghost_node_date`
(`urtpe/links.py:2298`) reads 概要核准日期 from the Taipei ashx, and the
platform really holds it. No value is misinterpreted.

**Risk.** A future consumer that trusts the key name joins Taipei data as
if it were national (the viewer reads it at `viewer/app.js:906` for the
virtual node's badges; the 國/北 distinction is exactly what the key
claims to carry). The G2/`case-record-join` dual-id-space lesson applies:
an id-space (or here, a source-space) mismatch read as truth.

**Form:** openspec change (payload schema rename on `orphan_nodes`; the
viewer read site updates in the same change; a load-side alias keeps
already-emitted `projects.data.js` files rendering — `--from-js` repair,
the `emit-stage-index` precedent). Spec surfaces: `virtual-milestone-nodes`
(payload field requirement) + the viewer label spec.

| Key on an orphan node | Actual source | Correct? |
| --- | --- | --- |
| `milestones_national` | Taipei ashx (`case_milestones`) | **name wrong, data right** |
| `milestones_taipei` | twin-bridge / source-map merge | right |
| project-level `milestones_national` | twur view page 推動歷程 | right |
| project-level `milestones_taipei` | merged taipei milestones | right |

## D2 — ghost dates read the family's 概要核准, and the row order could read dates (revisit D12)

Two related findings from the same session's measurement.

### D2a — `_ghost_node_date` echoes the family 概要 onto plan cases

`_ghost_node_date` (`urtpe/links.py:2298`) walks
核定日期 → 權變核定日期 → 概要核准日期 with **no track test**. A 計畫/權變
case that never won approval (已駁回/自行撤回/已失效) still carries the
family's 概要核准日期 in its city record (the city echoes the 概要's
approval into every descendant case's 階段辦理過程 — verified live on
吉林717's triple: `outline_ok_date = 2007/01/30` on all of
09506200/09506202/09608051), so the ghost node is **dated with an approval
that is not the case's own event**.

Measured shapes:

- 吉林717's triple: 概要 [已失效] 2007-01-30, 計畫及權變 [已駁回] node_date
  2007-01-30 (its own event is 申請計畫 2013/11/18), 計畫 [自行撤回]
  node_date 2007-01-30 (own event 申請計畫 2008/12/31).
- 雅祥492's 10202021 [已駁回]: node_date = the 概要's 2011-03-08.
- Corpus: **25 cross-case member pairs share one date**; 18 of them carry a
  terminal schedule — the same 概要核准 echoed, not independent events.
  Inverse check: **0 case_ids carry 2 distinct node dates** (case_id is a
  strict key; date is not).

**Fix:** `_ghost_node_date` becomes track-aware. A plan-track case skips
概要核准日期 (leave the node undated → renders `(未核定)`, the honest
label — the 寶清375 shape). A 概要-track case keeps 概要核准日期 as its own
approval. Re-measure after: the 25 same-date pairs drop to ~7 (genuine
same-day serials only); the "dead-track-leads" inversions disappear from
the 51-project list (D12's known cost, `docs/viewer_sort_rules.md`).

**Form:** openspec change (`virtual-milestone-nodes` delta: ghost dates
read only the case's own track approval; payload re-emit).

### D2b — sort by distinct approval date (own-event fallback) instead of case_id

The user's question (2026-11-04): can rows sort by a distinct approval
date — falling back to the application date when no approval exists —
instead of case_id? Measured end to end with the refined key:

- Key: 概要-track cases read 概要核准 → 申請概要 → 申請計畫; plan-track
  cases read 核定 → 權變核定 → 申請計畫 → 申請權變 → 申請概要 (**never** the
  echoed 概要核准); ties and the undated tail break by case_id.

| | D12 (case_id first) | date-first with own-event key |
| --- | --- | --- |
| Cross-case same-date ties | 25 | 18 (all genuine same-day events; case_id separates) |
| Undated members | 30 | 21 |
| Order pairs vs case_id | — | 106 reorder |
| Non-chronological reads | **51 projects / 95 pairs** | **~0 by construction** |
| 相關連結 order match | by construction | no (cosmetic; the list renders separately) |

What it fixes: the 95-pair non-chronology (the 51-project list) dissolves;
same-day serial pairs read in approval order; the 9 row-between 概要
orphans land at their date position.

What it costs (all placement rules, not data):

1. **Mixed event kinds on one axis.** A dead attempt renders by its
   application date, before the approval that came years later. The row
   must name its kind: an application-dated node keeps `(未核定)` beside
   the date.
2. 21 undated members render last, by case_id (same tail as today).
3. The 相關連結 order guarantee (D12 Amendment 3) no longer holds in the
   graph; the pipeline-side `links.taipei` ascending emit stays.
4. Real nodes date by the gazette print today; a re-date moves a row.
   Optional mitigation (do not bundle): date real nodes from the case's
   own data2 核定 too.
5. **D12 is a recorded user decision in the spec**
   (`virtual-milestone-nodes`, `openspec/changes/archive/2026-09-02-add-virtual-node-ordering-and-chain/design.md`
   D12 + Amendment 3). Overturning it needs the change + the re-measure
   recorded on the board, with `docs/viewer_sort_rules.md` rewritten
   (its "do not sort by date" section becomes the history).

**Dependency: D2a first.** D2b's key reads the same fields D2a fixes. Run
the attachment fix, then re-measure the sort key on the re-emitted payload
(the table above was measured on today's payload; the 18 ties and 21
undated will move — expect fewer, since undated plan ghosts stop borrowing
the echo and get the application fallback instead).

**Form:** one openspec change covering D2a + D2b (same re-emit, same spec
surface `virtual-milestone-nodes` + viewer sort spec), test-first.

**Decided (user, 2026-11-05):** swap the row sort from case_id first to date
first (the own-event key above). D2a still runs first; the re-measure after its
re-emit is recorded in the change, not re-asked.

## D3 — the 國 badge: a key bug, and the two extra routes the user asked about

**Question (user, 2026-11-04).** Can 國 also attach to a 北 node by (a) the
same case id on the national page `view/<id>`, or (b) the same name as the
recno or its 北 case?

**Today's two sources** (`getNodeMilestoneBadges`, `viewer/app.js:176`):
A — a national approval label binds the node by stage + track, with a date
tie-break (`bindNationalLabels`, `viewer/app.js:151`); B — the node's first
case is in `view_verified_case_ids`. Measured over 622 twur projects and
1,357 北 nodes: 1,032 carry 國 (A only 356, B only 39, both 637); 325 do not.

### D3a — `nationalLabelKey` never binds a second-or-later 變更 (bug)

`nationalLabelKey` (`viewer/app.js:32`) builds `` `變更(${raw}次)` ``, so the
label 第二次變更權利變換計畫核定日期 keys to `變更(二次)`. Every payload node
spells the stage `變更(第二次)`. Run with the shipped helpers in a VM over the
payload:

| National approval labels | Count | Bound |
| --- | --- | --- |
| 擬訂 | 996 | 941 |
| 第一次變更 | 475 | 449 |
| 第二次 and later 變更 | **223** | **0** |

Example: 吉林717 node 762 (`變更(第二次)` 權利變換, 2019-10-02) and the
label 第二次變更權利變換計畫核定日期 = 108.10.03 (1 day off) — no 國 today.
With `` `變更(第${raw}次)` `` the corrected key gives **147 more nodes 國**
(1,032 → 1,179). Of their 157 new labels, 142 bind within ±1 day of the
label date; 15 bind as the single stage+track candidate with a drifting date
(the C1 rule). The board's C1 count "327 labels with no stage+track node"
included these labels; it read the bug as missing data. The code departs
from its own comment at `viewer/app.js:24-25` ("第二次→變更(第二次)"), so
this is a direct fix with no spec delta. No other approval label fails the
key: 0 national labels with 核定 or 核准 parse to null.

**Form:** direct `fix:` in `nationalLabelKey` plus a test on the 吉林717
node 762 shape (`tests/test_viewer_labels.py` runs the helpers in a VM).

**DONE (2026-11-05).** Fixed at `d8a63ca` ("nationalLabelKey spells
second-or-later 變更 as the nodes do"), test at
`tests/test_viewer_labels.py:560`. Direct `fix:` as proposed — no openspec
change, no re-emit (viewer only). The `變更(${raw}次)` spelling above is the
pre-fix state; `viewer/app.js:32` now reads `` `變更(第${raw}次)` ``.

### D3b — the two extra routes add almost nothing

After D3a, 178 北 nodes carry no 國:

| Cause | Nodes |
| --- | --- |
| The national page has no label for this stage — last updated before the approval (stale page) | 86 |
| The national page has no label for this stage — updated after the approval, still silent | 76 |
| The page's label bound a sibling node (the gazette has more rows of this stage+track than the page has labels, e.g. 吉林705's 1311 and 1370 against one 第一次變更事業計畫 label) | 12 |
| A label exists, the date tie-break refused (3 labels, 0 or 2+ survivors) | 4 |

(a) **Same case id on `view/<id>`.** The page's 縣市政府案件連結 lists one case
in 436 of 622 projects, two in 109, three or more in 23, and none in 54. So
this route confirms about one node per project, and it already is source B.
It adds **0** of the 178 nodes. The page list is also not clean: 6 pages link
a foreign case — 中山254's page links 辛亥163's 10202065, the id the C3
gate rejected.

(b) **Same name.** The page's link labels name only the linked cases, and the
page title names the first 擬訂 case, which already has 國 by label. Name
matching adds **0** nodes. A third reading — take stage and track from the
北 case's own city name instead of the gazette stage — touches only the 3
refused labels; it resolves 2 (吉林185, 市府247), and in 吉林185 the pick is
4 years from the label date. Not worth a rule.

**Conclusion.** Neither route closes the gap. The gap is national data the
page does not hold (162 nodes), labels the page gives to a sibling row (12),
and real ties (4). Fix D3a; keep A and B as they are.

## D4 — list badges, filters and two edge rules (user request 2026-11-05)

Four viewer proposals from the user, measured on the same payload
(scratchpad `ux4*.py` / `ux4*.js`; item 3 and item 4 run the shipped
helpers in a VM).

### D4a — 使照 is drawn as national when the city holds the date (bug)

The user asked to remove the edge between a recno node and 使照核發, because
the urotpe api already gives 建照/開工/使照. The edge exists because of a bug.
`buildConstructionChain` (`viewer/app.js:358`) sets
`nationalHit = !!(natLabel && national[natLabel])`, so 使照 joins the national
group whenever the national page has 使用核發日期, even when
`milestones_taipei` has 使照核發日期. The `history-graph` spec makes the
national group "使照 filled solely from 使用核發日期" (`openspec/specs/history-graph/spec.md:81`,
and `taipei-implementation-data` "National-only 使照").

| Edges into the 使照 event | Today | Spec-correct flag |
| --- | --- | --- |
| 現況 recno → 使照 (green) + dashed 開工 → 使照 | 288 | 1 (national only) |
| owning recno → 使照 + dashed 開工 → 使照 | 0 | 2 (使照 carried by another case) |
| solid 開工 → 使照 (one city case) | 42 | 327 |

- 287 of the 288 national-flagged events have the city date too; in 21 the
  two dates differ (e.g. 吉林811 city 2013/09/11, national 102.11.12) and the
  event shows the city date under a national label today.
- The flag also drives the 國 badge on the event (`viewer/app.js:1332`). The
  spec keeps 國 on a 使照 "corroborated by the national portal". The fix
  splits the flag: `national` (source group: no city date) and a separate
  corroboration flag for the badge, so the 287 keep 國.
- The flag fix alone leaves 3 recno → 使照 edges. The user's ruling
  (2026-11-05): 榮星53 and 潭美579 take all three dates from one city case,
  so they get no edge; only 南港729 keeps one (建照/開工 from 10812181,
  使照 from the national page view/769 only). Two more rules give exactly
  that (建照 comes from data2, 開工/使照 from data3 — user, 2026-11-05):
  1. **Viewer: source map first.** `milestones_source` already holds the
     per-date provenance (data2 for 建照; data3 for 開工/使照 via
     `pick_implementation_payload`, the C8a rule). The emitted
     `implementation` payload is the D5 *statistics* pick, not a date
     source, yet `buildConstructionChain` tries its exact match first.
     潭美579's 開工 2017/03/13 matches the statistics payload 10209171
     (recno 1052); the source map names 09809151, like 建照 and 使照.
  2. **Pipeline: the first holder wins an equal value.** When two cases
     carry the same date, both merges credit the **last** case read:
     `merge_stage_milestones` (`urtpe/links.py:2218`, last-write-wins on
     data2) and `pick_implementation_payload` (`urtpe/links.py:2190-2191`,
     keeps the first value but overwrites `source[label]`). 榮星53's 北區
     09001120 and 南區 09001123 are both 擬訂 plan cases with 建照
     2006/07/11 and 使照 2007/11/29; data3 of 09001120 also holds 開工
     2006/07/21. Corpus: 15 dates in 11 projects credit a later case
     (建照 8, 開工 5, 使照 2 — e.g. 蘭雅52, 寶清353-2, 懷生16).

  | Rules (all with the flag fix; group by case as today) | recno → 使照 edges left | Projects with 2+ source edges |
  | --- | --- | --- |
  | flag fix only | 榮星53, 潭美579, 南港729 | 16 |
  | + source map first | 榮星53, 南港729, 萬慶6, 敦化363-1, 民生134-6 | 11 |
  | + first holder (pipeline) | 榮星53, 潭美579, 南港729 | 11 |
  | **+ both** | **南港729** | **7** |

  Grouping by owning record (tested as an alternative) is not needed; the
  spec's "group by carrying case" stays.
- No test encodes the current flag (`tests/test_viewer_labels.py`,
  `tests/test_milestones_provenance.py` checked).

**Form:** direct `fix:` (code departs from the spec) + a test with both dates
present (expect solid 開工 → 使照, no 現況 edge, 國 badge kept).

### D4b — edges out of a dead end (已失效/自行撤回/已駁回)

No drawn gazette edge (`p.edges`, 760 revision edges) leaves a terminal
node — recno nodes are approvals. The edges out of a dead end are the two
viewer-drawn kinds:

| Edge | Total | Upstream end terminal |
| --- | --- | --- |
| virtual chain (virtual → next virtual, same cluster+track) | 48 | **36** |
| §4 dotted edge pointing down (orphan sorts above every recno row) | 307 | **160** |
| §4 dotted edge up to the branch-off row | 212 | 78 (edge INTO the dead end — kept) |
| construction source edge from an orphan | 6 | 0 |

Costs of removal:
1. The 160 terminal orphans lose their only connector and float (no recno
   row sits above them).
2. Chain removal also hides retry → success succession, e.g. 吉林676
   09601262 自行撤回 → 09703182 施工中; 603's 09511212 → 09511213 (both
   withdrawn) loses the link the spec scenario names.

The 36 chain edges by what the next case is: another dead end 20 (e.g.
吳興871-13 11112021 → 11406005 → 11410022), no case status 9 (e.g. 南港366
09407091 已失效 → 09606230), 審查中 6 (e.g. 德惠687-3 → 11409035), 施工中 1
(吉林676).

**Decided (user, 2026-11-05) — chain edges:** remove every chain edge whose
upstream virtual node is 已失效 / 自行撤回 / 已駁回 (all 36; 12 remain). The
`virtual-milestone-nodes` requirement "Virtual nodes chain row-by-row within a
cluster" gains the terminal-start exclusion, and its scenario "Attempt pair is
chained" must change: its example 吉林1021 09902261 (已失效) → 10201171 is
one of the 36.

**Decided (user, 2026-11-05) — dotted edges:** remove the 160 §4 dotted
edges that point down from a dead-end orphan (no recno row above it). Those
orphans render with no edge. The 78 dotted edges that run up into a dead end
(from its branch-off row) stay.

**Form:** openspec change, `virtual-milestone-nodes` (chain edge + §4 dotted
edge requirements and the 603 scenario).

### D4c — list badges: drop 審查中, add 已失效/自行撤回/已駁回

Today (`statusChip`, `viewer/app.js:487`): 審查中 chip on 37 projects, 撤回
chip on 4, 未核定 chip (`neverApproved`) on 4.

"Current recno node in a terminal state", read literally, matches **1**
project: 龍泉534 node 215 (11201181, 事業概要 已失效). Recno nodes are
approvals, so the state almost never ends one. Two wider readings:

| Reading | Projects |
| --- | --- |
| current recno node's case is terminal (literal) | 1 |
| a terminal case acted (申請/公聽會, not the echoed 概要核准) after the last gazette approval | 21 |
| newest case_id terminal | 31 — rejected: 26 of 31 are older than the current approval (吉林717's 09608051 is a 2008 withdrawal) |

- 15 of the 31 also carry a construction chip; the badge order with
  建照/開工/使照, 撤回 and 未核定 must be set.
- The 37 projects losing 審查中 show no state chip. The spec's reason ("silence
  must not read as not started", `history-graph` ~254–276) must change in the
  delta.

**Decided (user, 2026-11-05):** the literal reading — the badge shows the
current recno node's own case state when it is 已失效 / 自行撤回 / 已駁回
(today 1 project, 龍泉534). It renders after the 建照/開工/使照 chip when
both exist. The 審查中 chip is removed.

**Decided (user, 2026-11-05) — 撤回 and 未核定 chips:** remove both. The 4
projects that carry them (市府331, 雙連416-6, 龍泉534, 民生140-9) all have an
approved 擬訂 事業概要 as the current recno node; the chips came from older
dead cases of the family (3 of the 4 current cases have no schedule at all).
A gazette approval proves the unit was approved, so `neverApproved` cannot
hold for a gazette family; the 相關連結 note "未曾核定… 無國土管理署入口網頁"
(`viewer/app.js:1489`) goes with it (spec: `official-link-discovery` ~351,
`viewer-related-links` ~87). The other 3 show no state chip: their current
case has no dead-end state. 龍泉534 is different: its only case, 11201181
(`擬訂…龍泉段一小段534地號等16筆土地事業概要案`), is 已失效, so the list shows
`大安區-龍泉段一小段-534地號等16筆` with the **已失效** badge instead of 撤回 and
未核定. The new dead-end badge therefore matches 1 project today, as the
literal reading measured.

**Form:** openspec change, `history-graph` status-chip requirement.

### D4d — filters: drop 其他/都市更新計畫, add 計畫與執行

- 事業種類 options 其他 and 都市更新計畫 (the user's "都市計畫") match **0**
  nodes; removing them from the filter changes nothing shown. `TRACK_ORDER`
  feeds only the filter (`viewer/app.js:731`); the layout columns
  (`TRACK_COL1/2`) stay.
- 施工階段 → 計畫與執行: keeps 建照/開工/使照, adds 已失效/自行撤回/已駁回
  (same definition as D4c) and 計畫 (現況 = 概要/事計/權變). Current-node
  tracks: 事業概要 14, 事業計畫 264, 事業計畫、權利變換 186, 權利變換 218.

**Decided (user, 2026-11-05):** the 計畫 (現況 = 概要/事計/權變) options
match only the rest — a project with none of 建照/開工/使照 and no
已失效/自行撤回/已駁回 badge. So every project matches at most one 計畫與執行
state (construction, dead end or 計畫). The construction and dead-end options
use the same definitions as the list chips (D4c).

**Decided (user, 2026-11-05):** a current node with the combined track
事業計畫、權利變換 matches only its own option "事業計畫、權利變換" (not 事計,
not 權變). The 計畫 options are the exact current-node tracks: 事業概要 14,
事業計畫 264, 事業計畫、權利變換 186, 權利變換 218 (counts before the
construction/dead-end exclusion).

**Form:** openspec change, `viewer-filtering` (line 9 lists the 事業種類
options), together with D4c.

## D5 — 吉林676: recno 1303 prints 1筆 for an 18筆 unit (user, 2026-11-05)

The 2010-03-25 row 1303 reads `變更…吉林段四小段676地號1筆土地…` in both 案名
and 地號, so it forms its own family `中山區-吉林段四小段-676地號等1筆`. It
belongs to `…676地號等18筆` (recno 1347). Evidence:

- The city platform names its case 09703184
  `變更…676地號等18筆土地都市更新事業計畫案`; 1347's case is 09703182, the
  same 0970318x series.
- Both families resolve to the same national page (view/75), with the same
  implementer (遠雄) and planner (正宇).
- The pipeline's own §6.8 detector already flags both rows
  `片段家族合併候選 … （合併候選，需人工確認）`, which asks for human confirmation.

This is the designed use of the correction ledger (publisher error, a human
confirms it, keyed on land + date, applied before merge). The ledger cannot
do it alone today:

| Ledger entry on 1303 | merge `score` vs 1347 | Result |
| --- | --- | --- |
| none (today) | .35 + .2 + .3×(1/18) = **0.567** | flag band, no merge |
| `land_count` → 18 | **0.667** | still below `LINK_THRESHOLD` 0.7 |
| + a parcel list | ~1.0 | merges, but `land`/`parcels` are not in `CORRECTABLE_FIELDS`, and the 變更's real parcel list is not published anywhere we hold — writing 1347's 18 parcels would repair absent data by inference |
| shared `named_anchor` on both | 1.0 | merges, but the field means 原…基地/國宅 and is emitted in the payload — misuse |

`land_count` → 18 is needed in any case: the family anchor is the newest
member (1303, 2010), and `slug_for` takes its count, so a merged family
would otherwise be named `…676地號等1筆`.

Other gaps found:
- `--ledger` defaults to `None` (`urtpe/cli.py:613`). The ledger is applied
  only on a PDF ingest that passes `--ledger`, never on `--from-js`.
  AGENTS.md says the default is `urtpe-gazettes/corrections.jsonl`; the
  code disagrees.
- `--from-js` keeps families as emitted, so the merge appears only after a
  PDF ingest with the ledger.

**Proposed form:** openspec change on `correction-ledger` + `merge`. Add a
`confirm_merge` entry, keyed on both records' (land, date), that links the
pair before scoring. This answers the §6.8 "需人工確認" flag without
inventing a parcel list. Add a `land_count` → 18 entry on 1303 for the
family name. Then run a PDF ingest with `--ledger`.

**Decided (user, 2026-11-05):** `confirm_merge` for 吉林676, and `--ledger`
defaults to `urtpe-gazettes/corrections.jsonl` (option A: a forgotten flag
must not drop corrections silently). Change: `ledger-confirm-merge`.

## D6 — the twur override stopped applying when the slug changed (user, 2026-11-05)

**Question (user, 2026-11-05).** `https://twur.nlma.gov.tw/zh/urban/rebuild/view/18`
is not in 相關連結 for `萬華區-崇仁新村青年段一小段-711-3地號等2筆`. Also: how do
the two city cases (`09112120`, `09112121`) join that project?

**Finding 1 — the record is present and well-formed, but its key matches no
project.** `data/twur_overrides.json` holds the record under the key
`萬華區-崇仁新村青年段一小段-711-3地號等?筆`. The dataset's id is
`…等2筆`. `load_twur_overrides` keys on `project.project_id`
(`urtpe/links.py:713`), so the lookup misses, `links.twur` emits empty, and
`getNodeMilestoneBadges` (`viewer/app.js:192`) draws no 國 badge. The override
table holds exactly one record, so this is its whole population.

**Finding 2 — the slug change caused it.** Commit `c2cfbb9` (2026-11-01, Wave 4,
"the slug count falls back to the family before rendering ?") made `slug_for`
read the count from the family. Its own commit message names this project:

```
萬華區-崇仁新村青年段一小段-711-3地號等?筆 -> ...等2筆 (member count 2)
```

The emission trace pins the break to that window:

| commit | date | project_id | `links.twur` |
| --- | --- | --- | --- |
| `a90c2a1` | 2026-11-01 | `…等?筆` | `…/view/18` |
| `ad6b767` | 2026-11-02 | `…等2筆` | **empty** |

`data/twur_overrides.json` was not updated in that window. No `?筆` id remains
in the dataset (0 of 681), so the record can never apply as written.

**Finding 3 — the guard fired on 2026-11-03 and nobody acted.**
`unattached_overrides` (`urtpe/links.py:1567`) exists for this exact failure.
The CLI calls it on every `--links` run (`urtpe/links.py:3432`, from
`urtpe/cli.py:518`). It printed, at `data/reemit_viewgate_20261104.log:4`:

```
[WARN] twur override names a project not in the dataset: 萬華區-崇仁新村青年段一小段-711-3地號等?筆
```

A warning does not stop the run. `emission_faults` (`urtpe/emission.py:43`)
faults only *wholesale* absence, so 60 twur-less of 681 projects is conforming
by design — `--links` is advisory (the D5 recorded in `AGENTS.md`, not this
board's D5). Nothing refused, nothing re-checked.

**Finding 4 — the emission also lost the 7 national milestones, and the re-key
alone does not bring them back.** Measured on the current payload:

| field on the live project | today | before `ad6b767` |
| --- | --- | --- |
| `links.twur` | `""` | `…/view/18` |
| `links.milestones_national` | `{}` | 7 labels (93.04.22 … 97.01.03) |
| `links.twur_name` | absent | (never populated) |

The re-key restores only two fields: `load_project_cache`'s gap-fill copies
`twur_view_id` and `twur_url` alone (`urtpe/links.py:1606-1610`), and
`discover_project_links` returns that cached object verbatim on the non-fresh
path (`urtpe/links.py:597-612`). Verified: re-keyed, non-fresh → `twur_url`
present, `national_milestones` **0**. The 國 milestone labels need the view page
re-fetched.

**Finding 5 — a stub now shadows the rich cache, so an alias cannot help.**
Three cache directories hold this one unit:

| directory | `twur_view_id` | national ms | `view.html` |
| --- | --- | --- | --- |
| `…等2筆` (live id) | `null` | 0 | — |
| `…等_筆` (`?` → `_`) | `18` | 7 | yes |
| `未解析-1354` | `18` | 7 | yes |

`resolve_cache_dir` (`urtpe/links.py:1580`) returns the direct directory
whenever it exists, so an alias entry for the live id can never be consulted —
the 2026-11-02 run wrote a stub at the new id, and that stub shadows the richer
one. `data/project_aliases.json` holds no `?筆` → `2筆` entry either. Verified:
re-keyed against today's stub → `twur_url` present, `national_milestones` **0**;
with `fresh=True` (view page re-fetched) → `twur_url` present, **7** labels and
`twur_name` populated.

**Finding 6 — the join the user asked about already works, and works for the
right reason.** Both cases are in the payload, one per node:

| recno | stage | 核定日期 | case_id |
| --- | --- | --- | --- |
| 1423 | 擬訂 | 2005-02-24 | `09112120` |
| 1375 | 變更 | 2008-01-02 | `09112121` |

Three mechanisms do it, all of them built for this unit's shape:

1. `_section_variants` (`urtpe/links.py:1417`) strips the place prefix —
   `崇仁新村青年段一小段` → `青年段一小段`, the form the city indexes. Verified:
   returns both variants.
2. `_corroborated_area` (`urtpe/links.py:1396`) admits a parcel-less case name
   when it shares a place-name run with the gazette 案名. Both case names carry
   no 地號, so `_case_name_carries_parcel` returns False for both and
   corroboration is what does the work. Verified: True for both names against
   both gazette 案名.
3. `_match_case_by_date` (`urtpe/links.py:3181`) binds each node to the case
   with the same 核定日期, which is why 擬訂 and 變更 carry different ids.

The viewer draws 北 per node from `node.links.taipei`
(`viewer/app.js:184-187`). Only the 國 badge depends on `links.twur`. Note the
相關連結 section itself is a debug toggle, default OFF
(`viewer/app.js:1502-1508`).

**Gap in the tests.** No test ties the override key to the dataset.
`test_the_shipped_override_table_is_well_formed`
(`tests/test_twur_override.py:193`) checks the evidence fields only, and its
`PID` constant (line 34) is the stale `?筆` spelling — the suite passes while
the shipped record is inert. The record's own `reason` warns "revisit this
decision if a second case appears"; here the population went to n=0 the other
way, by the id moving rather than a second case arriving.

**Proposed form:** direct `fix:` — re-key the record to `…等2筆`, correct `PID`,
and add a test that asserts every key in `data/twur_overrides.json` names a
project in `data/projects.json` (offline, no re-emit needed). Then restore the
view-derived fields and re-emit. Two options for the restore, both measured:

- **(a) `--fresh` on the affected project**: the view page is re-fetched and all
  7 labels plus `twur_name` come back. Costs one portal request.
- **(b) copy the rich cache directory to the live id**: offline, no request, but
  it carries a `view.html` read on 2026-10-06 and needs a hand-written write into
  `.link_cache/` — the directory `AGENTS.md` names as the durable middle layer.

**Decision (user, 2026-11-05):** option **B** — re-key **and** restore.

**Correction to the restore method (measured 2026-11-05).** The decision was
recorded as "restore with `--fresh`". `--fresh` is **corpus-wide**, not
project-scoped: `LinksDiscovery._fresh_backup` (`urtpe/links.py:3402-3417`)
**renames the whole `data/.link_cache/`** to a timestamped backup and starts an
empty one. That is the 2026-08-24 incident shape AGENTS.md warns about — one
project's restore would wipe all 719 caches and orphan every mapping the index
alone cannot rebuild. `--fresh` is therefore **not** the method.

The targeted method is `refresh_project` (`urtpe/links.py:1786`), which
re-fetches one project's cases and re-runs its view-page absorb
(`urtpe/links.py:1998-2016`). Measured cache state for the target:

| Cache dir | `twur_view_id` | `national_milestones` | `view.html` |
|---|---|---|---|
| `…等2筆` (live id) | `null` | 0 | — |
| `…等_筆` (`?` → `_`) | `18` | 7 | yes |
| `未解析-1354` | `18` | 7 | yes |

`refresh_project` cannot do the restore: it never writes `national_milestones`
(no `extract_tuidui_history_from_view` call in lines 1786–2074). The cache copy
is the option the user did not choose.

The faithful method is **`discover_project_links(project, cache_dir,
fresh=True)` on this one project**, after the re-key. That function re-fetches
the view page and extracts 推動歷程 (`urtpe/links.py:720-721`). It does not call
`_fresh_backup`; only `LinksDiscovery.run` renames the cache. This keeps the
user's intent (one portal request, a current page, all 7 labels) and touches
one project only.

**Decision (user, 2026-11-05): option A** — `discover_project_links(fresh=True)`
on this one project, after the re-key. Compared with option B (copy the
`…等_筆` dir, offline):

| | A — per-project fresh fetch | B — copy the rich cache dir |
|---|---|---|
| National page | fetched today | from 2026-10-06 |
| `twur_name` | can be filled | stays empty |
| Network | about 5 requests (1 portal page, 2 cases' data2/3/4) | none |
| Scope of change | the whole project cache is rebuilt; a city re-date also lands | exactly the 7 labels; the city half is identical in both dirs |
| Process | normal pipeline path, single-writer lock | hand write into `.link_cache/`, no record of it |

A matches the user's first intent (one fetch, a current page).

An `unattached_overrides` that *refuses* rather than warns is a separate question
and is not proposed here: `--links` stays advisory by design (`AGENTS.md` D5), and
the coverage guard is what covers the default path.

**Corpus.** 60 of 681 projects carry no `links.twur` today. Only one override
record exists, so the re-key is the whole visible effect.

## D7 — `refresh_project` never re-derives the merged milestone projection (user, 2026-11-05)

**Question (user, 2026-11-05).** 松山區-寶清段四小段-599地號等27筆 shows no
建照核准 date, yet `uroTPE` holds it from data2. Why?

**Finding.** The date is in the cache and not in the emitted payload:

| location | 建照核發日期 |
| --- | --- |
| `case_milestones["09303270"]` | `2006/05/12` |
| `taipei_milestones` (merged, cache) | **absent** |
| emitted `links.milestones_taipei` | **absent** |

`taipei_milestones` and `milestones_source` are written **only** by the full
discovery path (`merge_stage_milestones`, `urtpe/links.py:672`, assigned at
line 694; the view absorb re-merges at line 794). `refresh_project`
(`urtpe/links.py:1868-1900`) rewrites `case_milestones` per case and never
re-derives the merged dict. The two therefore drift apart, and the stale merged
dict is what `attach_links_to_projects` (`urtpe/links.py:3077-3079`) copies into
the project.

**Mechanism, measured.** Rebuilding the merge from `case_milestones` over
`city_case_ids` and comparing to the stored dict:

| | count |
| --- | --- |
| caches with per-case milestones | 719 |
| **merged projection diverges** | **85** |
| of those, loses or alters ≥1 label | 84 |
| of those, carries ≥1 conflicting value | 66 |

Worst by label count: 南港段一小段-19-1 (32 labels, 3 cases), 敦化段二小段-449-12
(29, 3), 玉成段二小段-253 (27, 2), 犁和段三小段-89 (23, 4).

**Cause 1 — a case was appended after the merge (34 of 85).** 寶清599 is exact:
the stored dict equals a merge over `['09303271','09303272']` alone. The third
case, `09303270`, is in `city_case_ids` and holds 5 labels the merged dict lacks
— 公告公展日期, 公展公聽會日期, 申請幹事會日期, 申請核定日期, **建照核發日期**.
`refresh_project`'s search step appends a newly found case to `city_case_ids`
(`urtpe/links.py:1855`) but nothing recomputes the projection over it.

**Cause 2 — the city re-dated a label (5 of 85).** The stored dict holds a value
no case carries any more. 光華段四小段-282: stored 審議通過日期 `2026/03/18`,
while case `11408032` now reads `2026/09/23`. 市府段二小段-220-2 holds 公告公展
日期 `2011/01/10` with no holder at all.

**Cause 3 — 50 unexplained by subset or permutation.** Not a merge-order
artifact: for 0 of the 85 does a permutation of `city_case_ids` reproduce the
stored dict. These need their own look before the fix is written.

**D7b — the 50 are named (2026-11-06, `scripts/probe_d7b_naming.py`).**

Reproduced offline over the 719 caches that hold per-case milestones:

| | count |
| --- | --- |
| in sync with a merge over `city_case_ids` | 634 |
| **explained — the stored dict is a merge over an ordered SUBSET** | **35** |
| explained — a permutation of `city_case_ids` | 0 |
| **unexplained** | **50** |

The subset check scans every ordered subset (the merge is order-sensitive).
Beyond 8 ids the full permutation space is too large, so the two shapes the
pipeline produces are tried directly: every prefix and every single-id drop.
Both of the >8-id caches (虎林38, 木柵623) are explained by a prefix — a case
appended after the merge.

**The 50 split into four named shapes.** The naming test asks, for every label
where the stored value differs from the re-derived one: **does a case still
hold the stored value today?**

| Shape | Count | What it is |
| --- | --- | --- |
| `STALE_MERGE` | 20 | The stored value is **still held by a case**. Only the merge moved: a later case now carries the same label with a newer value, and the merged dict was never recomputed. |
| `NEW_LABEL` | 16 | A case carries a label the merged dict **never received** — the case was appended to `city_case_ids` after the merge, and nothing re-merged over it. |
| `WITHDRAWN` | 3 | The stored dict holds a label (or value) **no case carries any more** — the city withdrew it. |
| `MIXED` | 11 | Both: some labels still held, some withdrawn, some new. |

**The mechanism, confirmed at the code level.** `refresh_project`
(`urtpe/links.py:1863-1890`) rewrites `case_milestones[cid]` per case and
never re-merges. Two writes reach `case_milestones` after the merge:

1. the per-case pass — a case's data2 gained or lost a label, and the
   refresh wrote the new value into `case_milestones[cid]` while the merged
   dict kept the old one;
2. the search step (`urtpe/links.py:1845-1851`) — a case id the parcel search
   returned was **appended** to `city_case_ids` with an empty
   `case_milestones[cid]`, and the per-case pass then filled it. The merged
   dict never saw it.

Worked example — 中山區-吉林段四小段-508地號等17筆 (`STALE_MERGE`):

| | |
| --- | --- |
| `city_case_ids` | `11011241, 11011242, 11508022, 11508023` |
| `11508023` (appended after the merge) | `申請計畫日期 2026/08/25`, `申請權變日期 2026/08/25`, **`召開幹事會日期 2026/10/02`** |
| `11011241` / `11011242` | `召開幹事會日期 2022/11/15` |
| stored merged dict | `召開幹事會日期 = 2022/11/15`, source `11011242` |
| re-derived | `召開幹事會日期 = 2026/10/02` (the later case wins) |

The stored source map still names the case that holds the stored value, so the
projection is not corrupt — it is **stale**. 1,684 of the 1,720 labels in the
85 divergent caches still have a source map that agrees with the case data.

**What this means for the fix.** The decided rule (D7 = overwrite) projects
`case_milestones` exactly, so:

- the 20 `STALE_MERGE` and 16 `NEW_LABEL` caches are **repaired** — the
  re-derivation produces what a fresh discovery would produce;
- the 3 `WITHDRAWN` caches **lose** the withdrawn label. That is the decided
  behaviour (the city withdrew the date), and the withdrawn-approval rule
  (`_APPROVAL_FIELDS`) still governs the emit-time path;
- the 11 `MIXED` caches get both effects.

**No merge order explains any of the 50.** `scripts/probe_d7b_orders.py` tries
five orderings over the same ids — `city_case_ids` as stored, reversed, by
approval date, by case id, by label count — and by prefix or single-id drop.
**0 of the 50** is explained by any of them. The 50 are content differences,
not ordering artifacts.

**Blast radius is all three of the user's B/C surfaces at once.** 寶清599 shows
no 建照 in the list chip (`constructionStage`), none in the graph chain
(`buildConstructionChain`: verified in a VM — the chain holds 開工 and 使照 only),
and a 使照 國 badge whose 建照 partner is missing. Measured: 14 projects emit no
construction date that a case actually holds.

`--from-js` cannot repair it. The round-trip re-derives provenance credit only
for labels whose carriers agree on one value (`urtpe/links.py:3080-3097`); a
label the merged dict never received stays absent.

**Design question for the fix.** A re-derivation that projects `case_milestones`
exactly would drop the 5 cause-2 values. For 光華282 that is right (the city
re-dated it). For a label the city withdrew entirely it is a real removal, and
the withdrawn-approval rule (`_APPROVAL_FIELDS`, `urtpe/links.py:1664`) exists
precisely to keep such a date. So the re-derivation must state which of the two
it does, rather than assume. Note also that `attach_links_to_projects` injects
the data3 dates into `milestones_taipei` at emit time
(`urtpe/links.py:3151-3158`), so a cache-level re-derivation must not displace
that layer.

**Decision (user, 2026-11-05):** option **A** — **overwrite**. The re-derivation
projects `case_milestones` exactly; the 5 cause-2 values are dropped. The city
re-dated 光華282's 審議通過日期, so keeping the old value would keep a false date.
The withdrawn-approval rule (`_APPROVAL_FIELDS`) still governs the emit-time
path; the cache-level re-derivation does not keep it.

**Form:** openspec change (pipeline) + cache re-derive + re-emit. Same change as
D8 — one `refresh_project` edit, one re-emit.

## D8 — `refresh_project` never re-fetches data3/data4, so an empty implementation is permanent (user, 2026-11-05)

**Question (user, 2026-11-05).** 文山區-實踐段二小段-641地號等1筆 has no 開工
and no 使照, yet the dates exist. Why?

**Finding.** The live data3 endpoint holds both, and the cache holds neither:

| layer | 開工 (`Eng_Start_Date`) | 使照 (`Ulic_Date`) |
| --- | --- | --- |
| live `third.ashx` for `09009032` | `2004/09/24` | `2007/10/31` |
| cache `implementation` | `{}` | `{}` |
| emitted `milestones_taipei` | absent | absent |

`refresh_project` re-fetches only data2 (`fetch(cid)`) and the case header. It
never calls `fetch_taipei_implementation_api` / `fetch_taipei_rewards_api` — no
`implementation`, `third` or `rewards` write exists in the function (lines
1786–2075). `discover_project_links` returns the cached object verbatim on the
non-fresh path (`urtpe/links.py:597-612`), so the standing CLI run cannot repair
it either. `fresh=True` does: verified against the live API, `09009032` returns
34 fields and the run emits them.

**Corpus.** 6 of 719 caches hold case ids with an empty `implementation`. Probed
live, per project:

| project | case with recoverable data3 | dates |
| --- | --- | --- |
| 中山區-長安段一小段-454 | `11407047` | 開工 2026/06/05 |
| 內湖區-東湖段一小段-地號等?筆 | `10101081` | 開工 2014/10/16, 使照 2017/03/20 |
| 南港區-玉成段二小段-253-1 | — | statistics only (24 fields) |
| 南港區-玉成段二小段-733 | `11108191` | 開工 2025/07/11 |
| 文山區-實踐段二小段-641 | `09009032` | 開工 2004/09/24, 使照 2007/10/31 |
| 萬華區-華中段一小段-247 | — | statistics only (11–29 fields) |

4 of the 6 have a recoverable construction date; all 6 have statistics that the
emitted `implementation` card does not show. One case (`100904` in 東湖) returns
0 fields — a genuinely empty endpoint answer, which is not a defect.

**Cost of the fix.** Re-fetching data3 + data4 is 1–2 requests **per case**, on
top of the 3 signals per project the corpus refresh already spends
(`scripts/refresh_whole_corpus.py`). The endpoint is WAF-capped, which is why
that driver is sliced and resumable. A size-triggered refetch — only where
`implementation` is empty — costs 6 projects' cases and gets every date above.

**Decision (user, 2026-11-05):** option **B** — refetch **only** where
`implementation` is empty (6 projects). It recovers all 4 recoverable construction
dates at a fraction of the request cost, and the WAF-capped endpoint makes the
broad sweep the riskier choice.

**Form:** openspec change (pipeline) + cache refresh + re-emit. Shares D7's edit
and re-emit.

## Order

Priority: **P1** = wrong data on screen today; **P2** = a display gap with a
known cause; **P3** = cosmetic or single-project. Dependency is the finding that
must land first, because it changes the same code or the same re-emit.

**All decisions are made (2026-11-06).** The consolidated order is D9g; this
table is the per-finding view of it. Where the two differ, D9g wins.

| Step | Finding | Priority | Form | Depends on | Gate |
| --- | --- | --- | --- | --- | --- |
| D7b | the 50 divergences unexplained by subset or permutation | **P1** | investigation, then folded into D7 | — | measured before the fix is written |
| D7 | `refresh_project` never re-derives `taipei_milestones` — 85 of 719 caches diverge, 84 lose or alter a label, 14 projects emit no construction date a case holds | **P1** | openspec change (pipeline) + cache re-derive + re-emit | D7b | **decided: overwrite** (D7) |
| D8 | `refresh_project` never re-fetches data3/data4 — 6 of 719 caches hold an empty `implementation`, 4 with a recoverable construction date | **P1** | openspec change (pipeline) + cache refresh + re-emit | **D7** (one edit, one re-emit) | **decided: refetch per case** (26 cases / 22 projects; amended 2026-11-06) |
| D13 | 青年130 node 78 — stale cache: the city emptied `11501041`, the refresh kept it 已核准 | **P1** | part of the D7+D8 change | **D7**, **D8** | **decided: label 無, keep as orphan** |
| D14 | `--from-js` loader drops 3 node fields and coerces `district_land` `''` | **P1** | direct `fix:` + round-trip test | — | before the first re-emit |
| D14(b) | `district_land` from the collected 12-district enum (7 rows) | **P2** | openspec change (`cleanse`) + 2 tests | — | before the next PDF ingest (D9f) |
| D15 | review-flag order depends on cluster order (大龍265-7) | **P3** | openspec change (emitter) + test | — | rides a re-emit |
| **D9f-1** | the 2026-10-28 gazette prints no 核定日期 for 編號 3 — the recovery pass, widened to a truncated **date** | **P1** | openspec change (`truncated-row-recovery` + `pdf-tsv-extraction` + `gazette-reconciliation`) + code + test + one ingest | D9f | **AGREED** (user, 2026-11-06) — the rule recovers **57 of 59** rows with **0** ambiguous; 編號 3 → **2026-10-15**, the date the corpus already holds. **Not yet implemented** |
| **D9f-2** | the 168 list's `MEMO` as a fourth source for the approval date | **P2** | part of D9f-1's change — a **flag**, not a date source | D9f-1 | **AGREED** (user, 2026-11-06) — **measured**: the MEMO is empty for all **33** PDF-vs-platform disagreement cases, and it is the 核定**公告** date where it is present, so it cannot settle them |
| **D16** | the city writes 利 as U+F9DD, a compatibility ideograph — `權利變換` does not match | **P2** | `fix:` in the 案名 normalisation + test | — | found 2026-11-06. **Measured (D16a–D16c): 2 readers affected** — the track reader (1 live case) and `parse_name_id` (6 corpus rows / 3 projects, latent). The corpus's 6 carry 北/都/更 and are inert for the track; **0** corpus rows carry a compatibility 利. Fix waits for the user to open it |
| **D17** | `date_check` reports a false "exact" match when the wanted date is empty | **P2** | `fix:` — refuse an empty `want` + test | — | latent today (the caller guards); **must** land with D9f-1, which hands it an empty date on every call |
| D10 | the permit witness names the first permit of a tie — 43 projects show a 執照 date that is not the project's own 使照 | **P2** | openspec change (`official-link-discovery`) + re-emit | **D7** (the flag path reads the dict D7 corrupts) | **decided: 開工 match, else ambiguous** (D10e) |
| D6 | twur override key is the pre-`c2cfbb9` slug — the record never applies; 國 badge and 7 national milestones absent | **P2** | direct `fix:` (re-key + dataset-key test) + restore + re-emit | — | **decided: re-key + per-project `discover_project_links(fresh=True)`** (D6) |
| D9c-2 | `10708311` and `11412011` are absent from the city's parcel index — **DONE 2026-11-05** (live probe) | — | probe | — | — |
| D9c-2a | merge the stranded 南港566 cache (offline, 2 unplaced nodes); second id source for `11412011`; stop stub-over-alias shadowing | **P2** | cache merge + openspec change + code + test + re-emit | **D7** | single-writer rule |
| D9a-5a | header pass over the 84 no-link cases — **DONE 2026-11-05**: 0 approved; 78 in review, 5 closed, 1 revoked | — | read-only probe | — | — |
| D9e | 54 of 54 in-processing case_ids resolve — lock it in with an offline test | **P2** | `tests/` | — | — |
| D11 | the A/B/C surfaces read one dict | — | docs only | — | **DONE** (recorded below) |
| D9f | periodical 168 poller + hash change detection, coordinated with the PDF poll; then the 2026-11-03 ingest | **P2** | poller script + task action + ingest + re-emit | **D7**, **D14(b)** | single-writer rule |
| D9c-4 | monitor the cases D9a-5a confirms as not approved, after each new gazette | **P3** | re-run the cross-reference scripts | D9a-5a, D9f | new gazette published |
| D12 | architecture concerns — recorded, constrain D9g steps 2–9 | — | docs only | — | **DONE** (recorded below) |
| D3a | `nationalLabelKey` ordinal spelling — 223 labels never bind — **DONE** (`d8a63ca` + test at `tests/test_viewer_labels.py:560`); direct `fix:`, no openspec change and no re-emit needed | — | — | — | — |
| D4a | 使照 national flag + source-map-first + first-holder provenance — DONE (viewer `57a70cf`, pipeline with D1, re-emit `2bb3013`): only 南港729 keeps an edge | — | — | — | — |
| D4b–d | dead-end edges, list badges, 計畫與執行 filter — DONE `26e57f1`, archived `2026-11-05-viewer-deadend-and-filters` (`d2d15ee`) | — | — | — | — |
| D1 | rename the orphan `milestones_national` key — DONE with D4a-pipeline (`d524fae`+`24694a5`, re-emit `2bb3013`, archived) | — | — | — | — |
| D2 | `_ghost_node_date` track-aware + date-first sort — DONE (D2a re-emit `e97c18d`: 25→7 same-date pairs; D2b `56ae3ca`: 0 non-chronological projects, was 51) | — | — | — | — |
| D5 | 吉林676 `confirm_merge` + `--ledger` default — DONE (code `1517300`; ingest with the two ledger entries, 682 → 681 projects, 吉林676 holds 1303 + 1347, no 片段家族合併候選 flag left; archived `ledger-confirm-merge`) | — | — | — | — |

### Why D7 and D8 share one change

Both are one edit to `refresh_project`: recompute what the refresh just
invalidated, and re-fetch the layer it never fetched. Both need the same cache
pass and the same re-emit, and the re-emit is the ~23 MB write `AGENTS.md`
warns about. Splitting them would pay that cost twice.

### Why D7 is P1 and not P2

84 caches lose or alter a milestone label, 66 carry a conflicting value, and 14
projects hide a construction date the city publishes. The corrupted dict reaches
**all three** display surfaces (list chip, graph chain, 相關連結), so one fix
repairs every case the user asked about in A/B/C. D6 is a single record.

### Sequence

Superseded. The execution order is D9g.

## Decisions waiting on the user

| Entry | Question | Blocks |
| --- | --- | --- |
| — | None. D13, D8 (per case) and D14(b) were decided on 2026-11-06 (see "Decisions made"). | — |

Decided 2026-11-05 and moved into the findings: D2b (date-first sort), D4b
(chain + dotted edges), D4c (literal reading, after the construction chip),
D4d (計畫 options = the rest).

## D9 — P_project168 cross-reference: 466 platform cases vs gazette (added 2026-11-05)

**Finding.** The full `https://gis.uro.taipei/ashx/Get_project168.ashx` list (466 cases,
pageSize=50, `transition` key accepted but returns identical rows) was cross-referenced
against `data/projects.json` (gazette 2026-10-15, 681 projects) two ways:

| Match method | Cases found |
|---|---|
| By `case_id` → a node's `links.taipei` | 341 of 466 |
| By `case_id` → project-level `links.taipei` only | 35 more (376 total) |
| **In neither link layer** | **90** |

(An earlier "+338 by section + parcel" row came from a deep-match script that
counted cases twice. It is withdrawn.) All 54 in-processing cases resolve.

**Scope of the 168 list (measured 2026-11-05).** The gazette payload links
**1,982** distinct case ids. Only **376** of them are on the 168 list; 1,606 are
not. So the 168 list is a **subset** — its MEMO texts ("申請轉軌168專案") and the
正軌/轉軌 lookup point at the 168 fast-track program, not at every case in
review. It is **not** a complete register of cases awaiting approval. A case
that is in review but outside the 168 program does not appear in it.

### D9a — the 90 cases in neither link layer (recounted 2026-11-05)

| Category | Count | Detail |
|---|---|---|
| No link and no parcel match: the section is in the gazette, the parcel is not | 65 | e.g. `10506301`, `11001292`, `11010251` |
| No link and no parcel match: the section is not in the gazette | 19 | e.g. `11104211`, `11111151`, `11201191` |
| Revoked approval (`業經本府撤銷核准`), never gazetted | 3 | `10112154`, `10702271`, `10904071` (see D9d) |
| **Gazetted but unlinked** — the approval is in the gazette, `links.taipei` lacks the id | 2 | `10708311`, `11412011` (see D9c) |
| **Pending amendment on a gazetted project** — not approved | 1 | `11410026` (header: `NAME` 其他, `phase` Z, no 核定 date) |

The recount finds 0 unparseable names; the earlier "unparseable 3" row is
withdrawn.

**The 168 stage `-` does not mean "not gazetted".** All 87 cases with stage `-`
include `10708311`, which was approved on 2019-11-20 and is in the gazette. So
the 84 cases in the first two rows were "no link and no parcel match against the
2026-10-15 gazette", not proven new. One header request per case
(`get_project168_top.ashx`) decides each one.

**Header pass (D9g step 5a, run 2026-11-05, 84 requests, 0 errors,
`scripts/probe_header_pass_84.py` → `data/p168_header_pass.json`).** None of the
84 is approved:

| State (from the header `NAME`) | Count |
|---|---|
| **In review — the awaiting-approval list for the 168 subset** | **78** |
| Closed: 實施者自行撤回 (4) or 業經本府駁回 (1) | 5 |
| Revoked: 業經本府撤銷核准 (`11104211`, approved 2024-08-01, then revoked) | 1 |

The 78 in-review cases span every review step, from 業已提出申請審查 (11) to
申請報府核定中 (8). The gazette correctly holds none of them. So the 90 unlinked
cases resolve as: **78 in review, 9 closed or revoked, 2 gazetted but unlinked,
1 pending amendment on a gazetted project.**

### D9b — the 54 in-processing cases: **0 missing from gazette**

All 54 in-processing cases (`專案審查階段`, `審議階段`, `報核-公展階段`, `聽證階段`)
were found in the gazette. Measured 2026-11-05: 52 in a node's `links.taipei`, all
54 in the project-level `links.taipei`, **0 in neither**. None are "prospect
projects under approval" absent from the gazette. They are amendment-pending cases:
a previous version was gazetted, a new revision is in review.

**Conclusion:** the gazette is complete for in-processing cases. The gap is only in
case_id linkage (sibling case_ids, empty `links.taipei`, or case_id never discovered),
not in project coverage.

### D9c — mitigation options for the case_id linkage gap

The gap is not project coverage: every in-processing case is in the gazette. The gap
is that `links.taipei` does not carry the platform `case_id` for 3 matched-by-parcel
cases (sibling case_ids, or empty `links.taipei`). Four options, measured:

| Option | What it fixes | Code change? | Risk |
|---|---|---|---|
| **1. Correction ledger** (`confirm_merge`) | ~~Documents that the platform's referenced land core belongs to the gazette's actual project.~~ **Withdrawn** — see D9d: the ledger joins two *gazette* records and cannot add one the gazette does not hold | No — data only | None |
| **2. Discovery: a second source of case ids** | The city's parcel search does not index `10708311` or `11412011` (live probe, D9c-2). Add a second id source beside the search: ids from the 168 list, each confirmed by its header before it enters `city_case_ids`. `_match_case_by_date` then binds them. | Yes — `urtpe/links.py` + test | Low — each id is confirmed by its own header |
| **3. Discovery: populate empty `links.taipei`** | When `links.taipei` is empty at every level (`11410026`), retry discovery with looser matching. | Yes — `urtpe/links.py` | Medium — AGENTS.md warns against loosening the parcel matcher |
| **4. Monitor un-gazetted cases** | Re-run the cross-reference after each new gazette ingestion; the cases step 5a confirms as not approved should resolve as they are gazetted. | No — script | None |

**Accepted batch: 2 + 4** (option 1 withdrawn by D9d; option 3 not accepted).

**D9c-2 — live probe result (2026-11-05, `scripts/probe_sibling_search.py`).**
The city's parcel search (`Get_updcase_list.ashx`) does **not** return either
sibling, with or without the §6.7 guard:

| Search | Returned | Target present? |
|---|---|---|
| 南港段四小段 / 566 | `10708312` only | `10708311` — **no** |
| 玉成段二小段 / 166 | `10901211`, `10901212`, `11412012` (+ `10405044`, guarded out) | `11412011` — **no** |

So the guard is not the cause, and neither `refresh_project` nor a guard fix can
recover these ids. The case headers confirm what they are:

| Case | Header `CASE_NAME` / `NAME` | Approval date | Gazette node |
|---|---|---|---|
| `10708311` | 變更…南港段四小段566地號等6筆…事業計畫案 / 業經本府核定 | 2019-11-20 | recno 744 (2019-11-20), flagged `節點未能對應平台案件` today |
| `11412011` | 變更(第二次)…166地號等12筆…-B區 / 業經本府核定 | 2026-02-03 | recno 75 (2026-02-03), holds the A區 twin `11412012` |
| `11410026` | 變更…臨沂段三小段412…/ 其他, phase Z | none | none — the project's only node is recno 120 (擬訂) |

If `10708311` were in `city_case_ids`, `_match_case_by_date` would bind it to
node 744 with no other change. `11412011` would join its A區 twin on node 75, as
`10901211`/`10901212` already share node 563. **The only gap is the id source.**
`11410026` is a pending amendment, not a link gap; it leaves D9c.

**Recall of the parcel search, corpus-wide.** 16 nodes in 11 projects carry the
unplaced flag `節點未能對應平台案件`. Exactly **1** of them (node 744) has a
case name equal to a 168-list name. So the 168 list fixes 1 of 16 unplaced
nodes; the other 15 need another id source. Option 2 is worth an openspec change
only if it is a general second id source, not a 168-only patch.

**Correction (from `viewer-source-sync`, verified 2026-11-05): `10708311` was
found once, then lost through alias shadowing.** It is not absent from every
cache. The stranded directory `南港區-南港段四小段-566地號等6筆` (written
2026-11-04) holds `city_case_ids ['10708312', '10708311', '10006032']`, with full
milestones for `10708311` (核定 2019-11-20) and `10006032` (核定 2016-02-25). The
earlier finds most likely came from the all-parcel search step of
`resolve_node_cases` (`urtpe/links.py:2598-2603`, written for exactly this
南港566 shape).

`data/project_aliases.json` maps the live id `…等1筆` to that old id. But
`resolve_cache_dir` (`urtpe/links.py:1580-1590`) returns the live id's own
directory whenever it exists, and a stub exists — so the alias is never read.
This is the D6 Finding 5 shape (a stub at the new id shadows the richer old
dir) on a different project.

Measured over all 11 alias pairs:

| Pair | Ids only in the stranded dir | Unplaced nodes they would bind by date |
|---|---|---|
| 南港566 (`…等6筆` → `…等1筆`) | `10708311`, `10006032` | node 744 (2019-11-20), node 1063 (2016-02-25) |
| the other 10 pairs | none | none |

So the shadowing loses data in **one** project, and it accounts for **2 of the
16** unplaced nodes. Two consequences:

- The fix for 南港566 is a cache **merge**: union the stranded dir's case ids and
  per-case milestones into the live dir, then re-emit. No network and no new id
  source are needed for that project.
- The general defect is `resolve_cache_dir`'s "direct dir wins". The stub write
  is the root cause; a fix that merges an aliased dir into a fresh stub, instead
  of shadowing it, stops the loss recurring. Changing the resolution order for
  every aliased project is a broader behaviour change and needs its own openspec
  change.

`11412011` (玉成166) is in **no** cache, stranded or live, so it still needs the
second id source.

**Priority / dependency order for batch processing:**

| Step | Option | Priority | Form | Depends on | Gate |
|---|---|---|---|---|---|
| D9c-2 | Live parcel search probe — **DONE 2026-11-05**, both siblings absent from the city's index | — | probe | — | — |
| D9c-2a | Second id source: header-confirmed ids join `city_case_ids` in a refresh step | P2 | openspec change + `urtpe/links.py` + test + targeted refresh + re-emit | **D7** | single-writer rule; never written by the poller |
| D9c-4 | Monitor script: re-run cross-reference after each gazette ingest | P3 | `scripts/probe_crossref_p168_gazette.py` re-run | D9f | new gazette published |

### D9d — the 3 uncovered cases: the ledger does NOT apply (corrected)

**Correction (2026-11-05).** The first draft of D9d proposed a `confirm_merge`
ledger entry for each of the 3 cases, keyed on the gazette project's
`(land_core, iso_date)` with the platform's land core as `with_land_core`.
Measurement against `data/projects.json` shows **all 3 entries would be unmatched**
and would link nothing. The ledger's `apply` requires **both** keys to resolve to
exactly one record each (`urtpe/ledger.py:222-234`); an unmatched entry is reported
and links nothing, never guessed.

| Case | Platform's land core | Gazette record with that land core? | Result |
|---|---|---|---|
| `10112154` | 大安段三小段260地號等15筆 | **No.** The gazette's 大安段三小段 project holds parcels 243, 243-1, 245, 245-1, 250, 250-1, 250-2, 251, 251-1, 251-2, 251-3, 251-5, 252, 252-1, 252-2 — parcel 260 is not among them | entry unmatched |
| `10702271` | 豐年段四小段479-2地號等3筆 | **No.** Parcel 479-2 appears in **no** gazette section at all | entry unmatched |
| `10904071` | 玉成段一小段36地號1筆 | **No.** The gazette's 玉成段一小段 project holds parcels 169, 238, 239, 251, 270, 271, 272, 273 — parcel 36 is not among them | entry unmatched |

**Why the parcel match was wrong.** D9c's parcel match keyed on
`(section, first_parcel)` and fell back to "any parcel in the list". For these 3
cases the section matched but **no parcel matched at all** — the platform's parcel
is in a different unit that happens to share the section name. The earlier
cross-reference counted them as "matched" because the section name alone carried
them.

**Why they are genuinely outside the gazette.** Their `MEMO` approval dates
(2019-07-23, 2021-12-21, 2021-08-31) match **no gazette row in their own
section**. A revoked approval (`業經本府撤銷核准`) is not gazetted — the city
prints approvals, not revocations. So all 3 are correctly absent from the gazette;
their absence is the truth, not a gap.

**Correction to D9a.** The "Already approved (`核定階段`) but not linked — 3"
row is **wrong on both counts**: the platform stage is `核定階段` (the case
reached 核定), but the *approval was revoked*, so it was never gazetted. These 3
belong with the revoked row of D9a. The rest of the 90 split as D9a now shows:
84 with no link and no parcel match, 2 gazetted but unlinked, 1 pending
amendment.

**Correction to D9c option 1.** A `confirm_merge` entry cannot express "this case
is not in the gazette". The ledger joins two gazette records; it cannot add a
record that does not exist. **Option 1 is withdrawn** for these 3 cases.

### D9e — test: all 54 in-processing case_ids resolve

Offline test asserting each of the 54 in-processing case_ids appears in
`links.taipei` of some gazette project in `data/projects.json`. No re-emit, no
network.

Measured 2026-11-05: **54 of 54 pass** — 52 in a node's `links.taipei`, all 54 in
the project-level `links.taipei`, **0 in neither**. The test locks this in.

### D9f — periodical 168 source updates

The 168 list is a living source: new cases are added, `stage` values change
(`審查中` → `核定階段` → `已失效`/自行撤回/已駁回), and cases are withdrawn.
A one-time snapshot goes stale. This is **acquisition**, separate from gazette
ingestion (AGENTS.md: "Acquisition is separate from ingestion" and "Don't wire
polling into ingestion").

**Decision (user):** accept D9f, coordinated with periodical PDF update.

**Decision (user, 2026-11-05):** ingest the 2026-11-03 gazette together with the
first 168 poll.

**The PDF poller already exists.** `scripts/poll_gazette.py` (`urtpe/poller.py`)
runs from the Windows task `urtpe-poll`, weekly on Sunday 06:30. Last run
2026-11-02 06:30, result 0 ("re-uploaded identical content, 2026-10-15"); next
run 2026-11-09. The 2026-11-03 PDF in the archive was saved by hand on
2026-11-03 15:56 and has **no entry in `index.jsonl`** — the weekly poller did
not see it. A weekly cadence can miss a new gazette by up to 6 days.

**Coordination plan.** The 168 poller runs in the same scheduled task, straight
after the PDF check. Both only acquire (snapshot + hash). Ingestion stays one
explicit run: when a new gazette and a new 168 snapshot are both present, one
ingest reads the gazette, then the cross-reference runs against the fresh
snapshot. The 2026-11-03 gazette is the first such ingest.

**Proposed plan:**

| Step | Action | Priority | Form | Depends on |
|---|---|---|---|---|
| D9f-1 | Poll script: fetch all pages of `Get_project168.ashx` (pageSize=50, all `transition` values), save snapshot with content hash | P2 | `scripts/probe_fetch_p168_list.py` + a hash/change-detection wrapper | — |
| D9f-2 | Change detection: compare snapshot hash to previous; only re-cross-reference when hash changes | P2 | Same wrapper | D9f-1 |
| D9f-3 | On change: re-run `scripts/probe_crossref_p168_gazette.py` + `probe_deep_crossref_unmatched.py` against latest gazette | P3 | Same wrapper, or a thin wrapper | D9f-2 |
| D9f-4 | Store snapshots under `urtpe-gazettes/p168_snapshots/` (outside repo, like the gazette archive) | P2 | Directory layout | D9f-1 |

**Design constraints (from AGENTS.md):**
- Change detection by **content hash**, never by the platform's timestamp (the city re-uploads under later stamps).
- Single-writer lock (`.pipeline.lock`) serialises writers — one run per output tree.
- The poller never ingests; ingestion is a separate explicit act.
- No `pyproject.toml`, no CI, no build step — plain Python, system interpreter.

### D9f — the ingest was refused, then unblocked (2026-11-06)

**RESOLVED.** The ingest was first **refused** by the tripwire, and the
refusal was correct. It was then unblocked by step 9a (D9f-1, the widened
recovery pass) and **succeeded**. This section records the refusal, because
the reason it was right is what made the fix possible.

**The outcome, measured.**

```
[INFO] recovery: 5 recovered, 0 residual of 5 truncated row(s)
  編號 3: RECOVERED 核定日期 2026/10/15 (cases 11501034, from the 案名 alone)
  編號 190, 1007, 1133, 1208: RECOVERED (the 地號 truncations)
tripwire: PASS
  records: 1444  projects: 682
reconcile: 2026-10-15 -> 2026-10-28
  new approvals: 2   net change: +6 (1438 -> 1444)
  historical rows changed: re-dated 0, edited 0, vanished 0 (accepted: 0)
  recovered by this reader: 4
manual corrections applied: 2
unmatched corrections: 0
```

**The corpus stands at 1,444 records / 682 projects.** The approval the city
reprinted with an empty date is **not** reported as a withdrawal — the
recovered date matches the predecessor's identity key exactly.

**Two corrections the implementation did not need.** The design assumed the
tripwire would need an exemption for the recovered row and the reconciler a
new field. Neither was needed:

- the **tripwire** — the recovery pass runs *before* it (`urtpe/cli.py:292`
  against `:322`), and the recovered date is written in the cell format the
  reader parses, so the tripwire sees a date and passes;
- the **reconciler** — `key_from_raw` is `(normalized_land, iso_date)`, and the
  recovered date equals the predecessor's, so the row's key matches and
  `withdrawn_recent` does not fire. The `recovered_records` parameter was
  already wired and already routes the row out of the edit count.

**The 編號 renumbered the whole corpus.** The payload diff: 681 projects
changed and 1 is new — and **680 of the 681 changed projects have identical
content** (dates, names, stages, land, links). The change is the 編號: the
2026-10-28 gazette re-sorts its history by 核定日期, so every 編號 moved
(編號 is a coordinate, not an identity — AGENTS.md). The one project whose
content differs gained the new 2026-10-28 approval (case `10609183`).

That renumbering broke `tests/test_merge_count_shrink.py`, which keyed its
measured pairs on 編號. The pairs are now identified by their **content** (the
unit's fragment and the two counts). Two of the eleven units (桃源段三小段251,
玉成段五小段545) are no longer in the corpus — and were absent from the
2026-10-15 corpus too, so they had gone before.

**The cross-reference, re-run against the fresh payload:** 429 unmatched, 338
found by section+parcel, **88 genuinely unmatched** — 0 in processing, **3
already approved** (the known revoked cases of D9d), 85 undated (the in-review
cases).

**What follows is the record of the refusal.**

**What was done.**

- `scripts/poll_p168.py` — the 168 poller. It fetches the list (one request,
  sized by the `TotalCount` the endpoint reports), writes a snapshot under
  `urtpe-gazettes/p168_snapshots/`, and detects a change by **content hash**.
  It never ingests and never writes `data/.link_cache/` — the gazette poller's
  rule (AGENTS.md: "Acquisition is separate from ingestion").
- The Windows task `urtpe-poll` now runs **both** pollers, still weekly on
  Monday 06:30. Task run 2026-11-06 09:43, **Last Result 0**. The 168 log
  shows the first snapshot, then "unchanged" on the next check.
- The gazette poller found a **new gazette** on that run and archived it:
  `核定案件-2026-10-28.pdf`, publisher 資料更新 115-11-03 13:47, SHA-256
  `2afa1ba6…`. It is archived and **awaiting explicit ingestion** — the
  poller never ingests.

**The naming, first.** The board calls it "the 2026-11-03 gazette". That is
the **publication date** (the publisher's 資料更新 stamp), not the gazette's
identity. The document's own 統計至 line reads **115年10月28日** = 2026-10-28,
and the two files in the archive are **byte-identical** (both SHA-256
`2afa1ba6…`): `核定案件-2026-11-03.pdf` (saved by hand on 2026-11-03 15:56) and
`核定案件-2026-10-28.pdf` (archived by the poller). One document, two names.

**The refusal.**

```
tripwire: FAIL (1 fault(s))
  records: 1440  projects: 680
  calendar: mixed:gregorian  duplicate 編號: 0
  INCOMPLETE: 4 record(s) excluded because the publisher truncated their 地號 cell
  - 1 record(s) with an unparsed 核定日期: 3
```

Exit code **4** (`TripwireFailure`). Per the contract, **nothing was
written**: `data/projects.json` is byte-identical to its pre-ingest state
(SHA-256 `355b8208e9d4…`), and `clean.tsv`, `merged.tsv` and
`viewer/projects.data.js` keep their earlier timestamps.

**The fault is the publisher's, not the reader's.** 編號 3 is
`變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市更新事業計畫案`
(大安區, 永陞建設股份有限公司, 奇模工程有限公司). Every other cell is
complete; the 核定日期 cell is **empty**. Verified three ways
(`scripts/probe_p20261103_row3.py`):

1. the ruled table's own cell for row 3 reads `['3', '', '大安區', '變更(第二次)…']`;
2. the page's text jumps from `3` straight to `大安區` — **no ink at all** in
   the date column (the words inside the row's bounding box are `3`,
   `大安區`, the 案名, the 地號, the 實施者, the 規劃單位 — and nothing in
   between);
3. the extracted record carries `date: ""` and every other field verbatim.

So the publisher printed a row with no approval date. The tripwire's rule is
the spec's rule ("Never repair absent data by inference"), and a record whose
date is unknown cannot be placed on a timeline, dated, or reconciled against
its predecessor.

**Why this is a hard stop, not a problem to work around.** The plan's hard
stops name a non-zero CLI exit (2, 3, 4, 5, 1) and a tripwire raise. Exit 4
is both. The way past it is **not** a bypass flag — the tripwire has no
bypass — and it is not a reader change, because the reader is right.

**What the ingest would have produced** (measured offline, not written): 1,422
records read, 23 excluded as publisher-truncated (編號 69, 81, 190, 572, 674,
697, 704, 721, 728, 798, 829, 853, 865, 904, 914, 921, 932, 946, 999, 1007,
1133, 1208), 1,422 cleansed, **676 projects** (today: 681 on the 2026-10-15
gazette). The reconciliation against the 2026-10-15 predecessor was not
reached — the tripwire runs before it.

**Correction (2026-11-06).** The count was first written as 677. That figure
came from a probe that **skipped the correction ledger**; the real ingest
applies it (`urtpe/cli.py:434-440`). Measured with the ledger applied:
**676** projects — the ledger's two 吉林676 entries merge one pair, so the
family count falls by one more than the no-ledger figure shows. The ledger
report is clean: 2 corrections applied, **0 unmatched**.

**What would unblock it.** Three readings, in the order they cost:

1. **The city re-prints the row with its date.** Then the ingest runs as
   planned. The publisher's stamp is 115-11-03, so a corrected document may
   already exist.
2. **The approval date is recoverable from another source** — the city's
   platform holds the case by 案名 and 核定日期 (the `11412011` shape), so the
   date could be recovered by the **recovery pass** (`--recover-truncated`),
   which the spec already has for exactly this class of publisher defect. The
   record's 地號 cell is complete, so it is not a truncated 地號 row; it is a
   truncated **date**, and the recovery pass's scope would have to widen.
   **Explored below — the rule exists and works.**
3. **The row is excluded and named**, like the 23 publisher-truncated 地號
   rows. That is honest — the exclusion count is reported — but it drops a
   real approval from the dataset, and the tripwire's date rule would need to
   learn the exclusion.

**DECIDED and IMPLEMENTED (user, 2026-11-06).** The user agreed reading 2
— the widened recovery pass — and added the 168 list's `MEMO` as a fourth
source. The implementation landed as step 9a, and the ingest it unblocked
succeeded. See "D9f-1" below for the rule and the measurements, and "D9f — the
ingest was refused, then unblocked" above for the outcome.

### D9f-1 — the recovery pass, widened to a truncated DATE (explored 2026-11-06)

Reading 2 was explored to the point where the rule is written down. **It
works.** The date is recoverable, the acceptance is provable, and the
residual is small and characterised. What is left is the user's call on
whether to adopt it, because it changes what the pipeline writes.

**The shape of the defect.** For a truncated 地號 row the recovery pass
anchors on the **date** and the name is a filter: the 地號 cell is the
damaged part, so the surviving date identifies the case. For a truncated
**date** row the roles reverse — the 案名 must carry the identity alone, and
the date is what gets recovered. That is why the existing rule cannot be
reused as it stands: `match_row`'s check 4 asks the candidate's date to equal
the gazette's, and the gazette's is exactly what is missing.

**What the row keeps.** 編號 3's 案名 is complete, and
`R.parse_identity` reads it without help: district 大安區, section 通化段四小段,
mono 0336, count fragment `等26筆(原22筆)`, address core
`臺北市大安區通化段四小段336地號等26筆(原22筆)`. The 地號 cell is complete
too — 26 parcels, and the 案名 declares 26. So the row's **identity** needs
nothing repaired; only its date is missing.

**The rule, measured over 59 gazette rows** (one parcel search per row, one
header per candidate; `scripts/probe_recovery_date_rule_final.py`):

| check | what it reads |
|---|---|
| 1 | same unit — district + 段/小段 (the existing rule) |
| 2 | the **declared count** agrees (the existing rule, compared as a count — see F2) |
| 3 | the **stage ordinal** agrees — 擬訂 / 變更 / 變更(第二次) … (**new**) |
| 4 | the **track set** equals the row's — 事業計畫 / 權利變換 / both (**new**) |
| 5 | the approved candidates carry **ONE** date — the acceptance |

| Outcome | Count |
|---|---|
| **recoverable — exactly one date** | **57** |
| no candidate survives the name rule | 2 |
| **several dates — ambiguous** | **0** |

Checks 3 and 4 are what make it work. The name alone leaves **10 of 23**
rows ambiguous in the first measurement: the candidates are the unit's
successive revisions, each with its own approval date. The stage ordinal
resolves 8 of those; the track resolves the rest.

**Three defects the measurement found**, each fixed in the probe:

- **F1 — a compatibility ideograph.** The city writes 利 as **U+F9DD** (CJK
  COMPATIBILITY IDEOGRAPH-F9DD) in one case name (`11507018`), not U+5229.
  The character looks identical; the keyword `權利變換` does not match, and the
  row reads as 事業計畫 alone. **NFKC** folds it. Measured
  (`scripts/probe_compat_ideographs.py` live, `scripts/probe_compat_population.py`
  offline): the corpus's own 1,444 案名 carry compatibility ideographs in
  **6** rows — but for 北 / 都 / 更, which sit in the district name and in
  都市更新, where no track keyword touches them (the corpus is unaffected
  **by the track reader**; see D16a, D16c) — and **0** rows carry a
  compatibility 利. The city's case names carry exactly **1** of the 2,024 we
  hold (the `11507018` case). So the corpus is clean for the track; the
  platform side is not.
- **F2 — the count is written two ways.** A 案名 may write `地號N筆` rather
  than `等N筆`. The existing count-fragment check then rejects **every**
  candidate, including the right ones. The fix compares the **declared
  counts**, not the fragment strings — which also makes a real disagreement
  refuse (recno 40: the row says `等12筆`, the city says `等13筆`).
- **F3 — the track relation is equality, not a subset.** A subset relation
  admits the area-split twin (recno 10: `10012274` is 事業計畫, `11507024` is
  權利變換, and the row names 權利變換 alone) and creates a new ambiguity
  (recno 27). Equality keeps the residual at **0** ambiguous rows.

**A latent bug the exploration exposed.** `R.date_check(d1, d2, want)` with an
**empty** `want` returns `("exact", "uro_chk_date2")` — it matches the *empty*
second header field against the empty `want` and reports the wrong field
name. A false "exact". It is **latent today**: `_recover_one` returns early
when the date does not parse (`urtpe/recovery_pass.py:79-80`), so
`date_check` never sees an empty `want`. But a widened rule would hand it one
on every call, so the guard has to move (or `date_check` has to refuse an
empty `want`) before the widening lands.

**The accuracy, measured against the corpus's own dates.** The rule's job is
to replace a missing date, so it must recover the date the row would have
carried. Over the same 59 rows:

| | Count |
|---|---|
| the recovered date **equals** the corpus's own date | **55** |
| the recovered date differs | 2 |

The 2 disagreements are two distinct shapes:

- **recno 37** — 1 day apart (corpus 2026-07-01, platform 2026-07-02). The
  existing `date_check` already calls this `pm1` and accepts it when no exact
  candidate exists. The city and the platform differ by a day — the case the
  flag exists for.
- **recno 47** — 16 days apart (corpus 2026-06-01, platform 2026-06-17). **No
  candidate carries 2026-06-01** — not `11410007` (2026-01-21 / 2026-05-08 /
  2026-06-17), not `10912091` (2023-11-23), not `10501282` (2020-09-30). The
  PDF and the platform genuinely disagree, and **the name-only rule cannot
  recover the PDF's date** — it would write the platform's date instead.

**That is the rule's honest limit.** The rule recovers **the platform's**
approval date. Where the PDF and the platform agree — 55 of 57 — the recovered
date is the date the row would have carried, and the PDF's empty cell is filled
with the city's own statement. Where they disagree, the rule writes the
platform's date, and the disagreement is **invisible** unless it is flagged.

The 168 list's `MEMO` was added as a fourth source to settle exactly those
cases. It cannot: **all 33** disagreement cases have an empty MEMO, and the
MEMO is a different date (the 核定公告, not the 核定) where it is present. It
joins the rule as a **flag**, not as a source — see D9f-2 below.

For **編號 3 specifically** the two agree: the rule recovers **2026-10-15**
from one candidate (`11501034`, `uro_chk_date`), and the corpus already holds
that exact date as node recno 1 of `大安區-通化段四小段-336地號等26筆`. So for
this row the widened rule and the current dataset would not disagree.

#### D9f-2 — the 168 list's MEMO as a fourth source (user's addition, 2026-11-06)

The user added: for the rows where the platform's date disagrees with the PDF's,
check the **approval date in the 168 list** instead of the platform's. The
list's `MEMO` field carries a `核定公告` date, which looked like a third
source independent of both the PDF and the platform.

**Measured (`scripts/probe_168_memo_role.py`,
`scripts/probe_168_memo_coverage.py`) — the source does not exist for the rows
it would have to serve.**

| | Count |
|---|---|
| the list's rows | 466 |
| of those, carrying a `MEMO` date | **146** (135 with 核定公告) |
| of those, **no** date (`MEMO` = `-`) | 320 |

**The list is dated exactly where the case has been announced.** The dated
rows are the 核定階段 ones — 134 of the 137 dated rows sit in 核定階段. The
rest of the list is a register of cases still in review, which is what the
list is for.

**And the coverage is exactly inverse to the need.** Of the **33** cases in
the corpus where the PDF's date and the platform's date **disagree**:

| | Count |
|---|---|
| the list holds the case, **but its MEMO is empty** | **33** |

**Every single one.** The list's MEMO is empty for every case where the two
sources disagree — including the two that matter here:

| case | the PDF | the platform | the MEMO |
|---|---|---|---|
| `11502013` (recno 37) | 2026-07-01 | 2026-07-02 | `-` |
| `11410007` (recno 47) | 2026-06-01 | 2026-06-17 | `-` |
| `11501034` (編號 3) | 2026-10-15 | 2026-10-15 | `-` |

**The MEMO is a different date, not a second copy of the 核定日期.** Where the
MEMO and the case's own 核定日期 can both be read (109 joinable rows): they
**agree in 99** and **differ in 10** — by weeks or months
(`10401051`: the 核定日期 2023-06-08, the MEMO 2023-02-20). The MEMO is the
date the city **announced** the approval; the 核定日期 is the date it was
approved. A 核定公告 lags the approval by the time between the two events.

So the MEMO is **not** a substitute for the platform's date — it is a third
date, and a later one. It cannot decide which of the PDF's and the platform's
dates is right.

**What the MEMO IS good for, and it is worth having.** It is an independent
statement of the city's own announcement, so it is a **check** on a recovered
date: a MEMO that disagrees with the platform's 核定日期 is a signal that the
two differ, and a MEMO that agrees is a second confirmation. But:

- it is empty for **319 of 466** rows, so it is silent for most cases;
- it is empty for **all 33** disagreement cases, so it says nothing exactly
  where a tie-breaker is needed.

**The recommendation: the MEMO joins the rule as a FLAG, not as a source.**
When the list holds the case and its MEMO carries a date, the recovered date
is compared against it, and a disagreement is recorded — a `核定公告`-date
disagreement is a distinct signal from a PDF-vs-platform one, because it says
the city announced the approval on a different day than it approved it. The
recovered date itself still comes from the platform's own 核定日期.

**One thing the MEMO does settle.** For 編號 3 the list holds `11501034` with
`stage` = `-` and `MEMO` = `-`: the case is in the list but **not announced**
on the list. The list is therefore no evidence about this approval at all, and
the platform's `uro_chk_date` remains the only source — which is also the
source that agrees with the corpus's own date.

**What the widened rule must also do, beyond the date** (each is a separate
decision):

1. **The tripwire must learn the exclusion.** The date rule fires on the
   *read* rows; a recovered row must be exempt, or the tripwire still refuses.
2. **The reader must mark the row.** The extraction path marks a truncated
   地號 cell with `source_fault`; a truncated date needs its own marker, and
   `to_raw_records` must carry it (`urtpe/extract.py:856-861` already appends
   `核定日期缺漏` to `parse_error`).
3. **The 編號 must not be trusted.** The row is 編號 3 in the new document and
   recno 1 in the old one. 編號 is a coordinate, not an identity (AGENTS.md),
   so the recovered row must key on its land core and date, not its 編號.
4. **The reconciliation must not read the recovery as publisher movement.**
   The reconciler has a `recovered_records` parameter for exactly this — "a
   reader-side completion filed in the publisher's column" — and the recovered
   row must be listed there, or the run reports the city as having edited or
   withdrawn an approval it never touched.

**The 2 residual rows are not rule gaps.** recno 40's count disagreement (the
city says 13 parcels, the row says 12) and recno 53's missing candidate (the
row's 變更/權利變換 approval is not in the family's candidate set at all — a
pre-existing parcel-search recall limit, the D9c-2 shape). Both must refuse.

**The cost.** One parcel search and one header per candidate, per row with a
truncated date, plus **one** 168-list read per run (the list is a single
request — D9f's poller already fetches it, and the snapshot under
`urtpe-gazettes/p168_snapshots/` is the same content). The 2026-10-28 gazette
has **1** such row. The reader's own 23 excluded rows are the publisher-
truncated 地號 rows, which the pass already handles.

**AGREED (user, 2026-11-06).** The rule is adopted: widen the recovery pass to
a truncated **date** cell, with the 168 list's `MEMO` added as the **fourth
source** — and, as measured in D9f-2, the MEMO joins as a **flag** rather than
as a date source, because it is empty for all 33 cases where the PDF and the
platform disagree, and it is a different date (the 核定公告) where it is
present. The recovered date comes from the platform's own `核定日期`; a MEMO
that disagrees with it is recorded as a flag.

**The implementation is done** (`836b289`, archived
`2026-11-06-recover-truncated-date-cells` `8512063`). The change was five
edits across four modules plus a spec delta — and **two of the five turned
out to be unnecessary**:

1. `urtpe/extract.py` — the reader marks a truncated **date** cell with its own
   `source_fault` (today it only marks a truncated 地號 cell), and
   `to_raw_records` carries it. **Done.**
2. `urtpe/recovery.py` — the name-only rule (F1's NFKC, F2's count
   comparison, checks 3 and 4), plus **D17**: `date_check` must refuse an
   empty `want`. **Done.** Plus one thing the design did not foresee: the
   recovered date must be written in the **cell format** (`2026/10/15`), because
   the reader's `to_iso` accepts `YYYY/M/D` and `YY/M/D` and **rejects** the
   hyphenated form — an ISO date would have failed the tripwire and the
   cleanser.
3. `urtpe/recovery_pass.py` — the widened path: the date is recovered, the
   MEMO is compared and flagged, and the provenance records which source
   closed. **Done.**
4. `urtpe/tripwire.py` — a **recovered** row is exempt from the date rule.
   **NOT NEEDED.** The recovery pass runs *before* the tripwire
   (`urtpe/cli.py:292` against `:322`), and the recovered date is written in a
   format the reader parses, so the tripwire sees a date and passes.
5. `urtpe/reconcile.py` — the recovered row is listed in `recovered_records`.
   **NOT NEEDED.** The recovered date equals the predecessor's, so the row's
   identity key matches and `withdrawn_recent` does not fire; the
   `recovered_records` parameter was already wired and already routes the row
   out of the edit count.

**The board's D9g order changed as planned.** Step **9a** was the
implementation of the agreed rule, and it **gated step 9's ingest** — a
precondition, not a follow-up. The D9f-2 addition (the MEMO as a flag) was
part of 9a's change, not a separate step.

### What the reconciliation would have said (measured, 2026-11-06, superseded)

The tripwire runs before the reconciliation, so the reconciliation never ran
inside the CLI on the refused ingest. Measured offline against the current
`clean.tsv` as the predecessor:

```
reconcile: 2026-10-15 -> 2026-10-28
  new approvals: 2   net change: -20 (1442 -> 1422)
  historical rows changed: re-dated 5, edited 1, vanished 19 (accepted: 0)
  ~ withdrawn recent approval: 大安區 …通化段四小段336… @ 2026-10-15
  BLOCKING: the list shrank: 1442 -> 1422 records
  BLOCKING: 1 approval(s) from the previous newest cohort (2026-10-15) are
            absent from the new one: 大安區 …通化段四小段336… @ 2026-10-15
```

**Only 2 approvals are genuinely new**: 玉泉段二小段452-2 (大同區) and
通化段一小段812 (大安區). The rest of the document re-publishes what the
dataset already holds. **The real ingest agrees**: 2 new approvals, and
**0 re-dated, 0 edited, 0 vanished** — because the recovery pass completed
the empty date and the row's identity key then matched the predecessor's.

**編號 3 IS the 2026-10-15 approval, re-published with an empty date.** The
reconciler names it as a *withdrawn recent approval* — because the row's date
is empty, its identity key no longer matches. The approval is not withdrawn:
the current dataset holds it as node recno 1 of
`大安區-通化段四小段-336地號等26筆`, dated 2026-10-15, bound to the city's
case `11501034`. And the city agrees: that case's header reads
`uro_chk_date 2026-10-15` and its data2 reads `核定日期 2026/10/15`.

**The net change is -20, and most of it is the reader's own exclusion.** The
gazette holds 1,442 編號; 23 rows are excluded as publisher-truncated (the
地號 cell) and 1,422 are read. The reconciliation compares the **read** rows
against the predecessor's 1,442, so the exclusions appear as 19 vanished +
1 edited + 5 re-dated. That is why the report says "the list shrank". The
excluded rows are named in the ingest output; they are not lost.

**The 168 list names the case but not its date.** The list holds three rows
for the unit `通化段四小段336`: `10011271` (擬訂, `MEMO` = 2022/08/02核定公告),
`10011273` (變更, `MEMO` = 2023/03/21核定公告) and `11501034` — **the exact
case of 編號 3** — with `MEMO` = `-` and `stage` = `-`. So the list's `MEMO`
field carries the approval date for the *approved* rows, and carries nothing
for this one. The date is recoverable, but from the **city's own case
record**, not from the list.

**A measurement trap, for whoever repeats this.** The predecessor for the
reconciliation is the **previous gazette's rows** — the current `clean.tsv`,
1,442 rows. It is NOT `urtpe.corpus.build_corpus`, which returns candidates
from **every** archived gazette (79,895 rows on this archive) for the
recovery pass's use. Reconciling against the corpus reports a nonsensical
"79895 → 1440" and 790 re-dated rows. The figures above are the ones against
`clean.tsv`.

**What was NOT done in step 9.** The cross-reference against the fresh 168
snapshot (`scripts/probe_crossref_p168_gazette.py`) was not re-run: it reads
`data/projects.json`, and the dataset is still the 2026-10-15 one. The
re-emit did not happen, because the ingest did not.

## D9g — consolidated execution order

Every decision is made (D13, D8 per case and D14(b) on 2026-11-06). The measurements changed the order three times: D9c
option 1 is withdrawn (D9d), D6's restore method is **not** `--fresh` (it
renames the whole cache), and D9c-2's fix layer waits on a live search.

**ALL STEPS ARE DONE (2026-11-06).** Step 9a was added when step 9's ingest
was refused — the widened recovery pass (D9f-1) became the precondition for
the ingest, not a follow-up — and the user's fourth source (D9f-2, the 168
list's 核定公告 date) joined it as a **flag**. The corpus stands at **1,444
records / 682 projects**, published 統計至 2026-10-28.

**Order:**

| Step | Finding | Priority | Form | Depends on | Gate |
|---|---|---|---|---|---|
| 0 | D14 — the `--from-js` loader round-trips `stage_事業計畫`, `stage_權利變換`, `recovery` and `district_land` (no coercion of `''`); round-trip test is the gate | **P1** | direct `fix:` + test (no re-emit of its own) | — | **DONE** `8d480a0` — 537 nodes changed a field across one rebuild before the fix (533 `stage_事業計畫`, 533 `stage_權利變換`, 4 `recovery`, 4 `district_land`), 0 after; suite 1005 passed / 1 skipped |
| 0b | D14(b) — `_land_district` reads the collected 12-district enum (7 rows change) | **P2** | openspec change (`cleanse`) + 2 tests | — | **DONE** `12bfe5c`, archived `2026-11-06-district-land-from-district-enum` (`dc27ce0`) — 7 rows change (153, 382, 928 → 大安區; 926 → 士林區; 488, 558, 927 → `''`); 0 section / parcel / land_count / name / flag / other-field changes over the 1,442 rows; the flag still fires on 488/558/927; suite 1013 passed / 1 skipped |
| 1 | D7b — name the 50 divergences unexplained by subset or permutation | **P1** | measurement only | — | **DONE** — 634 in sync, 35 explained by an ordered subset, 0 by a permutation, **50 unexplained**: 20 `STALE_MERGE` (a case still holds the stored value; only the merge moved), 16 `NEW_LABEL` (a case appended after the merge), 3 `WITHDRAWN`, 11 `MIXED`; 0 of the 50 explained by any of 5 merge orders; the fix (D7 = overwrite) repairs 36 of them and drops the withdrawn labels in 14 |
| 2 | D7 + D8 + D13 — one `refresh_project` edit: re-derive `taipei_milestones`; re-fetch `data3`/`data4` **per case**; label a case 無 when its header row and data2 are both empty. One cache pass + one re-emit | **P1** | openspec change (pipeline) | steps 0, 1 | **DONE** `2d9cccf`, archived `2026-11-06-refresh-rederive-and-refetch` (`054099a`), re-emit `0da2dd2` — 380 of 681 projects changed, **0 with no explained cause** (D7 274, D8 31, D10 30, REFRESH_STATUS 12, D15 19, D15b 11, D13 3); the 718 caches that hold per-case milestones are now **all in sync** (was 85 divergent, 50 unexplained); **3** cases labelled 無 (`11501041`, `11410001`, `10310102`); **41** implementation cases re-fetched; D8's scope is **37 cases in 32 projects**, not 26 in 22 (the board's probe's approval list omitted `權變核定日期` and `概要核准日期`); suite 1056 passed / 1 skipped; viewer smoke passed |
| 3 | D10 — permit-witness selection: the permit whose 開工日期 matches the city's; otherwise mark `links.permit.ambiguous` (decided) | **P2** | openspec change (`official-link-discovery`) + re-emit | step 2 | **DONE** `38b411c`, archived `2026-11-06-permit-witness-by-construction-start` (`054099a`) — **15** witnesses moved to the right permit, **15** became ambiguous, 0 dropped; the projects whose witness date differs from the city's 使照 fall **43 → 23** (the 20 the board measured are fixed); 寶清57-13 now names `114使字第0094號`, 金華719 names `115使字第0018號`; the re-emit is `0da2dd2` |
| 4 | D6 — re-key `data/twur_overrides.json` to `…等2筆`, correct `PID`, add the dataset-key test, then `discover_project_links(fresh=True)` on that one project (decided, option A) | **P2** | direct `fix:` + one-project restore + re-emit | step 0 | **DONE** `e3b2b8e`, re-emit `4b120e4` — the record re-keyed to `…等2筆`, `PID` corrected, the dataset-key test added (`tests/test_twur_override.py`); the restore gained the **7** national milestones, the `twur_name` and the `view.html`; the re-emit changes exactly **1** project (`twur`, `twur_name`, `milestones_national`, `view_verified_case_ids`); the `[WARN] twur override names a project not in the dataset` line is gone; the viewer smoke counts **622** projects with a national page (was 621); suite 1057 passed / 1 skipped |
| 5 | D9c-2 — live parcel search for the 2 sibling projects | — | probe | — | **DONE 2026-11-05**: the city's search does not index either sibling |
| 5a | Header pass over the 84 "no link, no parcel match" cases | — | read-only probe | — | **DONE 2026-11-05**: 78 in review, 5 closed, 1 revoked |
| 6 | D9c-2a — (a) merge the stranded `南港566…等6筆` cache into the live `…等1筆` dir (offline; binds nodes 744 and 1063); (b) second id source for ids in no cache (`11412011`); (c) stop a stub from shadowing an aliased dir. One re-emit | **P2** | (a) cache merge; (b)+(c) openspec change + `urtpe/links.py` + test | **step 2** | **DONE** `a2f307b`, archived `2026-11-06-cache-alias-merge-and-second-id-source` (`0f238b8`), re-emit `1cb32f4` — **4** projects changed, all explainable (南港566 the merge, 玉成166 `11412011` added, 玉成253-1 `10203261`/`10203262` added, 青年130 node 78 binds `11510008`); the unplaced flag falls **16 nodes in 11 projects → 13 in 9**; the 168 list's paging is broken (each page advances by 1 row) — one request with `TotalCount` returns all 466; the scope is the section AND the parcel, adjacent; suite 1069 passed / 1 skipped; viewer smoke passed |
| 7 | D9e — offline test: all 54 in-processing case_ids resolve (54/54 pass today) | **P2** | `tests/` | — | **DONE** `02b71fa` — `tests/test_in_processing_cases_resolve.py`: 54 of 54 resolve (52 at the node level, all 54 at the project level, 0 in neither); offline, no network; suite 1072 passed / 1 skipped |
| 8 | D11 — record the A/B/C shared-dependency finding | — | docs | — | **DONE** (this board) |
| 9 | D9f — 168 poller + hash change detection in the `urtpe-poll` task, then one ingest of the 2026-11-03 gazette and a cross-reference against the fresh snapshot | **P2** | poller script + task action + ingest + re-emit | steps 0b, 2, **9a** | **DONE** — the poller and the task action (`scripts/poll_p168.py`; the task runs both pollers; task run 2026-11-06 09:43, Last Result 0); the **ingest succeeds** with `--recover-truncated`: **exit 0**, tripwire **PASS**, `編號 3: RECOVERED 核定日期 2026/10/15 (cases 11501034, from the 案名 alone)`, 5 recovered / 0 residual; reconcile **0 re-dated, 0 edited, 0 vanished**, 2 new approvals, net +6; ledger 2 applied / 0 unmatched; **1,444 records / 682 projects**; the cross-reference re-run against the fresh payload (429 unmatched, 338 found by section+parcel, 88 genuinely, 3 of them the known revoked cases); re-emit `eafb9dd` |
| 9a | **D9f-1 + D9f-2** — widen the recovery pass to a truncated **date** cell; the 168 list's `MEMO` is the fourth source (as a **flag**) | **P1** | openspec change (`truncated-row-recovery` + `pdf-tsv-extraction` + `gazette-reconciliation`) + code + test + one ingest | step 9 | **DONE** `836b289`, archived `2026-11-06-recover-truncated-date-cells` (`8512063`) — the rule recovers **57 of 59** gazette rows with **0** ambiguous; the recovered date equals the corpus's own date in **55 of 57**; 編號 3 → **2026/10/15**, the date the corpus already holds. The MEMO is a **flag** (empty for all 33 PDF-vs-platform disagreement cases; a different date where present). **The tripwire needed no exemption** — the recovery runs before it — and the reconciliation needed no change: the recovered date makes the row's key match the predecessor's. Suite 1086 passed / 1 skipped |
| 10 | D9c-4 — monitor the 78 in-review cases after each new gazette | **P3** | re-run the cross-reference scripts | step 9 | **DONE** — re-run against the fresh 2026-10-28 payload: **343** of the 168 list's 466 cases found in the gazette (was 341 on the 2026-10-15 payload), 123 not found; **52** of the 54 in-processing cases still resolve (the 2 that do not are new to the list); the deep cross-reference: 429 unmatched, **338** found by section+parcel, **88 genuinely unmatched** — 0 in processing, **3 already approved** (the known revoked cases of D9d), 85 undated (the in-review cases) |
| 11 | D13 — folded into step 2 (decided 2026-11-06) | — | — | — | see step 2 |
| 12 | D15 — sort a node's `review_flags` by a stable key | **P3** | openspec change (emitter) + test | — | **DONE** `cce5625`, archived `2026-11-06-stable-review-flag-order` (`13baf68`) — the emitter sorts by (case id, text); 20 nodes' flag order changes on the live payload, 0 flag sets and 0 flag counts change; suite 1020 passed / 1 skipped |

**Why this order.**

- **Step 0 first.** D14 is a loss on the rebuild path. Every re-emit in steps
  2, 3, 4, 6 and 9 runs through `--from-js`, so each one would drop the 533
  sub-stages again. A restore from `viewer/projects.data.js` is not lossless
  until D14 lands. It is small and has no network or cache dependency.
- **Step 0b before step 9.** The enum read is a cleanse rule, and only a PDF
  ingest re-cleanses. Step 9 is the next ingest (the 2026-11-03 gazette).
  `--from-js` re-emits in steps 2–6 carry the stored value, so they do not
  need 0b.
- **Steps 1–2 first.** D7 and D8 are the only findings that put *wrong data on
  screen today* (84 caches lose a milestone label; 14 projects hide a
  construction date the city publishes). D13 is the same `refresh_project`
  edit (a stale 已核准 on an emptied case). They share one edit and one
  re-emit, so splitting them would pay the ~23 MB write twice. D8 is now per
  case, so the cache pass refetches 26 cases in 22 projects, not 6 projects.
- **Step 12 (D15) before step 2, if ready.** It is an emitter sort and adds no
  write of its own; it rides step 2's re-emit, or the next one.
- **Step 3 after step 2.** D10's flag path reads `links.milestones_taipei`
  (`urtpe/links.py:3378-3381`) — the dict D7 corrupts. Landing D10 on the
  repaired dict means the flag sees correct values, and step 2's re-emit can
  carry D10's payload change with no extra write.
- **Step 4 before step 6.** D6 is a config record plus a one-project cache
  restore plus a re-emit. Doing it first means step 6's re-emit carries the
  restored 國 badge too, and the re-emit count stays at 3 rather than 4.
- **Step 5 is done.** The live search showed the fix belongs in the id source,
  not in the search guard or the attach step.
- **Step 6 after step 2.** `refresh_project` appends a newly found case id
  without re-deriving `taipei_milestones` — that is D7 cause 1. Run before the
  D7 fix, it would create a new divergence on the two sibling projects.
- **Step 6 uses `refresh_project`, not `--fresh`.** `refresh_project`
  (`urtpe/links.py:1786`) is project-scoped: it re-fetches one project's cases,
  re-runs the parcel search (which is what surfaces the sibling case_id), and
  re-runs the view-page absorb. `--fresh` would rename the whole cache
  (`urtpe/links.py:3402`) — the 2026-08-24 incident shape.
- **Steps 2, 3, 4, 6 share re-emits.** Each re-emit rewrites all six tracked
  files plus `viewer/projects.data.js` (~23 MB). Do not batch them into one run
  without measuring — D7 and D8's shared edit is justified because it is *one*
  code change; D10, D6 and D9c-2a are separate concerns.
- **Step 7 is offline.** It needs no re-emit and no network, so it can land
  anywhere. It goes here because it locks in what D9b measured.
- **Step 8 is docs only.** It records the A/B/C shared-dependency finding that
  was answered in chat and never written down.
- **Steps 9–10 last.** The 168 poller is acquisition, and the monitor depends on
  it. Neither changes emitted data on the current gazette. **Step 9a's
  exception is below.**
- **Step 9a (D9f-1 + D9f-2) gates step 9's ingest.** The ingest is
  refused by the tripwire because the 2026-10-28 gazette prints no 核定日期
  for 編號 3. The widened recovery pass is the **only** reading that both
  keeps the approval and lets the ingest proceed — reading 1 (the city
  re-prints) needs no code but no date; reading 3 (exclude the row) drops a
  real approval and still needs the tripwire to learn the exclusion. So 9a
  sits **before** the ingest, not after it: it is a **precondition** of step 9,
  not a follow-up. It is P1 — it is the only thing standing between the
  corpus and a gazette. The rule is **agreed** (user, 2026-11-06): the
  recovered date comes from the platform's own 核定日期, and the 168 list's
  `MEMO` joins as a **flag** — it is empty for all 33 PDF-vs-platform
  disagreement cases, so it cannot be the source that settles them.
- **Step 10 waits for step 9.** The monitor re-runs the cross-reference
  against a gazette the corpus has ingested. Until the ingest lands, the
  corpus is still the 2026-10-15 one and the cross-reference would answer
  against a stale payload. It stays P3.
- **Step 9's cross-reference also waits.** It reads `data/projects.json`, so
  it belongs after the ingest, in the same step.

**What D9c option 1 becomes.** Instead of a ledger entry, the 3 revoked cases
are **recorded as a negative** — the platform's approval was revoked, so the
gazette's silence is correct. The natural home is the same `no_match_ledger`
pattern the national-portal sweep already uses (a negative that expires and is
re-probed), not the correction ledger, which joins gazette records.

**What D9c-2 changes — decided by the 2026-11-05 probe and the alias check.**
The city's parcel index does not hold `10708311` or `11412011`, guarded or not.
`10708311` (with `10006032`) is already in the stranded `…等6筆` cache, which
the live id's stub shadows; merging that dir fixes 南港566's two unplaced nodes
offline. `11412011` is in no cache, so it needs the second id source: confirm
each id by its header and add it to `city_case_ids` in a refresh step. The
earlier branches ("the attach step drops one", "a refresh appends them", "fix
the guard") are withdrawn.

**Two-source coverage.** The recno PDF (gazette) and the 168 list together cover
approved → in-processing → revoked **for the 168 subset only**. What they do not
cover:

| Stage | Covered by | Gap |
|---|---|---|
| Submitted, awaiting approval | 168 list (`審查中`, `專案審查階段`, `報核-公展階段`, `審議階段`, `聽證階段`) | **the 168 list holds 376 of the 1,982 case ids the gazette links** — cases in review outside the 168 program are not listed |
| Approved | gazette PDF | none measured |
| Revoked / rejected / withdrawn | 168 list (`stage` = `-` or a terminal state) | 3 revoked cases confirmed absent from the gazette — correct |
| Construction execution (開工, 使照, 成果報備) | `third.ashx` / `fourth.ashx` | D8: 6 caches hold an empty `implementation`; 4 have a recoverable date |
| Post-execution | `third.ashx` `Report_Date` | 65 of 2,951 cached payloads carry it |

## D10 — the permit witness names the wrong permit (使照核發日期 vs 執照日期)

**Question (user, 2026-11-05).** Why do 使照核發日期 and 執照日期 differ, for
`松山區-寶清段一小段-57-13地號等1筆` (case `10212211`) and
`大安區-金華段一小段-719地號等1筆` (case `10308211`)?

**The mechanism.** The building authority's 使用執照摘要 open data is a **third
witness** for the 使照 date (`urtpe/permit_sources.py`, the
`building-permit-adapter` change). The viewer renders the witness beside the
使照 slot (`viewer/app.js:1364-1375`):

```
使照核發日期：2025/06/25　執照093使字第0294號（2004-09-14）
```

The two dates differ because **the emitted `links.permit` names the first
permit of a tie, not the permit the city's 使照 belongs to**.

### D10a — the selection rule is "first winner", and the tie is common

`attach_links_to_projects` (`urtpe/links.py:3371-3377`) takes `permits[0]`:

```python
if permits:
    best = permits[0]
    project.links["permit"] = {"permit_no": best.permit_no, "date": best.date, ...}
```

`match_project_permits` (`urtpe/permit_sources.py:113-135`) returns every
permit whose parcel overlap ties for the highest count, sorted by permit number
(`sorted(no for no, c in counts.items() if c == best)`). So `permits[0]` is the
**alphabetically first permit number**, which is the *oldest* one — not the one
the project's own 使照 came from.

The permit index keys on the **mono** parcel (the sub-parcel is stripped at
`urtpe/links.py:3359`, `mono = str(parcel).partition("-")[0]`). Every permit on
that mono number lands on the same key, so a section that redeveloped over time
accumulates permits — one per building phase.

### D10b — the two named cases, measured

**寶清57-13** — the project's parcel is `57-13`, so mono `57`. Four permits sit
on that mono:

| permit | 使照 | 開工 | 原核發執照 |
|---|---|---|---|
| 093使字第0294號 | 2004-09-14 | 2000-05-04 | 088建字第0418號 |
| 107使字第0028號 | 2018-01-30 | 2015-01-08 | 103建字第0067號 |
| 110使字第0038號 | 2021-03-23 | 2017-07-10 | 106建字第0020號 |
| **114使字第0094號** | **2025-06-25** | **2020-05-06** | 108建字第0140號 |

The city reports `Ulic_Date = 2025/06/25` and `Eng_Start_Date = 2020/05/06` —
**both** point at `114使字第0094號`, the *last* permit. The emitted witness is
`093使字第0294號` (2004-09-14), the *first*.

**金華719** — the project's parcels span 719…739 across its nodes, so the index
sees two mono keys with permits:

| key | permits |
|---|---|
| (`大安區`, `金華段一小段`, `719`) | 115使字第0018號 (2026-01-28, 開工 2021-12-23) |
| (`大安區`, `金華段一小段`, `739`) | 096使字第0079號 (2007-03-01), 096使字第0131號 (2007-04-20) |

All three tie at 1 parcel each. The city reports `Ulic_Date = 2026/01/28` and
`Eng_Start_Date = 2021/12/23` — **both** point at `115使字第0018號`, the one on
parcel **719**, the parcel the anchor node (recno 81, 變更(第三次), 2026-01-07)
carries. The emitted witness is `096使字第0079號` (2007-03-01), from parcel
**739** — a parcel the anchor no longer lists.

### D10c — corpus scale

Measured over all 681 projects against the live permit index (19,216 keys):

| Outcome | Count |
|---|---|
| City's 使照 == the **first** matched permit (witness is right) | 271 |
| City's 使照 == a **later** matched permit (**witness is wrong**) | **20** |
| City's 使照 matches **no** matched permit | 23 |
| More than one matched permit | 33 (24 with a city date) |
| **Emitted `links.permit.date` differs from the city's 使照** | **43** |

So **43 projects show a permit date that is not the project's own 使照**. The
flag mechanism does not catch them: `permit_review_flags`
(`urtpe/links.py:3380-3381`) fires only when the **city** and **national** dates
disagree, and these projects have no national 使用核發日期 at all — the flag
needs two portal values, and here only one exists. The witness is wrong and
**silent**.

### D10d — the disambiguator that already exists

The **開工日期** picks the right permit in both named cases and in **18 of the
33** multi-permit projects that carry one:

| Case | city's 開工 | permit with that 開工 | city's 使照 | that permit's 使照 |
|---|---|---|---|---|
| 寶清57-13 | 2020/05/06 | 114使字第0094號 | 2025/06/25 | 2025-06-25 ✓ |
| 金華719 | 2021/12/23 | 115使字第0018號 | 2026/01/28 | 2026-01-28 ✓ |

The permit record carries both dates (`PermitRecord.construction_start`,
`urtpe/permit_sources.py:43`). The 開工 date is the city's *own* value
(`Eng_Start_Date`), so it is a **citable disambiguator** — not an inference.

### D10e — the fix shape

**Rule (decided by the user, 2026-11-05):** when more than one permit matches,
pick the one whose `construction_start` equals the city's 開工日期. When that
does not leave exactly one, show **no single permit** and mark the payload
`links.permit.ambiguous` with the candidate list.

**Do not** fall back to "the permit whose date equals the city's 使照". That
makes the witness copy the value it exists to check, so it could never expose a
disagreement. The 開工 tier is safe because 開工 is a different field.

Effect on the 33 multi-permit projects: 18 resolve by 開工; 4 have no 開工 date;
11 have a 開工 date that matches zero or several permits. Those 15 show the
ambiguity instead of an arbitrary permit.

**Interaction with D8 (from `viewer-source-sync`).** 87 projects carry a permit
but no city 使照 date. `permit_review_flags` compares only when both portal dates
exist, so these 87 skip the comparison today. D8's refetch can fill 使照 for
some of them and move them into the comparison. 實踐641 is the known case: its
permit `096使字第0436號` (2007-10-31) equals the data3 使照 (2007/10/31), so after
D8 it should show agreement and no flag. A flag there is a real signal, not D8
noise.

**Order matters:** the 開工 date must be read from the **source map**
(`milestones_source`), not from `links.milestones_taipei` — the same rule D4a
already established for the construction chain. Reading the merged dict would
inherit D7's corruption.

**D7 interaction.** The flag call reads `project.links["milestones_taipei"]`
(`urtpe/links.py:3378-3381`) — the exact dict D7 finds corrupted. D7's fix
therefore **repairs the flag path too**, which is why D7 must land before D10's
re-emit.

**Form:** openspec change (`official-link-discovery` — the permit-witness
requirement) + payload re-emit. The selection rule is a pure function over
`(permits, 開工 date, 使照 date)`, so it is test-first and offline.

## D11 — the A/B/C surfaces share one milestone source, so D7 breaks all three

*The three surfaces share one milestone source (`links.milestones_taipei`), so
the D7 divergence is a single defect with three symptoms, not three defects.*

**Finding (measured by the `viewer-source-sync` session, 2026-11-05, HEAD
`6457de7`).** The three surfaces — A 相關連結, B graph node, C project list —
read label and status from different places:

| Surface | Label source | Status source | Code |
| --- | --- | --- | --- |
| A 相關連結 | `candidate_names[cid]` → node 案名; 國 = `twur_name` | `case_schedules[cid]` | `viewer/app.js:635-675`, `1516-1527` |
| B graph node | node `case_name`; 國 = `bindNationalLabels` | `node.links.taipei`, `stage_事業計畫` / `stage_權利變換` | `viewer/app.js:176-198`, `465-472` |
| C project list | `p.name` | `execStateOf` → `constructionStage` → `case_schedules` | `viewer/app.js:488-496` |

Measured against `data/projects.json` (681 projects, gazette 2026-10-15):

| Metric | Value |
| --- | --- |
| `candidate_names` | 674 of 681 |
| `twur_name` | 621 (all twur projects) |
| `case_schedules` | 622 |
| case ids that render with no display name | **0** |
| combined-track projects with a node carrying both sub-stages | 364 of 364 |

"0 unnamed" means: every case id in a project's `links.taipei` is anchored on a
node, or in `candidate_names`, `case_milestones` or `search_rejected`. None
fails all four.

**Conclusion.** The sync contract holds for name and status. It breaks only in
the milestone projection, and all three surfaces read it. That is why 寶清599
shows no 建照 in the list chip, none in the graph chain, and a 使照 國 badge
without its 建照 partner — and why D7 is P1.


## D12 — architecture concerns (review 2026-11-05)

Four concerns, each measured or read from the code. None blocks the batch; each
constrains how a D9g step is built.

1. **The 168 list is a program subset, not a register.** It holds 376 of the
   1,982 case ids the gazette links (D9). A poller over it sees the 168
   fast-track program only. The D9f plan and any "awaiting approval" view must
   say so, and must not present the list as the whole pipeline. A complete
   pending-case source is still unknown; finding one is open research.
2. **The parcel search has a recall limit.** The city's own parcel index omits
   two approved cases (D9c-2), and 16 nodes in 11 projects are unplaced
   (recounted after the `28d1eb5` ingest by graph-order-issues; step 6(a)
   fixes 2, D13 explains 1). The
   pipeline has one id source; a missing id stays missing with no signal except
   the unplaced flag. A second, header-confirmed id source (D9g step 6) is the
   structural fix; the 168 list closes 1 of the 16 today.
3. **Acquisition must not write durable state.** AGENTS.md: "Acquisition is
   separate from ingestion." The D9f poller may write only snapshots under
   `urtpe-gazettes/p168_snapshots/`. Ids from a snapshot enter `.link_cache`
   only through a separate refresh step under the single-writer lock and the
   coverage guard (`urtpe/coverage.py`).
4. **Peer sessions share this tree and cache.** Several sessions work in
   `D:\project\urTPE` at once. The lock serialises pipeline writers, but not
   hand-run scripts or doc edits. Before any cache-writing step in D9g (2, 3, 4,
   6), confirm no other session is running one.

Two smaller ones:

- **`--fresh` is a corpus-wide trap.** It renames the whole `.link_cache`
  (D6). Its help text says only "強制重新爬取". A per-project fresh path exists
  (`discover_project_links(fresh=True)`) but no CLI flag exposes it.
- **One-shot scripts accumulate.** This review added about 25 scripts. They are
  committed with the `probe_` prefix that AGENTS.md uses for archaeology, so
  they are not read as durable tools.

## D13 — 青年130 node 78 lost its `implementation` payload (peer graph-order-issues, 2026-11-05)

Project `萬華區-青年段一小段-130地號等3筆`, node recno 78 (2026-01-20).

**Cause.** The cache holds two live cases with the same name: `11501041`
(已核准) and `11510008` (已核定). Their `case_milestones` are identical; both
show 核定 2026/01/20. `_bind_from_name_step` binds only when exactly one live
case matches. With two matches and no area suffix, it returns `[]`. Node 78
thus has `links.taipei = []` and the flag 節點未能對應平台案件. A node takes
`implementation` only from an anchored case (`urtpe/links.py:3235-3241`), and
the one payload is under `11501041`.

**History.** `11510008` entered the cache in `c084833` (whole-corpus refresh,
2026-11-04). The `--from-js` re-emits copied the old `implementation` forward
and hid the loss. The PDF ingest `28d1eb5` re-derived every node and showed it.
A no-ledger A/B run shows the same loss, so D5 did not cause it.

**Live re-check (2026-11-06, user request) — the cache is stale.** The user
saw on the city platform that `11501041` is empty and `11510008` holds the
data. Ten read-only requests confirm it:

| Source | `11501041` | `11510008` |
|---|---|---|
| header (`get_project168_top.ashx`) | empty | 事業計畫階段─業經本府核定, `uro_chk_date` 2026-01-20 |
| data2 milestones | empty | 14 dates, same as the cache |
| data3 implementation | empty | 9 keys (`Settle_Old_Doors` now 140.0; the cache's `11501041` copy says 0.0) |
| data4 rewards | empty | 18 keys, same values as the cache's `11501041` copy |
| parcel search 青年段一小段/130 | **not returned** | returned, 已核定 |

The city moved the case from `11501041` to `11510008` and emptied the old id.
The cache still holds the old id as live (已核准) with the old payload.

**Why the refresh kept the stale case.**

1. `refresh_project` treats an empty header as no evidence
   (`urtpe/links.py:1895`: "a missing row ({} / None) is no evidence"). So
   `11501041` keeps 已核准.
2. An empty data2 keeps the cached milestones (`urtpe/links.py:1886`).
3. A case id that the parcel search no longer returns stays in
   `city_case_ids`. The refresh only appends.
4. `refresh_project` never fetches data3/data4 (D8). So `11510008` has no
   `implementation` entry. **D8's decided scope (option B: refetch only where
   the project's `implementation` is empty) misses this project**, because the
   dict holds entries for `10006192` and `11501041`.

Rule 1 is deliberate: one empty response can be a transient failure. The gap
is that no rule tells "the city removed this id" from "the request failed".

**Options (user decision), revised:**

1. **Retire a case the city removed.** Trigger: all of (a) header, data2,
   data3 and data4 are empty, (b) the parcel search no longer returns the id,
   and (c) a same-name sibling is live. Then mark the id 無 (or record
   `superseded_by`). The existing 無 rule in `filter_live_cases` then binds
   `11510008` alone. Add the per-case data3/data4 fetch for `11510008`.
2. **Prefer the case with a header** (tie-break in `filter_live_cases`). This
   binds `11510008` but leaves the stale `11501041` data in the cache.
3. **Leave it unanchored.**

Option 1 fixes the cause; option 2 hides it. Each needs an openspec change, a
test and a count of the other caches the rule changes.

**Decision (user, 2026-11-06): keep the empty case as an orphan, labelled
[無].** The city states nothing about a removal, so the pipeline must not
claim one: no retirement, no `superseded_by`, the id stays in
`city_case_ids`. The rule: when a refresh reads an **empty** header row
**and** empty data2 for a case, it records the case's state as 無 (it no
longer keeps the stale 已核准). The existing rule in `filter_live_cases` (a 無
case yields to a live sibling with a state) then binds `11510008` to node 78.
The per-case data3/data4 fetch (D8, per case) gives `11510008` its
`implementation`. Both go into the step 2 change.

- **Why two empty sources, not one.** One empty response can be a transient
  failure (the reason for `urtpe/links.py:1895`). Two endpoints empty in the
  same refresh is the measured shape here.
- **Scope, offline (2026-11-06).** 59 live cases have no cached header; 3 of
  them have a same-name sibling (青年130 `11501041`, 虎林38 `11410001`, 中山57
  `09801094`). Which cases become 無 is known only after the live refresh, so
  the refresh report must list every case it labels 無, and the count must be
  read before the re-emit.

**Second instance and a near-miss (peer graph-order-issues, live 2026-11-06).**

- **虎林38 `11410001`** (`信義區-虎林段四小段-38地號等138筆`): header empty,
  data2/data3/data4 empty, not in the parcel search. Its same-name sibling
  `11502012` is live (事業計畫階段─業經本府核定; data2 12, data3 25, data4 18
  keys). Same shape as `11501041`. The rule's live population is 2.
- **美仁800 `09707196`** is **not** this shape. Its header reads
  業經本府撤銷核准 and data2/data3/data4 are live (17/32/20 keys). It is a
  revoked case, not an emptied one. The rule fires only on an **empty**
  header, so it does not touch this case. The test must pin that. Its cached
  schedule is none, so the header wording decides, not the schedule.
- **The parcel search is not part of the rule.** The search omits approved
  ids for known reasons (D9c-2: `10708311`, `11412011`). This agrees with the
  user's decision: the rule claims no removal.

**Constraint on step 2: a 無 case's cached payload must not win the project
payload.** `select_best_payload` (`urtpe/links.py:2133`) picks the payload
with the most keys. After the per-case refetch, `11510008` holds 9 keys and
the stale `11501041` copy holds 19, so the stale copy would still win. The two
copies disagree (`Settle_Old_Doors` 0.0 vs the live 140.0). The 無 case keeps
its id and its cached data (the user's decision: an orphan, no removal), but
the payload selection (`implementation` and `rewards`) must skip a case
labelled 無 when a live case has a payload. Add this to the step 2 tests.

**The constraint covers both selection layers** (peer, verified 2026-11-06).
`pick_implementation_payload` (`urtpe/links.py:2163`) has a second layer: it
collects dates over every 擬訂 plan case (`_PLAN_CASE_RE` matches both
`11501041` and `11510008`), and a field no plan case carries falls back to the
`select_best_payload` pick. So the 無 exclusion must apply to (1) the
key-count pick, for `implementation` and `rewards`, and (2) the plan-case date
collection. For 青年130 neither payload carries a date today, so the visible
effect is the statistics; the test must still cover both layers. The
conflict flags that name the 無 case stay (honest reporting).

**The constraint already changes projects today** (offline,
`scripts/probe_d13_wu_payload_wins.py`, 2026-11-06). Existing 無 cases win the
pick in:

| Project | 無 case wins | live sibling payload |
|---|---|---|
| 信義區-雅祥段一小段-227-4地號等10筆 | `11009142` (26 keys) impl + rewards | `11009141`: **1 key** |
| 北投區-立農段五小段-163-2地號等4筆 | `11211211` (22) impl + rewards | `11409026`: 17 |
| 萬華區-萬華段二小段-894地號等22筆 | `11010191` (24) impl + rewards | `11507019`: 19 |
| 中山區-吉林段四小段-705-3地號等14筆 | `10410012` rewards | — |

No date today comes from a 無 case. 虎林38: `11410001` has an empty cached
payload (0 keys), so it does not win; the 無 case `10806141` (30 keys) ties
with two live 30-key cases and loses on order. **雅祥227 needs a look in
step 2:** the rule would replace a 26-key payload with a 1-key one. The step 2
change must state what happens when the live payload is near-empty, and the
step 2 report must list these 4 projects with before/after payload sizes,
together with 青年130 and 虎林38.

## D14 — the `--from-js` loader drops three node fields (peer graph-order-issues, 2026-11-05)

`_load_projects_from_js` builds each `CleanRecord` at `urtpe/cli.py:102-132`.
It does not set `stage_事業計畫`, `stage_權利變換` or `recovery`. The PDF path
sets them (`urtpe/cleanse.py:294-306,330-336`), and the emitter writes them
(`urtpe/graph.py:66-67,78-80`). Thus every `--from-js` re-emit drops them from
every node.

**`district_land` is coerced, not dropped.** `urtpe/cli.py:73` reads
`node.get("district_land", "") or node_district`. An emitted `''` thus becomes
the node's district on the first `--from-js` run, and later runs carry that
value forward. Four nodes show it (verified 2026-11-06, `1517300` vs now):

| recno | land cell starts | `1517300` (from-js) | now (PDF ingest) |
|---|---|---|---|
| 153, 382, 928 | 臺北大安區辛亥段四小段… | 大安區 | `''` |
| 926 | 臺北士林區百齡段二小段… | 士林區 | `''` |

The cells print 臺北X區 with no 市. `DISTRICT_RE` (`urtpe/cleanse.py:19`) is
`臺北市(.{1,4}?區)`, so `_land_district` returns `''`.

**A second question this raises (not decided).** The cell does name the
district (大安區, 士林區); only 市 is missing. So `''` is what the regex reads,
but it may not be what the cell means. Two separate fixes are possible: (a) the
loader round-trips `''` as-is (the D14 fix, below); (b) `DISTRICT_RE` also
accepts 臺北X區. (b) is a cleanse rule change and needs its own openspec change.
Without (b), (a) makes 4 nodes show no land district.

Peer measurement for (b) (graph-order-issues, 2026-11-06): across 1,442
`clean.tsv` rows, `district_land` is empty on exactly these 4 rows, and they
are the only land cells that start 臺北 without 市. A loose
`臺北市?(.{1,4}?區)` changes these 4 rows only (1,438 identical) and reads the
row's own district column each time. The 案名 of the same rows prints 臺北市,
and all 4 already carry 案名與地號段小段不一致. So `''` is a reader artifact.
**(b) must not absorb the 臺北市投區 typo** (recnos 488, 558, 927, a missing
北, flagged 行政區與地號行政區不一致). Both regexes read 投區; that is a
separate defect. (b) needs its own test: a 臺北大安區 cell reads
`district_land = 大安區`. The round-trip test alone would also pass on `''`.

**Decision (user, 2026-11-06): cleanse from the collected enum, not a looser
regex.** `_land_district` reads the first district name from the 12 values
collected in `clean.tsv`'s `district` column (中山區 中正區 信義區 內湖區 北投區
南港區 士林區 大同區 大安區 文山區 松山區 萬華區). Measured offline on 1,442
rows: **7 rows change, none other.**

| recno | land cell starts | today | enum read |
|---|---|---|---|
| 153, 382, 928 | 臺北大安區… | `''` | 大安區 |
| 926 | 臺北士林區… | `''` | 士林區 |
| 488, 558, 927 | 臺北市投區… | 投區 | `''` |

The 投區 rows now read `''`: 投區 is not a district, and the enum does not
guess the missing 北 (never repair by inference). Their flag
行政區與地號行政區不一致(地號為投區) must still fire — the test must pin it,
because its text interpolates the land district. `_section`
(`urtpe/cleanse.py:92`) also splits on `DISTRICT_RE`; the change must keep the
section and parcels of these 7 rows unchanged, or report the diff. The enum
change only takes effect on a **PDF ingest** (`--from-js` does not re-cleanse),
so it must land before D9g step 9. Tests: a 臺北大安區 cell reads 大安區; a
臺北市投區 cell reads `''` and keeps its flag.

**Measured drift** (true pre-ingest baseline `1517300` vs the ingest
`28d1eb5`, peer re-measure): `stage_事業計畫` filled on 533 nodes,
`stage_權利變換` on 533, `recovery` on 4, `district_land` changed on 4,
`implementation` 1 (value → none: D13's node 78), `is_current` 1 (吉林676 node
1347, caused by D5's merge). Of the 533, 79 nodes change on screen. This is why
the PDF ingest changed 375 projects after the three `--from-js` re-emits (D1
`2bb3013`, D2a `e97c18d`, D2b).

**View impact.** `viewer/app.js:468` reads `n.stage_權利變換 || ""` with no
fallback to `n.stage`. So 79 nodes show a different 權利變換 sub-stage after
the ingest than after a `--from-js` re-emit.

**Fix shape.** The loader must round-trip, not coerce.

1. Restore `stage_事業計畫`, `stage_權利變換` and `recovery`, in the same
   pattern as the `implementation` and `links` restore lines
   (`urtpe/cli.py:133-138`).
2. Read `district_land` as-is, including `''`. Keep the fallback only when the
   key is absent (older payloads):
   `node["district_land"] if "district_land" in node else node_district`.
3. Gate: a round-trip test. Emit, load with `--from-js`, emit again. The four
   fields must be identical on every node. This is not D7 or D8 (both are about `refresh_project`); it is the
rebuild path. D9g step 0.

## D15 — the D5 ledger reorders the review flags on 大龍265-7 (peer graph-order-issues, 2026-11-05)

Project `大同區-大龍段一小段-265-7地號等2筆`, node recno 1242. An A/B run
against `--ledger ""` (same PDF, same flags) isolates one change: 3
`review_flags` are reordered, not added. `10908274`, `11411017` and
`10908273` swap places. The flag text (孤兒案件未達相似度門檻, same case ids,
same scores) does not change.

**Cause.** The second ledger entry (吉林676 merge) changes the family's member
order. That changes the cluster iteration order, and so the order in which the
orphan cases are found.

**Impact.** Cosmetic in the viewer. It is the only D5-caused payload change
outside 吉林676. A stable sort of `review_flags` (for example by case_id, then
text) removes the order dependency. D9g step 12, P3.

**DONE (2026-11-06).** `cce5625`, archived
`2026-11-06-stable-review-flag-order` (`13baf68`). The emitter sorts a node's
`review_flags` by (case id, text) — the case id the flag names, then the flag
text; a flag that names no case id (the cleansing flags) sorts first. The sort
lives in the emitter, not at the four raising sites, so a flag raised by any
path lands in the same place. Measured on the live payload: **20** nodes' flag
order changes, **0** flag sets and **0** flag counts change.

### D15b — the unplaced-node flag quotes a date that changed shape between runs

Found while attributing the step 2 re-emit (2026-11-06). The
`節點未能對應平台案件` flag quotes the node's own date, and that date reached
the flag in whatever form the pipeline held: **slash-western** from the PDF
(`2013/11/5`), **ISO** from a `--from-js` rebuild (`2013-11-05`). The flag text
therefore changed between runs, so the duplicate collapse — which is by exact
text — stopped working, and the same finding appeared twice in two spellings.

**Measured:** 15 nodes carried both spellings after the step 2 re-emit (the
nodes whose date is read from a case whose milestones the D7 re-derivation
rewrote).

**Fix.** The flag quotes a **normalised** date (`_flag_date`,
`urtpe/links.py`), and the `--from-js` loader normalises the stored copies
(`_normalise_flags`, `urtpe/cli.py`). The flag's text is now a function of the
node, not of the run, and the copies collapse again. 11 projects changed by
this. Suite: `tests/test_flag_date_normalisation.py`.

### D16 — the city writes 利 as a compatibility ideograph (found 2026-11-06)

Found while measuring D9f-1's name-only rule. The city's live case name for
`11507018` writes **利 as U+F9DD** (CJK COMPATIBILITY IDEOGRAPH-F9DD), not
U+5229 (CJK UNIFIED IDEOGRAPH-5229). The character renders identically; the
keyword `權利變換` does not match, so the case reads as 事業計畫 alone and the
rule cannot pair it with the gazette row.

**Measured** (`scripts/probe_compat_ideographs.py`, live; and
`scripts/probe_compat_population.py`, offline):

| side | names read | carrying a compatibility ideograph |
|---|---|---|
| the corpus's own 案名 (1,444 rows, from the PDF) | 1,444 | **6** — for 北 / 都 / 更 |
| the city's case names (the 2,024 we hold) | 2,024 | **1** — for 利 |

The original measurement read the city's names live, from **60 parcel
searches** — 360 names. That is a **sample**, and it is the source of the
"1 in 360" figure quoted elsewhere. (The sample's size is not stable either:
a re-run on 2026-11-07 read 357 names, because the searches return what they
return.) The population we hold is the link cache: **2,024 distinct city case
ids**, of which **1** carries a compatibility ideograph — the same case,
`11507018`. The live-case finding does not change; only its denominator
does, and the denominator is now the whole set we hold rather than 60 units'
worth.

**The corpus is not affected by the TRACK reader.** Its 6 compatibility
characters sit in the **案名** — in the `臺北市` of the district prefix (北 as
U+F963) and in `都市更新` (都 as U+FA26, 更 as U+F901). They are inert for the
track because **no track keyword contains them**: the reader tests 事業計畫 /
權利變換 / 事業概要 / 都市更新計畫, and none of the four carries a compatibility
ideograph. **0** corpus rows carry a compatibility 利, and **0** corpus rows
change track under NFKC (D16a measures the field and the mechanism).

**But the corpus IS affected by a second reader.** `parse_name_id` returns
nothing at all for those 6 rows, so the corpus's own land core for 3 projects
is empty. See **D16c**.

**NFKC** folds every compatibility ideograph to its unified form, so
`unicodedata.normalize("NFKC", name)` is the folding the reader needs. It is
not in `R.normalize_name`, whose table is a fixed list of the drift measured
on the 2026-10-26 gazette (計劃→計畫, ㄧ→一, full-width parens, spacing).

**Status: not fixed.** It is folded in the D9f-1 probe only. A general fix
would touch `R.normalize_name` (the recovery pass's own normalisation) and
the places that compare a 案名 to a platform name. **Measured (D16a–D16c): the
scope is 2 readers**, not 1 — the track reader (1 live case) and
`parse_name_id` (6 corpus rows in 3 projects, latent). The blast radius is
small, but "small" is a measurement, not a scope. Recorded here so it is not
lost with the D9f-1 decision.

### D16a — what NFKC would change, measured over the whole corpus (2026-11-06)

The peer session asked for this before any NFKC change is opened: run the
normalisation over the payload and show what it moves, so the change's
test-first group can pin it.

**Probes:** `scripts/probe_nfkc_effect.py`, `scripts/probe_nfkc_plan_cases.py`,
`scripts/probe_nfkc_live_case.py`, `scripts/probe_compat_field.py` (all
read-only, offline).

**1. The corpus's own 案名 — 6 records, and the track does not move.**

| | Count |
|---|---|
| corpus rows carrying a compatibility ideograph | **6** (recnos 8, 121, 179, 611, 613, 615) |
| of those, the **track** changes after NFKC | **0** |
| corpus rows whose 案名 NFKC differs at all | 19 — 13 full-width parens (already normalised), 6 compatibility ideographs |
| corpus rows whose **track** changes after NFKC | **0 of 1,444** |

**The 6 characters are in the 案名, not the 地號 cell.** Measured over every
text column of `clean.tsv`: `name` and `name_raw` carry them (6 rows each);
the `land` column carries **0**. Their positions inside the 案名 are index 3
(北, U+F963, in `臺北市`), and the two characters of 都市更新 (都 U+FA26 at
index 24–27, 更 U+F901 at index 26–29).

**They are harmless because no track keyword contains them.** The track
reader tests the substrings 事業計畫 / 權利變換 / 事業概要 / 都市更新計畫, and
**none** of those four keywords contains a compatibility ideograph. So the
corpus's 北 / 都 / 更 are simply never compared against anything.

**The live case is the opposite case in the same class.** Its character
(U+F9DD, 利) sits at index 32 of 38 — **inside** `權利變換`, which *is* a
keyword. That is why it breaks the track and the corpus's six do not: the
corpus's characters sit in text no keyword touches; the live case's sits in
text a keyword does.

**So the two populations differ by WHERE the character is, not by which
character it is.** A test that only checks the corpus's track would pass
while the live bug survived, because the corpus's six are harmless for a
reason the live case does not share.

**2. The one live case name — the track DOES move.**

`11507018` (大安區-復興段三小段-3地號等2筆), read from the payload rather than
typed, because a hand-typed string carries the unified form:

| | Before NFKC | After NFKC |
|---|---|---|
| the track `_tracks()` reads | `['事業計畫']` | `['事業計畫', '權利變換']` |
| the plan-case matcher `_PLAN_CASE_RE` | False | **False** |

**The plan-case matcher is NOT affected**, and the reason is in the regex:
`^擬訂.*都市更新(事業計畫|事業計畫及權利變換計畫)案` requires the name to
**start** with 擬訂, and this case's name starts with 變更. Measured over the
**whole link cache** (2,099 case names): **1** name carries a compatibility
ideograph, and **0** names would newly match the plan-case matcher after
folding.

The corpus records for the same unit are unaffected because the PDF's own
names use the unified form — recno 28 (變更) and recno 686 (擬訂) both read
`事業計畫、權利變換` today.

**The matcher IS compatibility-blind — but no name is the shape that proves
it.** A counterfactual `擬訂` title carrying the compatibility form does
flip: as-is no match, after folding a match. The regex's keyword
`都市更新(事業計畫|…)` contains no compatibility ideograph, so it cannot see
one. The counterfactual is a property of the **regex**, not of any name in
the corpus or the cache.

**So the fix has exactly one reader to change on the LIVE side:** the track
reader, at the point where a city's case name is compared to a gazette 案名.
The implementation-dates path is not involved. A claim that NFKC would
restore the implementation dates for this case is **not supported** by the
data.

**But this is not the whole change.** The corpus's own 6 records have a
**second** reader affected — `parse_name_id` — and it is the more consequential
of the two. See **D16c**.

### D16b — the 都市更新計畫 keyword is not exposed either (2026-11-06)

The peer session raised the edge the framing above puts me closest to: the
keyword `都市更新計畫` contains 更, and the corpus's 更 (U+F901) also sits
inside `都市更新`. If a name held **both** — the keyword in its unified form
and the compat 更 inside 都市更新 — the substring test could in principle
match across the boundary.

**Measured** (`scripts/probe_nfkc_keyword_exposure.py`):

| | Count |
|---|---|
| corpus names containing the literal `都市更新計畫` | **0** |
| corpus names where a compat char sits immediately before a 更 | **0** |
| link-cache case names containing the literal `都市更新計畫` | **0** |
| the boundary shape anywhere in the cache | **0** |
| **payload node names containing the literal `都市更新計畫`** | **10** |

**The 10 are all in `name_raw`**, the PDF's untouched text — the PDF prints
`土地都市更新計畫案` (the abbreviation the cleanser then rewrites to
`土地都市更新事業計畫案`). All 10 carry **no** compatibility character, and
the **cleaned** `name` no longer contains the keyword at all. Their tracks are
unchanged by folding (`事業計畫` before and after).

**So the exposure does not exist anywhere.** The keyword's own 更 is the
unified U+66F4; the corpus's 更 is U+F901; and no name in the corpus, the
payload's cleaned names or the cache carries the literal four-character
keyword at all.

### D16c — a SECOND reader is affected: `parse_name_id` (2026-11-06)

The peer session's document named a third reader, and it holds. **My "one
reader" conclusion above was wrong**: the compatibility form breaks
`parse_name_id` as well, and that is the more consequential of the two.

**Measured** (`scripts/probe_compat_name_id.py`):

| | Count |
|---|---|
| corpus rows whose `parse_name_id` changes after folding | **6 of 1,444** — the same 6 |
| of those, the parse is empty today | **6** — `('', '', '', None)` |

For all 6, the parse returns **nothing at all** today and the full identity
after folding:

| recno | now | folded |
|---|---|---|
| 8, 615 | `('', '', '', None)` | `('北投區', '桃源段四小段', '424-8', 15)` |
| 121, 611 | `('', '', '', None)` | `('信義區', '三興段一小段', '972', 9)` |
| 179, 613 | `('', '', '', None)` | `('南港區', '南港段三小段', '274', 16)` |

**Why it is harmless today, and why it still matters.** The index core the
national portal is keyed on is built from the **portal's own title**, not
from the corpus's 案名 — and the portal's titles for these 3 units carry no
compatibility form. Measured (`scripts/probe_compat_index_core.py`): the
crawled index holds **no** core for these 3 units at all, so the lookup
misses either way, and the 3 projects' portal links came from elsewhere
(the cached view pages: view/791, view/793, view/253).

So the defect costs **nothing today** — but it means the corpus's own land
core for these 3 projects is empty, and any reader that builds a core from
the corpus's 案名 gets nothing. That is the same population the
`land-identity-fallback` spec covers, and the same reason the fallback
exists.

**The change therefore has TWO readers to fix**, not one:

1. **the track reader**, where a city's case name is compared to a gazette
   案名 — the one live case, `11507018`;
2. **`parse_name_id`**, where the corpus's own 案名 yields no identity — the 6
   records in 3 projects.

**Status: measured, not fixed.** The fix waits for the user to open the
change. The test-first group should pin:

1. the one live case reads both tracks after folding;
2. the 6 corpus records are unchanged in track;
3. **the corpus record count does not move** — a normalisation at the
   cleansing boundary runs before merge, so a change there moves the project
   counts. Pinning the count is what catches that;
4. **the live case is checked by name, not by count** — the corpus's six are
   harmless for a reason the live case does not share, so a test that only
   checks the corpus would pass while the live bug survived;
5. **the 6 records parse to their identity after folding**, and the 3
   projects' land core becomes the folded one — the second reader, which a
   track-only test would not catch;
6. **the 3 projects' portal links do not move** — they are already right, and
   a change at the cleansing boundary must not disturb them.

**The test-first group, when the user opens the change:**

1. the one live case reads both tracks after folding;
2. the 6 corpus records are unchanged in track;
3. **the corpus record count does not move** — a normalisation at the
   cleansing boundary runs before merge, so a change there moves the project
   counts. Pinning the count is what catches that;
4. **the live case is checked by name, not by count** — the corpus's six are
   harmless for a reason the live case does not share, so a test that only
   checks the corpus would pass while the live bug survived.

### D16d — the general form: a scope is a claim about what was not measured

Six corrections were made to the D16 finding while it was being measured, in
two sessions, and the shape was the same each time: **a scope was drawn from
a partial measurement and stated as settled.** Two sessions produced them, in
both directions — a scope overstated and a scope understated — so the pattern
belongs to neither and is recorded here as the board's own conclusion.

| the correction | what was stated | what was true |
|---|---|---|
| a character read by eye | "3 compatibility forms" | **4** across the data — 3 in the corpus (U+F901, U+F963, U+FA26) and the live U+F9DD |
| a match compared against `None` | "762 names would change" | 0 — a `Match` is never equal to `None` |
| a field guessed from the neighbouring column | "the corpus's characters sit in the 地號 cell" | the 案名 — the 地號 column carries 0 |
| a reader count taken from the reader in view | "1 reader is affected" | 2 — `parse_name_id` also breaks |
| a denominator taken from a sample | "1 in 360" | 1 in the **2,024** city case names we hold |
| a blast radius read as a scope | "the population is 1 case in 360" | 1 live case **and** 6 corpus rows |

**The rule this produces: a measurement is not a scope, and a scope is a
claim about what was not measured.** "Small" is a measurement. "One reader"
is a scope, and it was wrong in both directions before it was right.

**And the second form, which the table's own first row exposed: a figure is a
claim about what was counted.** The wrong "2" was not a wrong measurement —
it was a different **unit** from every other row: two groups rather than two
characters, in a table where every other row counts things. A row can be
consistent with itself and inconsistent with the table around it. The two
forms are the same failure seen from two sides: one counted the wrong set,
the other counted the wrong thing.

So the finding is recorded as the **measurements** (D16a–D16c) with the probes
that produced them, and a reader who wants to check the scope can re-run them
instead of trusting a conclusion that has already been wrong six times. The
same six corrections, in the same table, are recorded in
`docs/DashboardNUXUI.md` §14.0 — and
`scripts/probe_two_correction_tables.py` compares the two tables cell for
cell, so their agreement is measured rather than believed.

### D17 — `date_check` reports a false "exact" match on an empty date (found 2026-11-06)

Found while measuring D9f-1. `R.date_check(d1, d2, want)` with an **empty**
`want` returns `("exact", "uro_chk_date2")` — it compares the *empty* second
header field against the empty `want` and reports that field as the one that
closed.

**It is latent today.** `_recover_one` returns early when the 核定日期 does not
parse (`urtpe/recovery_pass.py:79-80`), so `date_check` never sees an empty
`want` on the existing path. But D9f-1 hands it one on **every** call — the
whole point of the widened rule is that the gazette's date is empty — so the
guard has to move, or `date_check` has to refuse an empty `want`, **before**
the widening lands. Otherwise every candidate reads as an exact match.

**Status: not fixed.** It is a one-line guard, but it belongs with D9f-1's
change, not ahead of it.

## D18 — three coverage questions, and two gates that did not hold (2026-11-06)

The user asked three questions about the emitted dataset: are there projects
not in the lists; are there recno in no project; does every recno carry a 北
badge. Each is answered below, with the proof that answers it. Two of the
answers exposed gates that did not hold, and both gates are now closed.

### D18a — the three questions, answered

**Proof script:** `scripts/probe_three_coverage_proofs.py` (read-only; re-derives
every number from the emitted files).

**Q1 — projects not in the lists.** A project is *in* a list when one of the
case ids it carries is on that list.

| Population | Count |
|---|---|
| projects in the corpus | **682** |
| on the 168 list (`Get_project168.ashx`, 466 cases) | **215** |
| carry case ids, none of them on the 168 list | **460** |
| carry **no** case id at all → in neither list by construction | **7** |

The 168 list is a **subset**, not a register of every case: it holds the 168
fast-track program. A case in review outside that program is not on it. The
88 ids the list holds that the payload does not name resolve as 84 not
approved (the header pass, D9g step 5a), 1 revoked (`11104211`), and 3 never
gazetted.

The 7 projects with no case id:

| Project | Why |
|---|---|
| 中正區-河堤五小段-399地號等3筆 | the 地號 cell says 河堤段**五**小段, the 案名 says 四 — the platform search finds nothing |
| 中正區-臨沂段三小段-412地號等12筆 | `11410026` — the platform's sibling case, never gazetted |
| 信義區-吳興一小段-330地號等43筆 | no platform case |
| 信義區-吳興段二小段-163-2地號等2筆 | the unit is named 吳興街二期整宅地區; the search does not reach it |
| 大安區-復興段一小段-3地號等2筆 | no platform case |
| 大安區-懷生段一小段-928地號等1筆 | no platform case |
| 萬華區-萬華段一小段-519-2地號等35筆 | the 地號 cell says 萬**大**段一小段, the 案名 says 萬華段 — the platform search finds nothing |

The national portal's list is reached by **land core**, not by case id, and
its crawl is **WAF-capped** (110 entries). A partial crawl is not a missing
project: proving that list complete needs a live re-crawl, not the cached
file. The payload names 620 distinct view ids; 109 of them are in the crawled
index.

**Q2 — recno in no project.** **None.** The merge partition is total and
disjoint over the 1,444 cleansed records:

| Check | Count |
|---|---|
| clean.tsv records | 1,444 |
| payload nodes | 1,444 |
| distinct node recnos | 1,444 |
| a recno in **two** nodes | **0** |
| a cleansed record in **no** project | **0** |
| a node whose record is not cleansed | **0** |
| merged.tsv rows / distinct project_id | 1,444 / 682 |

**Q3 — every recno attached to a 北 badge (case_id).** **13 of 1,444 nodes
carry no case id, and all 13 are named.** The badge is drawn from a node's
`links.taipei` (`viewer/app.js`, `getNodeMilestoneBadges`); the flag
`節點未能對應平台案件` names the same condition. The two agree **exactly**:

| Check | Count |
|---|---|
| nodes carrying a case id | 1,431 |
| nodes carrying **no** case id | **13** |
| nodes flagged 節點未能對應平台案件 | **13** |
| of those flagged, carrying a case id anyway | **0** |

No node is silently unbound: every node with no badge carries the flag that
says why.

### D18b — the `--from-js` path had no partition gate at all

**Found 2026-11-06, while proving Q2.** The census gate
(`Tripwire.check_partition`) compares domain objects, so it only runs on the
PDF path. The `--from-js` path — the re-emit path, used for every refresh
since 2026-08 — had **no** partition check.

**Measured.** A payload missing one node loaded as **1,443** members with no
complaint, and was written back as a complete dataset. Three corruption
shapes reached the emitter; two were refused and one crashed:

| Shape | Before | After |
|---|---|---|
| a node dropped, the count left alone | loaded silently (1,443) | **exit 4**, the count and the recno named |
| a node dropped, the count rewritten to match | loaded silently | **exit 4**, the recno named against `clean.tsv` |
| a family whose anchor node was dropped | **exit 1** (`StopIteration` in `graph.py:181`) — a crash, not a refusal | **exit 4**, the family and its anchor named |

**The fix.** `Tripwire.check_emitted_partition` reads the payload document
*as it is on disk*, before the loader rebuilds it. It checks the count
against the nodes, the family member list against the family's nodes, the
anchor against the family's nodes, and — the independent reference —
`clean.tsv`, the file the ingest wrote. A payload that lost a record **and**
had its count rewritten is internally consistent, so only a reference outside
the payload can see the loss.

### D18c — the census gate checked the wrong partition

**Found 2026-11-06, while proving Q2.** The gate ran **before** the ledger's
confirmed merge (D5), so it checked the **pre-ledger** family set:

| | Count |
|---|---|
| families the gate checked | **683** |
| families the payload carried | **682** |
| families `review_report.txt` printed (`專案家族: 682`) | 682 |
| families the tripwire report printed (`projects: 683`) | **683** |

The gate was one family short of the truth and still passed, and the report
printed a count the payload did not have. The ledger now runs **before** the
census gate and before the tripwire report, so both speak about the partition
that is actually emitted. The reconciler already compared against the
post-ledger set, so that comparison is unchanged and now consistent with the
gate.

### D18d — the badge and the flag could disagree, and nothing checked

**Found 2026-11-06, while proving Q3.** The flag is raised and cleared only
on the `--links` path. A payload that kept the flag after the binding
survived the round trip as a stale finding, and a node that bound nothing
without the flag was silently unbound.

`urtpe/emission.py` now checks the two against each other: a node with no
case id and no flag, or a node with a case id and the flag, is **named**.
The check applies only to a project that link discovery reached — a run
without `--links` binds nothing, and a check that fires on every run is a
check nobody reads.

### D18e — the board header, and what it claimed

The board header read "**Open items: none**" and the corpus "**1,444 records
/ 682 projects**". Both were right about the payload and wrong about the
**gate**: the gate checked 683. The header stays as it is — the payload never
moved — but the sentence that claimed the corpus was sound now rests on a
gate that holds.

**Status: fixed.** Three gates, one probe, ten tests.

### D18f — the report, and where to find it

**`docs/coverage-report.html`** — the three questions, answered, in one page.
Generated by `scripts/coverage_report.py` (read-only: it writes one HTML file
and touches nothing else). Every figure is re-derived at generation time from
the emitted files; nothing is copied from a previous run.

The page is self-contained and opens offline from `file://`, like the viewer
and `docs/release-diff.html`. It answers each question with the counts it
compared, names the records and the projects it could not account for, and
states plainly what it cannot prove — the national portal's list is reached by
land core and its crawl is WAF-capped, so that side needs a live re-crawl, not
the cached file.

The proof behind the page is re-runnable on its own:

```
python scripts/probe_three_coverage_proofs.py   # the three questions, from the emitted files
python scripts/coverage_report.py               # the page
```

**Status: done.** The openspec change `gate-the-emitted-partition` is
**archived** (2026-11-07), and its four spec deltas are synced: the partition
requirement in `history-graph` and the badge/flag agreement in
`official-link-discovery`.

## Decisions made (2026-11-05)

| Entry | Decision | Blocks |
|---|---|---|
| D6 | Re-key `data/twur_overrides.json` to `…等2筆`, correct `PID`, restore with per-project `discover_project_links(fresh=True)` (option A, 2026-11-05) — not corpus-wide `--fresh` | D6 fix + re-emit |
| D7 | Option A — overwrite (re-derive `taipei_milestones` exactly from `case_milestones`, drop the 5 re-dated values) | D7 re-derive rule |
| D8 | Option B — refetch `data3`/`data4` only where `implementation` is empty (6 projects). **Amended 2026-11-06: per case** — every live case with an approval date and no `implementation` entry (26 cases in 22 projects); the per-project rule missed 青年130 (D13) | D8 scope + cache pass |
| D13 | Keep the emptied case as an orphan labelled 無 (no removal claimed); a refresh labels a case 無 when its header row and data2 are both empty; folded into D9g step 2 (2026-11-06) | D9g step 2 |
| D14(b) | Cleanse `district_land` from the collected 12-district enum, not a looser regex (2026-11-06); 7 rows change | D9g step 0b |
| D9c | Options 1+2+4 → **option 1 withdrawn** (D9d: the ledger cannot add a record the gazette does not hold); **2+4 stand** | D9c-2, D9c-4 |
| D9f | Accept periodical 168 poller plan, coordinated with periodical PDF update | D9f-1 |
| D10 | The permit whose 開工日期 matches the city's; otherwise `links.permit.ambiguous` (2026-11-05) | D10 openspec change |
| Gazette 2026-11-03 | Ingest together with the first 168 poll (2026-11-05). **The document's own 統計至 is 2026-10-28** — 2026-11-03 is the publisher's 資料更新 stamp, and the two archive files are byte-identical | D9g step 9 |
| **D9f-1** | **AGREED** (user, 2026-11-06) — widen the recovery pass to a truncated **date** cell, so the 2026-10-28 gazette's 編號 3 can be ingested. The rule recovers the **platform's** `核定日期`; where the PDF and the platform disagree the disagreement is flagged | D9g step 9a |
| **D9f-2** | **AGREED** (user, 2026-11-06) — the 168 list's `MEMO` is the **fourth source**. **Measured: it cannot be a date source** — it is empty for all 33 cases where the PDF and the platform disagree, and it is the 核定**公告** date (a different date) where it is present — so it joins as a **flag**: a MEMO that disagrees with the recovered date is recorded | D9g step 9a |
| D9g step 5a | Run the header pass — done: 78 in review, 5 closed, 1 revoked | — |
| D11 | Recorded — docs only, no decision needed | — |

Decided 2026-11-05 and moved into the findings: D2b (date-first sort), D4b
(chain + dotted edges), D4c (literal reading, after the construction chip),
D4d (計畫 options = the rest).
