## Why

Two label defects in `buildRelatedLinkLabels` (viewer/app.js):

- **C7**: a case a node anchors is labelled with that node's `case_name` (the
  gazette row), not the city's own case name. 307 anchored cases show a wrong
  label: 20 lose an area suffix (吉林508's 11011241 shows without `-A區`),
  48 show another stage word, 8 show another parcel count, 231 differ in other
  wording. With the area-split binding, one node carries 2+ cases and the
  gazette label cannot tell them apart.
- **C10**: the 國 label (anchorName) is the latest gazette node's name; the
  national page names the project by its first 擬訂 case (the cached `view.html`
  `<title>`). Measured: 452 of 632 projects with a cached page show the wrong
  name (302: the title equals an earlier node's name; 150: it equals no node).

## What Changes

- 相關連結 labels each case with its own city name: `candidate_names[cid]`
  first for anchored cases too (the city's own name wins at level 1; the
  gazette name stays as the node's own label in the graph).
- The pipeline stores the national page `<title>` as `twur_name` (re-parsed
  from the cached `view.html` — no request), and the 國 label reads it.
- One re-emit (the new field + corrected labels).

## Capabilities

### Modified Capabilities
- `viewer-related-links`: the label chain's node level SHALL prefer the
  city's own case name (`candidate_names[cid]`) for anchored cases; the 國
  anchor label SHALL be the national page's own name (`twur_name`).

### Added Capabilities
- `cache-freshness`: the emitted payload SHALL carry `twur_name` from the
  project's own national page `<title>`.

## Impact

- `viewer/app.js`: `buildRelatedLinkLabels`.
- `urtpe/links.py`: parse the cached `view.html` `<title>` at absorb time.
- Re-emit; no API call.
