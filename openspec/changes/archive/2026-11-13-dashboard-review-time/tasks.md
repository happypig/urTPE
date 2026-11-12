# Tasks: dashboard-review-time

## 1. Tests first (test-first gate — every task here is checked before any task in groups 2–4)

- [x] 1.1 `scripts/dashboard_smoke.js` — print the review chart's caption as
  `reviewCap` so the 概要 notice is readable; no other harness change.
- [x] 1.2 `tests/test_dashboard_rules.py` — a `node()` fixture helper that binds
  a node to a case id (`links.taipei`) with a stage label and gazette date, and
  a `project()` that accepts several cases; the existing single-case helper
  keeps working.
- [x] 1.3 `tests/test_dashboard_rules.py` — the four carried scenarios under the
  new rule: 2015-01-01 → 2018-01-01 reads 3.0; 核定 before 申請 is absent and
  excluded from medians and chart; the even-count median 1, 2, 3, 10 shows 2.5;
  each chart year carries a project count for each interval.
- [x] 1.4 `tests/test_dashboard_rules.py` — the eight added scenarios: the
  application comes from the first approval's own case (2.0, not 6.0); a 擬訂
  node after an earlier 變更 is the first approval; 概要-only projects count in
  the project card, are left out of both medians, and the caption names them;
  the 萬隆519 shape reads 5.0 and 9.0, ending before the permit; no permit ends at the latest approval
  (5.0 against 3.0); a permit before every node leaves line 2 absent and line 1
  shown; the card shows the pre-permit median and names the first-approval
  median; joined cases take the earliest application.
- [x] 1.5 `tests/test_dashboard_rules.py` — the dotted-ROC test asserts through
  idle years with a national 核定 date (D7).
- [x] 1.6 Run `python -m pytest tests/test_dashboard_rules.py -q` and record
  the failing set: the new review tests must fail against the unchanged page,
  the rest must stay green. (Recorded: 11 failed, 36 passed — the eleven are
  the review scenarios; `test_approval_before_application` passes on the old
  page too, as both rules leave it absent.)

## 2. Implementation

- [x] 2.1 `viewer/dashboard.js` derivation: eligible nodes (track ≠ 事業概要),
  first approval (擬訂 first, else earliest), the case lookup through
  `links.taipei` → `links.case_milestones` with the node's own milestones as
  fallback, application = min(申請計畫日期, 申請權變日期), approval date =
  min(核定日期, 權變核定日期) else the node date; line 1, line 2 (permit =
  earliest 建照核發日期 across the project's cases), total from the new
  application; `only_outline` flag per project.
- [x] 2.2 `viewer/dashboard.js` aggregation: `median_review1`,
  `median_review2`, `outline_only` count per scope; `reviewOf` returns both
  series keyed by the first approval's year.
- [x] 2.3 `viewer/dashboard.js` render: `reviewChart` draws two series with a
  legend (first approval = `ok`, pre-permit = `alt`), tooltips naming the
  interval; the 審議 card shows the pre-permit median with the first-approval
  and total medians in its sub-line; the caption carries the 概要 count when
  non-zero; strings and the definitions block in both languages.
- [x] 2.4 Run `python -m pytest tests/test_dashboard_rules.py tests/test_viewer_dashboard.py -q`
  green; `node scripts/dashboard_smoke.js --payload viewer/projects.data.js --preset`
  renders the live payload without a throw.

## 3. Evidence

- [x] 3.1 Run the full suite; refresh the collected-test count in `AGENTS.md`.
- [x] 3.2 Measure both medians, their counts and the 概要 count on the current
  payload through the harness and record them in design.md's table (note the
  payload commit; if the D5 ingest has landed, the 675-project figures).
- [x] 3.3 Append to `docs/DashboardNUXUI.md` §14 (newest first, a `14.-3`
  entry dated 2026-11-13) and to `docs/portal_operations_log.md` at the bottom:
  the rule, the measured figures, the seven ledger entries and their fix
  commit, D4's two unfixed items.

## 4. Archive

- [x] 4.1 `openspec validate dashboard-review-time --strict` — clean.
- [x] 4.2 Copy `openspec/` to a temp dir and run the archive there; expect
  `+ 0, ~ 1, - 0`, no missing-scenario abort, and the synced requirement
  carrying all twelve scenarios.
- [x] 4.3 Run the real archive and commit as
  `openspec: archive dashboard-review-time and sync its spec delta`, path-limited.
