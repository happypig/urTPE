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

## 3. Verification

- [x] 3.1 The suite passes; the page renders from `file://` with the new
  links resolving.
- [ ] 3.2 `check_deploy.py` reports about.html fresh after the push.
