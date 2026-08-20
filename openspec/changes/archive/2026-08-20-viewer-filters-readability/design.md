## Context

The pipeline is PDF → positional parse → raw.tsv → cleanse → clean.tsv → similarity merge → merged.tsv → projects.json → viewer. The viewer is the only human-facing component: a static three-file app (`index.html`, `app.css`, `app.js`) plus generated `projects.data.js`, loaded entirely client-side with no build step. The list renders all 718 projects at once; the detail renders one project's SVG timeline and a records table. Today's only control is a free-text search box; there is no structured filtering.

See proposal.md - Why for the motivation (filtering gap + unreadable fixed-coordinate SVG).

## Goals / Non-Goals

**Goals:**
- Multi-select 地區 / 年度 / 事業種類 filters with live result counts, AND-combined with the existing search.
- Uniform SVG scaling via `viewBox` so labels stay legible at any panel width.
- Label legibility over edges, dynamic graph height, and a district color chip in list and detail.

**Non-Goals:**
- No server-side filtering or pagination; 718 items remain fully client-side.
- No changes to the merge/cleanse pipeline or `projects.data.js` schema — the viewer derives filter values from fields already present on each project's nodes.
- No virtualized list rendering; item count is small enough to re-render per filter change.

## Decisions

**D1 — Filters are derived client-side from the loaded data, not regenerated.**
Each project in `projects.data.js` already carries `district` and `nodes[]` with `date` (ISO) and `track`. The viewer computes: district set (12), year set from every member's `date` year across all projects, and the fixed track value set (`事業計畫`, `權利變換`, `事業計畫、權利變換`, `事業概要`, `都市更新計畫`, `其他`).
*Alternative considered:* emitting filter enumerations into `projects.data.js` via `viewer.py`. Rejected — the schema is frozen by the history-graph spec, and deriving is trivial; regenerating the data file for a UI concern adds a pipeline dependency.

**D2 — Multi-select checkboxes (Design X).**
Each selector is a dropdown whose panel contains labeled checkboxes plus a 全選/清除 pair. Selection state lives in a plain object keyed by dimension. Unchecked = inactive.
*Alternatives considered:* native `<select multiple>` (poor styling, no clear affordance), single-select (loses multi-district browsing), three standalone enable toggles (Design Y — rejected by user for X).

**D3 — Any-member semantics for 年度 and 事業種類; single-value for 地區.**
A project matches 年度 if any of its nodes' `date` year is in the checked set; matches 事業種類 if any node's `track` is in the checked set; matches 地區 if the project's own `district` is checked. Dimensions AND together; the search box also ANDs.
*Alternative considered:* anchor-only (only the `is_current` node counts). Rejected by user in favor of any-member multi-select.

**D4 — SVG output switches to a `viewBox`-based responsive box.**
Replace the fixed `width`/`height` attributes with `viewBox="0 0 w h"` + CSS `width:100%; height:auto;` so the whole graph (positions and text) scales uniformly. The authored coordinate space (PAD/COL_W/row spacing) is unchanged — only the rendering container changes.
*Alternative considered:* computing layout in live CSS pixels via `getBoundingClientRect`. Rejected — larger change, breaks the stable column layout.

**D5 — Node label halo via `paint-order`.**
Apply `paint-order: stroke; stroke: #fff; stroke-width: 3px` to node label text so lines passing behind labels are knocked out. Cheap, pure CSS, no layout change.
*Alternative considered:* background `<rect>` behind each label. Rejected — needs per-label measurement and re-layout on font differences.

**D6 — Dynamic SVG height.**
Height = `PAD*2 + nodeCount*64` instead of `max(560, …)`, with the same floor applied to width from lane count. A 1-record project now renders a compact box.

**D7 — District chips with a fixed 12-color palette.**
A stable hash from the district name picks a color from a palette; the chip appears on each list item and in the detail header. Colors are purely presentational, not encoded in data.

## Risks / Trade-offs

- [Any-member over-links projects with scattered years] → Visible via the live count and chips; acceptable — the user chose any-member for browsing breadth.
- [Vertical-space cost of three always-visible dropdowns on small screens] → The filter bar wraps; dropdown panels are absolutely positioned and close on outside click.
- [`viewBox` text can still be small at very narrow widths] → Uniform scale keeps it readable (unlike today's squish); further size tuning is a CSS-only follow-up.
- [Hash colors may be unlucky (two districts too close)] → 12 districts, 12-color palette, manually verify contrast once in the browser.