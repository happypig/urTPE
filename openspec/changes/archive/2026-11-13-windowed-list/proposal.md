# Proposal: windowed-list

## Why

An empty search renders all 680 list rows. The DOM build costs ~17 ms; layout
and paint cost ~63 ms — the browser paints every row and discards most
off-screen (`list.scrollHeight` ~34,000 px against a 920 px viewport;
`docs/inspection-batchE.md` E3, re-measured 2026-11-12). **Paint is the
cost, not JavaScript.**

The gate is the harness, not the viewer: `scripts/viewer_smoke.js` stubs
`getBoundingClientRect()` to zeros and provides no `scrollTop`,
`clientHeight` or `offsetHeight` — exactly the values a windowed list reads.
Nothing checks the harness automatically (it runs by hand, offline). A
windowed list without harness support ships with no automated check at all.
So the change's first task is harness geometry, and the test-first gate is
satisfied by harness cases.

## What Changes

- `scripts/viewer_smoke.js` gains geometry: `scrollTop`, `clientHeight`,
  `offsetHeight`, and a mutable `getBoundingClientRect`, so windowing is
  drivable.
- `viewer/app.js` `renderList` renders only the rows near the viewport
  (first visible row ± buffer); spacers at both ends hold the full list
  height so the scrollbar never jumps. The helper is written so the
  dashboard can call it (the notes' §8.4).
- The deep link keeps working: `openFromHash` renders the window containing
  the target row BEFORE `scrollIntoView`, or the link silently selects
  without showing.
- The harness's overlap/badge checks walk the rendered window; the harness
  case decides whether to walk the window or force the full render.

## Capabilities

### Modified Capabilities

- `history-graph`: the list-render requirement — only rows near the viewport
  render; spacers hold the height; the deep link renders before it scrolls.

## Impact

- Code: `viewer/app.js` (the window helper + `renderList`), `viewer/smoke.js`
  (geometry stubs + the windowing cases).
- Not touched: the payload, the pipeline, the dashboard.
