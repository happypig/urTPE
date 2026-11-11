# Tasks: about-page-links

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_about_page.py` — the about page carries no stylesheet
  file and no external font/style request, and its inline styles use the
  docs design system's tokens: `#0f172a` ink, `#cbd5e1` hairline, `#1d4ed8`
  info link, and a `prefers-color-scheme: dark` block with the docs palette
  (`#e2e8f0` ink, `#334155` line, `#0b1220` bg).
- [x] 1.2 `tests/test_about_page.py` — the three doc pages carry a 關於 link
  at their header's right edge whose target is `../viewer/about.html`
  (release-diff and coverage reports read the committed generated files; the
  ETL page is hand-written).
- [x] 1.3 `tests/test_release_diff_publish.py` — the release-diff report's
  back link points at `../viewer/about.html` and carries no
  回專案歷史圖 link.
- [x] 1.4 `tests/test_about_page.py` — header ordering: in the viewer's and
  the dashboard's headers, 關於 is the last navlink, with the site's other
  links (政策儀表板, 專案歷史圖) to its left.
- [x] 1.5 `tests/test_release_diff_publish.py` — the regenerated reports'
  header link matches the generator (the generator emits the 關於 link; the
  committed files carry it).

## 2. Implementation

- [x] 2.1 `scripts/release_diff_report.py` — the header block emits
  `<a class="backlink" href="../viewer/about.html">關於</a>` in place of
  `← 回專案歷史圖`; regenerate `docs/release-diff.html` (the working tree's
  uncommitted 02:10 regeneration rides along).
- [x] 2.2 `scripts/coverage_report.py` — the header gains the same back
  link (the page had none); regenerate `docs/coverage-report.html`.
- [x] 2.3 `docs/etl_process.html` — the header's link row gains 關於 at the
  right edge (hand-written page, matching the docs link style).
- [x] 2.4 `viewer/about.html` — restyle onto the docs design system: slate
  tokens, dark-mode block, card/sub/lead hierarchy, docs link colour;
  content unchanged.

## 3. Verification

- [x] 3.1 The suite passes; `node scripts/viewer_smoke.js` passes.
- [x] 3.2 The regenerated reports diff only in the header link and the
  already-pending count changes.
- [ ] 3.3 The four pages open from `file://` in a browser; dark mode reads
  correctly on the about page.
