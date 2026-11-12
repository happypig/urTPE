# Tasks: dashboard-spec

## 1. Tests first (test-first gate — every task here is checked before any task in groups 2–3)

- [x] 1.1 `scripts/dashboard_smoke.js` — a node harness after `scripts/viewer_smoke.js`:
  loads `viewer/dashboard.js` in a stub DOM with `window.PROJECTS` preset from the
  payload file given on the command line, an optional `--hash` argument, and a
  `fetch` stub that serves a given `index.html` text or rejects; stubs the
  geometry the charts call (`clientWidth`, `offsetWidth`,
  `getBoundingClientRect`, `getComputedTextLength`), `location.hash`,
  `history.replaceState`; prints as JSON the document `lang`, the scope line,
  the takeaway sentence, the six cards, the pipeline rows, the approvals and
  review series, both tables (cells and link targets), the definitions block,
  and the `src` the page set on the dataset script. Exits non-zero when the
  page throws.
- [x] 1.2 `tests/test_dashboard_rules.py` — fixture payloads written per test
  (as `tests/test_viewer_degrades.py` does), `pytest.skip` when node is
  absent; stage requirement: one test per scenario (completion decides; start
  without completion; permit without start; approved only; the node's stage
  label does not decide).
- [x] 1.3 `tests/test_dashboard_rules.py` — idle requirement: 5.0 years flags
  停滯5年以上 and counts in the card; 3.0 flags 停滯3至5年; 已完工 never flagged
  and absent from the watchlist; the same payload rendered under two different
  fake "today" clocks gives identical idle years.
- [x] 1.4 `tests/test_dashboard_rules.py` — dates requirement: `107.02.08`
  reads as 2018-02-08; `2026/2/30` is absent; a date after `published_date` is
  absent and neither sets a stage nor shortens idle time.
- [x] 1.5 `tests/test_dashboard_rules.py` — review requirement: 3.0 years from
  2015-01-01 to 2018-01-01; approval before application is absent and excluded
  from the median and the chart; the even-count median 1, 2, 3, 10 shows 2.5;
  each review-chart year carries its project count.
- [x] 1.6 `tests/test_dashboard_rules.py` — approvals requirement: one 擬訂 and
  one 變更 node in 2020 count one each; an undated node counts in no year.
- [x] 1.7 `tests/test_dashboard_rules.py` — households / land requirement: the
  share of site is capped at 100.0; the households card shows 50 split 30 / 20
  across 施工中, 已領建照未開工 and 已完工 fixtures; a 已完工 project's
  `Welfare_Area` still counts with a project count of 1.
- [x] 1.8 `tests/test_dashboard_rules.py` — scope requirement: under
  `#district=萬華區` the cards and both tables cover 萬華區 only while the
  by-district series still list every district; an unknown district renders the
  city view.
- [x] 1.9 `tests/test_dashboard_rules.py` — tables requirement: the watchlist
  orders 6.8 before 4.2 and links each name to `index.html#project=<project_id>`;
  fourteen public-land projects yield twelve rows, largest first; an empty
  watchlist shows 此範圍內沒有停滯三年以上的未完工專案。 and no rows.
- [x] 1.10 `tests/test_dashboard_rules.py` — view requirement:
  `#district=萬華區&lang=en` renders English stage names with `lang="en"`; no
  hash renders Traditional Chinese with `lang="zh-Hant"`; the definitions block
  follows the language and names the 3- and 5-year convention.
- [x] 1.11 `tests/test_dashboard_rules.py` — page requirement: two payloads with
  different projects render different cards (no literal figure); `index.html`
  text naming `projects.data.js?v=abc` makes the page request
  `projects.data.js?v=abc`; a rejecting fetch makes it request the plain path;
  a payload with no project list shows 無法載入 projects.data.js。. The deploy
  record, the derived version on the page's own assets and the unversioned
  reference report are already pinned by `tests/test_viewer_dashboard.py` —
  cite those tests, do not duplicate them.

## 2. Evidence — the delta describes the shipped code (no writes under `viewer/`)

- [x] 2.1 Run `python -m pytest tests/test_viewer_dashboard.py tests/test_dashboard_rules.py -q`
  and require green against the unchanged `viewer/dashboard.js`; a red test here
  means the delta, not the page, is wrong — fix the scenario.
- [x] 2.2 Re-run the measurement in design.md's table on the current
  `data/projects.json` and confirm the stage, flag, review and completion-source
  figures (or update the table with the new payload date if a gazette landed).
- [x] 2.3 Confirm the D2 gap is still 0 completion / 3 start projects, and
  record the three `project_id`s in the notes entry of 2.4 as a follow-up
  candidate, not as a defect of this change.
- [x] 2.4 Append to `docs/DashboardNUXUI.md` §14 (revision record, newest
  first, so a `14.-2` entry dated 2026-11-12) one entry naming the artifact
  URL as the provenance of the port, commit `94cd3e8`, this change, and the D2
  gap. Append to `docs/portal_operations_log.md` at the bottom.

## 3. Archive

- [x] 3.1 `openspec validate dashboard-spec --strict` — clean, Purpose accepted.
- [x] 3.2 Copy `openspec/` to a temp dir and run `openspec archive dashboard-spec`
  there; expect `+ 10, ~ 0, - 0` with no missing-scenario abort; confirm the
  created `specs/policy-dashboard/spec.md` carries the Purpose and no `TBD`,
  and diff it against the delta.
- [x] 3.3 Run the real archive; refresh the collected-test count in `AGENTS.md`
  with `python -m pytest --collect-only -q | Select-Object -Last 1`; commit as
  `openspec: archive dashboard-spec and sync its spec delta` with the two new
  files, the two docs appends and the archived change — path-limited, so
  another session's staged files stay theirs.
