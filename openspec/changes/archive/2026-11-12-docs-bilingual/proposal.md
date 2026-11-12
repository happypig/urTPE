# Proposal: docs-bilingual

## Why

The site's readers are zh_TW policy readers — the viewer, the dashboard and
the three generated reports are zh_TW. The two hand-written doc pages are
not: `docs/etl_process.html` is English-only, and `docs/domain-model.html`
is bilingual but English-default (its head comment says so, and its CSS
shows English until the reader checks 中文). A reader who reaches the ETL
write-up from the 關於 page or a search result reads a different language
from every page that linked them there.

The user's mockup rule (2026-11-12) also fixed where the switch belongs: the
header's right edge, packed against the 關於 chip. On the domain model the
switch is centre-aligned today — `justify-content:space-between` spreads the
title block, the switch and the chip across the row.

Actors: the zh_TW policy reader landing on a write-up; the maintainer, who
keeps both renderings in one file.

## What Changes

- **The ETL page becomes bilingual**, pairing-based like the domain model:
  prose passages carry `<span class="en">…</span><span class="zh">…</span>`
  pairs in one DOM; the technical names — file paths, module names, flags,
  exit codes, spec sections — stay verbatim in both renderings. A two-line
  inline script toggles the `en` class; the page still works with scripting
  disabled, one rendering showing by CSS alone.
- **Both hand-written pages default to zh_TW.** The document element declares
  `lang="zh-Hant"`, and the CSS hides the English rendering unless the reader
  switches to it. The domain model's switch label flips accordingly
  (中文 → English), because the label names what checking it does.
- **The switch packs against the 關於 chip.** The domain model's header drops
  `justify-content:space-between`; the title block takes `flex:1`, so the
  switch and the chip sit together at the right edge — the same anatomy the
  other five header pages use.
- The generated reports (release-diff, coverage) stay zh_TW-only; they are
  generator-emitted and already monolingual zh_TW.

## Capabilities

### Added Capabilities

- `docs-pages`: the two hand-written doc pages are bilingual, default to
  zh_TW, and carry the language switch at the header's right edge beside the
  關於 chip.

## Impact

- Code: `docs/etl_process.html` (pairing + switch + default),
  `docs/domain-model.html` (default flip + switch position),
  `tests/test_about_page.py` (the three pins).
- Not touched: headers' link targets, deploy record, generators, pipeline.
- Verification: the suite, and a browser pass over both pages from `file://`.
