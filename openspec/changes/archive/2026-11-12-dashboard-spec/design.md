## Context

The page shipped on 2026-11-11 (`94cd3e8`, a different session) and closed its
publishing contracts on 2026-11-12 (`ee389c2`). It is a hand port of the Claude
Desktop artifact "Taipei urban renewal: process duration"
(`https://claude.ai/artifact/DMpCPHZGqougawwmvMxz2H`); the artifact's 14-column
derivation was rebuilt in the repo and matched byte-for-byte on 682 rows on
2026-11-09. So the shipped `viewer/dashboard.js` is the reference implementation
and the delta in `specs/policy-dashboard/spec.md` describes exactly what it does.
See proposal.md — Why for the motivation.

Actors: the dashboard render path (`viewer/dashboard.js`, plain JS, one IIFE, no
framework, no build), the emission path (`urtpe/viewer.py` rewriting `?v=` into
every page that references the site's assets), the payload
(`viewer/projects.data.js`, the same `window.PROJECTS` the viewer reads), and
the node smoke harness (`scripts/viewer_smoke.js`) whose shape the new test
harness follows. System boundary unchanged: static `file://` bundle, published to
GitHub Pages from `main`, verified by `scripts/check_deploy.py`.

Measured on the 2026-10-28 payload (680 projects / 1,444 records) on
2026-11-12, by re-running the page's rules in Python (the method is in
`docs/DashboardNUXUI.md` Appendix A; the figures below are the evidence the
scenarios were written against, not spec content):

| Rule | Measured |
| --- | --- |
| Stage | 已完工 406 · 施工中 127 · 已核定未領建照 122 · 已領建照未開工 25 |
| Flag (unfinished 274) | 推進中 231 · 停滯3至5年 33 · 停滯5年以上 10 |
| Review years | n 679, median 3.67; 1 project with first approval before application (absent) |
| Completion sources (406) | `Ulic_Date`+使用核發日期+`permit.date` 262 · `permit.date` only 74 · `Ulic_Date`+`permit.date` 40 · `Ulic_Date`+使用核發日期 18 · 使用核發日期+`permit.date` 9 · `Ulic_Date` only 2 · 使用核發日期 only 1 |
| Public land | 346 projects hold any; 2 exceed `Base_Area` (capped) |
| Date forms | ROC dotted only in `milestones_national` (2,981 values); case milestones 22,842, nodes 1,444, `permit.date` 385, `Eng_Start_Date` 494, `Ulic_Date` 322 — all Gregorian |
| Districts | 12 |

## Goals / Non-Goals

**Goals:**

- Give the dashboard a capability of its own, ADDED-only, so the archive creates
  `openspec/specs/policy-dashboard/spec.md` with its Purpose and touches no other
  spec — the scenario-name guard (`findMissingCurrentScenarios`) has nothing to
  compare and nothing to drop.
- Pin every derivation rule with a test over a fixture payload, so a regression
  to a different stage order, a different clock, or a different application
  source fails a test and not only a reader.
- Record the artifact as provenance in one tracked place.

**Non-Goals:**

- No change to `viewer/dashboard.js`, `dashboard.html` or `dashboard.css`. The
  code is the reference; the spec follows it, including the two dead reads in D2.
