## Why

The analyst running `--links` needs Taipei case_ids and milestone timelines for
every project. The previously specified path — resolve a national-portal view
page, then scrape its 縣市政府案件連結 block for city links — collapses in
practice: twur.nlma.gov.tw resets crawler connections (WAF), so only 3/709
projects ever resolved via hand-curated fallback mappings. Meanwhile the
Taipei platform itself (gis.uro.taipei) exposes simple `ashx` POST endpoints —
used by its own search form and detail page JavaScript — that return clean JSON
with no session, ViewState, or browser automation required. Adopting these
endpoints raised resolution from **3/709 (0.4%) to 697/709 (98.3%)** with full
29-field milestone timelines, and is already implemented and in production;
this change captures that shipped reality in specs.

## What Changes

- **New Taipei-first discovery flow** in `urtpe/links.py`:
  - Search cases by 地段小段 + 母號 + 子號 via `POST ashx/Get_updcase_list.ashx`
    → returns candidate cases with numeric detail ids.
  - Fetch per-case 階段辦理過程 milestones via `POST ashx/Get_project168_second.ashx`
    → 30-field date timeline mapped through `STAGE_FIELD_MAP`.
  - National portal (bulk index / fallback view_id) demoted to **supplementary**
    source: twur view URL + 推動歷程 only; failures there never block Taipei resolution.
- **Robust HTTP layer**: gzip response handling (magic-byte detection) shared by
  all fetches; retry with exponential backoff on connection errors.
- **Case-id extraction rule**: numeric detail ids parsed from each entry's
  `details` URL query string — the entry's own `case_id` field holds internal
  codes (e.g. `R091306-02`) and MUST NOT be used for detail URLs.
- **Per-project checkpoint cache**: results cached under
  `data/.link_cache/<project>/result.json`; runs are resumable across
  interruptions; stale caches cleared when discovery logic changes.
- **Status derivation fixed**: final status computed from actually obtained
  results (`resolved` = case_ids + milestones; `resolved_no_city` = case_ids
  only; `unresolved` otherwise) instead of an unreachable branch.
- CLI: existing `--links`, `--fresh`, `--playwright` (kept as manual fallback
  tool), plus `--from-js` round-trip fix preserving ISO dates.

## Capabilities

### New Capabilities

- `taipei-case-discovery`: discovers city-platform case_ids and milestone
  timelines directly from the Taipei platform's internal JSON APIs by land
  parcel search, independent of the national portal.

### Modified Capabilities

- `official-link-discovery`: discovery reordered **Taipei-first** — city
  case_ids and milestones come from the Taipei JSON APIs; the national portal
  (bulk index join or fallback view_id) is supplementary for the twur URL and
  推動歷程 only. City links no longer scraped from portal view pages.

## Impact

- `urtpe/links.py`: new `_post_taipei_api`, `search_taipei_cases_api`,
  `fetch_taipei_milestones_api`, `STAGE_FIELD_MAP`; `discover_project_links`
  rewritten Taipei-first; `fetch_url` gains gzip handling.
- `urtpe/cli.py`: `--from-js` ISO-date preservation fix (dates were wiped on
  every round trip); `--playwright` flag retained as manual fallback.
- `viewer/projects.data.js` schema: unchanged shape, but `links.taipei` now
  populated for ~697 projects and `milestones_taipei` carries real timelines.
- Emitted data verified: 697/709 resolved (12 unresolved = named-anchor units
  without stable parcels, by design); all 1,419 node dates preserved.
- Docs: `docs/final_results_json_api.md` records endpoint details.
