# Dataset completeness and churn audit

**Checked:** 2026-10-26 · **Follows:** `recover-truncated-rows-via-api` (archived 2026-10-26,
commit `20a2c92`) and the emission it produced (`532236e`, 1,442 records / 694 projects,
`published_date` 2026-10-15).
**Scope:** every gazette held in `D:\project\urtpe-gazettes\` (six publications,
2026-08-11 → 2026-10-15) and the emitted payload `data/projects.json`.
**No pipeline run was made for this audit.** Every number below comes from re-reading the
archived PDFs and the emitted files; nothing under `data/` or `viewer/` was written, so the
single-writer lock and the ~23 MB emission diff were not touched.

This consolidates five separate questions asked after the recovery change landed:

| # | Question | Answer | Section |
|---|---|---|---|
| 1 | Is every printed record present in the emission for 2026-10-15? | Yes — 1,442 printed, 1,442 emitted, 0 missing, 0 extra | [§2](#2-records-2026-10-15-pdf-vs-emission) |
| 2 | Does every record bind to a project family, in **each** gazette? | Yes — the partition is total and disjoint in all six; 0 unbound, 0 double | [§3](#3-projects-every-record-binds-to-exactly-one-family) |
| 3 | Why did the first viewer show 718 projects? | 718 = 709 + 9 duplicate `-2` slugs, collapsed by `84f7a8a`; 709 → 691 is publication-driven | [§4](#4-why-the-first-viewer-said-718-and-why-the-count-kept-falling) |
| 4 | How many records are new / deleted against the previous gazette? | 3, 5, **48 / 35**, 1, 1 — only the 2026-10-01 republication churns | [§5](#5-record-churn-between-consecutive-gazettes) |
| 5 | Was any of this already recorded? | No — `docs/gazette-churn.md` stops at 2026-08-27 and `scripts/gazette_churn.py` excludes 1151002 by design | [§6](#6-what-the-churn-says) |

---

## 1. What "complete" means in this audit

Three artefacts are compared, and they are produced by different code paths on purpose:

1. **The publication** — rows counted straight from each page's own ruling lines with
   `page.find_tables(strategy="lines")`, independent of `urtpe/extract.py`. This is the
   ground truth for "what the city printed".
2. **The reader** — `extract.extract_pdf_with_meta(..., corpus=..., retain_truncated=True)`
   → `to_raw_records` → `cleanse.cleanse_all` → `merge.merge`, using each gazette's real
   completion corpus (every *other* archived gazette), so a cell completed from a sibling
   publication is not mistaken for a publisher truncation.
3. **The emission** — `data/raw.tsv`, `data/merged.tsv` and `data/projects.json`.

A record is identified across gazettes by **(核定日期, 案名, 段, 首筆地號)**, never by 編號:
the list is newest-first, the city prepends and re-dates rows, and the shift is not even
affine (`AGENTS.md`, domain invariants). Within one gazette, `編號` is used only as the
coordinate it is.

Rows whose 地號 cell the publisher truncated are **excluded from cleanse/merge by design**
(`to_raw_records` marks them `source_fault`), so they are counted and named separately
rather than being allowed to look like deletions. The recovery pass owns them
(`openspec/specs/truncated-row-recovery/spec.md`).

---

## 2. Records: 2026-10-15 PDF vs emission

| Measure | Value |
|---|---|
| PDF pages | 246 |
| Printed data rows (independent census) | 1,442 |
| Distinct 編號 | 1,442, range 1..1442, **0 gaps, 0 repeats** |
| `data/raw.tsv` rows | 1,442, all `gazette_id = 2026-10-15` |
| In PDF, not emitted | **0** |
| Emitted, not in PDF | **0** |
| 案名 / 核定日期 / 行政區 mismatches | 0 / 0 / 0 |
| 地號 cells differing | 18 — all *longer* in the emission, none shorter, none unexplained |

The 18 longer cells are the corpus completions: the printed cell stops mid-token (a
publisher truncation), and the same case carries the full 地號 list in another gazette. All
18 happen to be rows whose 案名 declares exactly 3 parcels — a three-parcel cell is wide
enough to reach the printed row height that clips it.

| 編號 | page | printed chars → emitted | | 編號 | page | printed chars → emitted |
|---|---|---|---|---|---|---|
| 67 | 11 | 511 → 669 | | 796 | 134 | 511 → 669 |
| 79 | 13 | 382 → 399 | | 827 | 139 | 368 → 470 |
| 570 | 95 | 511 → 669 | | 851 | 144 | 358 → 455 |
| 672 | 112 | 397 → 672 | | 863 | 146 | 366 → 487 |
| 695 | 116 | 368 → 470 | | 902 | 152 | 366 → 487 |
| 702 | 118 | 368 → 470 | | 912 | 154 | 358 → 455 |
| 719 | 121 | 383 → 560 | | 919 | 155 | 383 → 560 |
| 726 | 122 | 368 → 470 | | 930 | 157 | 323 → 384 |
| | | | | 944 | 160 | 366 → 487 |
| | | | | 997 | 169 | 393 → 455 |

### The truncation budget: 22 = 18 + 4

| Path | Count | Where it shows |
|---|---|---|
| Cell completed from the completion corpus | 18 | `raw.tsv` 地號 longer than the printed cell |
| Row recovered through the case API | 4 | `projects.json` `recovery` node, `partial: true` |

The four recovered rows are the ones no sibling gazette can complete — they are truncated
in **every** publication that carries them:

| recno | project | 案名 declares | recovered parcels | flag |
|---|---|---|---|---|
| 188 | 中正區-永昌段四小段-46-4地號等117筆 | 117 | 106 | partial |
| 1005 | 萬華區-雙園段二小段-505地號等77筆 | 77 | 75 | partial, ambiguous zone |
| 1131 | 南港區-南港段一小段-720地號等105筆 | 105 | 71 | partial |
| 1206 | 文山區-萬隆段二小段-519地號等56筆 | 56 | 53 | partial |

None is repaired by inference: the recovered list is what the API returned, marked
`partial`, and the declared count is left disagreeing with it where it disagrees.

Before the recovery emission the same document parsed as **1,427 rows with 15 exclusions**
(`docs/urotpe_api_vs_pdf.md`, 2026-10-25). Fourteen of those fifteen are cells the
completion corpus can now fill; `1131` is the one that stays publisher-truncated and needed
the API. The other three always-truncated rows (188, 1005, 1206) were *parsed* then with a
clipped 地號, as were four cells (695, 702, 726, 827) that are corpus-completed today — the
older classifier both over-excluded and under-excluded, and both directions are the visible
signature of its change with the 2026-10-07 rebuild.

The 案名-declared parcel-count cross-check is a separate gate
(`openspec/changes/archive/2026-10-26-check-declared-parcel-counts`); in this gazette 112
printed cells carry no closing phrase and are its input set — being count-checkable is not
the same as being truncated: 48 rows per Gregorian gazette disagree with their own 案名 while
being complete as published.

---

## 3. Projects: every record binds to exactly one family

For each gazette: census the PDF, read it with its real corpus, merge, then check that the
partition is **total** (no cleansed record left without a family) and **disjoint** (no
record in two families, no empty family).

| gazette | pages | printed rows | publisher-truncated (outside merge) | merged | families | unbound | double | empty | 編號 gaps / dups |
|---|---|---|---|---|---|---|---|---|---|
| 2026-08-11 | 201 | 1,419 | 4 | 1,415 | 704 | 0 | 0 | 0 | 0 / 0 |
| 2026-08-20 | 201 | 1,422 | 4 | 1,418 | 707 | 0 | 0 | 0 | 0 / 0 |
| 2026-08-27 | 202 | 1,427 | 4 | 1,423 | 709 | 0 | 0 | 0 | 0 / 0 |
| 2026-10-01 | 246 | 1,440 | 4 | 1,436 | 691 | 0 | 0 | 0 | 0 / 0 |
| 2026-10-06 | 246 | 1,441 | 4 | 1,437 | 691 | 0 | 0 | 0 | 0 / 0 |
| 2026-10-15 | 246 | 1,442 | 4 | 1,438 | 691 | 0 | 0 | 0 | 0 / 0 |

In every gazette `len(all family members) == len(cleaned records)` — measured, not assumed.

The current emission, checked the same way:

| Measure | Value |
|---|---|
| `projects.json` counts | 694 projects, 1,442 records |
| Member slots / distinct recnos | 1,442 / 1,442 — 0 double-booked |
| Projects with 0 members | 0 |
| Family sizes | 269 singletons + 425 multi (222×2, 124×3, 51×4, 16×5, 11×6, 1×7) |
| Districts / date range | 12 / 2002-03-21 → 2026-10-15 |

1,438 merged rows + 4 recovered rows = 1,442; 691 merged families + 3 families formed by
the recovered rows = 694.

### 14 land cores that appear as two families

Not losses — every record is bound, but one site's history is split across two
`project_id`s because the two approvals declare different parcel counts, so `merge.score`
falls below `LINK_THRESHOLD = 0.7` on parcel coverage alone.

| land core | the two entries | why they stayed apart |
|---|---|---|
| 中山區 中山段二小段 202 | `…-202地號等12筆` / `…-202地號等1筆` | second row says `(原12筆)` |
| 中山區 吉林段四小段 676 | `…-676地號等18筆` / `…-676地號等1筆` | 18 vs 1, no `原` phrase |
| 中正區 中正段一小段 44 | `…-44地號等5筆` / `…-44地號等1筆` | second row says `(原5筆)` |
| 信義區 吳興段二小段 790-6 | `…-790-6地號等29筆` / `…-790-6地號等4筆` | second row says `(原29筆)` |
| 信義區 犁和段三小段 89 | `…-89地號等16筆` / `…-89地號等1筆` | second row says `(原16筆)` |
| 內湖區 文德段二小段 615 | `…-615地號等1筆` / `…-615地號等1筆-2` | identical 案名 → slug collision, `merge.py:154-158` |
| 北投區 桃源段二小段 251 | `…-251地號等17筆` / `…-251地號等2筆` | second row says `(原17筆)` |
| 北投區 立農段一小段 513 | `…-513地號等17筆` / `…-513地號等3筆` | second row says `(原17筆)` |
| 南港區 南港段四小段 566 | `…-566地號等6筆` / `…-566地號等1筆` | second row says `(原6筆)` |
| 南港區 玉成段三小段 545 | `…-545地號等8筆` / `…-545地號等4筆` | second row says `(原8筆…)` |
| 士林區 芝蘭段四小段 130 | `…-130地號等9筆` / `…-130地號等1筆` | second row says `(原9筆)` |
| 大同區 玉泉段二小段 91 | `…-91地號等42筆` / `…-91地號等7筆` | second row says `(原42筆)` |
| 大安區 金華段一小段 719 | `…-719地號等11筆` / `…-719地號等1筆` | second row says `(原11筆)` |
| 文山區 萬隆段二小段 519 | `…-519地號等23筆` / `…-519地號等56筆` | the 56-parcel entry is the **recovery node** (partial list) |

11 of the 14 carry `(原N筆)`; `文德段二小段615` is the only `-2` slug in the payload
(measured: exactly one `project_id` ends in `-2`). The `萬隆段二小段519` split is an
artefact of recovery: the API returns 56 declared parcels while the older rows list 23, so
the two rows look like different sites.

Over-merge was checked separately: no record pair in different families scores ≥ 0.7 on
`merge.score`, and every family's member set matches the re-derived clustering (0
disagreements).

---

## 4. Why the first viewer said 718, and why the count kept falling

The viewer's project count is a function of the payload, not of the gazette, so it moved
three times without a single record changing:

| Count | Where it came from | Records |
|---|---|---|
| **718** | first emission — 709 families plus 9 families whose slug collided and were suffixed `-2`/`-3` | 1,419 |
| **709** | after `84f7a8a` collapsed the `-2` duplicates (`merge.py:154-158` dedupes by ordinal, so the same 9 families no longer count twice) | 1,419 |
| **693** | the 2026-10-01 republication | 1,439 (emission) |
| **691** | re-reading 2026-10-01 with today's code | 1,436 mergeable |
| **694** | 2026-10-06/10-15 with the 4 recovered rows | 1,442 |

The 718 → 709 step is verified from the committed payloads, not from memory: the blob at
`84f7a8a~1` carries **718** `project_id`s of which 9 end in `-2`/`-3`, the blob at
`84f7a8a` carries **709** with 2, and today's `532236e` carries **694** with 1.

So 718 → 709 was a **display defect**, not data: the same 1,419 records, the same families,
counted twice for nine of them. 709 → 691 was **publication-driven**, and re-reading
2026-08-27 with today's code reproduces the 709, which rules out a code regression as the
cause of the drop.

### Exact family churn, 2026-08-27 → 2026-10-01

**28 dead / 11 born / 1 merge** — 709 − 28 + 11 − 1 = 691.

A family is *dead* when none of its rows survives into the next publication (matched on the
printed identity, not on `project_id`); *born* when none of its rows existed before. All 28
dead and all 11 born are listed here, because the split matters: only 23 of the 28 are real
losses.

#### 28 dead families

| family (`project_id`) | rows | why it died |
|---|---|---|
| 中山區-中山段一小段-450地號等12筆 | 1 | 事業概要 row removed from the list |
| 中山區-中山段三小段-57地號等7筆 | 2 | both rows removed |
| 中山區-德惠段二小段-582-2地號等14筆 | 1 | 事業概要 row removed |
| 中山區-榮星段五小段-755地號等1筆 | 1 | 事業概要 row removed |
| 中山區-正義段二小段-315地號等9筆 | 1 | row removed |
| 中山區-正義段四小段-243地號等24筆 | 1 | 事業概要 row removed |
| 中正區-中正段一小段-111地號等35筆 | 1 | 事業概要 row removed |
| 中正區-永昌段四小段-46-4地號等117筆 | 1 | **still printed** — truncated in 10-01, so outside the merge |
| 中正區-臨沂段一小段-396地號等3筆 | 1 | row removed |
| 中正區-臨沂段一小段-435地號等13筆 | 1 | 事業概要 row removed |
| 信義區-逸仙段三小段-285地號等2筆 | 1 | 2006 row retitled, joined the 2008/2010/2011 rows |
| 信義區-雅祥段四小段-662地號等32筆 | 1 | 事業概要 row removed |
| 北投區-桃源段五小段-575地號等1筆 | 1 | trailing `_` removed from the 案名 |
| 北投區-關渡段二小段-55地號等4筆 | 1 | row removed |
| 士林區-光華段二小段-956地號等26筆 | 1 | `（原22筆）` → `(原22筆)` |
| 士林區-天山段二小段-264地號等15筆 | 1 | 事業概要 row removed |
| 士林區-永新段三小段-395地號等1筆 | 2 | `核定公告_` → `核_定公告` |
| 大同區-市府段一小段-18-1地號等19筆 | 1 | 事業概要 row removed |
| 大同區-延平段一小段-314地號等36筆 | 1 | row removed |
| 大同區-迪化段三小段-343-4地號等23筆 | 1 | 事業概要 row removed |
| 大安區-仁愛段一小段-85地號等5筆 | 1 | 事業概要 row removed |
| 大安區-仁愛段四小段-114地號等2筆 | 3 | all three rows removed |
| 大安區-懷生段四小段-301地號等7筆 | 1 | 事業概要 row removed |
| 大安區-辛亥段四小段-277-1地號等23筆 | 1 | row removed |
| 大安區-通化段五小段-518地號等2筆 | 1 | 事業概要 row removed |
| 文山區-華興段四小段-44-2地號等12筆 | 1 | 事業概要 row removed |
| 萬華區-福星段四小段-319地號等35筆 | 1 | 事業概要 row removed |
| 萬華區-萬大段一小段-50-11地號等35筆 | 1 | 事業概要 row removed |

That is **16 事業概要 families, 7 other real removals, 4 typographic re-keys and 1
truncation flip** (永昌段四小段46-4 is printed in 10-01 but clipped there, so the row is
not deleted — see §5). The four re-keys are not losses: after the normalisation §5 applies
the record is byte-identical, which is why none of them appears in the deletion list.

#### 11 born families

| family (`project_id`) | rows | why it was born |
|---|---|---|
| 中正區-永昌段五小段-248地號等47筆 | 1 | new approval 2026-09-30 |
| 信義區-逸仙段三小段-285地號等2筆 | 4 | 3 new rows + the retitled 2006 row |
| 信義區-雅祥段一小段-599地號等22筆 | 1 | new approval 2026-10-01 |
| 內湖區-文德段二小段-231-3地號等4筆 | 1 | new approval 2026-09-15 |
| 北投區-奇岩段五小段-615地號等5筆 | 1 | new approval 2026-09-17 |
| 北投區-桃源段五小段-575地號等1筆 | 1 | re-keyed (trailing `_`) |
| 士林區-光華段二小段-956地號等26筆 | 1 | re-keyed (parentheses) |
| 士林區-永新段三小段-395地號等1筆 | 2 | re-keyed (`核_定公告`) |
| 大安區-仁愛段三小段-654地號等4筆 | 1 | new approval 2025-12-11 |
| 松山區-西松段二小段-54地號等9筆 | 1 | new approval 2026-09-24 |
| 萬華區-萬華段二小段-894地號等22筆 | 1 | new approval 2026-09-10 |

**7 genuinely new families, 3 re-keys, 1 rename-grown family** — consistent with §5, where
the same publication adds 48 records: the 7 new families account for 7 of them, 逸仙285 for
3 more, and the remaining 38 arrive inside families that already existed.

#### The one merge

`懷生段三小段-249地號等26筆` was carried as **two** projects in 08-27 because the
2020-08-05 row's 行政區 cell read 中正區 while its 案名 said 大安區. `merge.score` returns 0
on a district mismatch, so the mislabelled row could not join its own family. The
republication corrects the cell to 大安區 and the two entries become one — a label fix, not a
data change. That is the −1 in `709 − 28 + 11 − 1 = 691`.

---

## 5. Record churn between consecutive gazettes

Rows are matched on the printed identity **(核定日期, 案名, 段, 首筆地號)**. Leftovers are
paired again ignoring the date (re-dated rows) and ignoring the name (retitled rows); only
what still has no partner counts as new or deleted. No exact-identity key occurs twice in
any gazette, so "unchanged" is exact rather than approximate.

### Summary

| transition | printed before → after | unchanged | edited | new | deleted | genuinely new | genuinely gone | net |
|---|---|---|---|---|---|---|---|---|
| 08-11 → 08-20 | 1,419 → 1,422 | 1,415 | 0 | 3 | 0 | **3** | **0** | +3 |
| 08-20 → 08-27 | 1,422 → 1,427 | 1,418 | 0 | 5 | 0 | **5** | **0** | +5 |
| 08-27 → 10-01 | 1,427 → 1,440 | 1,372 | 14 | 50 | 37 | **48** | **35** | +13 |
| 10-01 → 10-06 | 1,440 → 1,441 | 1,436 | 0 | 1 | 0 | **1** | **0** | +1 |
| 10-06 → 10-15 | 1,441 → 1,442 | 1,437 | 0 | 1 | 0 | **1** | **0** | +1 |

Four of the five transitions are pure append. All of the churn sits in the 2026-10-01
republication, which grew from 202 to 246 pages.

### Truncation flips (2 of the raw 50 / 2 of the raw 37 are not churn)

The set of publisher-truncated rows is **not** constant across gazettes — re-pagination moves
which cells clip:

| gazette | the 4 truncated rows |
|---|---|
| 2026-08-11 / 08-20 / 08-27 | 南港段一小段720（105筆）, 萬隆段二小段519（56筆）, 雙連段一小段197（72筆）, 長春段二小段559-5（83筆） |
| 2026-10-01 / 10-06 / 10-15 | 南港段一小段720, 萬隆段二小段519, 永昌段四小段46-4（117筆）, 雙園段二小段505（77筆） |

So two rows printed in 08-27 become readable in 10-01 (they look "new") and two readable in
08-27 become truncated in 10-01 (they look "deleted"):

- `+ 2007-07-06 長春段二小段559-5` — truncated as 08-27 編號 1381
- `+ 2013-01-08 雙連段一小段197` — truncated as 08-27 編號 1210
- `− 2017-02-16 雙園段二小段505` — truncated as 10-01 編號 1003
- `− 2024-12-30 永昌段四小段46-4` — truncated as 10-01 編號 186

南港720 and 萬隆519 are truncated in all six publications and therefore never enter this
comparison at all.

### 2026-08-11 → 2026-08-20: 3 new, 0 deleted

```
2026-08-18  立農段五小段163-2      擬訂臺北市北投區立農段五小段163-2地號等4筆土地都市更新事業計畫及權利變換計畫案
2026-08-19  龍泉段一小段217-7      擬訂臺北市大安區龍泉段一小段217-7地號等21筆(原217-6地號等20筆)土地都市更新事業計畫案
2026-08-20  福星段四小段393-1      擬訂臺北市萬華區福星段四小段393-1地號等18筆土地都市更新事業計畫及權利變換計畫案
```

### 2026-08-20 → 2026-08-27: 5 new, 0 deleted

```
2026-08-25  逸仙段三小段34          變更(第三次)臺北市信義區逸仙段三小段34地號等6筆(原4筆)土地(基隆路整宅B基地)都市更新權利變換計畫案
2026-08-25  文林段三小段838-1       變更(第二次)臺北市北投區文林段三小段838-1地號等7筆土地都市更新權利變換計畫案
2026-08-26  光華段二小段956         擬訂臺北市士林區光華段二小段956地號等26筆（原22筆）土地都市更新事業計畫及權利變換計畫案
2026-08-27  振興段四小段166         擬訂臺北市北投區振興段四小段166地號等7筆土地都市更新事業計畫及權利變換計畫案
2026-08-27  懷生段四小段4           變更臺北市大安區懷生段四小段4地號等19筆土地都市更新事業計畫及擬訂權利變換計畫案
```

### 2026-08-27 → 2026-10-01

#### 14 rows edited in place (5 re-dated, 9 retitled) — net count unchanged

| land core | old date | new date |
|---|---|---|
| 康寧段三小段420 | 2025-08-05 | 2025-11-26 |
| 逸仙段二小段107-2 | 2017-08-08 | 2017-02-18 |
| 逸仙段三小段294-4 | 2008-11-14 | 2012-08-22 |
| 中山段四小段473 | 2007-11-20 | 2006-12-20 |
| 景美段一小段501 | 2005-03-18 | 2007-08-02 |

```
2024-03-12 天母段三小段96      擬訂…事業計畫及權利變換計畫案 → 變更…都市更新權利變換計畫案
2023-09-06 中南段四小段105     變更…權利變換計畫案 → 變更(第二次)…105(原90)地號等13筆(原24筆)…
2022-12-29 南海段一小段687     …案核定_公告 → …案核定公告_（底線位置對調，純排版）
2021-07-20 虎林段四小段38      擬訂…138筆(原120筆) 事業計畫案 → 變更…事業計畫案
2021-03-24 永吉段四小段44      變更(第二次)…26筆 權利變換計畫案 → …權利變換計畫(釐正圖冊)
2018-01-25 吉林段四小段603      擬訂…40筆 事業計畫案 → 變更…事業計畫案
2018-01-09 寶清段一小段341-1    寶清段ㄧ小段（異體字） → 寶清段一小段
2016-10-04 吉林段四小段705      擬訂…(含釐正圖冊)案 → 變更…(含釐正圖冊)案
2006-01-09 逸仙段三小段285      擬訂…(晶宮大廈)事業計畫案 → …事業計畫及權利變換計畫案
```

#### 48 genuinely new — 36 historical backfills + 12 recent

Historical rows dated 2005–2025 that the publication had not carried before:

```
2005-03-01 萬慶段三小段434     變更臺北市文山區萬慶段三小段434地號等4筆土地都市更新事業計畫案
2005-08-03 南海段二小段332     擬訂臺北市中正區南海段二小段332地號等30筆土地都市更新權利變換計畫案
2007-02-27 寶清段七小段678     變更臺北市松山區寶清段七小段678地號等1筆土地(原豪門世家基地)都市更新權利變換計畫案
2007-04-14 南海段二小段332     變更臺北市中正區南海段二小段332地號等30筆土地都市更新事業計畫案
2008-04-28 大龍段二小段15      變更臺北市大同區大龍段二小段15地號等2筆(原7筆)土地都市更新事業計畫案
2008-05-29 逸仙段三小段285     變更臺北市信義區逸仙段三小段285地號等2筆土地(晶宮大廈)都市更新權利變換計畫案
2009-03-17 興安段二小段558     變更臺北市文山區興安段二小段558地號等5筆土地都市更新事業計畫及權利變換計畫案
2009-05-27 景美段一小段522     變更臺北市文山區景美段一小段522地號等27筆土地都市更新事業計畫及權利變換計畫案
2009-10-26 興隆段二小段377     擬訂臺北市文山區興隆段二小段377地號等35筆土地都市更新權利變換計畫案
2010-06-28 興安段二小段558     變更(第二次)臺北市文山區興安段二小段558地號等5筆土地都市更新事業計畫及權利變換計畫案(釐正圖冊)
2010-07-23 逸仙段三小段285     變更(第二次)臺北市信義區逸仙段三小段285地號等2筆土地(晶宮大廈)都市更新權利變換計畫案
2011-08-22 德惠段二小段573     擬訂臺北市中山區德惠段二小段573地號等56筆土地都市更新權利變換計畫案
2011-11-24 逸仙段三小段285     變更(第三次)臺北市信義區逸仙段三小段285地號等2筆土地(晶宮大廈)都市更新權利變換計畫案
2011-12-13 長安段一小段579     變更臺北市中山區長安段一小段579地號等1筆土地(原世和大樓基地)都市更新事業計畫案
2012-07-06 奇岩段四小段13      變更臺北市北投區奇岩段四小段13地號等2筆土地都市更新權利變換計畫案(釐正圖冊)
2012-10-08 虎林段四小段629     擬訂臺北市信義區虎林段四小段629地號等12筆土地都市更新權利變換計畫案
2013-01-02 永昌段六小段158     變更(第二次)臺北市中正區永昌段六小段158地號等48筆土地都市更新權利變換計畫案(含釐正圖冊)
2013-04-16 長安段二小段684     變更臺北市中山區長安段二小段684地號等13筆土地都市更新事業計畫案
2013-08-20 玉泉段一小段11      變(第二次)更臺北市大同區玉泉段一小段11地號等73筆土地都市更新權利變換計畫案暨釐正圖冊案
2013-09-06 南港段一小段527     變更臺北市南港區南港段一小段527地號等4筆土地(R13)都市更新權利變換計畫(含釐正圖冊)案
2013-10-18 中南段二小段862     變更(第二次)臺北市南港區中南段二小段862地號等1筆土地都市更新權利變換計畫案(釐正圖冊)
2013-11-14 玉泉段一小段11      變更(第三次)臺北市大同區玉泉段一小段11地號等73筆土地都市更新事業計畫及權利變換計畫暨變更(第一次)釐正圖冊案
2013-11-28 興隆段二小段377     變更(第四次)臺北市文山區興隆段二小段377地號等35筆土地都市更新權利變換計畫釐正圖冊案
2013-12-24 東湖段一小段17-2    變更(第二次)臺北市內湖區東湖段一小段17-2地號等1筆土地都市更新事業計畫及權利變換計畫(含釐正圖冊)案
2014-01-07 寶清段一小段341-1   擬訂臺北市松山區寶清段一小段341-1地號等28筆土地都市更新權利變換計畫案
2014-03-13 中南段二小段862     變更(第三次)臺北市南港區中南段二小段862地號等1筆土地都市更新權利變換計畫案
2014-11-17 吉林段三小段811     變更(第二次)臺北市中山區吉林段三小段811地號等28筆(原35筆)土地都市更新權利變換計畫案(含釐正圖冊)
2016-05-27 敦化段一小段703     變更(第二次)臺北市松山區敦化段一小段703地號等9筆土地都市更新權利變換計畫釐正圖冊案
2016-05-27 寶清段一小段51-3    變更臺北市松山區寶清段一小段51-3地號等1筆土地都市更新權利變換計畫(含釐正圖冊)案
2018-02-02 芝山段一小段127-1   擬訂臺北市士林區芝山段一小段127-1地號等6筆土地都市更新事業計畫及權利變換計畫案
2021-12-06 雙連段三小段689     擬訂臺北市大同區雙連段三小段689地號(原726地號)等40筆(原35筆)土地都市更新權利變換計畫案
2022-05-25 大同段一小段447-2   變更(第二次)臺北市大同區大同段一小段447-2地號等2筆土地都市更新權利變換計畫(含釐正圖冊)案
2022-09-15 橋北段一小段574-1   變更(第二次)臺北市大同區橋北段一小段574-1地號等41筆土地都市更新權利變換計畫案
2024-03-21 奇岩段五小段444     變更(第二次)臺北市北投區奇岩段五小段444地號等7筆土地都市更新權利變換計畫案
2025-08-13 臨沂段三小段318     變更(第四次)臺北市中正區臨沂段三小段318地號等4筆土地都市更新權利變換計畫案
2025-12-11 仁愛段三小段654     擬訂臺北市大安區仁愛段三小段654地號等4筆土地都市更新事業計畫案
```

Rows approved after 2026-09-10:

```
2026-09-10 萬華段二小段894     擬訂臺北市萬華區萬華段二小段894地號等22筆土地都市更新事業計畫及權利變換計畫案
2026-09-15 文德段二小段231-3   擬訂臺北市內湖區文德段二小段231-3地號等4筆土地都市更新事業計畫案
2026-09-15 華中段一小段247     變更(第二次)臺北市萬華區華中段一小段201-2、352地號等26筆土地都市更新事業計畫及擬訂權利變換計畫案
2026-09-17 奇岩段五小段615     擬訂臺北市北投區奇岩段五小段615地號等5筆土地都市更新事業計畫案_核定公告
2026-09-17 大業段三小段314     變更(第二次)臺北市北投區大業段三小段314地號等21筆土地都市更新權利變換計畫案
2026-09-23 雅祥段一小段492     變更臺北市信義區雅祥段一小段492地號等13筆土地都市更新事業計畫案
2026-09-24 西松段二小段54      擬訂臺北市松山區西松段二小段54地號等9筆土地都市更新事業計畫案
2026-09-24 長春段一小段764     變更臺北市中山區長春段一小段764地號等2筆土地都市更新事業計畫及權利變換計畫案
2026-09-29 桃源段四小段424-8   變更臺北市北投區桃源段四小段424-8地號等15筆土地都市更新事業計畫及權利變換計畫案（內文用異體字更／都）
2026-09-30 永昌段五小段248     擬訂臺北市中正區永昌段五小段248地號等47筆土地都市更新事業計畫案
2026-09-30 關渡段二小段303     變更臺北市北投區關渡段二小段303地號等5筆土地都市更新權利變換計畫案
2026-10-01 雅祥段一小段599     擬訂臺北市信義區雅祥段一小段599地號等22筆土地都市更新事業計畫及權利變換計畫案
```

#### 35 genuinely deleted — 16 are 事業概要 rows

```
2020-01-15 中正段一小段111 35筆      2020-02-06 榮星段五小段755 1筆
2020-02-12 德惠段二小段582-2 14筆    2020-04-14 迪化段三小段343-4 23筆
2020-05-27 雅祥段四小段662 32筆      2020-06-24 臨沂段一小段435 13筆
2020-09-29 福星段四小段319 35筆      2021-01-20 華興段四小段44-2 12筆
2021-09-15 萬大段一小段50-11 35筆    2022-03-22 中山段一小段450 12筆
2022-03-24 通化段五小段518 2筆(原1筆) 2022-05-04 仁愛段一小段85 5筆
2022-10-06 市府段一小段18-1 19筆     2023-04-18 天山段二小段264 15筆
2024-05-09 懷生段四小段301 7筆       2025-08-19 正義段四小段243 24筆
```

```
2000-09-29 仁愛段四小段114   擬訂臺北市大安區仁愛段四小段114地號等6筆土地都市更新事業計畫案
2005-10-25 仁愛段四小段114   變更臺北市大安區仁愛段四小段114地號等6筆土地都市更新事業計畫案
2008-05-20 仁愛段四小段114   變更(第二次)臺北市大安區仁愛段四小段114地號等2筆土地都市更新事業計畫案
2010-02-23 中山段三小段57    擬訂臺北市中山區中山段三小段57地號等7筆土地都市更新事業計畫案
2013-06-10 溫泉段四小段559   變更臺北市北投區溫泉段四小段559地號等36筆土地都市更新事業計畫及擬訂權利變換計畫案
2014-02-27 吳興段三小段196   擬訂臺北市信義區吳興段三小段196地號等17筆土地都市更新事業計畫案
2014-02-27 溫泉段四小段559   變更(第二次)臺北市北投區溫泉段四小段559地號等36筆土地都市更新事業計畫案
2016-01-21 懷生段一小段931   變更(第五次)臺北市大安區懷生段一小段931地號等20筆土地都市更新權利變換計畫案-西區
2017-10-26 美仁段一小段800   擬訂臺北市松山區美仁段一小段800地號等9筆土地都市更新事業計畫案
2018-01-25 永吉段四小段44    變更(第二次)臺北市信義區永吉段四小段44地號等26筆土地都市更新事業及變更權利變換計畫案
2018-09-13 正義段二小段315   擬訂臺北市中山區正義段二小段315地號等9筆土地都市更新事業計畫案
2018-12-27 辛亥段四小段277-1 擬訂臺北市大安區辛亥段四小段277-1地號等23筆(原19筆)土地都市更新事業計畫及權利變換計畫案
2019-02-19 臨沂段一小段396   擬訂臺北市中正區臨沂段一小段396地號等3筆土地都市更新事業計畫案
2019-02-26 逸仙段二小段151   變更(第二次)臺北市信義區逸仙段二小段151地號等21筆土地都市更新權利變換計畫案(含釐正圖冊)(A區段)
2019-03-19 中山段三小段57    變更臺北市中山區中山段三小段57地號等7筆土地都市更新事業計畫及擬訂權利變換計畫案
2020-02-27 延平段一小段314   擬訂臺北市大同區延平段一小段314地號等36筆土地都市更新事業計畫及權利變換計畫案
2022-09-14 關渡段二小段55    擬訂臺北市北投區關渡段二小段55地號等4筆土地都市更新事業計畫及權利變換計畫案
2024-03-21 北安段一小段60-1  擬訂臺北市中山區北安段一小段60-1地號等10筆土地都市更新事業計畫案
2025-12-11 大業段五小段1-2   擬訂臺北市北投區大業段五小段1-2地號1筆土地都市更新事業計畫及權利變換計畫案
```

Three names repeat inside the deletion list — `仁愛段四小段114` (2000, 2005, 2008),
`中山段三小段57` (2010, 2019) and `溫泉段四小段559` (2013, 2014) — i.e. the city dropped
whole small families, not single rows.

### 2026-10-01 → 2026-10-06: 1 new, 0 deleted

```
2026-10-06  大業段四小段574  變更臺北市北投區大業段四小段574地號1筆土地都市更新事業計畫案
```

### 2026-10-06 → 2026-10-15: 1 new, 0 deleted

```
2026-10-15  通化段四小段336  變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市更新事業計畫案
```

---

## 6. What the churn says

- **The gazette is an append-only list except when it is republished.** Four of five
  transitions add 1–5 rows and touch nothing historical; the 2026-10-01 republication
  (202 → 246 pages) added 36 backfilled historical rows and 12 fresh approvals, dropped 16
  事業概要 rows and 19 older rows, and corrected 14 existing rows in place.
- **"Net +13" is the least informative number available.** The same transition is 48
  additions and 35 removals. Anything that reports only the net figure cannot distinguish a
  quiet week from a re-publication.
- **The standing churn document could not have caught it.** `docs/gazette-churn.md` is
  generated with `CUTOFF = "2026-08-11"` and lists only 1150820 / 1150827; its own comment
  says 1151002 is "deliberately excluded … carries 15 records whose 地號 cell the publisher
  truncated". That was true under the older classifier; with the corpus-completion and
  recovery paths in place the same publication is readable, and it is the only one that
  churns. Regenerating it is a code change (the cutoff and the exclusion), not a docs fix.
- **Truncation moves between publications.** Four rows clip at 08-27 that do not at 10-01,
  and vice versa. A cross-gazette diff built on the reader's output will invent two
  additions and two deletions unless the truncated sets are reconciled, which is why §5
  subtracts them explicitly.

## 7. Open items

| Item | Evidence | Status |
|---|---|---|
| `index.jsonl` records 1,414 for 2026-08-11 | today's partition is 1,415 mergeable + 4 truncated = 1,419 printed | **1 row unexplained**, from the 2026-10-07 ingest; the other five entries match today's read or differ only by recovery |
| `index.jsonl` records 1,439 for 2026-10-01 | 1,440 printed | consistent with **3 of 4** recovered rows landing at that publication; 10-06 and 10-15 match printed exactly |
| 南港段一小段720, 萬隆段二小段519 | truncated in all six publications | stable publisher blind spot; both carry partial `recovery` nodes |
| 14 two-entry land cores | §3 | under-merge, not loss; 11 carry `(原N筆)`, 1 is a bare count change (吉林段四小段676), 1 is a slug collision, 1 is a recovery artefact |
| 19 non-概要 deletions | §5 | no same-land-core partner under any date or name; a name-similarity screen cannot separate a re-keyed row from boilerplate (64 spurious pairs at ≥ 0.75), so no re-keying is claimed |

---

## Appendix A — how each number was produced

The audit used the same functions the pipeline does, so the comparison is against the real
reader rather than a re-implementation:

```python
corpus = corpus_mod.build_corpus(members, exclude=gid, cache_dir=cache)
recs, meta = extract_mod.extract_pdf_with_meta(str(pdf), corpus=corpus,
                                               retain_truncated=True)
