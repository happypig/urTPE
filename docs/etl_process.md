# ETL Process — PDF to Viewer

The pipeline turns the Taipei City Government's urban-renewal approved-cases
gazette (臺北市都市更新核定案件一覽表) into a per-project history graph and a
static HTML viewer. One command runs it:

```powershell
python -m urtpe.cli source.pdf -o data --viewer viewer --links
```

This document describes each stage: what it reads, what it writes, and the gate
that protects it. The domain rules behind the stages live in
`openspec/config.yaml`; the companion docs are `docs/cli_flow_v2.md` (CLI flow
and link discovery) and `docs/domain_model.md` (entity model).

Measured on the 2026-10-28 gazette: **1,444 records → 675 projects**, dates
2002-03-21 to 2026-10-28, calendar mixed (Gregorian), 318 nodes flagged for
review, 13 auto-fixes applied. (Re-measured 2026-11-13; the ledger merges —
萬隆519 and 河堤399, then the five split families reunified on 2026-11-13 —
moved the project count from 682 to 680 to 675. The rule did not change; the
population did.)

---

## 1. Pipeline overview

```
gazette PDF (uro.gov.taipei, ~2 MB, weekly-to-monthly)
  │
  ▼
[1] Acquire      scripts/poll_gazette.py — hash-gated download into the archive
  │                D:\project\urtpe-gazettes\核定案件-YYYY-MM-DD.pdf
  ▼
[2] Extract      urtpe/extract.py — ruled-table read, cell by cell
  │                → RawRecord list  → data/raw.tsv (verbatim)
  ▼
[3] Cleanse      urtpe/cleanse.py — normalize, derive, flag
  │                → CleanRecord list → data/clean.tsv
  ▼
[4] Ledger       urtpe/ledger.py — apply manual corrections (content-keyed)
  ▼
[5] Merge        urtpe/merge.py — similarity clustering into families
  │                → Project list → data/merged.tsv
  ▼
[6] Links        urtpe/links.py — portal discovery onto the merged families (--links)
  ▼
[7] Graph        urtpe/graph.py — per-project node/edge history
  │                → data/projects.json (schema v2)
  ▼
[8] Viewer       urtpe/viewer.py — window.PROJECTS payload for the static page
                   → viewer/projects.data.js  (open viewer/index.html from file://)
```

Stage [8] has an input path too: `viewer/projects.data.js` is both input and
output. `--from-js` reloads it and re-emits it, so the viewer payload is state,
not scratch.

Two regimes run the stages:

| Regime | Command | Stages run |
| --- | --- | --- |
| Full ingest | `python -m urtpe.cli <pdf> -o data --viewer viewer --links` | all of them, from the PDF |
| Rebuild | `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links` | reload payload → links → graph → viewer |

A full rebuild takes ~45 s and is the only way a reader change reaches
historical records uniformly (`urtpe/cli.py:249`, `_ingest_pdf` docstring).
A rebuild skips stages 2–5: the payload's nodes are loaded back as
CleanRecords verbatim (`urtpe/cli.py:118`, `_load_projects_from_js`).

---

## 2. Acquisition (stage 1)

`scripts/poll_gazette.py` answers one question: has the city published a
gazette we do not hold? It never ingests. Ingesting an archived gazette is a
separate explicit act (`python -m urtpe.cli <path>`).

- Change detection is by content hash (SHA-256), never by timestamp. The
  publisher re-uploads unchanged documents under a later 資料更新 stamp;
  measured 2026-10-05, the page advertised 115-09-29 while the newest gazette
  held was 2026-09-24 and the PDF was byte-identical.
- Steady-state cost is one ~86 KB page GET. The ~2 MB PDF downloads only when
  the page's bytes change.
- Every check appends a dated record to `poll_log.jsonl` with status
  `new_gazette` / `reuploaded` / `unchanged` / `failed`. A check that found
  nothing must not look like a check that never ran.
