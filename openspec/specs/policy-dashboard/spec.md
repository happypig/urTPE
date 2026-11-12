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

The dashboard SHALL take a project's application date as the earliest of its
申請計畫日期 and 申請概要日期 among the case milestones and the national
portal's 事業計畫申請日期. Review years SHALL be the time from that date to
the project's first approval — its earliest dated approval node — and total
years the time from that date to its completion date, each in years of
365.25 days to two decimals. Either figure SHALL be absent when one of its two
dates is absent or when the end precedes the start; a duration is never
negative.

A median SHALL be computed over present values only — the middle value, or
the mean of the two middle values — rounded to one decimal, and SHALL be shown
with the number of projects it covers. The scope's summary card SHALL show the
median review years and, for completed projects, the median total years. The
review chart SHALL show the median review years by the year of first approval
with the project count for each year, drawn point to point, because a curve
would suggest values the data lacks.

#### Scenario: Both dates present

- **WHEN** a project's earliest application date is 2015-01-01 and its first approval node is dated 2018-01-01
- **THEN** its review years are 3.0

#### Scenario: Approval before application

- **WHEN** a project's first approval node is dated before its earliest application date
- **THEN** its review years are absent and it is excluded from every review median and from the review chart

#### Scenario: The median over an even count

- **WHEN** the scope holds four projects with review years 1.0, 2.0, 3.0 and 10.0
- **THEN** the median review shown is 2.5

#### Scenario: The count travels with the median

- **WHEN** the review chart shows a year
- **THEN** that year's median is accompanied by the number of projects it covers

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

The dashboard SHALL keep its state — the selected district and the language —
in the URL hash (`#district=<name>&lang=en`), so a view can be linked, and a
change of the hash SHALL re-render the page. The default language SHALL be
Traditional Chinese; `lang=en` SHALL render every label, stage name, section
lede, caption and the definitions block in English, and the document's `lang`
attribute SHALL follow the language. The definitions block (定義與限制) SHALL
state, in the current language, how stage, idle years and review time are
defined and what the page does not cover: only approved cases appear, and
projects stuck before approval are not in the gazette.

#### Scenario: A linked view

- **WHEN** the page is opened with `#district=萬華區&lang=en`
- **THEN** it renders 萬華區 in English, with the stage names translated and `lang="en"` on the document

#### Scenario: The default language

- **WHEN** the page is opened with no hash
- **THEN** it renders the city view in Traditional Chinese with `lang="zh-Hant"` on the document

#### Scenario: The definitions travel with the language

- **WHEN** the language is switched
- **THEN** the definitions block is shown in that language and still names the 3- and 5-year convention