- No MODIFIED delta. The header links and the 關於 chip stay in
  `viewer-related-links`; the derived cache-bust of `index.html` stays in
  `pdf-tsv-extraction`; the artifact-list rule stays in `deployment-verification`.
  The new capability restates the dashboard-specific consequences of those
  rules (its own assets' version, its three deploy entries) because the tests in
  `tests/test_viewer_dashboard.py` pin exactly those, and a scenario with no
  home is a scenario that drifts.
- No chart geometry in the spec: bar widths, tick choice and tooltip placement
  are rendering, not contract. The one drawing rule the spec keeps — the review
  line is point to point — is a statement about what the data supports.
- No fix for the D2 gap in this change.

## Decisions

- **D1 — One capability, not one per section.** The four sections share one
  flatten step (one row per project) and one scope rule; splitting them would
  restate the stage and flag rules four times. Alternative considered: fold the
  dashboard into `viewer-related-links`, where its header already lives. Rejected:
  that spec is about site links and the about page, and the archive of a
  MODIFIED delta there would have to carry every scenario of the requirement it
  replaces.

- **D2 — Spec the source list as the code has it, and record the dead reads
  here.** The page reads 開工日期 and 使照核發日期 from each case's milestones
  (`links.case_milestones[*]`), and the current payload never carries either
  key there: 0 of 1,444 case entries. They live at the project level, in
  `links.milestones_taipei` (開工日期 in 508 projects, 使照核發日期 in 332),
  which the page does not read. Measured consequence: 0 projects misclassified
  on completion (the other three sources cover every one) and 3 projects whose
  Taipei 開工日期 the page does not see, shown as 已領建照未開工 or
  已核定未領建照 while the city records a start
  (`中正區-永昌段四小段-132-2地號等15筆`, `士林區-光華段四小段-282地號等2筆`,
  `大安區-龍泉段二小段-771地號等27筆`). The spec states the sources the code
  lists, because that is the observable rule today; the stage scenarios are
  written with `Eng_Start_Date` and `Ulic_Date` so they pass against the shipped
  code. Adding `milestones_taipei` to the start and completion sources is a
  behavior change for a follow-up change, with its own measurement — the notes'
  §10 rule 4 ("construction stages read from the project level") argues for it.
  Alternative considered: fix it inside this change. Rejected: a spec-restore
  change that also moves three projects' stage is two changes under one name.

- **D3 — Scenarios name payload fields, not functions.** `Ulic_Date`,
  `Eng_Start_Date`, `links.permit.date`, `published_date` are the external data
  contract the page consumes; `flatten`, `kpiOf`, `pipelineOf` are not named
  anywhere in the delta. The page's helpers may be renamed; the fields are what
  the pipeline emits.

- **D4 — Tests drive the real page through node, and read the rendered DOM.**
  `scripts/dashboard_smoke.js` loads `viewer/dashboard.js` in a stub DOM after
  the shape of `scripts/viewer_smoke.js`, with `window.PROJECTS` preset so the
  page's own `fetch` path is skipped, and prints the rendered takeaway, the six
  cards, the pipeline rows and both tables as JSON; `tests/test_dashboard_rules.py`
  writes a fixture payload per scenario and asserts on that JSON, and skips when
  node is absent, as `tests/test_viewer_degrades.py` does. The stub needs the
  geometry the charts call and the viewer harness does not stub:
  `clientWidth`, `offsetWidth`, `getComputedTextLength` (text width falls back
  to 8px per character when it returns 0), plus `location.hash`,
  `history.replaceState` and `URLSearchParams`. Alternative considered: a
  Python re-implementation of the rules tested against the page's output on the
  real payload. Rejected: it tests the re-implementation, and the real payload
  cannot stage the edge cases (a date after 統計至, approval before
  application) without editing it. Alternative considered: the `> POC:` escape
  hatch, as `sync-specs-to-s41-fixes` used. Rejected: that change had its pins
  already; this one has none for the rules.

- **D5 — The borrowed-version and `file://` scenarios are tested through a
  stubbed `fetch`.** The harness can present `index.html` text with a `?v=` and
  record the `src` the page sets on the script it appends, or make the fetch
  reject and assert the plain path. No network, no server.

- **D6 — Measured figures stay in this document.** The spec's scenarios use
  small fixtures with round numbers; the corpus figures above are the evidence
  that the rules as written are the rules that produced the live page, and they
  will be stale at the next gazette. A reader who wants today's numbers opens
  the page.

## Risks / Trade-offs

- [The archive creates the main spec from the delta's `## Purpose`; a delta
  without it leaves a `TBD` placeholder] → the delta opens with the Purpose;
  task 3.1 runs `openspec validate --strict`, which reports a Purpose shorter
  than 50 characters.
- [A test asserts rendered text, so a label edit breaks it] → tests match
  numbers and structural facts (row order, link targets, `lang` attribute),
  and the few sentences they match (the two empty-list sentences, the
  load-failure sentence) are themselves spec content.
- [The D2 follow-up, once done, moves 3 projects and changes the stage
  scenarios' source list] → that change carries a MODIFIED delta with every
  scenario of the stage requirement; the risk is the ordinary one and the
  guard note in AGENTS.md covers it.
- [The suite count in AGENTS.md goes stale] → task 3.3 refreshes it with
  `--collect-only`.
