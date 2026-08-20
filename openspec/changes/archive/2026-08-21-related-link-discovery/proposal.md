## Why

An analyst browsing a project's history in the viewer has no way to jump to the
authoritative case record held by the Taipei City government (都市更新審議服務平台,
gis.uro.taipei) or the national portal (內政部國土管理署都市更新入口網,
twur.nlma.gov.tw). Today the pipeline emits only what is in the PDF list; the
official cross-links — which carry live 辦理進度, 階段辦理過程, 會議日期, 獎勵資料,
公告公文, and 公開計畫書 — are not surfaced at all, so users must re-search both
sites by hand. The two sites cross-reference each case (the national portal
embeds a 縣市政府案件連結 pointing at gis.uro.taipei case_ids), and both are
crawlable, so the links can be discovered automatically rather than curated.

**Moreover**, the official process timelines from both portals — the national
portal's 推動歷程 tab (事業計畫/權利變換 申請/核定 dates) and the Taipei platform's
階段辦理過程 tab (full stage-by-stage timeline: 公聽會, 公展, 幹事會, 聽證, 審議會,
核定, 建照) — contain authoritative milestone data that should be **merged into
the project history graph** as additional nodes/edges, not just linked out. This
enriches the graph with the official procedural timeline that the PDF list
cannot provide.

## What Changes

- Add a **link-discovery adapter** (`urtpe/links.py`) that crawls the national
  portal for each project's land-identity core, resolving the twur.nlma.gov.tw
  `view/<id>` page and the 縣市政府案件連結 → gis.uro.taipei `case_id`(s) it embeds.
- **Scrape the 推動歷程 tab** from the national portal view page (pre-loaded in
  hidden `.data_table_box` panels) extracting the 事業計畫/權利變換 申請/核定 dates.
- **Scrape the 階段辦理過程 tab** from the Taipei platform case page (pre-loaded
  in hidden `#data2` panel) extracting the full stage-by-stage milestone timeline.
- **Merge both timelines into the history graph** as additional nodes (milestones)
  and edges (stage progressions), cross-referenced with the existing approval
  nodes by date/stage — so the graph shows both the PDF approval chain and the
  official procedural timeline.
- Emit a `links` map per project into `projects.json` and `projects.data.js`,
  keyed by the same land-identity core the merge step already anchors on; link
  targets attach per node where the 縣市政府案件連結 is per-approval-stage.
- Extend the viewer detail pane with a 相關連結 section under the graph/table,
  rendering both links (twur + gis.uro.taipei) as clickable outbound anchors.
- Add `links.tsv`/crawl log output so misses and multi-case mappings are visible
  in the review report for manual verification.
- **Gated on crawl POC**: coverage rate and join accuracy are provisional until a
  crawl over a sample (e.g. the 玉泉段二小段40地號等29筆 and 臨沂段一小段507地號等3筆
  cases, which together expose the one-case→many-case_id and initial-vs-latest
  name mismatches) is validated against known answers.

## Capabilities

### New Capabilities
- `official-link-discovery`: crawls the national portal and Taipei platform for
  each project, joins by land-identity core, scrapes 推動歷程 and 階段辦理過程
  timelines, merges them into the history graph, and exposes per-project/per-node
  official 相關連結 in the graph data and viewer.
- `viewer-related-links`: renders the discovered links in the viewer detail pane
  as clickable 相關連結 for both the national portal and the city platform.

### Modified Capabilities
- `history-graph`: node/project JSON gains a `links` field carrying discovered
  official links; **nodes also gain a `milestones` field** for the merged
  procedural timeline; the emitted document and data file must include both
  without breaking the existing schema consumers.

## Impact

- New module `urtpe/links.py` (web crawl adapter) + tests; a new CLI flag (e.g.
  `--links`) to run discovery against `data/` output.
- `urtpe/graph.py` node/project shape gains `links` and `milestones`;
  `urtpe/io.py` gains a `links.tsv` writer; `viewer/app.js` + `viewer/app.css`
  render 相關連結.
- `projects.json` / `projects.data.js` schemas evolve (additive); the existing
  e2e and graph tests must be updated for the new fields.
- New dependency: an HTTP client + HTML parser (stdlib `urllib` + `html.parser`
  to stay dependency-light). Crawl cadence is one request per project plus one
  per resolved view page (national) plus one per Taipei case_id — needs polite
  throttling and caching.