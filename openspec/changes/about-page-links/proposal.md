# Proposal: about-page-links

## Why

Three follow-ups to the 關於 page, all reported together after the page
shipped:

1. **The doc pages are one-way doors.** `docs/etl_process.html`,
   `docs/release-diff.html` and `docs/coverage-report.html` are reachable
   from the about page, but none carries a 關於 link back, and the
   release-diff report's only back link is 回專案歷史圖 — a path that now
   bypasses the about page entirely. A reader who lands on a report from a
   search result has no route to the license, the sources or the contact.
2. **The 關於 link sits inconsistently.** The viewer header carries
   政策儀表板 then 關於; the dashboard carries 專案歷史圖 then 關於. The user
   asks for a single rule: 關於 is the rightmost link in every header, and
   the other site links (政策儀表板, 專案歷史圖) sit to its left in the
   same order as today. Also: the three doc pages carry the 關於 back link
   at their header's right edge, replacing the release-diff report's
   回專案歷史圖 (the about page already links the viewer, so the viewer
   stays reachable in one hop).
3. **The about page wears a foreign palette.** It was built with the
   viewer's cream/terracotta tokens, while the three doc pages share a
   different, complete design system: slate/white ground, `#0f172a` ink,
   hairline `#cbd5e1`, blue `--info` links, bordered rounded cards with
   tinted variants, `15px/1.65 system-ui` body with Noto Sans TC, a
   `prefers-color-scheme: dark` block, and the `.sub`/`.lead`/`.ttl small`
   text hierarchy. The user asks the about page to use that design system
   instead — one system across all four pages in `docs/` and `viewer/`'s
   about page, dark-mode included.

Actors: the reader moving between the four pages; the two report generators
(`release_diff_report.py`, `coverage_report.py`) whose header markup changes;
the pinned tests in `tests/test_release_diff_publish.py` (the back-link
contract) and `tests/test_about_page.py` (self-containment, links).

## What Changes

- **The three doc pages gain a 關於 back link** at the header's right:
  `docs/etl_process.html` (hand-written) and the two generated reports (via
  their generators). The release-diff report's `回專案歷史圖` back link is
  removed — its replacement is `../viewer/about.html`, and the viewer
  remains one hop away through it.
- **The about page adopts the docs design system**: the slate/white tokens,
  the dark-mode block, the card/sub/lead hierarchy, and the docs link
  colouring, replacing the viewer's cream palette. Content is unchanged; the
  scope statement from `about-page-scope` stays.
- **Header order pinned by test**: in every header, 關於 is the last
  (rightmost) navlink; the viewer's 政策儀表板 and the dashboard's
  專案歷史圖 keep their current positions to its left.

## Capabilities

### Modified Capabilities

- `viewer-related-links`: the release-diff back link now points at the about
  page; the three doc pages carry the 關於 link; the header ordering rule.

## Impact

- Code: `viewer/about.html` (styles only), `docs/etl_process.html` (header
  link), `scripts/release_diff_report.py` + `docs/release-diff.html` and
  `scripts/coverage_report.py` + `docs/coverage-report.html` (header link,
  regenerated), `tests/test_release_diff_publish.py`,
  `tests/test_about_page.py`.
- Note: the working tree's `docs/release-diff.html` and
  `docs/coverage-report.html` already carry uncommitted regenerations
  (2026-11-12 02:10, made from the live 680-project dataset after the
  revoke-dead-schedule and 懷生928 merges). This change regenerates them
  again with the new header link; the count changes ride along in the same
  commit and are attributed there.
- Not touched: pipeline, payload, viewer headers (already conforming).