- The archive lives outside the repo at `D:\project\urtpe-gazettes\`
  (override: `URTPE_ARCHIVE_ROOT`). `index.jsonl` records per publication:
  digest, reader version, record/project counts, `publisher_url`. Never
  delete a member; the corpus, the reconciler and the release-diff report all
  re-read archived PDFs.

The publisher serves one PDF link at a time and repoints it on every
publication. The live link names "whatever is newest". A version-specific URL
(`…/relfile/18558/10496/<uuid>.pdf`) names one document and stays durable;
the archive index records it per entry.

---

## 3. Extraction (stage 2) — `urtpe/extract.py`

pymupdf reads each page with `find_tables(strategy="lines")`. Cell boundaries
come from the document's own ruling lines, never from stored coordinates —
the city has moved columns and changed calendars between publications, and a
reader anchored on geometry survives both. There is no positional or
text-alignment fallback: `strategy="text"` measured as collapsing a 4-column
grid to 2 and merging two cells into one field.

Seven columns per row, verbatim: 編號, 核定日期, 行政區, 案名, 地號, 實施者,
更新規劃單位. Plus `gazette_id` (the 統計至 publication date).

### 3.1 Refusal, not approximation

A structure the reader cannot read exactly raises `TableStructureError`
(exit 3) and nothing is written. Located faults, one per problem:

- merged cell — a grid edge with no ruling line across it
- ragged grid / ragged row — wrong cell count
- no table on page — ruling lines absent or undetectable
- cell content owned by a spanning cell

### 3.2 Page furniture and wrapping

- A cell wrapped across lines inside its boundary is re-joined by removing
  only the newlines (`urtpe/extract.py:53`).
- The city prints the page number inside the last row's 地號 cell on some
  pages. `strip_page_footer` removes it only when the trailing digits equal
  that page (`urtpe/extract.py:372`).
- The header band is not located by position. From 1151006 the city stopped
  drawing it after page 1, so grid row 0 became a real record; the test is
  content-based — a row whose 編號 fails `RECNO_RE` is a band, otherwise data
  (`urtpe/extract.py:617`).
- A defective export repeats one data row in the page header of every later
  page; `_dedupe_by_recno` keeps the first occurrence.

### 3.3 Publisher truncation — the two-fault distinction

A 地號 cell fails in two unrelated ways, and the distinction decides the
response (`AGENTS.md`, check-declared-parcel-counts):

1. **Reader fault** — page furniture inside the cell. Stripped, per §3.2.
2. **Publisher fault** — the city cut the cell at the printed row height and
   never drew the remainder. The text is absent from the PDF. Never repaired
   by inference; the record is excluded and named.

A cell is publisher-truncated when its text ends in a tail pattern
(`、，,` / digit / sub-parcel hyphen — the measured `…578、579-` of 編號 1005),
or when it lost its closing phrase while showing fewer parcels than its own
案名 declares. A cell whose closing phrase (`地號等N筆土地`) is present is
never count-checked: 48 rows per Gregorian gazette disagree with their 案名
and are complete as published.

Two bounded repairs exist, both with audit entries:

- **Corpus completion.** Another approval of the same unit elsewhere in the
  archive completes the cell, only when three checks all hold: same 段/小段,
  the truncated text is a literal prefix of the candidate's, and the
  candidate's parcel count equals the count the 案名 declares
  (`complete_truncated_cell`, `urtpe/extract.py:279`). The candidate corpus
  is built once per archive state and cached
  (`urtpe/corpus.py`, `.corpus_cache/` outside the output tree).
- **API recovery (opt-in).** `--recover-truncated` keeps the truncated row,
  and `urtpe/recovery_pass.py` re-identifies it through the city's own APIs
  (gis.uro ashx + UDD GeoServer) with four independent checks: same unit,
  surviving 案名 contained, declared count present, date closes. Recovered
  rows carry provenance and enter the flow; unresolvable rows are residuals,
  back on the plain exclusion path. Without the flag, output is
  byte-identical and no request is sent.

An empty 核定日期 cell is the mirror defect (publisher printed no date). The
recovery pass recovers it from the 案名 when exactly one approval date closes
(D9f-1, `urtpe/recovery_pass.py:69`).

The exclusion count is reported in the run output, the tripwire report and
`review_report.txt`. A short gazette never reads as a faithful copy.

### 3.4 Calendars

ROC (`115/8/27`) through the 2026-08-27 gazette; Gregorian from the
2026-09-24 gazette onward. Both accepted per cell — one publication may mix —
and normalized to ISO-8601 (`to_iso`, `urtpe/extract.py:391`). A year under
1911 is unambiguously ROC. `published_date` comes from the document's own
統計至 line.

---

## 4. Cleansing (stage 3) — `urtpe/cleanse.py`

Pure logic, no I/O. `RawRecord → CleanRecord` with three kinds of annotation:
`auto_fixes` (applied), `review_flags` (needs a person), and `parse_error`
(raw layer, kept in raw.tsv).

### 4.1 Known-error normalization (auto_fixes)

| Input | Output | Fix note |
| --- | --- | --- |
| 松化區 | 松山區 | 行政區錯字→松山區 |
| 計劃 | 計畫 | (name normalization) |
| ㄧ | 一 | (compatibility ideograph) |
| 事業換計畫 | 事業計畫 | 案名錯字→事業計畫 |
| 土地都市更新計畫案 | 土地都市更新事業計畫案 | 案名補事業(都市更新計畫案簡寫) |
| 地號 cell glued into 案名 | recovered from the 案名 tail | 地號自案名尾端復原(地號欄黏入案名) |
| single-parcel cell contradicting a count-1 案名 | trust the 案名 | 地號欄單筆地號與案名矛盾→依案名 |

A single record may carry several fixes. Every application is named, so a
fix is reversible after the fact.

### 4.2 Derived fields

From the 案名 and 地號 cells: `section`, `first_parcel`, `parcels`,
`aliases` (原地號 renumbering: `689地號(原726地號)`), `land_count`,
`orig_count` (`13筆(原11筆)`), `named_anchor` (`原東星大樓基地`),
`area_section` (甲/A/B 區段), `stage` (擬訂 = 0 / 變更 = 1 / 變更(第N次) = N)
and `track` (事業概要 / 事業計畫 / 權利變換). Combined-track 案名 carry two
stage ordinals, emitted additively as `stage_事業計畫` / `stage_權利變換`
(`urtpe/cleanse.py:381`).

The district read uses the corpus's own 行政區 column as its enum
(D14(b), `collect_districts`) — the city prints 臺北大安區 / 臺北士林區
(no 市) and 臺北市投區 (no 北), so a strict 臺北市-anchored regex misreads
them. A cell naming no district in the enum reads `''` and keeps the
mismatch flag; the system never infers the missing character.

### 4.3 Review flags (review_flags)

Ambiguity is surfaced, never resolved silently. Current measured set
(2026-10-28 gazette, 321 flagged nodes):

- 日期無法解析 — the date cell parsed to neither calendar
- 地號無法解析(缺少段小段) / (缺少地號清單)
- 行政區與地號行政區不一致(地號為X) — the two columns disagree
- 案名與地號段小段不一致(地號為X)
- family carries no land count; project_id keeps the ? placeholder

Link discovery adds flags after merge (§7): 孤兒案件未達相似度門檻,
階段與平台案件狀態不一致, 節點未能對應平台案件, 片段家族合併候選.

---

## 5. Correction ledger (stage 4) — `urtpe/ledger.py`

Manual corrections live in an append-only JSONL ledger, by default
`urtpe-gazettes/corrections.jsonl` (override: `URTPE_LEDGER` / `--ledger`;
an explicit empty string opts out for forensic runs). It applies on every
PDF ingest — an operator cannot drop corrections by omitting an option.

Keyed on **land core + ISO approval date**, never on 編號. 編號 is a
coordinate in a newest-first mutable list; the city prepends new approvals
and re-dates historical rows, so a 編號-keyed patch lands on a different
row after the next publication.

Entry kinds:

| Kind | Effect |
| --- | --- |
| field correction | sets one of the correctable fields (track, stage, land_count, …) |
| `confirm_merge` | unions a record pair before similarity scoring — a §6.8 borderline pair a person confirmed (D5) |
| `accept_removal` | lets reconciliation accept a genuine city-side deletion |

Entries are only ever appended. Fixing a wrong correction means appending
one that supersedes it (`supersedes`), which keeps the history. Applied,
unmatched and superseded entries are all named in the run report. Measured
2026-11-13: 14 effective entries — eight confirmed merges (吉林676, 萬隆519,
河堤399 and the five families of 2026-11-13) and six field corrections
(`land_count`, `stage` twice, `stage_index` twice, `iso_date`).

The ledger runs **before** the tripwire report and the census gate, because
both must speak about the partition that is actually emitted (`urtpe/cli.py:388`).

---

## 6. Merge (stage 5) — `urtpe/merge.py`

~70% of records are repeat stage approvals of the same 更新單元. Identity is
found by weighted similarity, never equality — parcel coverage changes and
renumbering break exact keys.

- Candidates: records sharing (district, section), plus shared named anchors.
- Score `score(r1, r2)` in [0,1]: section .35, first parcel .2, parcel-set
  Jaccard .3, count bridge .1 (`urtpe/merge.py:40`). Named anchors score 1.0.
  Alias bridges (renumbering) score 0.95; a count bridge (`原N筆`) scores 0.8.
- Site-shrink rule (S13): when district+section+first-parcel match exactly and
  one record's `orig_count` equals the other's `land_count` — the gazette's
  own (原N筆) — the Jaccard term is dropped and the rest renormalized. A plan
  change that replaces the parcel set must not split its family.
- Threshold: link at **≥ 0.7** (`LINK_THRESHOLD`), flag the band 0.5–0.7 as
  borderline pairs for review (`FLAG_THRESHOLD`).
- Clustering: union-find over linked pairs; ledger-confirmed pairs union
  before scoring.

Each family gets:

- **Anchor** — newest 核定日期; tie-break to lowest recno (`pick_anchor`).
  The anchor is the family's 現況 record.
- **project_id** — the anchor's normalized land-core slug:
  `{district}-{section}-{first_parcel}地號等{count}筆` (`slug_for`). The count
  falls back to the family when the anchor carries none; `?` stands honestly
  when no member answers, with a flag. Families with identical slugs get
  `-2`, `-3` suffixes.

project_id is **not a stable identity** — it is the slug of the latest
approval's land core and churns (~11% of multi-record families have moved).
Within one gazette use recno; across sources use the land core
`{district}{section}{first_parcel}地號等{count}筆`.

The census gate (`Tripwire.check_partition`, `urtpe/tripwire.py:202`) then
verifies the partition is total and disjoint: every cleansed record belongs
to exactly one family, members sum to the record count, and the counts agree.
A violation exits 4 and nothing is written.

---

## 7. Link discovery (stage 6, `--links`) — `urtpe/links.py`

The largest module (4,450 lines, both portal adapters). `--links` is
recommended and advisory by design (D5); the default path runs without it and
the emission-fault check then names the absence. Discovery runs against the
merged families, before the graph document is built.

Per project, keyed on the anchor's land core:

1. **Cache check** — `data/.link_cache/<project_id>/result.json` hit means
   zero HTTP calls for that project. The cache is the durable middle layer,
   not scratch: ~727 project dirs, plus `view.html` per project,
   `portal_index.json` (bulk index of ~110 newest national entries — the
   crawl is WAF-capped), and `no_match_ledger.json` (sweep negatives, 14-day
   TTL). Cache dirs migrate across project_id churn through
   `data/project_aliases.json` (tracked configuration).
2. **Taipei platform JSON API** — `Get_updcase_list.ashx` by section +
   first parcel (both the 案名's section and the 地號 cell's own form), then
   `Get_project168_second.ashx` per case_id for the 34-field milestone map
   (`STAGE_FIELD_MAP`, `urtpe/links.py:895`), plus third.ashx (implementation)
   and fourth.ashx (rewards).
3. **National portal supplement** — the bulk index resolves the project's
   `view/N` page; the page supplies 推動歷程 milestones and the `twur_url`.
   A strict matcher accepts a page only on section + parcel + count equality
   (notation-normalized). The curated fallback `data/taipei_case_ids.json`
   and `data/twur_overrides.json` (one human-verified entry) resolve the
   rare misses.
4. **Status** — `resolved` (city case ids + milestones) / `resolved_no_city`
   / `unresolved` / `error`. Results land in `crawl_log.tsv`.

Attachment (`attach_links_to_projects`, `urtpe/links.py:3919`) writes
project-level `links` onto each Project: `twur`, `taipei` (sorted case ids),
`milestones_national`, `milestones_taipei`, plus per-case dicts
(`case_milestones`, `milestones_source`, `case_schedules`, `superseded_by`,
`view_verified_case_ids`). Date-aligned anchoring binds each case to the
recno nodes it belongs to.

All fetches use browser-like headers, exponential-backoff retries, and
gzip/deflate decoding. The single-writer lock covers the cache; the coverage
guard (`urtpe/coverage.py`) wraps discovery and aborts before emission when a
coverage flag drops or every identity re-keys — the shape of the 2026-08-24
incident, where four concurrent runs wiped 47 caches.

The overnight sweep `scripts/fetch_remaining_national_portal.py` backfills
projects still missing twur links (WAF-polite: 60–180 s sleeps, `--deadline`
default 06:30), writes into the same cache, and regenerates the viewer by
spawning `--from-js --links --viewer`.

---

## 8. Gates — ordered, before any artifact is written

Every gate evaluates before the first write, so a refused ingestion leaves
raw.tsv, clean.tsv, merged.tsv, projects.json and the viewer payload exactly
as they were. A check that runs after the damage is not a check.

| Order | Gate | Module | Refusal |
| --- | --- | --- | --- |
| pre-read | single-writer lock | `urtpe/lock.py` | exit 5 |
| after read | structural faults | `urtpe/extract.py` | exit 3 |
| after read | completeness tripwire: 編號 contiguity (minus explained exclusions), unparsed dates, pages with no table | `urtpe/tripwire.py:38` | exit 4 |
| after merge | census partition: total, disjoint, counts agree | `urtpe/tripwire.py:202` | exit 4 |
| after merge | reconciliation vs. the archived predecessor | `urtpe/reconcile.py` | exit 2 |
| on emission | emission-fault check: link/implementation data wholly absent; badge/flag disagreement | `urtpe/emission.py` | warning only |

Exit codes are a contract (`AGENTS.md`):

| Code | Meaning | State on disk |
| --- | --- | --- |
| 0 | success | written |
| 2 | unexplained reconcile changes, `--allow-reconcile-block` not given | archive/index written, emission not written |
| 3 | `TableStructureError` | nothing written |
| 4 | `TripwireFailure` (incl. census) | nothing written |
| 5 | `LockHeld` | nothing written |
| 1 | anything else | not a contract — diagnose before retrying |

Reconciliation compares the new gazette against its archived predecessor.
Per-record content diffing is unsound here — the city edits historical rows
and re-sorts the export, so a deletion, an edit and a re-dating are the same
observation. Three signals are authoritative: approvals newer than the
predecessor's newest date, net record change, and calendar. Historical
movement is reported, never treated as removal. Blocking conditions are the
ones the data does support: the list shrinking, the newest cohort withdrawn,
a total re-key. Each comparison is persisted per publication to
`urtpe-gazettes/change_sets/`.

On the `--from-js` path the partition gate runs on the payload document as it
is on disk, before the loader rebuilds families from nodes
(`urtpe/cli.py:577`), with clean.tsv's recnos as the independent reference.

---

## 9. Graph emission (stage 7) — `urtpe/graph.py`

`build_graph_document` (`urtpe/graph.py:170`) attaches the discovered links
and emits schema v2:

```json
{
  "schema_version": 2,
  "generated_at": "...", "source": "...", "published_date": "2026-10-28",
  "counts": {"projects": 675, "records": 1444},
  "projects": [ <project graph>, ... ]
}
```

Per project (`build_project_graph`, `urtpe/graph.py:56`):

- **nodes** — one per record, sorted by (ymd, recno): `recno`, `date` (ISO),
  `stage`, `stage_index`, `track`, `area`, `is_current` (the anchor),
  `case_name`, `name_raw`, `land`, `section`, `first_parcel`, `parcels`,
  `aliases`, `land_count`, `orig_count`, `named_anchor`, `area_section`,
  `implementer`, `planner`, `review_flags`, `auto_fixes`, `district`,
  `district_land`, the per-track stages, and — when present — `links`,
  `implementation`, `recovery`.
- **edges** — deduplicated `{from, to, kind}`:
  - `revision`: the chain ordered by date converging on the anchor
  - `track`: per-track chains (事業計畫, 權利變換, …)
  - `section`: A/B 區段 branches within one stage/track
- project-level `links`, `implementation`, `rewards`, `published_date`.

Flag hygiene at emission: duplicates collapse (the 2026-10-06 dataset carried
1,162 copies of one flag — one per `--links` run) and order is a stable key
(case id, then text), so a merge that reorders a family cannot reorder its
flags (`urtpe/graph.py:15`, `:36`).

Artifacts written across a full run:

| File | Writer | Content |
| --- | --- | --- |
| `data/raw.tsv` | `io.raw_to_tsv` | every row verbatim + parse_error |
| `data/clean.tsv` | `io.clean_to_tsv` | 24 columns, all derived fields |
| `data/merged.tsv` | `io.merged_to_tsv` | clean + project_id + is_current |
| `data/projects.json` | `io.write_json` | the full graph document |
| `data/review_report.txt` | `report.review_report` | tripwire, reconcile, ledger, fixes, flags, families, borderline pairs |
| `data/crawl_log.tsv` | `links.write_crawl_log` | per-project discovery status |
| `viewer/projects.data.js` | `viewer.write_projects_js` | `window.PROJECTS = {…};` — the viewer's only data input |

A run against the repo's own tree refreshes `viewer/` even without `--viewer`
(`urtpe/cli.py:706`). Note the ~24 MB diff: `projects.json` (12.8 MB),
`projects.data.js` (9.3 MB) and the three TSVs are tracked; stage deliberately.

---

## 10. The viewer (stage 8) — `viewer/index.html` + `viewer/app.js`

A static `file://` site. No dev server, no fetch — the page loads exactly
four files and `<script src="projects.data.js?v=…">` bypasses file:// CORS.

