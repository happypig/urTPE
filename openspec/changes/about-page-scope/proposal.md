# Proposal: about-page-scope

## Why

The 關於 page (archived 2026-11-12) states the site's counts without their
population. A policy reader who opens the national portal's statistics table
sees 433 報核中 for 臺北市 and asks why this site shows only 680 projects.
The answer is scope, not gap: the gazette the site reads carries **approved**
cases only, so applications still under review are absent by design — and the
city's own 推動成果 page gives the application-level totals (1,480 事業計畫
報核, 630 核定實施).

The page already says "這裡只有已核定案件" on the dashboard's 定義與限制, but
the about page's 資料來源與處理 section — the section that names the corpus —
does not, and it links none of the official statistics. A number without its
population invites a false comparison.

Actors: the policy reader arriving from PUMA.taipei, comparing this site
against the two official statistics pages; the maintainer, who answers the
"why 680?" question today from memory.

## What Changes

- The about page's 資料來源與處理 section gains a scope statement: the graph
  holds approved cases only (680 projects / 1,444 records at the 2026-10-28
  gazette); the in-review pool is absent by design; the two official
  figures — the city's 1,480 報核 / 630 核定實施 and the national portal's
  433 報核中 (統計至 2026/09/30) — are named with links to their pages:
  - https://uro.gov.taipei/News_Content.aspx?n=B649EEAA7A7E35DB&sms=3DCF9FD28E559058&s=F0E9E31078AF60FE
  - https://twur.nlma.gov.tw/zh/urban/statistics/view/7
- The figures stay dated in the page text. The official pages move (the
  national table is 統計至 2026/09/30); a reader must be able to tell which
  snapshot each number is from. The site's own count is not hand-copied into
  the sentence — the page reads it from nothing; the sentence names the
  gazette date and the reader gets the live count from the pages' meta line,
  so the scope statement does not go stale while the pages stay fresh.
  (The 680/1,444 figures in the spec scenario are the values measured at
  proposal time; the page states the date and lets the site's own meta line
  carry the moving numbers.)

## Extended 2026-11-12: the domain-model page joins the header rule

The user's mockup (2026-11-12) pins the 關於 control's final shape: the
navlink chip — terracotta text, hairline border, 8px radius — closing the
header at the right edge on every published page. Fixing the five pages that
differed made the rule explicit, and it exposed one more page with no 關於
link at all: `docs/domain-model.html`. A reader who lands on the bilingual
domain model from a search result has no route to the license, the sources
or the contact. Its header gains the same chip, so the rule holds across all
six header pages (the mockup's five plus the domain model).

## Capabilities

### Modified Capabilities

- `viewer-related-links`: the about-page requirement gains the scope-statement
  clause and its scenario; extended, the documentation-pages clause names the
  domain-model page too and the rightmost-link rule covers its header.

## Impact

- Code: `viewer/about.html` (one paragraph in the sources section),
  `tests/test_about_page.py` (the scope assertions).
- Not touched: headers, deploy record, pipeline, reports.
