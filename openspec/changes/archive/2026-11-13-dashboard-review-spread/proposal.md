# Proposal: dashboard-review-spread

## Why

The policy reader of the dashboard's 審議量能與時程 section sees one figure per
year and interval: the median. `dashboard-review-time` (archived 2026-11-13)
settled how the two intervals are derived, and the user asked on the same day
for the spread behind those medians: a year whose median reads 3.8 says
nothing about whether its projects took between 3 and 5 years or between 1 and
20. Measured on the 2026-10-28 payload at `67f0f1c`: the city view covers
2002–2026 with no missing year, the longest first-approval interval is 17.71
years and the longest pre-permit interval 21.39, against medians near 3 and 4.
The median chart cannot show that, and its caption only warns that "years with
few projects move a lot".

The user stated the design on 2026-11-13 and answered three open points before
the change was opened: the page opens on the median chart as it does today;
the fan connects across a year with no project (all 12 districts have such
years); and every year is drawn, however few projects it holds (76 of 235
district-years hold one project).

## What Changes

- The review chart gets a two-way switch, 中位數 / 完整 (Median / Full). 中位數
  is the chart the page shows today, unchanged, and is the default.
- 完整 shows the spread of both intervals by year of first approval:
  - `review2_years` (application to the approval before the building permit)
    as a continuous fan: a light band from the shortest to the longest value,
    a darker band from the 25th to the 75th percentile, and the median as a
    line. Straight segments between years, no smoothing; a year with no
    project is crossed by the segment between its neighbours.
  - `review_years` (application to the first approval) overlaid as one box per
    year: a thin line from the shortest to the longest value, a box from the
    25th to the 75th percentile, and a dot at the median.
- Percentiles are read by linear interpolation between the two nearest ranks
  and rounded to one decimal; the shortest and longest values are shown to one
  decimal too.
- In 完整 one tooltip per year lists the five values and the project count for
  both intervals.
- The chart title, the caption and the legend follow the view, in both
  languages.
- The switch state lives in the URL hash (`review=full`), beside the district
  and the language, so a view stays linkable.
- Not changed: how `review_years` and `review2_years` are derived, the 審議時間
  中位數 card, the median view's figures and tooltips.

No part of this change is gated on a POC: it reads figures the page already
derives. The three measurements above stand in for one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `policy-dashboard`: one requirement is added (the review chart's 完整 view:
  the switch, the five values, the marks, the tooltip, the text). The
  requirement "The view is linkable and bilingual" is modified to name the
  review view as a third item of linked state; its three scenarios are carried
  and one is added. The requirement "Review time runs from the earliest
  application to the first approval, total time to completion" is not touched.

## Impact

- `viewer/dashboard.js`: `reviewOf` (five values per year beside the median),
  `reviewChart` (the 完整 drawing), the review card (switch, title, caption,
  legend by view), `state` / `readHash` / `writeHash`, the strings in both
  languages.
- `viewer/dashboard.css`: the switch and the tooltip table.
- `scripts/dashboard_smoke.js`: reads the review view, the switch, the title,
  the legend, the 完整 tooltips and the mark classes; a `--press` option fires
  the switch.
- `tests/test_dashboard_rules.py`: one test per new scenario.
- `docs/DashboardNUXUI.md` §14, `docs/portal_operations_log.md`, `AGENTS.md`
  (the collected-test count).
- No pipeline code, no data file, no payload field.