`write_projects_js` also rewrites the `?v=` cache-bust on both script tags
from the dataset itself (`urtpe/viewer.py:26`): publication date + a 4-hex
digest of date-and-counts. Identical data yields an identical version, so an
unchanged re-run does not churn index.html. `consistency_faults` then
verifies the file on disk carries this run's `published_date` and `counts`.

### Page structure

- `<header>` — title, links to the dashboard and the 關於 page, meta line
  (`675 個專案 / 1444 筆記錄 · 統計至 2026-10-28`), search box (`#filter`).
- `#filters` — four dropdown dimensions: 地區 (district), 年度 (year),
  事業種類 (track), 計畫與執行 (construction stage: 建照/開工/使照/已失效/
  自行撤回/已駁回 + tracks).
- `#list` — project list, sorted by the 現況 record's recno; each item shows
  district color chip, project_id, construction-stage chip, dead-end chip,
  record count (+ virtual orphans), implementer, base area.
- `#detail` — the selected project: timeline graph, detail table, milestone
  cards, implementation/rewards cards.

### Timeline graph (SVG)

Columns are tracks (事業概要 → 事業計畫 → 事業計畫、權利變換 → 權利變換),
section branches per column. Rows are content-addressed: approval rows 64 px,
execution-event rows 32 px (`viewer/app.js:3`, viewer-graph-layout spec).
Three sources interleave by date: real approval nodes, **virtual orphan
nodes** (platform cases no gazette record cites — `links.orphan_nodes`,
rendered with a `(未核定)` tag when undated), and execution events 建照 →
開工 → 使照 (`buildConstructionChain`). The 使照 date has three witnesses
(city, national, building-authority permit data) and the permit record
decides disagreements.

