# Refine Event Source Edges & Callout Details

## Why

Viewers tracing construction history on the graph get mislead by three
concrete defects observed on real families:

1. **False attribution edges** — 大安區-金華段四小段-513-3地號等13筆 draws an
   edge from recno 797 (case 10011042) to 使照核發日期， but 使照's data comes
   from case 10011041 (recno 1040). The plan-in-force heuristic invents
   relationships between unrelated nodes.
2. **Redundant event hyperlinks** — 開工/使照 labels link to case 10011041's
   detail page even though the 北 badge beside recno 1040 already opens the
   same page; the badges also lack rollover tooltips naming which case they
   point to (案10011041 vs 案10011042).
3. **Missing callout content** — the callout never shows 土地使用分區， and
   planners read zones as abbreviations (住三 for 第三種住宅區)， not the full
   string.

Additionally, 建照核發日期's carrying case is provable in the cache (only
10011041 carries it) but the last-write-wins merge discards that provenance
before emission, so 建照 cannot join a source group.

## What Changes

- Emit `milestones_source` (additive optional map: label → winning case_id)
  while merging stage milestones, so every slot's carrying case is provable —
  including 建照核發日期. `schema_version` unchanged.
- Replace the plan-in-force attribution heuristic with **source-group edges**:
  events group by provenance (Taipei case / national-only); a solid edge
  connects each group's source record to the group's first event; solid chain
  within a group; **dashed** edge between chronologically adjacent groups,
  colored by the incoming group. No edges to non-source records.
- Drop event-label hyperlinks when the event's carrying case anchors to a
  record (the record's 北 badge is the access point); keep the link only for
  unanchored carrying cases. National-sourced events rely on the 現況 node's
  國 badge for the twur destination.
- Add rollover tooltips to the graph badges: 北 shows `案<case_id>`, 國 shows
  the national view id.
- Add a 4th callout row: non-empty 土地使用分區 values (Landkind1/2/3)
  abbreviated and joined with `/` (第三種住宅區 → 住三，
  第三之一種住宅區 → 住三之一， 商三特 kept, 道路用地 → 道路).
- Guarantee provenance completeness as a BDD rule: every emitted
  建照/開工/使照 value SHALL resolve to its source (milestones_source,
  implementation case_id, or national) with no heuristics — expressed as a
  spec requirement, guarded by a corpus pytest over `projects.data.js`
  (isolated slots fail with family/slot/value listed), and explainable via a
  small CLI inspector (`scripts/inspect_slot.py <project_id> [slot]`) that
  prints the full per-case provenance breakdown.
- Callout visibility on real data additionally requires the pending
  `--links` regeneration (operational note; the per-record snapshot emission
  already landed in `complete-viewer-field-labels`).
- No change to fetch or cache; the one emission addition is additive and
  optional.
- No part of this scope is gated on the PDF-parsing/similarity POC findings —
  neither the parsing nor the merge/threshold surface is touched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `taipei-implementation-data`: add requirement — stage-milestone merge SHALL
  emit `milestones_source` (label → winning case_id) so slot provenance is
  provable at the viewer.
- `history-graph`: refine the construction-event requirement — source-group
  edge model replaces plan-in-force attribution; event hyperlinks only for
  unanchored sources; badge rollover tooltips; callout gains the abbreviated
  使用分區 row.

## Impact

- `urtpe/links.py`: record the winning case per merged label (one small map
  built in the existing merge loop; attach to project links).
- `viewer/app.js` + `viewer/app.css`: edge grouping, hyperlink rule, badge
  tooltips, callout 4th row + zone abbreviations.
- Tests: `tests/test_links.py` (milestones_source attach),
  `tests/test_viewer_labels.py` (structural),
  `tests/test_milestones_provenance.py` (corpus BDD invariant),
  browser spot-checks on 金華段四小段-513-3 (single pink group) and
  北安段一小段-14-2 (mixed groups).
- `scripts/inspect_slot.py`: CLI provenance explainer (debug tool).
