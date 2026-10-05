## Purpose

Defines how a gazette PDF is turned into raw TSV rows, and — equally important — what the reader refuses to do. The reader takes all cell boundaries from the document's own table structure, accepts either calendar the city chooses to print, and aborts rather than emitting output it cannot prove is complete.

## MODIFIED Requirements

### Requirement: Extract all records as raw TSV rows

The system SHALL convert the source PDF into a raw TSV with one row per approved case plus a header, deriving every cell boundary from the document's own table structure rather than from fixed coordinates, and preserving the original cell text verbatim without normalization. Each row SHALL carry a `gazette_id` identifying the publication it came from.

#### Scenario: Full extraction of a publication

- **WHEN** the pipeline processes a gazette PDF
- **THEN** the raw TSV contains one data row per approved case found in the document plus one header row
- **AND** each row has the 7 columns 編號, 核定日期, 行政區, 案名, 地號, 實施者, 更新規劃單位, plus `gazette_id`
- **AND** the number of rows equals the highest 編號 present, because 編號 is contiguous from 1

#### Scenario: Column positions shift between publications

- **WHEN** a publication moves every column horizontally relative to a previously processed one
- **THEN** every cell is still read from its correct column, because boundaries come from the table's ruling lines rather than from stored coordinates
- **AND** 案名 and 行政區 are not exchanged

#### Scenario: Line-wrapped cells are re-joined

- **WHEN** a cell wraps across multiple lines within its own cell boundary (e.g. 實施者 "嘉興發股份有限公" + "司")
- **THEN** the cell is emitted as one continuous value ("嘉興發股份有限公司") with no mid-cell newline

#### Scenario: Raw text is verbatim

- **WHEN** the source contains a known data error (e.g. district "松化區" or name fragment "權利變換計劃案")
- **THEN** the raw TSV preserves it unchanged, because normalization belongs to the cleansing step

#### Scenario: Page furniture is excluded

- **WHEN** a page repeats the column header, the title "臺北市都市更新核定案件一覽表", the "統計至…" line, or a page number
- **THEN** none of these appear in any data row

#### Scenario: Repeated header row carrying a data row

- **WHEN** a publication repeats the row for 編號 1 in the page header of every page after the first
- **THEN** the repeat is discarded as a duplicate of 編號 1 rather than emitted as an additional record
- **AND** the last genuine record on each affected page is emitted in full

### Requirement: Extract records under either calendar

The system SHALL accept both the Republic of China calendar form (`115/8/27`) and the Gregorian form (`2026/9/24`) in the 核定日期 column, deciding per cell, and SHALL emit each date as an ISO-8601 calendar date.

#### Scenario: Republic of China calendar publication

- **WHEN** a publication prints 核定日期 as `115/8/27`
- **THEN** the record's date is emitted as `2026-08-27`

#### Scenario: Gregorian calendar publication

- **WHEN** a publication prints 核定日期 as `2026/9/24`
- **THEN** the record's date is emitted as `2026-09-24`

#### Scenario: Calendars mixed within one publication

- **WHEN** one publication contains both calendar forms
- **THEN** each cell is interpreted on its own and every date is emitted as ISO-8601
- **AND** the mix is reported rather than silently normalized

#### Scenario: Unparseable date

- **WHEN** a 核定日期 cell cannot be interpreted as a date in either calendar
- **THEN** the run is aborted and the offending page, row, and cell text are reported
- **AND** no output is written

### Requirement: Capture the official published date from the document

The system SHALL read the "統計至" line from the document and emit it as publication metadata alongside the raw TSV, without treating it as page furniture. The publication date SHALL be derived from the document's own content and SHALL NOT be a fixed value.

#### Scenario: Published date is read from the document

- **WHEN** a PDF whose 統計至 line reads `統計至115年9月24日` is processed
- **THEN** the metadata records that publication date rather than any previously known value
- **AND** the 統計至 line itself appears in no data row

#### Scenario: Publication date differs from any prior run

- **WHEN** a PDF is processed whose 統計至 date differs from the date recorded for the previously ingested gazette
- **THEN** the metadata carries the date found in this document
- **AND** no previously recorded date is substituted

#### Scenario: Published date threads through pipeline meta

- **WHEN** the CLI runs with the extracted publication date
- **THEN** it appears in the pipeline meta dict, in projects.json, in projects.data.js
- **AND** the viewer header displays the publication date rather than a generation timestamp

#### Scenario: A run refreshes the viewer without being asked

- **WHEN** a run targets the repository's own output tree
- **THEN** the viewer's `projects.data.js` is rewritten from the dataset that run emitted, whether or not a viewer target was passed
- **AND** the viewer cannot continue to serve a dataset an earlier or abandoned publication produced

#### Scenario: The cache-bust names the publication the data carries

- **WHEN** the viewer data is written
- **THEN** the asset version referenced by `index.html` is derived from the emitted dataset's publication date
- **AND** it is not a literal maintained by hand, so it cannot name a publication the data does not carry

#### Scenario: Viewer and dataset disagree

