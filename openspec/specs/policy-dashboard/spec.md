# policy-dashboard Specification

## Purpose
The policy dashboard turns the viewer's per-project history payload into the
figures a policy reader asks for — stalled cases, review workload and speed,
relocation demand, and public land in the pipeline — computed in the browser
from the published dataset, for the whole city or one district, with no figure
typed by hand.
## Requirements
### Requirement: The dashboard is a published page that computes every figure from the viewer's payload

The site SHALL publish a policy dashboard page (`viewer/dashboard.html`, with
`dashboard.js` and `dashboard.css`) beside the viewer. The page SHALL read the
same dataset the viewer reads — `projects.data.js`, the `window.PROJECTS`
payload — and SHALL derive every figure it shows from that payload at render
time. No figure on the page is a literal maintained by hand: the corpus moves
at every gazette (three payload re-emits on 2026-11-06 each moved the
durations while the project count stayed the same), and a typed figure reads
as current until it does not.

The page SHALL request the dataset with the cache-bust version the viewer's
`index.html` names for `projects.data.js`, so both pages share one cached copy
and the dashboard never pairs with a dataset the viewer has already left
behind. When that version cannot be read — the page was opened from `file://`
and `index.html` cannot be fetched — the page SHALL load the dataset by its
plain relative path rather than fail.

The page's own script and stylesheet references SHALL carry the same derived
version the viewer's assets carry, rewritten by the same emission step that
rewrites `index.html`; a reference left without a version SHALL be reported as
a fault, not silently given one, because the page's markup is hand-maintained
and an invented version would mask the drift. The page and both assets SHALL
be listed in `viewer/deploy.json`, so their served bytes are compared against
the committed build.

The header SHALL state the dataset's scope from the payload: the project
count and the record count from `counts`, and the 統計至 date from
`published_date`. When the payload is absent or carries no project list, the
page SHALL show a load-failure sentence (無法載入 projects.data.js。) in place
of its content; the header's site links stay, as `viewer-related-links`
requires.

#### Scenario: The figures follow the payload

- **WHEN** the dataset is rewritten with a different set of projects and the page is rendered again
- **THEN** the scope line, the six summary cards, every chart and both tables reflect the new payload
- **AND** no figure on the page is a literal in the page's own markup or script

#### Scenario: The dashboard borrows the viewer's dataset version

- **WHEN** the page is served from the site and `index.html` names `projects.data.js?v=<version>`
- **THEN** the dashboard requests `projects.data.js` with that same `<version>`

#### Scenario: Opened from disk

- **WHEN** the page is opened from a `file://` URL and `index.html` cannot be fetched
- **THEN** the dashboard loads `projects.data.js` by its plain relative path and renders

#### Scenario: The page's assets carry the derived version

- **WHEN** the viewer data is written and the asset version is rewritten
- **THEN** `dashboard.html` references `dashboard.js` and `dashboard.css` with the same version `index.html` carries
- **AND** a dashboard asset reference left without a version is reported as a cache-bust fault naming the page and the asset

#### Scenario: The page is a listed artifact

- **WHEN** the deploy record is read
- **THEN** it names `viewer/dashboard.html`, `viewer/dashboard.js` and `viewer/dashboard.css`

#### Scenario: The payload fails to load

- **WHEN** `projects.data.js` cannot be loaded, or the payload carries no project list
- **THEN** the page shows the load-failure sentence in place of its content

### Requirement: Each project is placed in one of four stages by its furthest recorded construction milestone

The dashboard SHALL place every project in exactly one stage, decided in this
order from the project's own records as a whole:

1. 已完工 — the project carries a completion date: a 使照核發日期 among its
   case milestones, the implementation record's use-permit date (`Ulic_Date`),
   the national portal's 使用核發日期, or the date of the use-permit witness
   the pipeline selected for it (`links.permit.date`).
2. 施工中 — no completion date, but a construction-start date: a 開工日期
   among its case milestones or the implementation record's `Eng_Start_Date`.
3. 已領建照未開工 — neither, but a 建照核發日期 among its case milestones.
4. 已核定未領建照 — none of the above.

A project's completion date is the latest of its completion dates; its start
date and its permit date are the earliest of each. The stage SHALL read from
the project level, never from the stage label of its latest approval node,
because an approval's stage names a planning step (擬訂 / 變更), not a
construction state. In English the four stages read "Approved, no building
permit", "Permit issued, not started", "Under construction", "Completed".

