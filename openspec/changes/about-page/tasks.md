# Tasks: about-page

## 1. Tests first (test-first gate — every task here is checked before any task in group 2)

- [ ] 1.1 `tests/test_about_page.py` — the about page exists at `viewer/about.html`,
  is valid enough HTML to open, and carries `<html lang="zh-Hant">`.
- [ ] 1.2 `tests/test_about_page.py` — the page states CC BY 4.0 for the site's own
  content (本站採用 CC BY 4.0 授權), and the upstream-data line is a separate
  sentence deferring to the data's own terms, not covered by the license claim.
- [ ] 1.3 `tests/test_about_page.py` — the page names the three data sources:
  the gazette (核定案件一覽表), `gis.uro.taipei`, `twur.nlma.gov.tw`.
- [ ] 1.4 `tests/test_about_page.py` — the page links the release-diff report at
  `../docs/release-diff.html` (labelled 歷次公報差異) and the coverage report at
  `../docs/coverage-report.html`, both relative; the targets resolve on disk.
- [ ] 1.5 `tests/test_about_page.py` — the page carries the contact link
  `https://www.threads.com/@twhappypig`.
- [ ] 1.6 `tests/test_about_page.py` — the page is self-contained: no `<script>`,
  no stylesheet or image fetched from any origin, so it renders offline from
  `file://` (the release-diff report's own self-contained contract, applied to
  a hand-written page).
- [ ] 1.7 `tests/test_about_page.py` — the page states, in one sentence each,
  what the release-diff report establishes (why the project count moves) and
  what the coverage report establishes (the three proofs), so a reader can
  decide whether to open them.
- [ ] 1.8 `tests/test_about_page.py` — the page mentions the truncated-record
  rule in its ETL abstract: excluded and named, not repaired by inference.
- [ ] 1.9 `tests/test_about_page.py` — the page ties the dashboard's figures to
  the PUMA policy pages: links to the 都更政策 and 住宅政策 pages
  (`puma.taipei`) exist.
- [ ] 1.10 `tests/test_about_page.py` — the viewer header carries a 關於
  navlink to `about.html` in the markup; the 歷次公報差異 navlink is gone
  from the viewer header.
- [ ] 1.11 `tests/test_viewer_dashboard.py` — the dashboard header carries a
  關於 navlink to `about.html` in the markup (extend the existing
  two-links group; the 專案歷史圖 back link stays pinned).
- [ ] 1.12 `tests/test_release_diff_publish.py` — the report-link tests are
  rewritten for the new chain: the viewer header carries the 關於 link, the
  about page links the report by target `../docs/release-diff.html`, and the
  report's back link to the viewer is unchanged.
- [ ] 1.13 `tests/test_release_diff_publish.py` — the deploy record lists
  `viewer/about.html`, so `check_deploy.py` compares its served bytes
  (extend the existing artifact-list assertion).
- [ ] 1.14 `tests/test_about_page.py` — the about page's link into the reports
  survives the reports' regeneration: the generators' output paths are the
  ones the page links (`docs/release-diff.html`, `docs/coverage-report.html`
  — assert against the generators' own output path constants).

## 2. The about page and headers (implementation)

- [ ] 2.1 `viewer/about.html` — the page itself: zh_TW, four sections in order
  (授權, 資料來源與處理, 資料可信度, 聯絡), the same cream/charcoal/terracotta
  palette via inline `<style>` (no stylesheet file, so no cache-bust entry and
  nothing to rewrite), no script, relative links only, external links
  (`puma.taipei`, Threads) carry `rel="noopener"` and open in a new tab.
- [ ] 2.2 `viewer/about.html` — the ETL abstract: one short paragraph, plain
  words, the four sources, the similarity merge, the named-exclusions rule.
  Cite `docs/etl_process.html` as the full write-up by relative link.
- [ ] 2.3 `viewer/about.html` — the 資料可信度 section: one abstract sentence
  each for the two reports, their links, and the PUMA tie-in line naming
  都更政策 and 住宅政策 as the pages the dashboard supports.
- [ ] 2.4 `viewer/index.html` — the header's 歷次公報差異 navlink becomes
  關於 → `about.html`; the 政策儀表板 navlink is untouched.
- [ ] 2.5 `viewer/dashboard.html` — the header gains a 關於 navlink to
  `about.html` beside 專案歷史圖; `dashboard.js`'s `navDiff` string (unused
  since it was written) is removed or repurposed for the new link's label.
- [ ] 2.6 `viewer/deploy.json` — `viewer/about.html` joins the `artifacts` list.

## 3. Verification

- [ ] 3.1 The full suite passes (`python -m pytest`) — count and skip noted.
- [ ] 3.2 `node scripts/viewer_smoke.js` still passes (the header change must
  not disturb the smoke harness).
- [ ] 3.3 The page is opened from `file://` in a browser and from the published
  site after push: every link resolves, no console errors, no network request
  beyond the clicked external links.
- [ ] 3.4 `python scripts/check_deploy.py` reports about.html fresh after the
  push that publishes it.
- [ ] 3.5 `AGENTS.md`'s site description names the about page among the
  published pages if the layout section lists them (check; append only if the
  section does).
