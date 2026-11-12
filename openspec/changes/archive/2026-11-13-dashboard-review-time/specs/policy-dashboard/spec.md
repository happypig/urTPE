## MODIFIED Requirements

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