Badges per node:

- **北** — the node's anchored Taipei case, linking to its
  `r_progress_detail.aspx` page
- **國** — the national portal: bound per-label by stage+track+date
  (`bindNationalLabels`, `viewer/app.js:149`), or on nodes whose case the
  view page itself names (`view_verified_case_ids`)
- **現況** — the anchor node

### Milestone cards

`renderMilestones` (`viewer/app.js:684`) renders two `<details>` cards:
推動歷程 (國土署) from `links.milestones_national`, and 階段辦理過程 (台北市)
from `links.milestones_taipei` — or a placeholder with a portal link when the
city data is absent but `twur` exists. 執行階段 (implementation) and 獎勵資料
(rewards) cards render from the third/fourth ashx payload.

### Detail table

Essential columns first (recno, date, stage, track, is_current, case_name,
land, section, implementer, planner, **review_flags**, **auto_fixes**,
**recovery**), full columns on expand (parcels, aliases, counts, anchor,
area_section). Recovered rows render provenance badges: 復原, 部分清單,
修正…, A/B併案, 日期±1, and the memo disagreement badge (`viewer/app.js:1495`).

### Policy dashboard — `viewer/dashboard.html` + `viewer/dashboard.js`

A second page over the same payload. It loads `projects.data.js` with the
`?v=` that `index.html` names, flattens each project to one row in the
browser (stage, idle time, the two review intervals, households, public
land) and computes every figure at render time — nothing on the page is
typed by hand, so the figures move with the payload (`policy-dashboard`
spec). Four sections: stalled cases, review workload and speed, relocation
demand, public land. Its state — district, language, review view — lives in
the URL hash, so a view can be linked.

