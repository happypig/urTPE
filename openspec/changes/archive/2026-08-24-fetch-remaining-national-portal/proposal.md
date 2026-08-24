## Why

The national portal (twur.nlma.gov.tw) holds the 推動歷程 timeline for every urban-renewal case, including the critical **使用核發日期** (occupancy permit) that only appears on the portal. Our current data has **591 of 709 projects (83%) missing** this link and its milestones. The bulk portal index crawl only captured ~110 recent entries (2023-05 onward) before WAF terminated it; the remaining 591 projects are older, never indexed, and will never be without targeted per-project search. The fix is a time-bounded, sequential fetch script that runs until 6:30 AM, prioritizing recent projects first, with polite 3-5 min intervals, logging failures and continuing, auto-regenerating the viewer at completion — all as an isolated script that doesn't touch the existing discovery pipeline.

## What Changes

- **New runnable script** `scripts/fetch_remaining_national_portal.py` — time-bounded fetch of missing portal data
- **Isolated from core pipeline** — reads `viewer/projects.data.js`, writes only to `data/.link_cache/<project>/result.json` and `view.html`; never modifies `urtpe/links.py`, `urtpe/cli.py`, or existing discovery logic
- **Time-bounded runner** — runs until 06:30 local time, then exits gracefully and regenerates viewer data via `python -m urtpe.cli --from-js --links`
- **Sequential, polite** — 3-5 min random interval between projects; 3 retries with exponential backoff on WAF/connection errors
- **Prioritization** — recent projects first (by anchor 現況 date descending) to maximize 使用核發日期 hits
- **Failure resilience** — logs failures to stderr + JSON log, continues immediately; no project blocks the queue
- **Auto-regenerate** — on completion (or 6:30 AM timeout), runs `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer viewer --links` to rebuild `viewer/projects.data.js`
- **Zero schema changes** — viewer data format unchanged; only `links.twur` and `links.milestones_national` populated

## Capabilities

### New Capabilities

- `fetch-remaining-portal`: time-bounded, sequential fetcher for missing national portal data with polite intervals, failure logging, and auto-regeneration

### Modified Capabilities

- None — no existing capability's requirements change; this is an operational tooling addition

## Impact

- **Code**: new file `scripts/fetch_remaining_national_portal.py` only
- **Data**: `data/.link_cache/<project>/result.json` and `view.html` for up to ~40-60 projects (4-hour window × 3-5 min intervals)
- **Viewer**: `viewer/projects.data.js` regenerated with new `twur` URLs and `milestones_national`
- **Zero risk** to existing pipeline (`urtpe/links.py`, `urtpe/cli.py`, `build_portal_index`, `discover_project_links` untouched)