#### Scenario: A completion date decides the stage

- **WHEN** a project carries a use-permit date from any of the four completion sources, with or without a start date
- **THEN** its stage is 已完工

#### Scenario: A start date without a completion date

- **WHEN** a project carries a construction-start date and no completion date
- **THEN** its stage is 施工中, whatever its building-permit dates

#### Scenario: A building permit without a start

- **WHEN** a project carries a 建照核發日期 and neither a start date nor a completion date
- **THEN** its stage is 已領建照未開工

#### Scenario: Approved only

- **WHEN** a project carries approval nodes and none of the construction dates above
- **THEN** its stage is 已核定未領建照

#### Scenario: The node's stage label does not decide

- **WHEN** a project's latest approval node is a 變更 of a 權利變換計畫 and the project carries no construction date
- **THEN** its stage is still 已核定未領建照

### Requirement: Idle time is measured from the last recorded progress to the gazette's own date

For every project the dashboard SHALL take the last activity as the latest
valid date among: its approval nodes, every date in its case milestones, every
date in its national milestones, its start dates and its completion dates.
Idle years SHALL be the elapsed time from that date to the payload's
`published_date` — the gazette's 統計至 line — in years of 365.25 days, to two
decimals. The clock is the gazette, never the day the page is viewed, so the
same payload gives the same figure on any day.

The dashboard SHALL flag an unfinished project (any stage but 已完工) as
停滯5年以上 when its idle years are 5 or more, as 停滯3至5年 when they are 3
or more, and as 推進中 otherwise. A completed project SHALL never be flagged,
whatever its idle years. The page SHALL say, in its definitions block, that
the 3- and 5-year cut-offs are a convention of the page and not a legal
definition, and that a quiet record can also mean missing data.

#### Scenario: Idle five years or more

- **WHEN** an unfinished project's last recorded date is 5.0 years or more before `published_date`
- **THEN** it is flagged 停滯5年以上 and counted in the scope's "unfinished, idle 5+ years" card

#### Scenario: Idle three to five years

- **WHEN** an unfinished project's last recorded date is 3.0 years or more, and under 5.0, before `published_date`
- **THEN** it is flagged 停滯3至5年

#### Scenario: A completed project is never flagged

- **WHEN** a project's stage is 已完工 and its last recorded date is ten years before `published_date`
- **THEN** it carries no idle flag and appears in no watchlist

#### Scenario: The clock is the gazette, not today

- **WHEN** the same payload is rendered on two different days
- **THEN** every project's idle years are identical on both days

### Requirement: Dates are read under either calendar and implausible dates are treated as absent

The dashboard SHALL read a date written in the Gregorian form (`2018-02-08`,
`2018/2/8`, with or without a trailing time) or in the dotted Republic of
China form (`107.02.08`, the year plus 1911). It SHALL treat as absent: any
other form, a date that does not exist on the calendar, a date before 1995,
and a date after the payload's `published_date`. An absent date never
contributes to a stage, to last activity or to a duration. The national
portal prints the dotted ROC form (2,981 values in the 2026-10-28 payload)
while every other source prints Gregorian; a future-dated or pre-1995 value
is a data defect, not a milestone.

#### Scenario: A dotted ROC date

- **WHEN** a national milestone reads `107.02.08`
- **THEN** it is read as 2018-02-08

#### Scenario: A date that does not exist

- **WHEN** a milestone reads `2026/2/30`
- **THEN** it is treated as absent and contributes to no figure

#### Scenario: A date after the gazette

- **WHEN** a milestone's date is later than `published_date`
- **THEN** it is treated as absent, so it neither sets a stage nor shortens idle time

### Requirement: Review time runs from the earliest application to the first approval, total time to completion

The dashboard SHALL anchor a project's review time on its first approval node.
The eligible nodes are the project's dated approval nodes whose track is not
事業概要; the first approval SHALL be the earliest eligible node whose stage
label begins with 擬訂, or, when the project has no such node, the earliest
eligible node. A project with no eligible node has no review time.

The application date SHALL be read from the city case bound to the first
approval node: the earliest of that case's 申請計畫日期 and 申請權變日期. When
the node is bound to more than one case — the city files one case per
building lot for one approval — the earliest date across those cases SHALL be
taken. The approval date of a node SHALL be the earliest of its case's
核定日期 and 權變核定日期, or the node's own gazette date when the case records
neither. Neither 申請概要日期 nor the national portal's application dates
contribute: an outline application precedes the plan under review, and the
national date is a second copy of the city's.

