# Tasks: docs-cream-restyle

## 1. Tests first (test-first gate)

- [ ] 1.1 `tests/test_about_page.py` — the design pin inverts: the page must
  carry the cream tokens (`#fff8f4`, `#211d1d`, `#f3d9bf`, `#ad4d2a`) and no
  slate tokens (`#0f172a`, `#cbd5e1`) and no dark-mode block.
- [ ] 1.2 `tests/test_about_page.py` — the three doc pages carry the cream
  tokens and no dark-mode block (the generators' emitted files are read).

## 2. Implementation

- [ ] 2.1 `scripts/release_diff_report.py` — the token block becomes the
  cream palette; the dark block goes; semantic cards/pills map onto cream
  tints; regenerate `docs/release-diff.html`.
- [ ] 2.2 `scripts/coverage_report.py` — same; regenerate
  `docs/coverage-report.html`.
- [ ] 2.3 `docs/etl_process.html` — the token block becomes cream; the dark
  block goes; the stage dots and score bar keep their hue roles with cream
  tints.
- [ ] 2.4 `viewer/about.html` — the token block becomes cream, the dark block
  goes (back to the palette it launched with, now under the cream rule).

## 3. Verification

- [ ] 3.1 The suite passes; the smoke harness passes.
- [ ] 3.2 All six published pages verified in Chrome (file:// and the live
  site): one palette, no dark seam, the 關於 links and header order intact.
- [ ] 3.3 `check_deploy.py` reports all artifacts fresh after the push.
