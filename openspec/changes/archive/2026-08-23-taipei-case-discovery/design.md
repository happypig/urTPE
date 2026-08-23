## Context

Shipped state (2026-08-23): `urtpe/links.py` already implements the
Taipei-first flow end to end and a full run resolved **697/709 projects
(98.3%)** with 29-field milestone timelines. This change captures that reality
in specs — the code exists; what follows is the reasoning behind each decision,
for maintenance.

Key facts about the Taipei platform discovered by inspecting its own JS:

- `R_progress.aspx`'s search form builds
  `qitem=qland&sectstr=<地段>&monobuf=<母號>&sunobuf=<子號>` and POSTs it to
  `ashx/Get_updcase_list.ashx`.
- `r_progress_detail.aspx?case_id=X` renders empty `<div id="...">` placeholders
  populated client-side by `ashx/get_project168_top.ashx` (basic info) and
  `ashx/Get_project168_second.ashx` (full milestone timeline) — so static HTML
  scraping of the detail page can never see milestones.
- Responses may be gzip-compressed because our request headers advertise
  `Accept-Encoding: gzip`.

## Goals / Non-Goals

**Goals:**
- Spec the ashx search + milestone APIs as the primary discovery path
- Re-modify `official-link-discovery`: national portal demoted to supplementary
- Record hard-won gotchas: details-URL id extraction, gzip, status derivation

**Non-Goals:**
- No new implementation work — this change documents shipped behavior
- No Playwright removal (`urtpe/taipei_playwright.py` stays as manual fallback)
- No changes to viewer, graph schema, or merge logic

## Decisions

### D1: Taipei-first ordering

City resolution starts with the Taipei parcel search; national portal lookup
runs afterwards and only decorates the result with twur URL + 推動歷程.
Alternative (keeping portal-first with Taipei as fallback) was rejected:
the portal's WAF resets crawler connections unpredictably, making any
portal-dependent path inherently unreliable (3/709 evidence).

### D2: Numeric ids from the details URL

Search results carry an internal `case_id` (e.g. `R091306-02`) that does NOT
match the numeric id needed by `r_progress_detail.aspx` and the milestone API.
The numeric id is embedded in the `details` URL. Parsing the URL is the only
reliable extraction.

### D3: Filter to r_progress_detail cases only

The parcel search also returns 劃定單元 and 更新地區 entries whose detail pages
have no milestone timeline. Filtering on `r_progress_detail.aspx` in the
details URL keeps only cases the milestone API can serve.

### D4: Fixed field map for milestones

`Get_project168_second.ashx` returns one JSON row per 計畫/權變 track with ~30
camelCase date fields. A static `STAGE_FIELD_MAP` (field → Chinese label)
keeps translation declarative and testable; empty values are skipped, ISO
datetimes normalised to dates.

## Risks / Trade-offs

- [Ashx endpoints are undocumented government internals] → They back the
  official public search form, so they are stable-facing; failure modes are
  handled (retry, degraded status), and the national-portal path remains as
  secondary decoration. Docs captured in `docs/final_results_json_api.md`.
- [12 unresolved named-anchor units] → By design: no stable parcel basis means
  no parcel-search key. Same limitation as merge's land-identity fallback.
- [gzip decoding regression] → Magic-byte check is localised in fetch helpers;
  unit-testable without network.

## Migration Plan

None required — behavior is already live and verified. This change formalises
it: validate specs → archive → sync into main specs.

## Open Questions

- None blocking. Possible future work: persist `Get_project168_First/Third…`
  data (contacts, execution stats) if the viewer ever needs them.
