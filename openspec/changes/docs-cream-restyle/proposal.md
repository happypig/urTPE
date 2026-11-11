# Proposal: docs-cream-restyle

## Why

The site now carries two palettes. The dashboard and the viewer (政策儀表板,
專案歷史圖) share the cream system — `#fff8f4` ground, charcoal `#211d1d`,
peach hairlines `#f3d9bf`, terracotta accent `#ad4d2a`, sun-highlighter
headings, shadowed cards. The three documentation pages (the release-diff
report, the coverage report, the ETL write-up) and the about page share a
different one — white ground, slate ink `#0f172a`, hairline `#cbd5e1`, blue
`--info` links, a dark-mode block.

A reader moving from the dashboard into a report crosses a visible seam: the
ground flips from cream to white, the link colour flips from terracotta to
blue, the headings lose the highlighter. The user asks for the docs pages to
wear the cream system too, so every published page reads as one site.

The about page follows the same rule: it was moved onto the docs palette
(openspec: about-page-links) before the cream rule covered it; it moves back
with the docs pages, so one system holds across all six published pages.

Actors: the reader crossing between the dashboard and the reports; the two
report generators whose palette blocks change; the pinned design test in
`tests/test_about_page.py`, which today pins the slate palette and would
fail after the move.

## What Changes

- **The three doc pages adopt the cream palette.** The token blocks change:
  slate → cream (`--bg:#fff8f4`, `--ink:#211d1d`, `--line:#f3d9bf`,
  `--panel:#ffffff`), links → terracotta `#ad4d2a`, headings gain the sun
  highlighter under `h2`, cards gain the dashboard's shadow treatment
  (`box-shadow: 6px 6px 0 var(--line)`), body text moves to the cream
  system's stack (Instrument Sans via the existing @import on the viewer —
  but the doc pages stay self-contained, so they keep a system stack that
  names the same fallbacks without fetching). Semantic colours map onto the
  cream system's existing values: status greens/reds/ambers keep their hue
  roles as tint-and-ink pairs built from the cream system (terracotta family
  for emphasis, the dashboard's `--flag5`/`--flag3` for warn/drop text).
- **The about page moves with them** — same token block, so all six pages
  share one palette.
- **Dark mode is dropped, deliberately.** The cream system has no dark-mode
  block; the dashboard and viewer render light-only. Giving the docs pages
  a dark block would make them the only dark pages on the site — a different
  seam, in the other direction. The dark blocks come out of the three doc
  pages and the about page.
- **The generators carry the change** (`release_diff_report.py`,
  `coverage_report.py`), so the next regeneration keeps it. The ETL page and
  the about page are hand-written.

## Capabilities

### Modified Capabilities

- `viewer-related-links`: the about-page requirement's self-contained clause
  gains the palette rule — the page wears the site's cream system, no
  dark-mode block, pinned by test.

## Impact

- Code: `docs/release-diff.html` + `scripts/release_diff_report.py`,
  `docs/coverage-report.html` + `scripts/coverage_report.py`,
  `docs/etl_process.html`, `viewer/about.html`,
  `tests/test_about_page.py` (the design pin inverts).
- Not touched: header links, deploy record, pipeline, the viewer/dashboard's
  own styles.
- Verification: the suite, the smoke harness, and a browser pass over all
  six pages (light only — the system is light-only now).
