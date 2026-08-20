## Why

The browser viewer is desktop-only (fixed 340px list, no responsive CSS), the detail
table under the graph shows only four columns (編號/核定日期/階段/事業種類 + 現況 badge),
and the header date shows the pipeline generation timestamp instead of the PDF's
official published date (統計至115年8月11日). Analysts need a mobile-friendly layout,
access to the full original row data per record (案名, 地號, 區段, 實施者, 更新規劃單位,
review_flags/auto_fixes), and the authoritative publication date from the source
document.

## What Changes

- **Responsive layout**: Stack project list above detail pane on narrow viewports
  (mobile-first CSS, media query at ~768px); remove fixed 340px width.
- **Full row data in detail table**: Extend the record table to show all original
  CleanRecord fields (case name, land/parcels, section, implementer, planner,
  review_flags/auto_fixes) as additional columns after 現況, defaulting to analyst
  essentials with an "展開全部" toggle for the full set.
- **Official published date in header**: Replace the `generated_at` timestamp in
  the meta line with "統計至 115年8月11日" (the 統計至 line from PDF page 1, y≈60),
  parsed during PDF extraction and threaded through the pipeline.
- **Extract PDF header date**: Capture the 統計至 date in `extract.py` (currently
  discarded as furniture) and propagate it via `cli.py` meta → `projects.json` →
  `projects.data.js` → viewer.

## Capabilities

### New Capabilities
- `viewer-responsive-layout`: Mobile-first responsive CSS stacking list above
  detail, with breakpoint at ~768px; no drawer or tab pattern.

### Modified Capabilities
- `viewer-filtering`: Detail table column set changes (adds full row fields,
  default essentials + expand toggle); meta line date source changes.
- `history-graph`: Node shape gains original row fields (case name, land, parcels,
  section, implementer, planner, review_flags, auto_fixes) so the viewer can
  render them; project meta gains `published_date` (the 統計至 date).
- `pdf-tsv-extraction`: Extraction must capture the 統計至 date line from PDF page 1
  and emit it in the pipeline meta.

## Impact

- `viewer/app.css`: Add media query, flex/grid responsive layout, table horizontal
  scroll for many columns.
- `viewer/app.js`: `renderDetail` emits full column set; header meta uses
  `published_date`; add "展開全部" toggle for row fields.
- `viewer/projects.data.js`: Carries `published_date` and enriched node data.
- `urtpe/extract.py`: `is_furniture` must retain 統計至 line; new field in
  extracted metadata.
- `urtpe/cli.py`: Thread `published_date` through pipeline meta.
- `urtpe/graph.py`: Node schema includes original row fields from `CleanRecord`.
- `urtpe/viewer.py`: Emit `published_date` and full node data into
  `projects.data.js`.
- Existing tests for viewer, graph, and extraction updated for new fields/layout.