# Project inspection — Batch B + C · collected 2026-11-03, planned and re-reviewed 2026-11-04

Split from `docs/inspection.md` (the main execution board) on 2026-11-04. This file holds everything about Batch B (the §37/§38 residuals), Batch C (the post-viewer-UX gaps), the integrated plan that treats both (S0–S16 + R), the decisions those steps waited on, and the measurement appendices G and H. The main board keeps one summary row and a pointer.
References to "waves 1–7" and the post-wave changes (§29–§38) are the earlier
executed work on the main board: read them in `docs/inspection.md`
("Execution order — the integrated plan" and its post-wave sections).

### Batch B — the §37/§38 residuals, collected 2026-11-03 — **QUEUED, not started**

Every item below is a residual that §37 or §38 left open. The viewer-UX waves
(`docs/viewer-UX.md`) changed how the viewer draws a case. They did not close any
item here. Measured at `2b96e5b`, on the payload emitted 2026-11-02
(1,442 records / 693 projects) and the 726 cache dirs.

| ID | Finding | Evidence now | Form | Gate |
| --- | --- | --- | --- | --- |
| B1 | New-case discovery covers refresh-selected projects only | the 336 project (大安區-通化段四小段-336地號等26筆) has 3 case ids, all 已核准; the selector skips it; its cache has no `case_headers` | openspec change | — |
| B2 | A superseded case keeps its undated node in the graph | 4 of the 5 superseded cases carry an orphan node with an empty `node_date`: 10410012, 10806141, 11009142, 11211211 | openspec change | B1 |
| B3 | A `fresh=True` re-discovery drops `case_headers` and `superseded_by` | `discover_project_links` never writes either field; only `refresh_project` does | direct `fix:` (corrected 2026-11-04 review: it restores state the code drops by mistake; see S1) | — |
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
| C5 | 使照 disagreement between the two portals is not flagged | 282 projects hold 使用核發/使照核發 from both portals: 260 agree, 22 differ (吉林811 2013-09-11 vs 2013-11-12; 榮星306 year; 虎林310 month). 13 projects hold it national-only, 32 city-only. 橋北574-1's national `291.08.02` renders as 2202-08-02 in the 推動歷程 card (`fmtDate`); the 使照 slot and the stage chip use the city's 2022/08/02 | openspec change S15 (decided 2026-11-04: the building-permit adapter replaces flag-only) | S0 |
| C6 | The 北 positional fallback binds 71 nodes on 51 projects, unmarked | re-run of the pipeline's own `_match_case_by_date` over the payload: 1,356 nodes match by date, 71 do not, 15 have no case. **Rule decided 2026-11-03 for the area-split ties (see "C6 in detail"):** one approved recno binds every same-date case of its area split. That covers 31 of the 71 nodes (56 cases, 15 projects) and folds their twin orphan nodes into the recno. Examples: 吉林508 (view/1062) recno 259 → 11011241 A區 + 11011242 B區; 榮星53 (view/25) 4 recnos, each → its 北區 + 南區 pair. The other 40 nodes are recorded by type and stay open | openspec change | S0 |
| C8 | The construction dates (建照 / 開工 / 使照) do not follow the case that owns them | **Rule decided 2026-11-04 (the user):** the city keeps 建照核發日期 (data2) and 開工日期 / 使照核發日期 (data3) on the **first 擬訂 plan case** — the one named 擬訂…都市更新事業計畫案 or 擬訂…都市更新事業計畫及權利變換計畫案. Two defects break it. (a) `select_best_payload` (`urtpe/links.py:1971`) keeps one data3 payload per project, chosen by key count, so the plan case's 開工/使照 are dropped when a later case has more statistics: 9 of the 13 "national-only 使照" projects (德惠573 09710240: 開工 2012/07/13, 使照 2015/07/13 cached, not emitted). (b) Discovery misses the 擬訂 plan case itself: 新光101 (09703181), 寶清599 (09303270), 敦化585-11 (10210171) — the parcel search does not return them; they were found by probing sibling case ids. See "C8 in detail" | openspec change | — |
| C9 | A parcel-count shrink (`等N筆(原M筆)`) splits one project in two | 吳興790-6: recno 978 (變更(第三次), 等4筆(原29筆)) scores 0.639 against recno 1157 (等29筆): same section and first parcel, count bridge 0.8, but the parcel sets share 1 of 32 (Jaccard 0.03). **11 project pairs** split this way, and 10 of them share one national page (view/118, 319, 321, 637, 84, 281, 718, 276, 231, 358) and their case ids. See "C9 in detail" | openspec change (`case-merging`) + re-emit + aliases | — |
| C7 | The 相關連結 label of an anchored case shows the gazette 案名, not the city's own case name | `buildRelatedLinkLabels` (`viewer/app.js:563`) labels each case a node anchors with that node's `case_name` (the gazette row). It reads `candidate_names` only for cases no node anchors. 307 anchored cases show a label that differs from their city name: 20 lose an area suffix (吉林508's 11011241 shows without "-A區"), 48 show another stage word (中山202 node 699: gazette 擬訂, case 變更), 8 show other parcel counts (文林176: 等13筆 vs 等14筆), 231 differ in other wording. With C6, one node carries 2+ cases, so the gazette label cannot tell them apart | openspec change (S9 `label-by-own-name`; the spec pins `node.case_name` first) + a review list for the 48 | — |
| C10 | The 國 label shows the latest gazette 案名, not the national page's own project name | `buildRelatedLinkLabels` (`viewer/app.js:594`) returns `anchorName` = the current (latest) node's `case_name`. The national page names the project by its first 擬訂 case: the cached `view.html` `<title>` (吉林705 view/57: 擬訂…事業計畫案; the viewer shows 變更…權利變換計畫(含釐正圖冊)案). Measured 2026-11-04 over 632 projects with a cached page: **452 show the wrong name** (302: the title equals an earlier node's name; 150: it equals no node, 149 of them a 擬訂 name). The title is not stored in the cache or the payload today | openspec change (S9 `label-by-own-name`) — store the title as `twur_name` (re-parse the cached `view.html`, no request) and label 國 with it | — |

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

**C5/C6 API correction (measured 2026-11-04).** C6 is our own binding
error, so the city API can correct most of it. C5 is a disagreement between
two offices, so it cannot.

C6, live probe of 3 type-5 examples (about 30 rate-limited, read-only
requests). The sibling-id probe found the missing case next to a cached id,
and the city's own approval date equals the gazette row:

| Node (gazette) | Bound now | Found | City approval |
| --- | --- | --- | --- |
| 臨沂318 recno 143, 變更(第三次), 2025-04-16 | 10409102 (2023) | 10409104 | `uro_chk_date2` 2025-04-16 (header only; data2 empty) |
| 犁和302 recno 281, 變更, 2023-12-28 | 10203251 (2019) | 10203253 | `Uro_Chk_Date2` 2023/12/28 |
| 吉林705 recno 1370, 變更, 2008-03-10 | 09307100 (事業概要) | ~~09307103, 自行撤回~~ → **09307104** by 案名 (corrected 2026-11-04; see "C6 resolver") | data2 copies 09307101's 2010/01/08 |

The probe also found 臨沂318's missing plan case 10409101 (2018-07-19).
data2 returned 22–23 identical rows per case, so keeping the first value of
each field lost nothing here (no test pins it). Two consequences: S12's
sibling probe covers most of type 5, and the case header's
`uro_chk_date`/`uro_chk_date2` must be stored as a second approval source
(S14), because a case can carry its approval only in the header. Estimated
open C6 nodes after S8, S12, S14 and the 案名 match: about 10, not 40
(superseded 2026-11-04: the "C6 resolver" binds all 71).

C5: the 22 disagreements were tested against the dates the city holds for
the same case (使照 after 建照 and 開工, before 成果報備, not in the future).
1 is decided: 橋北574-1's national `291.08.02` (2202) is in the future, so
the city's 2022/08/02 is right. 21 pass both ways, including the one-digit
typos (榮星306: 2022-09-23 vs 2023-09-23, both after 開工 2019-09-20). The 使照
is issued by the building authority (建管處); both portals copy it. Only the
building authority's permit record can settle the 21 (S15).

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

**C6 user resolutions (2026-11-04).** The user checked four fallback examples
against the city portal. Cache values verified the same day:

| Project, recno | Bound today (fallback) | Right case (user) | Rule it shows |
| --- | --- | --- | --- |
| 犁和302 (三小段) recno 281, 2023-12-28 變更 權利變換 | 10203251 (the 2019 擬訂 case, recno 830) | the missing 變更 權變 case — 10203253 (`Uro_Chk_Date2` 2023/12/28, found by the sibling probe) | discovery: S12 + S14 |
| 東湖34 recno 73, 2026-02-21 擬訂 | 11302181 (目前辦理情形 = 無, no milestones) | 11502008 (已核准, 核定 2026/02/11, same name) | **new rule:** a case with status 無 yields to a same-name sibling that is approved; the 無 case leaves the node |
| 玉成253 recno 508, 2022-01-04 擬訂 事計+權變 | 10405043 (審查中 變更) | the missing 擬訂 plan case — 10405041 (核定 2022/01/04, found in C8 (b)) | discovery: S12 |
| 吉林705 recno 1370, 2008-03-10 變更 事業計畫 | 09307100 (事業概要, by position) | 09307104 | **new rule:** 案名 match, with 自行撤回 cases excluded (09307103 has the same name but is withdrawn) |
| 吉林705 recno 1311, 2010-01-08 變更 事計+擬訂權變 | 09307100 (tie 09307101/09307104 refused) | 09307101 (核定 2010/01/08, 權變核定 2010/01/11) | 案名 match breaks the tie: only 09307101 carries this name |

吉林705 has a city data defect too: 09307104's data2 returns 核定日期
2010/01/08 (the date of 09307101), so the date matcher alone cannot place it.
With 1370 and 1311 bound by name, 09307100 (事業概要, 概要核准 2004/12/09) and
09307103 (自行撤回, 申請計畫 2014/02/24) stay orphan nodes, labelled by their
own city names (C7). Today 09307103's orphan carries node_date 2004-12-09,
which is the 概要 date; the right date is its 申請計畫日期. The project's 國 label also
shows the wrong name (C10).

So the 案名 match is the first rule for types 3–6, before any date drift
window: exact city name, withdrawn (自行撤回) and status-無 cases excluded when
an approved same-name sibling exists.

**C6 resolver: every recno gets its case (measured 2026-11-04).** User rule:
a recno always has a corresponding city case_id, so the fallback must find
it, never guess or drop it. Simulated over all 71 fallback nodes
(scratchpad `namematch3.py`, `probe19.py`), plus about 230 read-only
gis.uro requests:

| Step | How | Nodes resolved |
| --- | --- | --- |
| 1. Name over cached cases | tier 1 exact 案名; tier 2 loose (等, `(原N筆)`, 案及, 擬定, area suffix); tier 3 stage-with-ordinal + plan type. Skip 自行撤回/已失效; a 無 case yields to an approved same-name sibling; distinct area suffixes = area split | **52** — 21 single cases (18 correct the guess, 3 confirm it) + 31 area splits (the S8 set) |
| 2. Same-day id probe | `get_project168_top` on `<first 7 digits>0–9` of every known id (cached + national 相關連結); accept on CASE_NAME + header date | **14** — 福和75 10008273, 犁和302 10203253, 南港19-1 10111131, 南港601 10406241, 南港566 r744 10708311, 新光101 09703181, 玉成166 r782 10203261+10203262 (area split, ids only on the national page), 玉成253 10405041, 玉成729 10812182, 玉成五1 10408183, 三玉328 10209163, 寶清599 09303270, 敦化585-11 10210171, 敦化449-12 10209291 |
| 3. Header date on a cached case | the header's `uro_chk_date`/`uro_chk_date2` (S14) where data2 copies the plan case's date | **2** — 玉泉11 r1180 → 09504263 (header 2013-08-20 exact; data2 says 2008/05/15); 康寧626 r1019 → 09712204 (header 2016-11-12, 10 days off, same 變更(第二次)) |
| 4. Parcel search on every parcel | `Get_updcase_list` on each parcel of the node, not only `first_parcel` (`urtpe/links.py:596`) | **3** — 南港566 r1063 → 10006032 (parcel 567; 566 returns only the latest case; header 2016-02-25 exact); 金華455-3 r1397 → 09201071 (old first parcel 508; 2007-05-01 exact); 萬慶483-3 r1305 → 09408232 (parcel 459; 2010-03-08 exact) |

Result: **71 of 71** nodes get a case; 70 by exact date, 1 (康寧626) by
stage + a 10-day drift. No node needs the positional fallback or a removed
badge.

Two facts the probe corrected:

- **Case ids are a city-wide daily serial (ROC date + digit), not a
  per-project batch.** 10203252 is 中山111, 10405042 is 玉成253-1 (same date as
  玉成253's 10405041), 11502010–18 are nine other projects. A same-day id is a
  candidate only; CASE_NAME must match the node's land core. S12's ≥0.85
  land-core check is required, not optional.
- **The single-parcel search misses cases.** After a site shrink or a parcel
  renumber, the first parcel returns only the newest cases. Searching every
  parcel of the node until a name + date match is found closes the gap at a
  cost of a few searches per missing node.

Resolver order for S10 (and for R's new cases): candidates = cached cases ∪
national 相關連結 ids ∪ same-day ids ∪ all-parcel search results; approval
date = header ∪ data2; bind by name, then date (exact, ±1), then stage +
drift; bind all cases of an area split. Positional fallback is removed. A
node that still has no case is reported by name in the run report (none
today).

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
re-measure after S10, which now owns the area-split rule).

### Batch B + C — the integrated plan (reviewed 2026-11-03, re-reviewed 2026-11-04)

Both batches were reviewed together against the code and the payload at
`95ea60c`. The review corrected C1, C2, C3, C4 and B7 (see their rows). This
section is the one plan for all 18 findings (B1–B8, C1–C10; B8 and C3 are done). Priority uses the
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
| S0 | — | housekeeping | **DONE 2026-11-04** (`9696438`): the 3 invalid deltas fixed (deltas rebuilt from the live requirements so no scenario is dropped; the 國-badge and 無/NA requirements marked ADDED — they were never in the live specs; the case_headers CASE_NAME delta dropped, the live spec gained it with C3); `openspec validate --all` 25/25; all 4 changes archived as `2026-11-04-*`; show-no-state task 4.1 (header refresh, 547 caches) reassigned to R | — |
| S1 | P2 | B3 | **DONE 2026-11-04** (`5c88fc2`): on `fresh=True` discovery loads the prior cache and carries forward `case_headers`, `superseded_by`, `case_case_names`, `view_rejected`, `adopted_from_view`; 2 new tests (keep + never-drop), suite 872 passed / 1 skipped | — |
| S2 | P3 | B4 | **DONE 2026-11-04** (`92ef6b7`): `select_candidates` takes the payload keys and skips absent projects; `stranded_dirs` names them once per run (measured: 33 stranded dirs, candidates 89 → 85); 2 tests | — |
| S3 | P1 | C3 (= B7, B8) | **DONE 2026-11-04** — `reject-foreign-view-cases` implemented (`ba2700b`), re-emitted (`f961f6a`), archived (`e5a5986`, 23/23 tasks). Re-checked 2026-11-04: the gate runs after the absorb on every refresh, so a rejected id stays rejected (verified offline on a copy of 中山254: a second refresh keeps 10202065 out of `view_verified_case_ids` and `city_case_ids`). **Residual S3a (P3):** the absorb does not skip `view_rejected`, so each refresh re-fetches the rejected id's milestones and leaves them in `case_milestones` — all 4 rejected ids sit there in the payload today (10202065, 09608220, 09511211, 09807161). They reach no node, orphan, edge or 北 badge; only the 相關連結 label fallback reads `case_milestones`, and that path never sees a rejected id. Fix: the absorb skips `view_rejected` ids and the gate drops their `case_milestones` entry; add the second-refresh test | done; S3a = direct `fix:` |
| S4 | P1 | C1 | openspec change `bind-national-label-once` — per-label binding, exact then ±1-day tie-break, never guess; delta MODIFIES the archived §2 requirement. Viewer only, no re-emit | S0 |
| S5 | P2 | C4 | openspec change `parse-listed-parcel-names` — extractor learns the 、-list, `(原NNN)`, spaced and 號 shapes plus NFKC; unparseable names are reported, not dropped. Re-emit only (no fetch): the 8 dropped cases come back as orphans | S0 |
| R | P2 | B1, B5, B6, C2, §7 4.1 | openspec change `refresh-whole-corpus` — **run in resumable slices (user decision 2026-11-04)**: each slice (about 100 projects) takes the lock, writes into `data/.link_cache/` only, records a checkpoint and releases the lock; the tracked `projects.json` and `viewer/projects.data.js` are emitted once, after the last slice. A rate-limited refresh of all 726 caches: new-case discovery (B1), status re-derivation (B5), cleared status kept as a value (B6), the view backfill (C2, now gated by S3), and the missing headers (§7). Estimate the request count first; change detection decides what to fetch (see "R change detection") | S1, S3a, S5, S10, S13 (S3 done) |
| S6 | P2 | B2 | openspec change, small — a superseded case's undated orphan node is hidden or chained to its successor | R |
| S7 | P2 | C5 | **merged into S15 (user decision 2026-11-04)** — the flag-only plan is replaced by the building-permit adapter. What S7 kept: the range guard in `fmtDate` and the ROC converters (a year in the future renders as the raw text plus a warning), which ships inside S15 | — |
| S8 | P1 | C6 (types 1–2) | **merged into S10 (2026-11-04 review)** — the resolver's name step binds the same 31 area-split nodes (56 cases, 15 projects), so the date-tie rule is not needed; both would change `urtpe/links.py:2073`. The user's area-split rule (2026-11-03) stays as an S10 requirement | — |
| S9 | P1 | C7, C10 | openspec change `label-by-own-name` (**not a direct fix**, 2026-11-04 review): `viewer-related-links` requires `node.case_name` first in the 相關連結 name chain (`openspec/specs/viewer-related-links/spec.md:40`), so the change MODIFIES that requirement. Each case is labelled with its own city name (C7); the 國 label reads the national page `<title>`, stored as `twur_name` from the cached `view.html` with no request (C10, was S16). Viewer + one emit field + re-emit | S0 |
| S10 | P1 | C6 (types 1–6), C8 (b) | openspec change `resolve-recno-case` — replaces the positional fallback with the 4-step resolver: (1) 案名 over cached cases, area splits bind all cases (was S8); (2) same-day id probe, accepted on CASE_NAME + date (was S12); (3) header `uro_chk_date`/`uro_chk_date2` stored as an approval source (was S14); (4) parcel search on every parcel of the node. Measured 71 of 71 resolved, about 230 requests. MODIFIES `official-link-discovery` and `cache-freshness` (positional fallback). See "C6 resolver" | S0, S1, S5 |
| S16 | P1 | C10 | **merged into S9** (`label-by-own-name`, 2026-11-04 review): both fix `buildRelatedLinkLabels`, and the new `twur_name` payload field needs a spec | — |
| S11 | P2 | C8 (a) | openspec change `dates-follow-plan-case` — construction dates come from the first 擬訂 plan case (per area); D5 keeps the statistics only. Emit-side, no fetch: the first run recovers 開工/使照 on 8 national-only projects; run the emit again after S10, which adds the missing plan cases | S0 (second run: S10) |
| S12 | P2 | C8 (b) | **merged into S10 (2026-11-04 review)** — the same-day id probe is resolver step 2; the 7 missing 擬訂 plan cases are among its 14 finds. Correction: case ids are a city-wide daily serial, not a per-project batch, so a same-day id is accepted only on CASE_NAME + date | — |
| S13 | P2 | C9 | openspec change `merge-across-count-shrink` — `(原M筆)` bridges a site shrink; re-merge, aliases, cache migration | S0 |
| S14 | P1 | C6 (types 5–6) | **merged into S10 (2026-11-04 review)** — the header dates are resolver step 3 (玉泉11 09504263, 康寧626 09712204 need them) | — |
| S15 | P2 | C5 | openspec change `building-permit-adapter` — **replaces S7 (user decision 2026-11-04).** The building authority's 使用執照摘要 (data.taipei) is the third source for 使照, matched by parcel; the permit date is shown and the disagreeing portal value is flagged. Corrects 17 of 22 disagreements, confirms 12 of 13 national-only dates; only the unmatched cases (5 + 1) keep both portal dates and a flag. Includes the `fmtDate` range guard. See "S15 exploration" | S0, S11 |

**R change detection (design, recorded 2026-11-04).** No city endpoint
returns a per-case "last modified" date. The 40 endpoints in
`docs/urotpe_api.md` §3 carry event dates only; `get_Updated.ashx` returns one
date for the whole site (`2024/12/9` when probed). The national page does
carry one: every cached `view.html` (642 of 642) prints 資料更新日期 —
本專案資料最後更新於 YYY.MM.DD (2019–2022: 77, 2023: 260, 2024: 37, 2025: 196,
2026: 72). That date covers the national page only. It says nothing about the
city side, where R does most of its work: new 變更 cases appear in the city
first (玉成166 11412011, 吉林508 11508022/23), status changes appear there
first, and data3 dates appear there first. A date is also a hint, not proof:
the city re-uploads unchanged content with a new timestamp (`AGENTS.md`,
gazette detection). So R uses one cheap signal per source and fetches in full
only when the signal moves:

| Step | Source | Cheap signal | Full fetch only when |
| --- | --- | --- | --- |
| 1 | National page | 最後更新於, one request per project | the date is later than the cached page's |
| 2 | City parcel search | one search per project (already in the refresh); compare case ids and `schedule` with the cache | a case id is new, or a `schedule` differs |
| 3 | City case header | `get_project168_top` per case; compare `NAME`, `uro_chk_date`, `uro_chk_date2` | a value differs, or the case is still open (no 使照) |

A finished case (已完工 / 完成成果備查, with a 使照) skips data2/data3 unless
step 2 or 3 moves. Estimated effect: from about 5,500 requests (726 caches,
2,057 cases) to about 2,000–2,500. Every skip is counted in the run report, so
"not fetched because unchanged" never reads as "fetched and empty".

**S15 exploration (2026-11-04).** The 使照 is issued by the building
authority (臺北市建築管理工程處). It publishes its permit summaries as open
data on data.taipei (XML, no key):

| Dataset | Resource id | Size | Cover | Update |
| --- | --- | --- | --- | --- |
| 臺北市歷年使用執照摘要 | `0f3f9675-8356-4f1a-9908-1ce8892012fa` | 65.25 MB | ROC 90–114 | yearly |
| 臺北市115年度使用執照摘要 | `74a8b311-906e-44c4-91fb-7f413842d4e1` | 2.01 MB | current year, to last month | monthly |

Download: `https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=<id>`.
Each `<Data>` record carries 執照號碼, 發照日期 (ROC `YYYMMDD`), 原核發執照
(the 建照 number), 開工日期, 竣工日期, 地址, and every 地段號 in the form
`臺北市中山區吉林段三小段0811-0000號`. Matching key: section + parcel against
each project's own parcel list. 8,946 permits, ROC 090–115. Matching
building-permit datasets exist too (歷年 / 115年度 建造執照摘要).

Tested against the payload at `HEAD`, by parcel overlap:

| Group | Projects | Result |
| --- | --- | --- |
| Control: city = national (every 12th) | 22 | 22 of 22: the permit date equals both. The match is reliable |
| Disagreements | 22 | **city confirmed 8**, **national confirmed 9**, permit date matches neither 4, no permit 1 |
| National only (city blank) | 13 | national confirmed 12, no permit 1 |

So neither portal is the better one. The city is right on the large gaps
and the year/month typos (虎林310, 莒光466, 玉成180-1, 崇仰68, 橋北574-1). The
national page is right on the 1-day cases (all 5) and on 吉林811, 奇岩13,
龍泉712, 寶清678. Four cases are new shapes:

- **2 permits on one site.** 奇岩13 (2012-06-08 and 2014-06-19), 龍泉712
  (2005-11-04 and a 2006 雜字 permit), 懷生931 (2015-05-22 and 2016-05-17),
  仁愛54 (2003 雜字, 2005 建字). The first 建字 permit is the building's 使照;
  a later one is a 雜項 (minor work) or a second building. Each portal copied a
  different one. Rule: take the permit whose 原核發執照 is a 建字 number, and
  for an area split (懷生931 東區/西區) keep one per area.
- **玉泉91**: the permit says 2020-11-11; the city says 11-12, the national
  page 07-30. The national 07-30 equals the permit's 竣工日期, not its 發照日期.
- **No permit found**: 榮星306 (both portals carry 09-23; the permit
  111使字第0119號 sits on parcel 660 of the same section, which is outside the
  project's parcel list) and 德惠573 (104使字第0181號, 2015-07-13, sits on
  parcels 1048/1049, which the gazette lists under another number). A
  parcel-list miss, not a missing permit; an address or 建照-number key would
  catch both.

Design for the adapter: download both files (monthly cadence, cached under
the archive root like the gazettes, keyed by SHA-256 per `AGENTS.md`); index
by (section, parcel); for each project pick the 建字-origin permit(s) whose
parcels overlap most; emit it as a third witness with its permit number. The
viewer shows the permit date when it exists and flags the portal value that
disagrees. Never repair by inference: when the permit is missing, keep both
portal dates and the flag.

**Why this order (re-reviewed 2026-11-04).**

| Wave | Steps | Network |
| --- | --- | --- |
| 0 | S0 | none |
| 1 | S1, S2, S3a (direct fixes); S4; S5; S9 `label-by-own-name`; S11 first run | none |
| 2 | S10 `resolve-recno-case`; S13; S11 second run | about 230 gis.uro requests (S10) |
| 3 | S15; R in slices; S6 last | data.taipei (S15); gis.uro (R) |

- S0 first, because every later change writes a delta against specs that do
  not exist yet in `openspec/specs/`.
- S1 before any `--fresh` run and before S10, because a fresh run drops the
  `case_headers` that S10 writes. It is one function and one test.
- S5 before S10 and R: both add cases whose names pass the orphan gate
  (華中247's `201-2、352地號` is the C4 、-list shape). Fix the extractor
  first, or the new cases are dropped.
- S3a before R, or every slice fetches the 4 rejected ids again.
- S4 and S9 are viewer-side and independent of the data.
- S10 absorbs S8, S12 and S14: one change to `urtpe/links.py:2073`, one
  re-emit. R reuses its resolver for new cases, so S10 runs before R.
- S11 needs no network. Its first run recovers 8 projects; its second run,
  after S10, uses the plan cases that S10 finds.
- S13 changes project ids, so it runs before R, or R refreshes 11 caches that
  are about to merge.
- S15 runs after S11, because S11 moves the city 使照 onto the plan case and
  so changes the disagreement set that S15 compares. It uses no gis.uro
  requests, so it does not compete with R for the rate limit.
- S6 (B2) waits for R: a full re-discovery changes which cases exist and
  which are superseded.

### Decisions waiting on the user (Batch B + C)

| Entry | Question | Blocks |
| --- | --- | --- |
| ~~C6 / S8~~ | **Decided 2026-11-03** for the 31 area-split ties: one approved recno binds every same-date case of its area split (the user's 吉林508 / 榮星53 examples) | ~~S8~~ unblocked |
| ~~C6 / S10~~ | **Superseded 2026-11-04** by the user rule "every recno has a case_id": the resolver finds a case for all 71 fallback nodes, so no badge is guessed or removed | ~~S10~~ unblocked |
| ~~C5 / S7~~ | **Decided 2026-11-04**: the building-permit adapter (S15) replaces the flag-only plan; flags remain only where no permit matches | ~~S7~~ merged into S15 |
| ~~S3~~ | **Resolved 2026-11-04**: the other session implemented and archived the change itself; S3a records the one residual | — |
| ~~R~~ | **Decided 2026-11-04**: resumable slices with a checkpoint; slices write the cache only; one emission after the last slice | ~~R run~~ unblocked |

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
