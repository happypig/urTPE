## Why

The viewer currently shows only basic "相關連結" (external links) for each project, but the pipeline already extracts rich milestone data from both the national portal (推動歷程: 申請/核定 dates) and Taipei platform (階段辦理過程: full stage timeline with 15+ milestones). Analysts need to see these official procedural timelines directly in the detail pane — not just outbound links — to understand the full approval history without leaving the viewer.

## What Changes

- **New milestone display section** in the viewer detail pane showing 推動歷程 (national portal) and 階段辦理過程 (Taipei platform) as expandable timelines
- **Per-node milestone attribution** showing which milestones belong to which approval stage (事業計畫 vs 權利變換)
- **Progressive loading indicators** showing when national portal data is available vs when Taipei platform data is still loading/unavailable
- **Collapsible timeline cards** to avoid clutter when many milestones exist

## Capabilities

### New Capabilities

- `viewer-milestone-timeline`: renders 推動歷程 and 階段辦理過程 as expandable timeline cards in the detail pane, with per-node attribution and progressive loading states

### Modified Capabilities

- `viewer-related-links`: extends the existing 相關連結 section to embed milestone timelines inline rather than just external links

## Impact

- `viewer/app.js`: add `renderMilestones()` function, extend `renderDetail()` to include milestone cards
- `viewer/app.css`: add styles for timeline cards, expand/collapse, loading states, per-node badges
- No changes to pipeline, graph, or data schema — existing `links.milestones_national` and `links.milestones_taipei` fields on projects and nodes are already emitted