- **WHEN** the viewer's `projects.data.js` and the dataset's `projects.json` disagree on `published_date` or on the project or record count
- **THEN** the inconsistency is reported as a fault naming both files and both values
- **AND** a browser holding a superseded cache-bust is not the only way the drift becomes visible

### Requirement: Reject structures the reader cannot interpret exactly

The system SHALL refuse to produce output when the document's table structure cannot be read exactly as published, naming the page, row, and column of each fault. It SHALL NOT substitute an approximate reading, and it SHALL NOT fall back to a positional or text-alignment strategy. Any such fault SHALL leave previously emitted artifacts untouched.

#### Scenario: Merged cell spanning rows or columns

- **WHEN** a cell spans more than one row or column in the published grid
- **THEN** the run is aborted and the fault is reported with its page, row, and column
- **AND** the cell's content is not forwarded or duplicated into the rows it spans

#### Scenario: A page yields no table

- **WHEN** a page contains data rows but no detectable table structure
- **THEN** the run is aborted and the page number is reported
- **AND** the system does not attempt a positional or whitespace-aligned reading of that page

#### Scenario: Row shape does not match the published grid

- **WHEN** any extracted row does not have the same number of cells as the header row
- **THEN** the run is aborted and the offending page and row are reported

### Requirement: Refuse to emit an incomplete extraction

The system SHALL verify the structural completeness of an extraction before emitting it, and SHALL abort without writing output when any check fails. The checks SHALL cover, at minimum: 編號 values forming a contiguous run from 1 to the maximum with no gaps; every 核定日期 cell parsing as a date; every page yielding exactly one table; no row carrying a structurally incomplete cell; and the duplicate-編號 count not exceeding the known repeated-header artifact.

#### Scenario: Contiguous numbering is verified

- **WHEN** an extraction yields 編號 values 1 through 1436 with no gap
- **THEN** the completeness check passes and output is written

#### Scenario: A record is missing from the middle of the table

- **WHEN** an extraction yields 編號 values with a gap (e.g. 1-100 and 102-1436)
- **THEN** the run is aborted and the missing 編號 is reported
- **AND** no output is written

#### Scenario: Check fails after a partial run

- **WHEN** a completeness check fails on a gazette that would otherwise have been ingested
- **THEN** no raw TSV, clean TSV, merged TSV, projects document, or viewer data file is written or overwritten

## ADDED Requirements

### Requirement: Distinguish reader faults from source faults in cell content

The system SHALL classify every fault found in a cell's text by whether the reader or the publisher caused it, because the two demand opposite responses. A fault the reader could have prevented SHALL abort the run and write no output. A fault the publisher introduced, which no reading of the document can repair, SHALL NOT abort the run: the affected record SHALL be excluded from the emitted dataset, named with its page, row and column in the run report, and counted, so that a gazette missing records is never presented as complete.

#### Scenario: Page furniture absorbed into a cell

- **WHEN** a page-number footer lies geometrically inside the last row's 地號 cell rectangle and the reader would otherwise emit it as part of the cell's text
- **THEN** the reader identifies it as page furniture and excludes it
- **AND** the cell is emitted with its published text only
- **AND** if it cannot be excluded with certainty, the run is aborted rather than emitting the cell

#### Scenario: Publisher truncates a cell at the row height

- **WHEN** a 地號 cell's text ends in a dangling separator (`、` or `，`) or a half sub-parcel number such as `139-`, because the publisher stopped drawing the list at the printed row height
- **THEN** the record is reported as a source fault naming its page, row and column
- **AND** the record is excluded from the emitted dataset rather than emitted with an unknown parcel set
- **AND** the run continues and the excluded count is reported
- **AND** no parcel list is inferred from a sibling record, from the parcel count declared in the 案名, or from a wider text window

#### Scenario: Publisher's truncation removes only the closing phrase

- **WHEN** a 地號 cell ends mid-enumeration but still shows exactly as many parcels as the same row's 案名 declares
- **THEN** the parcel list is provably whole, only the closing phrase was lost, and the record is emitted normally with no fault reported
- **AND** no parcel is inferred from another record, another gazette, or the declared count

#### Scenario: Publisher's terminal wording variations are not faults

- **WHEN** a 地號 cell ends `地號等共 57筆土地`, `地號等 18 筆土地)`, `地號等 34 筆土 地` (the word 土地 split across a line), or a bare `地號等12筆` with no 土地
- **THEN** the record is emitted normally and no fault is reported
- **AND** the fault detector does not fire on any published wording variation that carries a complete parcel list

#### Scenario: A partial gazette is never presented as complete

- **WHEN** one or more records were excluded as source faults
- **THEN** the run report states the number excluded alongside the number emitted
- **AND** the emitted dataset is not described as a faithful copy of the publication

### Requirement: Extraction failures are reported with their location

The system SHALL report every structural fault it detects with enough location detail — page number, row index, and column name — for a person to find the corresponding cell in the source document without re-running the extraction.

#### Scenario: Multiple faults are reported together

- **WHEN** three pages each contain a merged cell
- **THEN** all three faults are reported in a single run rather than aborting on the first
- **AND** each names its page, row, and column