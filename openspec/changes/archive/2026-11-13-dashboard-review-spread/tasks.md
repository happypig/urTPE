# Tasks: dashboard-review-spread

## 1. Tests first (test-first gate — every task here is checked before any task in groups 2–4)

- [x] 1.1 `scripts/dashboard_smoke.js` — print `reviewView`, `reviewSwitch`,
  `reviewTitle`, `reviewLegend`, `hash`, `spread` (the 完整 tooltips read as
  year → interval → value), `reviewMarks` and `reviewPathCommands`; add
  `--press <label>`. The existing output keys keep their meaning.
- [x] 1.2 `tests/test_dashboard_rules.py` — the thirteen scenarios of the
  added requirement: the default view; the full view selected through the
  switch; percentiles on 1.0, 3.0, 4.0, 8.0; a year with one project; the
  tooltip with both intervals and different counts; an interval absent from a
  year; agreement of the two views on median and count; straight segments and
  one box per year; a missing year crossed; the card under both views; the
  English text; the empty scope; the district scope.
- [x] 1.3 `tests/test_dashboard_rules.py` — the added scenario of the modified
  requirement: `#district=萬華區&review=full` renders 完整 for the district,
  pressing 中位數 leaves `#district=萬華區`, an unknown `review` value renders
  中位數.
- [x] 1.4 Run `python -m pytest tests/test_dashboard_rules.py -q` and record
  the failing set: the new tests fail against the unchanged page, the rest
  stay green. (Recorded: 15 failed, 47 passed — the fifteen are the new
  tests, the thirteen added scenarios, the modified requirement's added one,
  and the 概要 notice under 完整.)

## 2. Implementation — aggregate (pure logic)

- [x] 2.1 `viewer/dashboard.js` — a percentile function (D2) and `reviewOf`
  rows carrying `min`, `q1`, `median`, `q3`, `max`, `projects`; `median` still
  from `median()` (D1).

## 3. Implementation — page (adapter)

- [x] 3.1 `viewer/dashboard.js` — `state.review`, `readHash`, `writeHash` (D5).
- [x] 3.2 `viewer/dashboard.js` — the 完整 drawing in `reviewChart`: fan,
  boxes, year columns with the table tooltip, the single-year case (D3, D4);
  the 中位數 drawing untouched.
- [x] 3.3 `viewer/dashboard.js` — the review card: switch, title, caption and
  legend by view, strings in both languages; focus returns to the pressed
  button.
- [x] 3.4 `viewer/dashboard.css` — the switch and the tooltip table.
- [x] 3.5 Run `python -m pytest tests/test_dashboard_rules.py tests/test_viewer_dashboard.py -q`
  green; `node scripts/dashboard_smoke.js --payload viewer/projects.data.js --preset --hash "#review=full"`
  renders the live payload without a throw.

## 4. Evidence

- [x] 4.1 Look at the rendered page in a browser, both views, both languages,
  city and one district, at a wide and a narrow width; fix what the look
  finds. (Served over 127.0.0.1; four fixes, recorded in design.md D3 and D4.)
- [x] 4.2 Run the full suite (`python -m pytest`); refresh the collected-test
  count in `AGENTS.md`. (1329 passed, 1 skipped; 1330 collected. The count in
  `AGENTS.md` read 1310 and was already five behind before this change.)
- [x] 4.3 Measure the city view's 完整 figures through the harness (latest
  year and the year of the longest value, both intervals) and record them in
  design.md, with the payload commit.
- [x] 4.4 Append to `docs/DashboardNUXUI.md` §14 (newest first, a `14.-4`
  entry dated 2026-11-13) and to `docs/portal_operations_log.md` at the bottom
  (§44).

## 5. Archive

- [x] 5.1 `openspec validate dashboard-review-spread --strict` — clean.
- [x] 5.2 Copy `openspec/` to a temp dir and run the archive there; expect
  `+ 1, ~ 1, - 0`, no missing-scenario abort; compare the synced
  `policy-dashboard` spec against the live one and confirm the only changes
  are the added requirement and the modified one's new sentences and scenario.
- [x] 5.3 Commit the implementation as `feat:`, path-limited; run the real
  archive and commit as
  `openspec: archive dashboard-review-spread and sync its spec delta`,
  path-limited; push `main`; run `python scripts\check_deploy.py`.
