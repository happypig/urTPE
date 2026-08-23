## Context

The viewer (`viewer/app.js`) currently renders a "相關連結" section with outbound links to the national portal and Taipei platform. The pipeline already extracts and emits rich milestone data in `links.milestones_national` (推動歷程: 申請/核定 dates) and `links.milestones_taipei` (階段辦理過程: full stage timeline). This data is available on both project and node levels but not rendered.

## Goals / Non-Goals

**Goals:**
- Render 推動歷程 and 階段辦理過程 as expandable timeline cards in the detail pane
- Show per-node milestone attribution via badges on graph nodes/table rows
- Progressive loading: show national data immediately, Taipei data with placeholder when unavailable
- Keep existing outbound links functional

**Non-Goals:**
- No new data fetching in the viewer (all data comes from `projects.data.js`)
- No changes to pipeline, graph emission, or data schema
- No real-time updates or polling

## Decisions

### D1: Timeline card component with CSS-only expand/collapse

Use a single `<details>`/`<summary>` pattern or CSS-only toggle (matching existing "展開全部" pattern) for expand/collapse. No JS state management needed.

**Why:** Matches existing "展開全部" pattern in the record table. Zero JS state, accessible, works without JS.

**Alternative considered:** React/Vue component — rejected (vanilla JS codebase).

### D2: Timeline data structure

Each milestone card renders from an array of `{label, date, source}` objects. Source distinguishes "national" vs "taipei" for badge styling.

```js
// Input from projects.data.js
project.links.milestones_national = {"事業計畫申請日期": "101.12.28", ...}
project.links.milestones_taipei = {"計畫公聽會日期": "2012/10/21", ...}

// Transformed for rendering
[
  {label: "事業計畫申請日期", date: "101.12.28", source: "national"},
  {label: "計畫公聽會日期", date: "2012/10/21", source: "taipei"},
  ...
]
```

### D3: Per-node badge in graph and table

Add a small badge (e.g., "🇹🇼" for national, "🏙️" for Taipei) to:
- Graph node `<g>` element (top-right corner)
- Table row (first column or new column)

Clicking badge opens a small popover/tooltip with that node's milestones.

**Why:** Keeps context local to the approval stage.

### D4: Progressive loading placeholder

When `milestones_taipei` is empty but `milestones_national` exists:
- Render "推動歷程" card normally
- Render "階段辦理過程" card with disabled state: "台北市資料未取得 · <a href='twur_url'>前往入口網查看</a>"

### D5: Reuse existing "展開全部" CSS pattern

The record table already uses `[data-tier="full"] { display: none }` with a toggle button. Apply identical pattern to milestone cards.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Too many milestones clutter the detail pane | Collapsible cards default to collapsed; "展開全部" toggle |
| Taipei data often unavailable (portal blocked) | Graceful placeholder with link to national portal |
| Per-node popover positioning in SVG | Use HTML overlay div positioned via `getBoundingClientRect()` |
| Milestone date format inconsistency (ROC vs Gregorian) | Display as-is from source; add tooltip with converted date if needed |

## Migration Plan

1. Add `renderMilestones()` function in `app.js`
2. Call it from `renderDetail()` after link section
3. Add CSS for `.milestone-card`, `.milestone-row`, `.milestone-badge`, loading states
4. Add per-node badge rendering in graph SVG and table
5. Test with fixture data (existing test fixtures have milestones)

## Open Questions

- Should milestones be sortable by date? (Current source order may not be chronological)
- Add date format conversion (ROC → Gregorian) in tooltip?
- Limit number of milestones shown before "show more"?