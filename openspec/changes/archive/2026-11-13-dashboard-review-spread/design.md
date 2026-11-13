# Design: dashboard-review-spread

## Context

Actors: the policy reader, who opens `viewer/dashboard.html`; the maintainer,
who stated the chart on 2026-11-13. Domain event: none — no gazette, no
ingest, no payload change. System boundary: the browser page only. The
pipeline (PDF → ruled-table read → raw.tsv → cleanse → clean.tsv → similarity
merge → merged.tsv → projects.json + viewer) emits `projects.data.js`; this
change reads the two per-project figures the page already derives from it
(`review_years`, `review2_years`, both settled by `dashboard-review-time`) and
adds a second drawing of them.

Measured on the 2026-10-28 payload at `67f0f1c`, through the page's own
`flatten`:

| Population | Value |
| --- | --- |
| years of first approval, city view | 2002–2026, 25 years, no missing year, both intervals |
| years present in one interval and not the other, city view | none |
| fewest projects in one city year | 3 (2003) |
| longest `review_years` | 17.71 |
| longest `review2_years` | 21.39 |
| districts with at least one missing year (`review2_years`) | 12 of 12 |
| district-years (`review2_years`) | 235, of which 76 hold one project |

The user's three answers (2026-11-13) close the open points: 中位數 is the
default; the fan connects across a missing year; every year is drawn.

Measured through the harness on the changed page (task 4.3, same payload,
`--hash "#review=full"`), city view:

| Figure on the page | Value |
| --- | --- |
| years drawn | 25: one fan (three paths), 25 boxes, 25 year tooltips |
| medians and counts that differ between 中位數 and 完整 | 0 of 50 |
| years whose five values are out of order after rounding | 0 |
| 審議時間中位數 card under either view | 3.8 years, the same sub-line |
| 2026, both intervals (no project of 2026 has a later approval yet) | 1.8 / 2.8 / 3.7 / 5.1 / 17.7, n 32 |
| 2003, both intervals, the year with fewest projects | 0.6 / 0.6 / 0.6 / 0.8 / 0.9, n 3 |
| longest first-approval value | 17.7, in 2026 |
| longest pre-permit value | 21.4, in 2007 (0.8 / 1.0 / 1.6 / 4.3 / 21.4, n 18) |

## Goals / Non-Goals

**Goals:**

- A 完整 view that shows the shortest, 25th percentile, median, 75th
  percentile and longest value of both intervals per year, with the marks the
  user named.
- A switch whose state is linkable, with 中位數 unchanged and default.
- Every figure of the new view asserted on the rendered page.

**Non-Goals:**

- The derivation of `review_years` and `review2_years`, and the 審議時間中位數
  card. Neither is touched.
- A table view of the spread, a download, or a per-project drill-down.
- A new asset version. The cache-bust is derived from the dataset
  (`urtpe/viewer.py:_asset_version`), and no dataset moves here.

## Decisions

### D1 — One aggregate, two drawings

`reviewOf` already groups each interval's values by the first approval's year.
It keeps `median` and `projects` and adds `min`, `q1`, `q3`, `max` to each
year's row. The 中位數 drawing reads `median` as before; the 完整 drawing
reads all five. The `median` of a row comes from the page's existing
`median()`, not from the percentile function at p = 0.5: the two are the same
number mathematically, but `(a + b) / 2` and `a + 0.5 × (b − a)` can differ in
the last bit, and a tie at the rounding boundary would then show two medians
for one year. The spec requires the two views to agree, so one function owns
the figure.

Pure logic (percentile, the per-year summary) stays in the aggregate block of
`dashboard.js`; the drawing reads rows and holds no arithmetic beyond scales.

### D2 — The percentile is the rank-interpolated one (R type 7)

"Linear interpolation between the two nearest ranks": for sorted values
`s[0..n-1]` and a fraction `p`, `h = (n − 1) × p`, `lo = floor(h)`, and the
value is `s[lo] + (h − lo) × (s[lo + 1] − s[lo])`. This is the definition
spreadsheets call PERCENTILE.INC and the one whose p = 0.5 case is the
median the page already shows (the middle value, or the mean of the two middle
values). Alternatives: nearest-rank (no interpolation, the user ruled it
out); the (n + 1) × p variants (their median agrees, their quartiles do not,
and they need a rule for ranks outside the data). Rounding is the page's
existing one-decimal rule, `Math.round(v × 10) / 10`, applied to all five
values.

### D3 — The marks

