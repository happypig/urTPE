## ADDED Requirements

### Requirement: The review chart switches between the medians and the full spread

The review chart SHALL offer two views, selected by a two-way switch in the
chart's own card: 中位數 (in English "Median") and 完整 ("Full"). 中位數 SHALL
be the view shown when the reader has selected none; it is the chart the
requirement "Review time runs from the earliest application to the first
approval, total time to completion" describes, with the same figures, the same
tooltips, the same title, caption and legend. The switch SHALL mark the view
in use as pressed, and using it SHALL change the chart and nothing else on the
page: the 審議時間中位數 card, its sub-line and every other figure read the
same under either view.

完整 SHALL show, for every year of first approval that holds at least one
project with the interval, five values of each interval: the shortest, the
25th percentile, the median, the 75th percentile and the longest. A percentile
SHALL be read by linear interpolation between the two nearest ranks of the
year's sorted values — with n values the p-th percentile sits at rank
(n − 1) × p counted from zero, and takes the value at the rank below plus the
fractional part of the rank times the step to the value above — and every one
of the five values SHALL be rounded to one decimal. The median so read SHALL
equal the median the 中位數 view shows for the same year and interval, and the
project count SHALL be the same count.

The two intervals SHALL be drawn on one frame and one vertical scale, each by
its own marks:

1. **To the approval before the building permit** (自申請至建照核發前之核定), as
   a continuous fan: a light band from the shortest to the longest value, a
   darker band from the 25th to the 75th percentile, and the median as a line.
2. **To first approval** (自申請至首次核定), overlaid as one box per year: a
   thin line from the shortest to the longest value, a box from the 25th to
   the 75th percentile, and a dot at the median.

The fan SHALL be drawn point to point, with straight segments between years
and no smoothing, because a curve would suggest values the data lacks. A year
that holds no project SHALL be crossed by the straight segment between the two
nearest years that hold one, and SHALL carry no box and no tooltip. Every year
that holds a project SHALL be drawn, however few it holds: with one project
the five values are equal, the fan narrows to a point and the box to its dot.

In 完整 each year SHALL carry one tooltip that names the year and lists, for
both intervals, the five values and the project count. An interval that has no
project in that year SHALL show no value there rather than a zero.

The chart's title, caption and legend SHALL follow the view, in the current
language. In 完整 the title SHALL say that the chart shows the spread and not
the median alone (審議年數分布，依首次核定年度); the caption SHALL say what
the five values are and SHALL keep the warning about years with few projects
and the count of projects with only a 事業概要 approval; and the legend SHALL
name each interval together with what its marks mean. When the scope holds no
review time, 完整 SHALL show the same sentence the 中位數 view shows
(沒有審議時間紀錄。), and the switch SHALL remain.

#### Scenario: The median view is the default

- **WHEN** the page is opened with no review view selected
- **THEN** the review chart shows the two medians by year, under the title 審議年數中位數，依首次核定年度
- **AND** the switch shows 中位數 as pressed and 完整 as not pressed

#### Scenario: The full view is selected

- **WHEN** the reader uses the switch to select 完整
- **THEN** the review chart shows the fan and the boxes, under the title 審議年數分布，依首次核定年度
- **AND** the switch shows 完整 as pressed

#### Scenario: Percentiles interpolate between the two nearest ranks

- **WHEN** a year holds four projects whose first-approval intervals are 1.0, 3.0, 4.0 and 8.0 years
- **THEN** 完整 shows for that year and interval: shortest 1.0, 25th percentile 2.5, median 3.5, 75th percentile 5.0, longest 8.0, with a project count of 4

#### Scenario: A year with one project

- **WHEN** a year holds one project whose first-approval interval is 3.0 years
- **THEN** all five values for that year and interval read 3.0, with a project count of 1
- **AND** the year is still drawn

#### Scenario: The tooltip lists both intervals

- **WHEN** a year holds two projects with a first-approval interval, and one of them has no pre-permit interval
- **THEN** the year's tooltip lists five values and a project count of 2 for the first-approval interval, and five values and a project count of 1 for the pre-permit interval

#### Scenario: An interval absent from a year

- **WHEN** a year's only project has a first-approval interval and no pre-permit interval
- **THEN** the year's tooltip shows the five values for the first-approval interval and no value for the pre-permit interval

#### Scenario: The full view agrees with the median view

- **WHEN** the same payload is shown in 中位數 and in 完整
- **THEN** for every year and interval the median and the project count are the same in both views

#### Scenario: The fan is drawn point to point

- **WHEN** 完整 shows three consecutive years
- **THEN** the fan's two bands and its median line are made of straight segments only
- **AND** the first-approval interval is drawn as one box per year, each with its line, its box and its dot

#### Scenario: A year with no project is crossed

- **WHEN** a scope holds projects first approved in 2018 and in 2020 and none in 2019
- **THEN** the fan runs unbroken from 2018 to 2020
- **AND** 2019 carries no box and no tooltip

#### Scenario: The card does not follow the switch

- **WHEN** the reader switches between 中位數 and 完整
- **THEN** the 審議時間中位數 card and its sub-line read the same under both views

#### Scenario: The text follows the view and the language

- **WHEN** 完整 is shown in English
- **THEN** the title, the caption, the legend and the switch read in English, and the legend names each interval with what its marks mean

#### Scenario: No review time in the scope

- **WHEN** the scope holds no project with a review time and 完整 is selected
- **THEN** the chart shows 沒有審議時間紀錄。 and the switch remains

#### Scenario: The full view follows the district

- **WHEN** the reader selects 萬華區 and 完整
- **THEN** the fan, the boxes and the tooltips cover 萬華區 only

## MODIFIED Requirements

### Requirement: The view is linkable and bilingual

The dashboard SHALL keep its state — the selected district, the language and
the review chart's view — in the URL hash (`#district=<name>&lang=en&review=full`),
so a view can be linked, and a change of the hash SHALL re-render the page.
The default language SHALL be
Traditional Chinese; `lang=en` SHALL render every label, stage name, section
lede, caption and the definitions block in English, and the document's `lang`
attribute SHALL follow the language. The definitions block (定義與限制) SHALL
state, in the current language, how stage, idle years and review time are
defined and what the page does not cover: only approved cases appear, and
projects stuck before approval are not in the gazette.

The review chart's view SHALL be 完整 when the hash carries `review=full`, and
中位數 for any other value or none. Using the switch SHALL write the view into
the hash and keep the district and the language already there; selecting
中位數 SHALL remove the `review` key, so the default view has one address.

#### Scenario: A linked view

- **WHEN** the page is opened with `#district=萬華區&lang=en`
- **THEN** it renders 萬華區 in English, with the stage names translated and `lang="en"` on the document

#### Scenario: The default language

- **WHEN** the page is opened with no hash
- **THEN** it renders the city view in Traditional Chinese with `lang="zh-Hant"` on the document

#### Scenario: The definitions travel with the language

- **WHEN** the language is switched
- **THEN** the definitions block is shown in that language and still names the 3- and 5-year convention

#### Scenario: A linked review view

- **WHEN** the page is opened with `#district=萬華區&review=full`
- **THEN** it renders 萬華區 with the review chart in 完整
- **AND** using the switch to select 中位數 leaves `#district=萬華區` in the address, with no `review` key
- **AND** a `review` value the page does not know renders 中位數
