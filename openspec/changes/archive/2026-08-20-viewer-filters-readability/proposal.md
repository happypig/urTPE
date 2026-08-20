## Why

Analysts browsing the 718-project history viewer cannot narrow the list to the district, approval year, or plan type they care about — the only control is a free-text search. Worse, the graph itself is hard to read: the SVG is authored in a fixed 960×560 coordinate space with no `viewBox`, so in a narrow panel it is squished to ~37% horizontally (labels render at ~3.7px, illegible), and node labels collide with the diagonal track/section edges that pass through them.

## What Changes

- Add three multi-select filter dropdowns above the project list: 地區 (12 districts), 年度 (2002–2026), and 事業種類 (`事業計畫`, `權利變換`, `事業計畫、權利變換` 併送, `事業概要`, `都市更新計畫`, `其他`).
- Filters combine with AND across dropdowns and the existing search box; within a dropdown, a project matches if any of its member records matches any checked value (any-member semantics), except 地區 which is a single value per project.
- Show a live "顯示 N / 718" count reflecting the active filter combination, and an empty state when nothing matches.
- Render the detail SVG with a `viewBox` + `preserveAspectRatio` so node positions and labels scale uniformly at any panel width.
- Add a white text halo (stroke knockout) on node labels so edges passing behind them stay readable.
- Size the SVG height from the node count instead of a fixed minimum, eliminating the large empty box for single-record projects.
- Add a color chip per district on list items and the detail header to make the district dimension scannable.
- No data regeneration required: anchor year, 事業種類, and district are all derivable from fields already present in `projects.data.js`.

## Capabilities

### New Capabilities

- `viewer-filtering`: multi-select 地區/年度/事業種類 filtering of the project list, combined with the existing search, with live result counts.

### Modified Capabilities

- `history-graph`: the render-the-history-in-a-browser-viewer requirement changes — the SVG must scale uniformly at any panel width, node labels must remain legible against edges, the graph height must follow the node count, and the list/detail must surface the district dimension.

## Impact

- `viewer/app.js`: filter state, dropdown UI construction, list filtering logic, SVG generation (`viewBox`, halo, dynamic height), district chip rendering.
- `viewer/app.css`: filter bar layout, dropdown/checkbox styling, district chip palette, empty state.
- `viewer/index.html`: filter bar markup.
- No changes to `urtpe/`, `data/`, or the PDF pipeline.