The review chart has two views, switched in its own card:

- **中位數** (default) — the median of both intervals by year of first
  approval: application → first approval, and application → the approval
  before the building permit.
- **完整** (`#review=full`) — the spread behind those medians. The pre-permit
  interval is a fan: a light band from shortest to longest, a darker band
  from the 25th to the 75th percentile, the median as a line, in straight
  segments. The first-approval interval is one box per year: a thin line, a
  box, a dot at the median. One tooltip per year lists the five values and
  the project count of both intervals. A percentile is read by linear
  interpolation between the two nearest ranks, to one decimal.

The page's own 定義與限制 block states each rule to the reader. Unlike the
viewer's smoke script, the dashboard's render path is in pytest:
`tests/test_dashboard_rules.py` renders the real page through
`node scripts/dashboard_smoke.js` (a stub DOM) and asserts on what it shows.

### Publishing

The site is GitHub Pages at `https://happypig.github.io/urTPE` (canonical
address in `viewer/deploy.json`, case-sensitive). `viewer/` is published from
`main`; a commit touching it leaves the live site stale until pushed —
`python scripts/check_deploy.py` reports fresh / stale / missing per artifact
against the served bytes.

Render-path regression check (manual, not in pytest):
`node scripts/viewer_smoke.js` runs the real `init() → renderList() →
renderDetail()` path against the payload in a stub DOM.

---

## 11. Operating the pipeline

Full ingest of a new gazette:

1. Run `python scripts/poll_gazette.py`. It archives on `new_gazette`.
2. Ingest: `python -m urtpe.cli "D:\project\urtpe-gazettes\核定案件-YYYY-MM-DD.pdf" -o data --viewer viewer --links`
3. Read the run output: tripwire PASS, reconcile report, ledger report,
   exclusion count. Any `[CENSUS]`/`[EMISSION]` line names a real defect.
4. Exit 0 commits the dataset (mind the ~23 MB diff). Exit 2/3/4/5 is a
   refusal — diagnose, never bypass with a flag.
5. Push `main` so Pages serves the new `projects.data.js`; verify with
   `python scripts/check_deploy.py`.

Rules that outlast any single run:

- One run per output tree. The lock (`data/.pipeline.lock`) is stale after 6 h
  or a dead PID; check the PID before deleting it.
- Never key anything durable on 編號; it shifts on every publication.
- The ledger, not a dated script, is where manual corrections go.
- `data/.link_cache/` is durable state — five backup dirs from past incidents
  exist because it was once lost. Do not delete it casually.
- Tests: `python -m pytest` (1,231 collected; one deliberate skip at
  `tests/test_idempotent_flags.py:117`).
