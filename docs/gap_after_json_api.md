# Gap Analysis: OpenSpec Artifacts vs Implementation

**Date:** 2026-08-23 (after Taipei JSON API integration, 697/709 resolution)

## Spec State vs Implementation State

```
SPEC STATE                          IMPLEMENTATION STATE
─────────────────────────────       ─────────────────────────────
official-link-discovery             links.py (Taipei-first API flow)
  "national portal is PRIMARY"  ──▶   Taipei ashx APIs are PRIMARY;
  extract case_ids from view          portal demoted to supplementary.
  page 縣市政府案件連結 block          No HTML parsing — pure JSON.
        ❌ OPPOSITE DIRECTION

history-graph                       projects.json
  nodes/links/published_date   ──▶   ✅ matches
        ⚠️ but spec missing: milestones_taipei/national in links,
           per-node links, district/district_land node fields

viewer-related-links                app.js renderMilestones()
  相關連結 section only        ──▶   ✅ + timeline cards, badges,
        ⚠️ milestone deltas exist only in UN-ARCHIVED change

portal-bulk-index                   build_portal_index()
  (delta spec in un-archived     ──▶   implemented, then DEMOTED to
   change; not in main specs)          supplementary by Taipei-first
        ❌ NEVER SYNCED + ALREADY OUTDATED
```

## Detailed Gaps

### 1. official-link-discovery (main spec) — MAJOR DRIFT

The main spec (`openspec/specs/official-link-discovery/spec.md`, 4
requirements) describes a national-portal-first discovery flow:

- Resolve view page via portal search with land-identity core
- Extract city case_ids from the view page's 縣市政府案件連結 block

The implementation now does the **opposite**:

- **Primary**: Taipei platform JSON APIs — `Get_updcase_list.ashx` search
  (section + parcel → numeric case_ids) and `Get_project168_second.ashx`
  (case_id → full 階段辦理過程 milestone timeline)
- **Supplementary**: national portal only for twur view URL and 推動歷程

The spec does not cover:

- The ashx JSON API endpoints at all
- `milestones_national` / `milestones_taipei` fields emitted in `links`
- gzip response handling
- The details-URL case_id extraction rule (numeric id lives in the
  `details` URL query string; the `case_id` field holds internal codes
  like `R091306-02`)
- Join is now section+parcel via API params, not land-core string equality

### 2. history-graph — PARTIAL DRIFT

Covered correctly: full CleanRecord node fields, `published_date`, `links`
object on projects.

Missing from spec:

- `milestones_national` / `milestones_taipei` dicts inside the project
  `links` object
- Per-node `links` (per-stage city case_ids)
- Node fields `district` / `district_land` (added for link-discovery core
  building)

### 3. viewer-related-links — DRIFT

Main spec covers only the 相關連結 outbound-links section. The implemented
viewer also renders expandable milestone timeline cards (推動歷程 /
階段辦理過程), per-node source badges (國/北), and progressive loading
placeholders. These behaviors exist as delta specs in the un-archived
`viewer-milestone-display` change only.

### 4. portal-bulk-index — NEVER SYNCED + OUTDATED

Exists only as a delta spec inside the un-archived
`portal-crawl-bulk-index-resume` change. It was fully implemented (bulk list
crawl → local index → offline join), then demoted to supplementary when the
Taipei-first flow replaced the primary discovery path.

### 5. Unspec'd additions

- CLI flags: `--from-js`, `--fresh`, `--playwright`, `--add-mapping-file`
- `urtpe/taipei_playwright.py` (browser-automation fallback tool)
- `docs/final_results_json_api.md` (API documentation outside OpenSpec)

## Change Lifecycle Gaps

| Change | Tasks | Archived? | Consequence |
|--------|-------|-----------|-------------|
| `portal-crawl-bulk-index-resume` | 33/33 ✅ | ❌ No | Its spec syncs never happened; its proposal already outdated |
| `viewer-milestone-display` | 0/25 checked (work actually done & verified) | ❌ No | 3 spec syncs missing |

## Root Causes of Drift

1. **Completed changes never archived** — archiving is the mechanism that
   syncs deltas into main specs; a complete change sitting in `changes/`
   means the main specs are stale.
2. **Architecture pivot done ad-hoc** — the Taipei-first rewrite was a major
   capability addition made during debugging without going through
   `/opsx-propose`.
3. **tasks.md not maintained during apply sessions** — checkboxes reflect
   intent at planning time, not verified completion.
4. **Schema grew silently** — new emitted fields without corresponding spec
   scenarios.

## Recommended Re-sync Sequence

### ① viewer-milestone-display

- Tick all 25 tasks retroactively (with honest notes on what verification
  was done: browser checks via wmux, syntax check, test suite)
- Archive → syncs `viewer-milestone-timeline` (new capability) +
  `viewer-related-links` (modified)

### ② portal-crawl-bulk-index-resume

- Amend proposal/design to record final state (bulk index is now
  supplementary after the Taipei pivot)
- Archive → syncs `portal-bulk-index` (new) +
  `official-link-discovery` (partial mod)

### ③ NEW change: `taipei-case-discovery`

- New capability covering the ashx search/milestone APIs, gzip handling,
  details-URL id extraction rule, checkpoint/resume caching
- Modified: `official-link-discovery` reordered Taipei-first with national
  portal supplementary
- Most tasks already done → mark retroactively, archive quickly

### ④ Optional: history-graph delta

- Add `milestones_national` / `milestones_taipei` and per-node `links` /
  district fields to the graph schema requirement

After all four: run `openspec validate --specs` to confirm main specs match
implementation.

## Practices to Keep Specs Synced Going Forward

1. **Archive at 100% immediately** — archiving *is* the sync mechanism; a
   "complete" change sitting in `changes/` means the main specs are stale.
2. **Pivot rule** — when debugging reveals an architectural shift (like
   discovering the ashx APIs), pause → `/opsx-explore` → `/opsx-propose` a
   delta rather than implementing through it.
3. **Tick checkboxes at task completion**, not session end.
4. **Periodic drift check** — run `openspec validate --specs` plus a small
   script diffing emitted schema keys (`projects.json`) against spec
   scenario fields.

## Related Documents

- `docs/final_results_json_api.md` — API discovery results and
  implementation details
- `openspec/changes/viewer-milestone-display/` — un-archived change
- `openspec/changes/portal-crawl-bulk-index-resume/` — un-archived change
