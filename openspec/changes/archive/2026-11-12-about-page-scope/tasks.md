# Tasks: about-page-scope

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_about_page.py` — the 資料來源與處理 section states the
  approved-only scope: the sentence pairs 本站資料 with 已核定, and states the
  in-review applications (報核中 / 審查中) are absent by design.
- [x] 1.2 `tests/test_about_page.py` — the scope statement links both official
  statistics pages: the city's 推動成果 page (uro.gov.taipei, the
  News_Content.aspx URL) and the national statistics table
  (twur.nlma.gov.tw/zh/urban/statistics/view/7).
- [x] 1.3 `tests/test_about_page.py` — the scope statement carries both
  official figures with their dates: 1,480 報核 / 630 核定實施 (city page)
  and 433 報核中 with the national table's 統計至 2026/09/30 named, so a
  reader can tell which snapshot each number is from.
- [x] 1.4 `tests/test_about_page.py` — the site's own count is not hand-copied
  into the scope sentence: the sentence names the gazette date only, and the
  moving figures stay where the pages compute them (the meta line), so the
  statement cannot go stale against the payload.

## 2. Implementation

- [x] 2.1 `viewer/about.html` — the 資料來源與處理 section gains the scope
  paragraph after the sources list: approved-only corpus, in-review absent by
  design, both official figures dated and linked.

## Extended 2026-11-12: the domain-model page joins the header rule

- [x] 4.1 `tests/test_about_page.py` — the mockup rule pinned: all six header
  pages (the five the mockup shows plus `docs/domain-model.html`) close their
  header with the navlink chip labelled 關於, defined with the 8px radius.
  Red before implementation.
- [x] 4.2 `viewer/index.html`, `viewer/dashboard.html` — the chip moves to the
  header's last position (after the meta line; on the viewer, after the
  search box).
- [x] 4.3 `scripts/release_diff_report.py` + `scripts/coverage_report.py` —
  the floated `.backlink` text link becomes the navlink chip, last in the
  header; both reports regenerated.
- [x] 4.4 `docs/etl_process.html` — the inline-styled link inside the subtitle
  becomes the navlink chip, last in the header.
- [x] 4.5 `docs/domain-model.html` — the header gains the navlink chip
  labelled 關於 → `../viewer/about.html`, after the language switch.
- [x] 4.6 The suite passes; `check_deploy.py` is unaffected (the domain model
  joins the deploy record under docs-cream-restyle, not here).

## 3. Verification

- [x] 3.1 The suite passes; the page renders from `file://` with the new
  links resolving.
- [x] 3.2 `check_deploy.py` reports about.html fresh after the push.
