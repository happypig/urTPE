## MODIFIED Requirements

### Requirement: Execution events render once, sourced from records or ghost anchors

The history graph SHALL render each execution date (建照核發日期 / 開工日期 / 使照核發日期) exactly once, in the shared execution column. An execution date whose provenance is an orphan case (non-PDF, no anchor record) SHALL NOT be duplicated in the ghost column; instead, the orphan's dashed-circle ghost anchor node connects to that event with a slanted solid pink source edge, exactly as anchored records do.

When the project carries a building-authority permit witness (`links.permit`),
the 使照 slot's callout SHALL name the witness — the permit number beside the
portal value — and a disagreement flag the portals' two values raise SHALL
render as a review note on the event, naming the value the permit confirms.
An out-of-range ROC year (a year above the current 民國 year) SHALL render as
the raw source text with a warning class, never as a fabricated far-future
date (橋北574-1's `291.08.02` rendered 2202-08-02).

#### Scenario: 建照核發日期 renders once with its orphan source
- **WHEN** 建照核發日期 2022/02/17 is attributed to orphan case 09907221 in 文山區-木柵段三小段-623地號等39筆
- **THEN** the graph shows a single 建照核發日期 event, connected to the 09907221 dashed-circle anchor by a slanted solid pink edge
- **AND** no second 建照核發日期 appears in the ghost column

#### Scenario: Ghost anchors without construction dates render bare
- **WHEN** an orphan ghost anchor's payload contains no execution dates (e.g., 09907223)
- **THEN** only its dashed-circle anchor node renders in the ghost column

#### Scenario: The permit witness rides the 使照 slot
- **WHEN** a project's `links.permit` carries `{permit_no: "102使字第0298號",
  date: "2013-11-12"}` and the portals' 使照 values disagree
- **THEN** the 使照 event's callout names the permit number
- **AND** the review note names the value the permit confirms

#### Scenario: An out-of-range ROC year renders verbatim with a warning
- **WHEN** a milestone date reads `291.08.02` (an ROC year above the current
  民國 year — 橋北574-1's national 使用核發日期)
- **THEN** the value renders as the raw text `291.08.02` with the
  date-range-warning class
- **AND** no 2202 date is fabricated