Two intervals SHALL be derived from the application date, each in years of
365.25 days to two decimals:

1. **To first approval** (自申請至首次核定): to the approval date of the first
   approval node.
2. **To the approval before the building permit** (自申請至建照核發前之核定): to
   the approval date of the latest eligible node dated before the project's
   earliest 建照核發日期 among its case milestones; when no 建照核發日期 is
   recorded, to the approval date of the latest eligible node. When the permit
   precedes every eligible node the interval is absent.

Total years SHALL be the time from the application date to the project's
completion date. Any of the three figures SHALL be absent when one of its two
dates is absent or when the end precedes the start; a duration is never
negative.

A median SHALL be computed over present values only — the middle value, or
the mean of the two middle values — rounded to one decimal, and SHALL be shown
with the number of projects it covers. The scope's summary card SHALL show the
median of the second interval, and SHALL name in its sub-line the median of
the first interval and, for completed projects, the median total years. The
review chart SHALL show both medians by the year of the first approval's date,
each with its project count for the year, drawn point to point with a legend
naming the two intervals, because a curve would suggest values the data lacks.
Projects whose every node is a 事業概要 approval SHALL be counted in the scope's
project card but left out of both intervals, and the chart caption SHALL say
how many such projects the scope holds when there are any.

#### Scenario: Both dates present

- **WHEN** a project's first approval node is bound to a case whose 申請計畫日期 is 2015-01-01 and whose 核定日期 is 2018-01-01
- **THEN** its first-approval interval is 3.0 years

#### Scenario: Approval before application

- **WHEN** the first approval's case records a 核定日期 earlier than its 申請計畫日期
- **THEN** both intervals are absent and the project is excluded from every review median and from the review chart

#### Scenario: The median over an even count

- **WHEN** the scope holds four projects whose first-approval intervals are 1.0, 2.0, 3.0 and 10.0 years
- **THEN** the median shown for that interval is 2.5

#### Scenario: The count travels with the median

- **WHEN** the review chart shows a year
- **THEN** each interval's median for that year is accompanied by the number of projects it covers

#### Scenario: The application is read from the first approval's own case

- **WHEN** a project's first approval node is bound to case A (申請計畫日期 2016-01-01, 核定日期 2018-01-01) and a later 變更 node is bound to case B (申請計畫日期 2012-01-01)
- **THEN** the first-approval interval is 2.0 years, not 6.0

#### Scenario: A 擬訂 node is preferred as the first approval

- **WHEN** a project's earliest eligible node is a 變更 dated 2017-05-10 and a 擬訂 node dated 2017-11-23 follows it
- **THEN** the 擬訂 node is the first approval, and the intervals start from its case's application date

#### Scenario: Only 事業概要 approvals

- **WHEN** a scope holds one project whose every node is a 事業概要 approval and one project with a 擬訂 事業計畫 node
- **THEN** the project card counts 2, both medians cover 1 project, and the review caption says one project with only a 事業概要 approval is left out

#### Scenario: Time to the approval before the building permit

- **WHEN** a project's first approval case reads 申請計畫日期 2008-02-07 and 核定日期 2013-02-07, a 變更 node's case reads 核定日期 2017-02-07, a later 變更 node's case reads 核定日期 2022-11-23, and a case records 建照核發日期 2018-07-16
- **THEN** the first-approval median for the project reads 5.0 years and the pre-permit median 9.0, ending at 2017-02-07 and not at 2022-11-23

#### Scenario: No building permit: the latest approval

- **WHEN** a project records no 建照核發日期 and its nodes' approval dates are 2018-01-01 (擬訂, application 2015-01-01) and 2020-01-01 (變更)
- **THEN** the pre-permit interval is 5.0 years and the first-approval interval 3.0

#### Scenario: The permit precedes every approval

- **WHEN** a project's earliest 建照核發日期 is earlier than every eligible node
- **THEN** its pre-permit interval is absent while its first-approval interval is still shown

#### Scenario: The card shows the pre-permit median

- **WHEN** a scope's first-approval median is 3.0 years and its pre-permit median is 5.0 years
- **THEN** the 審議時間中位數 card shows 5.0 and its sub-line names 3.0 as the first-approval median

#### Scenario: Joined cases take the earliest application

