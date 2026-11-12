# Tasks: docs-bilingual

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_about_page.py` — both hand-written doc pages default to
  zh_TW: `<html lang="zh-Hant">`, the CSS hides the English rendering when the
  `zh` class is set and hides the zh rendering when it is cleared.
- [x] 1.2 `tests/test_about_page.py` — the language switch sits immediately
  before the 關於 chip in both headers, with no link or other label between
  them, and the chip stays the header's last link.
- [x] 1.3 `tests/test_about_page.py` — the ETL page's prose is pairing-based:
  the `.en` and `.zh` span counts are equal and at least 40 each, so the page
  ships both renderings in one DOM rather than a hand-patched single language.

## 2. Implementation

- [x] 2.1 `docs/etl_process.html` — prose passages become en/zh span pairs;
  the technical names stay verbatim; the header gains the switch between the
  title block and the 關於 chip; `lang="zh-Hant"`; the two-line toggle script.
- [x] 2.2 `docs/domain-model.html` — default flips to zh_TW (`lang="zh-Hant"`,
  the CSS pair inverts, the switch label becomes English, the toggle script
  sets the class accordingly); the header drops `justify-content:space-between`
  so the switch packs against the 關於 chip.

## 3. Verification

- [x] 3.1 The suite passes; the smoke harness passes.
- [x] 3.2 Both pages verified in Chrome (served over 127.0.0.1 — the Claude-in-Chrome
  extension refuses `file://` navigation): zh_TW on open, the switch swaps both ways
  without a reload, the chip stays at the right edge. The pass caught the domain
  model still showing both renderings — its English prose was bare text the CSS
  pair cannot hide — plus a pre-checked switch, a zh span nested in an en span
  (the asymmetry h3 rendered empty in zh mode), and two bare fragments
  (`= land core slug`, footer `source of truth` in the zh rendering); all fixed
  and pinned in tests/test_about_page.py.
