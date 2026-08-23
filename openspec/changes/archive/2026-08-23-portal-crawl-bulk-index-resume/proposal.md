## Why

The analyst running `--links` needs the official portal links for all 709 projects, but the current crawler performs 709 sequential per-project searches (plus view and Taipei case fetches, ~1,400–2,700 requests total at a fixed 1s delay) and **dies on the first connection reset** — a live run against twur.nlma.gov.tw crashed with `ConnectionResetError` after minutes of crawling, leaving no usable partial output. The crawl is both too fragile and slower than necessary: the portal's own list pages expose all 675 Taipei cases across 68 pages, so 709 searches are redundant when one bulk pass plus a local join (against the land-identity cores already extracted from the PDF) achieves the same resolution.

## What Changes

- **Bulk portal index**: crawl the portal's list pages once (`city_id=2`, ~68 pages) and build a local index `{normalized land_core → view_id}` saved as `data/portal_index.json`; reuse the cached index on re-runs unless `--fresh`.
- **Local join instead of per-project search**: resolve each project's land-identity core against the cached index offline — zero search HTTP requests in the steady state.
- **Retry with exponential backoff**: every fetch retries up to 3 times (2s/4s/8s) on connection errors before marking the item unresolved; the crawl never dies on a single reset.
- **Checkpoint/resume**: per-project results are cached; an interrupted run resumes from the first uncached project instead of restarting. On repeated failure the run degrades gracefully (marks unresolved, continues) and exits with a crawl log.
- **Browser-like request headers**: send realistic `User-Agent`, `Accept`, and `Accept-Language` headers to reduce WAF-triggered resets.
- **CLI unchanged**: `--links` keeps its current interface; `--fresh` (new flag) forces re-fetch of the index and cached pages.

## Capabilities

### New Capabilities

- `portal-bulk-index`: build and cache a local index of all national-portal Taipei rebuild cases (view_id + normalized land-identity core per case) from a single bulk crawl of the portal list pages.

### Modified Capabilities

- `official-link-discovery`: resolution now joins projects to the portal via the cached bulk index (instead of one live search per project); fetches add retry with exponential backoff; discovery is resumable from cache and degrades gracefully on repeated network failure instead of aborting the run. The unique-hit rule, per-node attribution, crawl log, and emitted `links` shape are unchanged.

## Impact

- `urtpe/links.py`: list-page parsing (new `ListPageParser`), index build/save/load, join logic replacing `search_national_portal` per project, retry/backoff in `fetch_url`, resume-aware `LinksDiscovery.run`.
- `urtpe/cli.py`: add `--fresh` flag (passed through to discovery).
- New artifacts: `data/portal_index.json`, `data/.link_cache/` (existing, now authoritative for resume), `data/crawl_log.tsv` (unchanged shape).
- Tests: new fixtures for list pages and retry behavior; existing link tests updated where `search_national_portal` is replaced by the index join (the POC sample cases 玉泉段二小段40地號等29筆 → view/771 and 臨沂段一小段507地號等3筆 → view/292 remain the acceptance anchors).
- No changes to viewer, graph, or merge behavior; `projects.json` schema is unchanged.

## Post-completion Addendum (2026-08-23)

All deliverables shipped as specified: bulk index build/join, retry with
backoff, checkpoint/resume, browser-like headers, `--fresh` flag.

Subsequently, discovery of the Taipei platform's internal JSON APIs
(`Get_updcase_list.ashx` parcel search, `Get_project168_second.ashx`
milestones) made **city case_id resolution independent of the national
portal entirely** — raising resolution from 3/709 to 697/709. As a result
the bulk portal index is now a **supplementary** source (twur view URL +
推動歷程 only), no longer the primary resolution path described above.
That pivot is out of this change's scope; it is tracked by a follow-up
change (`taipei-case-discovery`) which will re-modify
`official-link-discovery` accordingly. See `docs/final_results_json_api.md`.