- **WHEN** a first approval node is bound to two cases whose 申請計畫日期 are 2013-04-08 and 2013-06-01 and whose 核定日期 are both 2019-07-24
- **THEN** the first-approval interval runs from 2013-04-08

### Requirement: Approvals are counted by year and split between new plans and changes

The dashboard SHALL count every dated approval node of every project in the
year of its date, and SHALL class a node whose stage label begins with 變更 as
a change and any other node as a new plan (擬訂). The approvals chart SHALL
show both counts for each year in the selected scope, and its caption SHALL
say that the latest year is partial.

#### Scenario: A change and a new plan in one year

- **WHEN** a project has nodes dated 2020-03-01 (stage 擬訂事業計畫) and 2020-09-01 (stage 變更事業計畫(第1次))
- **THEN** 2020 counts one new plan and one change

#### Scenario: An undated node is not counted

- **WHEN** an approval node carries no readable date
- **THEN** it is counted in no year

### Requirement: Households, public land and public-benefit area are read from the implementation record

For every project the dashboard SHALL read from the implementation record the
existing households (`Old_Doors`), the public-benefit floor area
(`Welfare_Area`), and the public land as the sum of state land (`State_Area`)
and city land (`Muni_Area`), each rounded to a whole number. Public land's
share of the site SHALL be public land over the site area (`Base_Area`) in
percent to one decimal, capped at 100, and absent when the site area is absent
or zero.

For the selected scope the summary cards SHALL show: households in unfinished
projects, split between projects under construction (施工中) and projects not
yet started; public land in unfinished projects, with the count of projects
that hold any; and public-benefit area across projects of every stage, with
the count of projects that provide any. "Unfinished" means every stage but
已完工. The page SHALL say that these are the figures filed with each plan and
may differ from built results.

#### Scenario: Public land larger than the site is capped

- **WHEN** a project's state and city land together exceed its `Base_Area`
- **THEN** its share of site is shown as 100.0

#### Scenario: Households split by construction

- **WHEN** a scope holds one 施工中 project with 30 households, one 已領建照未開工 project with 20, and one 已完工 project with 50
- **THEN** the households card shows 50, split 30 under construction and 20 not yet started

#### Scenario: Public-benefit area counts every stage

- **WHEN** a scope's only project with a `Welfare_Area` is 已完工
- **THEN** the public-benefit card still shows that area and a project count of 1

### Requirement: Every figure is available for the whole city and for one district

The dashboard SHALL compute every figure for 全市 and for each district the
payload carries, and SHALL let the reader select one district. Under a
district selection the takeaway sentence, the summary cards, the stage chart,
the approvals chart, the review chart and both tables SHALL cover that
district only. The two by-district charts — households and public land in
unfinished projects — SHALL keep every district and dim the others, so the
selected district stays comparable with the rest. A district name the payload
does not carry SHALL fall back to the city view.

#### Scenario: A district is selected

- **WHEN** the reader selects 萬華區
- **THEN** the cards, the stage chart, the approvals chart, the review chart and both tables cover 萬華區 only
- **AND** the households and public-land charts still show every district, with the others dimmed

#### Scenario: An unknown district

- **WHEN** the URL names a district the payload does not carry
- **THEN** the page renders the city view

### Requirement: The watchlist and the public-land table name the projects behind the figures

The watchlist SHALL list every unfinished project flagged 停滯3至5年 or
停滯5年以上 in the selected scope, longest idle first, with its stage, last
progress date, idle years, households and implementer. The public-land table
SHALL list the twelve unfinished projects with the largest public land in the
scope, with stage, public land, its share of the site and households. In both
tables the project name SHALL link to that project's history graph in the
viewer (`index.html#project=<project_id>`) by a relative path, so the link
works from `file://` too. An empty list SHALL show a sentence saying so rather
than an empty table.

#### Scenario: The watchlist order and link

- **WHEN** a scope holds two flagged projects idle 4.2 and 6.8 years
- **THEN** the watchlist shows the 6.8-year project first
- **AND** each project name links to `index.html#project=<its project_id>`

#### Scenario: The public-land table is capped at twelve

- **WHEN** a scope holds fourteen unfinished projects with public land
- **THEN** the table shows the twelve with the largest public land, largest first

#### Scenario: Nothing to list

- **WHEN** a scope holds no flagged project
- **THEN** the watchlist shows the sentence 此範圍內沒有停滯三年以上的未完工專案。 and no rows

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