raw = extract_mod.to_raw_records(recs)
clean = cleanse_mod.cleanse_all(raw)          # drops source_fault rows
projects = merge_mod.merge(clean)             # the partition under test

owner = {m.recno: p.project_id for p in projects for m in p.members}
assert set(owner) == {m.recno for m in clean}                    # total
assert len([m for p in projects for m in p.members]) == len(clean)  # disjoint
```

`members` is every archived PDF except the one being read, so the completion corpus is the
real one. The printed census uses `page.find_tables(strategy="lines")` and takes the first
column of each row, keeping only cells that are purely digits — independent of
`urtpe/extract.py`, which is what makes it a check rather than a restatement.

The cross-gazette comparison normalises names with NFKC, strips whitespace and the
`核定公告` / `_` tails, then matches exactly on (date, name, 段, first parcel), then pairs
leftovers ignoring date and ignoring name.

The scripts were ad-hoc this session (`%TEMP%\gazette_audit.py`, `gazette_transitions.py`,
`flip_check.py`, `q2_projects.py`, `census_1015.py`) and are not committed; they are cheap
to rebuild from the snippet above. Promoting them to `scripts/` would be a code change with
its own test, so it was not done here.

## Appendix B — the six publications

| gazette | archived file | pages | sha256 (first 16) |
|---|---|---|---|
| 2026-08-11 | `核定案件-2026-08-11.pdf` | 201 | `e85c497654983520` |
| 2026-08-20 | `核定案件-2026-08-20.pdf` | 201 | `ed95e4297ccbd724` |
| 2026-08-27 | `核定案件-2026-08-27.pdf` | 202 | `f09a25c7643e0286` |
| 2026-10-01 | `核定案件-2026-10-01.pdf` | 246 | `a3ad23b0c6b08fe5` |
| 2026-10-06 | `核定案件-2026-10-06.pdf` | 246 | `045314464c5ef520` |
| 2026-10-15 | `核定案件-2026-10-15.pdf` | 246 | `9b80a6bcbf7c18e0` |

Two of the archived files were downloaded under a later date and filed by publication:
`核定案件-2026-10-06.pdf` arrived as `核定案件-2026-10-13.pdf` and
`核定案件-2026-10-15.pdf` as `核定案件-2026-10-23.pdf` (`index.jsonl`, `source_path`).
The published date comes from each document's own 統計至 line, not from the download.
