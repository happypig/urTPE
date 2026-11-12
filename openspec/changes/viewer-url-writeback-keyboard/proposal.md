# Proposal: viewer-url-writeback-keyboard

## Why

The viewer's left-hand list is mouse-only and its URL is read-only:

1. **No keyboard path.** The list items are `div` elements with an `onclick`
   handler (`viewer/app.js:911`). The codepoint-level search over
   `viewer/app.js` (1,710 lines) reads: `tabindex` 0, `keydown`/`keyup` 0,
   `role=` 0, `aria-` 0. A keyboard user cannot select a project.
2. **The URL is only read, never written.** The read half shipped with the
   dashboard's deep link (94cd3e8): `openFromHash` (`viewer/app.js:1626`)
   reads `#project=<project_id>` on load and on `hashchange`. Clicking an
   item does not touch the hash (`viewer/app.js:1624-1625` says so in a
   comment), so a reader who selects a project cannot copy the selection out
   of the address bar.

**A shareable URL must be writable, and the only writer is a selection. A
selection must be reachable, and the only reach is focus.** Focus,
activation and write-back are one edit in one function (`renderList`'s item
construction). Splitting them publishes half a feature
(`docs/inspection-batchE.md` E2).

## What Changes

- Each list item becomes focusable (`tabindex="0"`, `role="button"`), with a
  visible focus indicator (`:focus-visible` in `viewer/app.css`).
- Enter and Space activate the item, exactly as a click does.
- Selecting a project (click or keyboard) writes the selection into the URL
  with `history.replaceState` — one history entry per page load, never a
  push per click.
- The read half (`openFromHash`, the hash format, the dashboard's
  `encodeURIComponent` encoding) does not move.
- Scope: steps 1–4 of the notes' §8.3. No windowing (E3), no debounce.

## Capabilities

### Modified Capabilities

- `history-graph`: the list-item requirement gains keyboard access and URL
  write-back — a selection is reachable by keyboard, is written to the URL,
  and the deep link's read path is unchanged.

## Impact

- Code: `viewer/app.js` (the item template, the key handlers, the
  `replaceState` call, the retired comment), `viewer/app.css`
  (`:focus-visible`).
- Tests: `scripts/viewer_smoke.js` gains focus/URL assertions (the harness
  cases this batch's E3 builds on).
- Not touched: the payload, the pipeline, the dashboard's links.
