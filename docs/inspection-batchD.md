# Project inspection — Batch D · collected 2026-11-04

Findings from the post-Batch-B+C session (2026-11-04, payload at `47453f9`:
1,442 records / 682 projects, the corpus converged after waves 1–3 of the
Batch B + C plan). Four findings, all measured (D4 added 2026-11-05). The board follows the
`docs/inspection-batchBC.md` structure: findings, then the integrated plan,
then the decisions that gate execution.

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

## Order

| Step | Finding | Form | Gate |
| --- | --- | --- | --- |
| D3a | `nationalLabelKey` ordinal spelling — 223 labels never bind | direct `fix:` + test; no re-emit (viewer only) | — |
| D4a | 使照 national flag ignores the city date — 287 wrong 現況 → 使照 edges; plus source-map-first (viewer) and first-holder provenance (pipeline) — decided 2026-11-05: only 南港729 keeps an edge | viewer: flag split + source map first, direct `fix:` + test; pipeline: first holder wins, small openspec delta on `taipei-implementation-data` ("the case whose value won the merge") + re-emit | pipeline part rides D1's re-emit |
| D4b–d | dead-end edges, list badges, 計畫與執行 filter | one openspec change, viewer only (`virtual-milestone-nodes`, `history-graph`, `viewer-filtering`) | user decisions below |
| D1 | rename the orphan `milestones_national` key (source-space truth) | openspec change + `--from-js` load alias + re-emit | — |
| D2 | `_ghost_node_date` track-aware, then the date-primary sort key (user decision 2026-11-04 pending on the re-measure) | one openspec change, `virtual-milestone-nodes` + viewer | D1 (same re-emit rides D1's payload) |

## Decisions waiting on the user

| Entry | Question | Blocks |
| --- | --- | --- |

Decided 2026-11-05 and moved into the findings: D2b (date-first sort), D4b
(chain + dotted edges), D4c (literal reading, after the construction chip),
D4d (計畫 options = the rest).
