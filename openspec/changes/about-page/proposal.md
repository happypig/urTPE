# Proposal: about-page

## Why

The site's readers now include policy readers, not only analysts. The
dashboard (`viewer/dashboard.html`, merged 2026-11-12) was built to support the
PUMA 都更政策 and 住宅政策 pages, and a policy reader who lands on it has no
answer to three questions the site can answer: who owns this and may I reuse
it, where does the data come from and how was it made, and how far can the
numbers be trusted.

The pieces exist but are unreachable from the pages a policy reader opens:

- The license is stated nowhere on the site.
- The ETL write-up (`docs/etl_process.html`) is full-length developer
  documentation; a policy reader needs its abstract, not its §3.1.
- `docs/release-diff.html` (歷次公報差異) and `docs/coverage-report.html`
  (資料覆蓋度報告) are reachable only through the viewer's header link, and
  the coverage report is not linked from any page at all.
- The contact address lives only in this repository's git log.

The current 歷次公報差異 header link is the wrong shape for this: it is one
report of four things a reader needs, named in pipeline jargon. It is replaced
by an 關於 page that carries all four, with the reports one click away.

Actors: the policy reader arriving from PUMA.taipei, the site maintainer, and
the two report generators (`scripts/release_diff_report.py`,
`scripts/coverage_report.py`) whose pages the about page must keep pointing at
by stable relative paths.

## What Changes

- **A new published page, `viewer/about.html`.** zh_TW, static, no script,
  relative links throughout so it works from `file://` like every other page.
  It carries, in this order:
  1. 授權 — 本站採用 CC BY 4.0 授權, scoped to the site's own pages and the
     emitted dataset; one separate line stating that the upstream government
     data (the gazette PDFs and both portals) follows its own terms.
  2. 資料來源與處理 — the gazette PDF (臺北市都市更新核定案件一覽表), the
     Taipei platform (`gis.uro.taipei`), the national portal
     (`twur.nlma.gov.tw`), and a concise abstract of the ETL flow: extract
     from the PDF's ruled table, cleanse, merge repeat approvals of the same
     unit by similarity, enrich from the two portals, emit the per-project
     history graph the pages render. Named exclusions and gates stated in one
     sentence, not a section.
  3. 資料可信度 — concise abstracts of 歷次公報差異 (why the project count
     moves between gazettes; the report re-reads every archived PDF) and
     資料覆蓋度報告 (the three coverage proofs: no project outside both
     rosters, the record partition complete and disjoint, every platform case
     bound to a node), each linking its full report, plus one line tying the
     dashboard's figures to the PUMA 都更政策 and 住宅政策 pages it supports.
  4. 聯絡 — https://www.threads.com/@twhappypig .
- **The viewer header's 歷次公報差異 link is replaced by 關於.** The release-diff
  report stays reachable from the about page. This changes a pinned contract
  (`tests/test_release_diff_publish.py`) and a live spec requirement
  (`viewer-related-links`); the delta carries the requirement's four scenarios
  and its body.
- **The dashboard header gains 關於** beside 專案歷史圖, so a reader who lands
  on the dashboard — the page policy readers arrive at — reaches the about
  page from there too.
- **`viewer/deploy.json` names `viewer/about.html`**, so `check_deploy.py`
  compares its served bytes against the committed build like every other
  artifact. The page carries no script and no stylesheet of its own, so it
  needs no cache-bust entry.

## Capabilities

### New Capabilities

(none — the about page is a second property of `viewer-related-links`' scope:
how the site's pages link to each other.)

### Modified Capabilities

- `viewer-related-links`: the release-diff link moves from the viewer's header
  to the about page, and a new requirement pins the about page's content
  contract — license, sources, report links, contact, zh_TW, relative paths.

## Impact

- Code: `viewer/about.html` (new), `viewer/index.html` (header link),
  `viewer/dashboard.html` (header link), `viewer/deploy.json` (artifact list),
  `tests/test_release_diff_publish.py` and `tests/test_viewer_dashboard.py`
  (the pinned link contracts).
- Not touched: the pipeline, the payload, the report generators. The about
  page is hand-written like the headers are; the reports stay generated pages.
- Not gated on POC findings: no parsing or merge behaviour changes.
- Deployment: the page ships when `main` is pushed; `check_deploy.py` covers
  it from the first publish.
