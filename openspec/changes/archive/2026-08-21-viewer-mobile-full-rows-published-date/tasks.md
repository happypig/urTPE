> POC: Validate PDF 統計至 date extraction on page 1 and table tiered-column rendering on mobile before full implementation.

## 1. Test-First / POC

- [x] 1.1 Write test for `extract.py` published date extraction: feed page 1 text with "統計至115年8月11日" at y≈60, assert metadata includes `published_date: "統計至 115年8月11日"`
- [x] 1.2 Write test for `graph.py` node schema: assert each emitted node contains all CleanRecord fields (case_name, land, parcels, aliases, land_count, orig_count, named_anchor, area_section, implementer, planner, review_flags, auto_fixes) and project has `published_date`
- [x] 1.3 Write test for viewer responsive layout: render app.js at 375px and 1200px, assert list stacks above detail on mobile, side-by-side on desktop, table horizontal scroll works
- [x] 1.4 Write test for detail table tiered columns: assert default render shows 11 essential columns, "展開全部" toggle reveals 6 additional columns, no JS rebuild needed
- [x] 1.5 Validate POC: run PDF extraction on actual source PDF page 1, confirm 統計至 date captured correctly

## 2. Pipeline Adapters (I/O)

- [x] 2.1 Update `urtpe/extract.py`: modify `is_furniture` to detect 統計至 pattern on page 1 (y≈60), emit `published_date` in extraction metadata dict
- [x] 2.2 Update `urtpe/cli.py`: read `published_date` from extraction metadata, add to pipeline `meta` dict passed to graph builder
- [x] 2.3 Update `urtpe/graph.py`: extend node dict in `build_project_graph` to include all CleanRecord fields; add `published_date` to project output from meta
- [x] 2.4 Update `urtpe/viewer.py`: write `published_date` into `projects.data.js` under `window.PROJECTS.meta.published_date`
- [x] 2.5 Update `urtpe/io.py` if needed: ensure any TSV/JSON writers handle new fields

## 3. Viewer Implementation

- [x] 3.1 Update `viewer/app.css`: add `@media (max-width: 768px)` grid layout for `.cols` (stack list above detail); remove fixed 340px width; use flexible `%` width on desktop; add `.table-wrap { overflow-x: auto }` for table horizontal scroll; add styles for tiered columns (`[data-tier="full"] { display: none }`) and toggle button
- [x] 3.2 Update `viewer/app.js`: modify `renderDetail` to emit two-tier `<th data-tier="essential|full">` / `<td data-tier="essential|full">`; add "展開全部" button that toggles CSS class on table to show/hide full-tier cells; update header meta to use `window.PROJECTS.meta.published_date` instead of `generated_at`
- [x] 3.3 Update `viewer/index.html` if needed: ensure viewport meta present; add version query param to projects.data.js script src for cache busting (optional)

## 4. Acceptance / End-to-End

- [x] 4.1 Run full pipeline regeneration: `python -m urtpe.cli` (or equivalent) → verify projects.json contains `published_date` and nodes have full CleanRecord fields
- [x] 4.2 Open viewer in browser: verify header shows "統計至 115年8月11日"; verify responsive layout at 375px/1200px; verify detail table shows essential columns, toggle reveals full columns, horizontal scroll works on mobile
- [x] 4.3 Run test suite: `pytest` — all existing tests pass + new tests from §1 pass
- [x] 4.4 Run `openspec validate` — change validates cleanly