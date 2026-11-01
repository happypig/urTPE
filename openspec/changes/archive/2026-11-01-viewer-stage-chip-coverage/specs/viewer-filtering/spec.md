# viewer-filtering Delta

## ADDED Requirements

### Requirement: The record table renders human-readable cells and ISO dates

The detail record table SHALL render values for human reading: a parcel list
SHALL render as `、`-joined prose (not a JSON array literal); an empty list or
dict SHALL render as an em dash (—); an absent value (`null`/`undefined`) SHALL
render as an em dash; and every date SHALL render in ISO form (`YYYY-MM-DD`) at
display time, converting ROC (`100.12.20`) and Taipei-slash (`2011/11/27`)
source spellings. The underlying data SHALL keep its source spellings verbatim —
these are display-time rules.

#### Scenario: A parcel list renders as prose

- **WHEN** the 地號清單 cell holds the parsed parcel list `["336","336-1","339"]`
- **THEN** the table renders `336、336-1、339`

#### Scenario: An empty or absent value renders as an em dash

- **WHEN** the 地號別名 cell holds an empty dict, or the 原地號數 cell holds
  `null`
- **THEN** the table renders — in both cells

#### Scenario: All three date forms render ISO in one pane

- **WHEN** a node date is `2026-10-15`, a Taipei milestone is `2011/11/27`, and
  a national milestone is `100.12.20`
- **THEN** all three render as ISO dates (`2026-10-15`, `2011-11-27`,
  `2026-12-20`) in the detail pane
- **AND** the data file still holds the original strings
