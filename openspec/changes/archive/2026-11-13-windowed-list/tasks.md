# Tasks: windowed-list

## 1. Tests first (test-first gate — harness cases)

- [x] 1.1 `scripts/viewer_smoke.js` — geometry stubs: `scrollTop` (mutable),
  `clientHeight` (920), `offsetHeight` (64 per row), and a
  `getBoundingClientRect` the harness can set per element.
- [x] 1.2 `scripts/viewer_smoke.js` — the windowing case: a full-height list
  (scrollHeight ≈ rows × 64) renders ~window rows in the DOM, not all.
- [x] 1.3 `scripts/viewer_smoke.js` — scrolling down re-renders the window
  around the new offset; the spacer heights keep the total height stable.
- [x] 1.4 `scripts/viewer_smoke.js` — the deep link: setting the hash to
  `#project=<id>` renders the window containing that row, then scrolls.

## 2. Implementation

- [x] 2.1 `viewer/app.js` — a window helper (`renderWindowedList`) written
  for both lists (the dashboard's future drill-down included): computes the
  visible range from `scrollTop`/`clientHeight`, renders
  [first − buffer, last + buffer], spacers top and bottom.
- [x] 2.2 `viewer/app.js` — `renderList` uses the helper; the scroll
  listener re-renders on movement past a row height.
- [x] 2.3 `viewer/app.js` — `openFromHash` renders the target's window
  before scrolling.

## 3. Verify

- [x] 3.1 `node scripts/viewer_smoke.js` — green (the windowing cases
  included). *(25 DOM rows for 675 projects; 2 spacers; all checks passed)*
- [x] 3.2 `python -m pytest` — full suite green. *(1314 passed / 1 skipped)*
- [ ] 3.3 Manual (the user's browser): scroll the full list, no jump, the
  deep link lands centered.
