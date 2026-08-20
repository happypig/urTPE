## Context

Current viewer state:
- `viewer/index.html` has viewport meta but no responsive CSS
- `#list` fixed at 340px, `.cols` flex row, `main` height `calc(100vh - 58px)`
- `app.js` `renderDetail` table shows only 4 columns + 現況 badge
- Header meta line uses `generated_at` timestamp from pipeline
- `extract.py` `is_furniture` discards 統計至 line as page furniture
- Pipeline meta in `cli.py` carries `generated_at` but no `published_date`

Pipeline flow: PDF → positional parse (`extract.py`) → raw.tsv → cleanse → clean.tsv → merge (`merge.py`) → merged.tsv → graph (`graph.py`) → projects.json → viewer (`viewer.py`) → projects.data.js.

## Goals / Non-Goals

**Goals:**
- Responsive layout: stack list above detail on <768px, side-by-side on desktop with flexible list width
- Detail table shows all CleanRecord fields (case_name, land, parcels, aliases, land_count, orig_count, named_anchor, area_section, implementer, planner, review_flags, auto_fixes) after 現況, default analyst essentials + "展開全部" toggle
- Header date = "統計至 115年8月11日" from PDF page 1, threaded through pipeline meta
- All changes additive — existing graph/tests still work with new fields

**Non-Goals:**
- No drawer/tab/hamburger patterns for mobile (stack only)
- No new PDF parsing logic beyond capturing 統計至 line
- No changes to similarity merge, cleansing, or project_id logic
- Portal link discovery and timeline merging remain in `related-link-discovery` change

## Decisions

### D1: Breakpoint at 768px, CSS Grid for layout
Use `@media (max-width: 768px)` to switch `.cols` from `flex-row` to `grid` with `grid-template-rows: auto 1fr` (list above detail). Desktop: `grid-template-columns: 30% 70%` (flexible, not fixed 340px). Alternative considered: flex with `flex-wrap` — grid gives cleaner vertical stacking without min-width hacks.

### D2: Table columns — two tiers via data attributes
Default columns (analyst essentials): 編號, 核定日期, 階段, 事業種類, 現況, 案名, 地號, 區段, 實施者, 更新規劃單位, review_flags/auto_fixes (11 columns). Full columns: add parcels, aliases, land_count, orig_count, named_anchor, area_section (17 total). Each `<th>`/`<td>` gets `data-tier="essential|full"`; "展開全部" toggles CSS `display: none` on full-tier cells. No JS rebuild of table — pure CSS toggle.

### D3: Horizontal scroll on table container only
Wrap `<table>` in `<div class="table-wrap" style="overflow-x: auto">` so mobile scrolls table only, not page. Desktop: no scroll needed at full width.

### D4: Published date extraction in `extract.py`
Modify `is_furniture` to recognize 統計至 pattern on page 1 (y≈60) and emit as `published_date` in the extraction metadata dict (not a row). The line format: "統計至115年8月11日" → parse to ROC year 115 = 2026, store as "統計至 115年8月11日" for display. Alternative: parse to ISO — display format is what the PDF shows, keep as-is for fidelity.

### D5: Pipeline meta threading
`cli.py` reads `published_date` from extraction metadata, adds to `meta` dict passed to `graph.py` → `build_project_graph` → each project gets `published_date`. `viewer.py` writes it into `projects.data.js`. Viewer `app.js` reads `window.PROJECTS.meta.published_date` for header.

### D6: Node schema extension in `graph.py`
`build_project_graph` already receives `CleanRecord` objects (full fields). Currently emits minimal node dict. Change to include all fields (case_name, land, parcels, aliases, land_count, orig_count, named_anchor, area_section, implementer, planner, review_flags, auto_fixes) in the node output. Project output gains `published_date` from meta. This is additive — no existing field removed.

## Risks / Trade-offs

- **Many table columns on mobile** → Horizontal scroll is the fallback; essential columns kept visible; "展開全部" opt-in keeps default readable.
- **Published date parsing** → Only on page 1; if PDF layout shifts, extraction may miss it. Mitigation: fallback to `generated_at` with warning in extraction report.
- **Node size growth** → ~709 projects × ~1-2 records avg × ~17 fields = larger projects.json. Acceptable (<5MB); no streaming needed.
- **CSS grid browser support** → All target browsers support grid; no polyfill needed.
- **Viewer cache** — projects.data.js is a JS file; browser caching means users may need hard-refresh. Mitigation: version query param `?v=...` in viewer.html script src (optional follow-up).

## Migration Plan

1. Extract 統計至 date in `extract.py` + add to extraction metadata
2. Thread `published_date` through `cli.py` → `graph.py` → `viewer.py`
3. Extend node schema in `graph.py` with full CleanRecord fields
4. Update `viewer/app.js` `renderDetail` for tiered columns + toggle
5. Update `viewer/app.css` for responsive grid layout + table-wrap + toggle styles
6. Run full pipeline regeneration; verify projects.json schema + viewer renders
7. Update tests for new fields/layout