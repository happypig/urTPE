# Tasks: viewer-url-writeback-keyboard

## 1. Tests first (test-first gate)

- [x] 1.1 `scripts/viewer_smoke.js` — the harness cases: a rendered list item
  carries `tabindex="0"` and `role="button"`; activating it (the harness
  calls the click handler; the key handler routes to the same function)
  selects the project; the URL hash equals
  `#project=<encodeURIComponent(project_id)>` after selection.
- [x] 1.2 `scripts/viewer_smoke.js` — Enter and Space on a focused item
  select it; other keys do nothing.
- [x] 1.3 `scripts/viewer_smoke.js` — selecting a second project replaces
  the hash (replaceState semantics: one hash, no history stack); no
  `pushState` call exists in the render path.
- [x] 1.4 `scripts/viewer_smoke.js` — the read half still works: setting the
  hash to `#project=<id>` and firing `hashchange` opens that project
  (the existing deep-link behaviour, unchanged).

## 2. Implementation

- [x] 2.1 `viewer/app.js` — the list item template: `tabindex="0"`,
  `role="button"`, and a named `select()` used by click, Enter and Space.
- [x] 2.2 `viewer/app.js` — on selection, `history.replaceState(null, "",
  "#project=" + encodeURIComponent(p.project_id))`, guarded for the smoke
  harness's stubbed `history`.
- [x] 2.3 `viewer/app.js` — the comment at `:1623-1625` ("clicking an item in
  the list does not rewrite the hash") is updated to the new behaviour in the
  same edit.
- [x] 2.4 `viewer/app.css` — the `:focus-visible` rule for `.item`.

## 3. Verify

- [x] 3.1 `node scripts/viewer_smoke.js` — green (the new cases included). *(all checks passed; 6 harness cases added)*
- [x] 3.2 `python -m pytest` — full suite green. *(1285 passed / 1 skipped)*
- [ ] 3.3 Manual (the user's browser): Tab reaches the list, Enter selects,
  the address bar carries `#project=`, a copy-paste + reload reopens the
  project.