One frame, one y scale from zero to the nice tick above the longest value of
either interval, in five steps: with the 中位數 view's four, 21.4 tops the axis
at 30 and a third of the plot is empty; with five it tops at 25. The colours stay with the entity: the first-approval interval
keeps `--fill`, the pre-permit interval keeps `--alt`, as in the 中位數 view
and its legend. The pair was run through the dataviz validator against the
panel surface: it passes the colour-vision and normal-vision floors (worst
adjacent ΔE 9.5 deutan, 27.8 normal); `--alt` is under 3:1 against the
surface, which the tooltip's figures and the shape difference (band against
box) relieve.

- Fan (pre-permit): the outer band is one closed path along the longest values
  and back along the shortest, filled at low opacity; the inner band the same
  between the 75th and 25th percentiles at a higher opacity; the median is a
  2px line. Paths use `M`, `L` and `Z` only. A year with no project adds no
  vertex, so the segment between its neighbours crosses it.
- Boxes (first approval), drawn over the fan: a 1.5px line from the shortest
  to the longest value; a box from the 25th to the 75th percentile, at most
  14px wide and never under 1px tall; a dot at the median in the panel colour
  with an ink outline, so it reads on the box. The box carries a panel-colour
  outline, the ring that separates it from the band beneath. The dot shrinks
  with the year's slot (radius 0.3 of the slot, between 2 and 3.5px): seen in
  the browser at a 284px plot, 25 full-size dots overprint into one bar.
- A scope with one year has a fan of zero width. It is drawn as a short band
  of the box's width at that year, so the interval stays visible.
- No direct value labels: the tooltip carries the figures, and five values on
  25 years would crowd the plot.

Each mark carries a class (`fan-range`, `fan-iqr`, `fan-median`,
`box-whisker`, `box-iqr`, `box-median`), which the harness counts.

### D4 — One tooltip per year, as a small table

The hover target is a transparent column over the full plot height, one per
year that holds a project, wider than any mark. Its tooltip is the year and a
table: one column per interval (the legend names, with the colour swatch), one
row per value — 最短, 第 25 百分位, 中位數, 第 75 百分位, 最長, 專案數. Six
short rows read down; two long interval names read across and may wrap. The
alternative, one line per interval with six numbers, needs a line about 570px
wide in English against a card that can be 300px.

Seen in the browser: an inline swatch is left on a line of its own when an
interval name wraps, so the swatch is pinned to the name's first line; and a
legend entry that wraps squeezed its swatch, so the swatch no longer shrinks.

`frame().show` already wraps each line in a `div` and accepts a node as a
line; `hover` gains a lazy form (a function that returns the lines) so the 25
tables are built on demand. An interval with no project in the year shows `—`
in its column.

### D5 — The switch is state, so it is in the hash

`state.review` is `"full"` or empty. `readHash` accepts only `review=full`;
`writeHash` writes the key only for 完整. The switch is a `role="group"` pair
of buttons with `aria-pressed`, placed under the card title. Using it writes
the hash and re-renders, as the district select does; focus returns to the
pressed button after the render, because the render replaces the card.

The card is built in `render`, not by `chartCard`, because its title, caption
and legend depend on the view. The legend in 完整 is two entries, each the
interval's name followed by what its marks mean.

### D6 — The harness reads the new view without inspecting geometry

`scripts/dashboard_smoke.js` gains: `reviewView`, `reviewSwitch` (label and
pressed state per button), `reviewTitle`, `reviewLegend`, `hash`; `spread`,
read from the 完整 tooltips by firing each hover handler and reading the
table; `reviewMarks`, the count of elements per mark class; and
`reviewPathCommands`, the set of path command letters in the chart. A
`--press <label>` option fires the click handler of the switch button with
that label before extraction. Counts and command letters are structure, not
coordinates, so the harness's rule — the figures come from what the reader
sees — holds.

## Risks / Trade-offs

- **The y scale follows the longest value.** One 21-year project stretches the
  axis and compresses the medians near 3 and 4. That is the fact the view
  exists to show; the 中位數 view remains for reading the medians.
- **Min-to-max bands follow single projects.** With few projects per year the
  outer band is an outlier trace. The caption keeps the warning, and the
  tooltip gives the count.
- **A cached stylesheet.** `dashboard.css` changes and the asset version does
  not, so a browser can hold the old stylesheet with the new script until its
  cache expires. The page then shows an unstyled switch and a plain tooltip
  table; both still work. A hand-edited version would be rewritten by the next
  emission and would break `test_the_dashboard_and_the_viewer_agree_on_the_version`.
- **Whole-page render on a switch.** It matches the district select. The cost
  is one render of a page that renders in a few milliseconds.
