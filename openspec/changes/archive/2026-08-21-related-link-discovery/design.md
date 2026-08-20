## Context

Actors: the analyst browsing the viewer wants to jump from a project's history
graph to the authoritative live record. Two external systems hold it — the
national portal (twur.nlma.gov.tw, server-rendered, searchable, embeds the city
links) and the Taipei City 都市更新審議服務平台 (gis.uro.taipei, JS-rendered).
System boundary: the pipeline today is PDF → parse → cleanse → merge →
projects.json → viewer, all offline. This change adds an outbound crawl adapter
that enriches merged projects with official links before graph emission.

Verified crawl facts (from probing the live portal):
- Search endpoint: `https://twur.nlma.gov.tw/zh/urban/rebuild/0?city_id=2&title=<core>`
  returns server-rendered HTML; the `title` field is the 案名/實施者/區位 keyword.
- Each result row links to `/zh/urban/rebuild/view/<id>` (the national link).
- Each view page embeds a 縣市政府案件連結 block with `gis.uro.taipei/r_progress_detail.aspx?case_id=<id>` link(s) — one view page can carry multiple case_ids (e.g. view/292 → 10110211 + 10810271).
- Portal case names are the initial 擬訂 approval; our project_id anchors on the latest 變更 approval — so the join key is the land-identity core (district + section + first parcel + count), which project_id already encodes.

## Goals / Non-Goals

**Goals:**
- Discover, for as many of the 709 projects as the portals cover, the national
  portal view URL and the city-platform case_id(s), without manual curation.
- Attach links per node where the city link is per approval stage; attach the
  national link at project level.
- Emit links into projects.json / projects.data.js and render 相關連結 in the viewer.
- Make coverage and mismatches visible in the review report.

**Non-Goals:**
- No crawling of gis.uro.taipei itself (JS-rendered); the city links come from
  the national portal's embedded 縣市政府案件連結 — one hop covers both.
- No near-real-time updates; discovery is a batch step re-run on regeneration.
- No attempt to scrape 辦理進度/獎勵/會議日期 content into the dataset — links
  point out to the live authoritative pages.

## Decisions

### D1: Join key = land-identity core, via one search query per project
Search the portal with the project's land-identity core (from project_id) and
`city_id=2`, take the unique result's view id. Alternative considered: crawling
all 68 list pages and matching locally — heavier (68 pages) and misses cases
whose core appears only in a wrapped title; per-project search is ~709
throttled requests and directly leverages the portal's own matcher. Query
fragments that return 0 or >1 results are flagged for review rather than guessed.

### D2: New adapter `urtpe/links.py`, pure logic kept separate
`links.py` is an I/O adapter (web) like `extract.py`/`io.py`: it owns URL
construction, HTML parsing, and response handling. Parsing via stdlib
`html.parser` keeps the pipeline dependency-light (no lxml/requests needed;
`urllib` suffices). The derived join/attach logic (mapping case_ids to nodes by
stage/track) stays in the domain layer so it is unit-testable without network.

### D3: Link shape in graph data
Per project: `links: { twur: "<view url>", taipei: ["<case_id>", ...] }`.
Per node: `links: { taipei: ["<case_id>"] }` for the approval-stage case links.
Empty when unresolved. This is additive — existing consumers (counts, nodes,
edges) are untouched; the viewer's detail renderer reads the new field and
renders 相關連結 only when present.

### D4: Throttling + cache for politeness and reproducibility
Sequential requests with a small delay; cache raw view pages (and search
results) under a crawl dir so re-runs don't re-hit the portal unless `--fresh`.
A crawl log records per-project status (resolved / unresolved / multi-case).

### D5: Coverage gate as part of the change
The crawl over the full set is the acceptance run; the review report lists
unresolved projects and multi-case mappings. The matching rule (unique search
hit, core-based) is provisional until the sample cases (玉泉段二小段40地號等29筆,
臨沂段一小段507地號等3筆) validate it, mirroring the pipeline's existing POC-first
convention.

## Risks / Trade-offs

- **Portal schema drift / blocking** → The adapter isolates parsing in one
  module; if twur.nlma.gov.tw changes layout or rate-limits, only links.py
  changes and discovery can be paused; cached pages keep old data usable.
- **Coverage shortfall** (675 portal Taipei cases vs 709 projects) → Unresolved
  projects are explicitly listed in the review report, not silently dropped.
- **False-positive joins** (same core, different unit, e.g. renumbered parcels)
  → Unique-hit rule + manual review of flagged multi/zero matches; named-anchor
  units (原東星大樓基地) have no stable core and will be unresolved by design.
- **Multi-case views** → Attach all case_ids; per-node assignment is best-effort
  by stage/track keyword (事業計畫/權利變換/概要) with the rest kept at project level.
- **git-blame/regeneration cost** → Crawl adds network time to the pipeline;
  the cache dir makes it a one-time cost per portal refresh.