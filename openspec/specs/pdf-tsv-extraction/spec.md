# pdf-tsv-extraction Specification

## Purpose

Converts the Taipei City Government's urban-renewal approved-cases gazette PDF into a raw, verbatim TSV. Cell boundaries come from the document's own ruling lines rather than fixed coordinates, so neither a column shift nor a calendar change alters what a cell contains. Both the Republic of China and Gregorian calendars are accepted and normalised to ISO-8601, a structure the reader cannot interpret exactly aborts the run rather than producing partial output, and a completeness tripwire gates every emission.
## Requirements
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

### Requirement: Distinguish reader faults from source faults in cell content

The system SHALL classify every fault found in a cell's text by whether the reader or the
publisher caused it, because the two demand opposite responses. A fault the reader could
have prevented SHALL abort the run and write no output. A fault the publisher introduced
SHALL NOT abort the run: the record SHALL either be excluded and named with its page, row
and column, or — where every check below is satisfied — completed from another approval of
the same unit and recorded with its provenance. In either case the affected count SHALL be
reported, so that a gazette missing records is never presented as complete.

When the run carries `--recover-truncated`, a publisher-truncated record SHALL additionally
be retained in the raw TSV, marked as a source fault, and SHALL carry its surviving cells
(核定日期, 行政區, the surviving 案名 text, and the surviving 地號 fragment) so that the
recovery pass can re-identify it; the marked rows SHALL NOT reach cleansing or merge until
the recovery pass resolves or abandons them. Without the flag the record SHALL be dropped
before emission exactly as before, and the raw TSV SHALL NOT contain it.

A 地號 cell is publisher-truncated when either signal fires:

- **Tail pattern.** The cell text ends in a dangling list separator (`、` `，` `,`), a
  trailing digit, or a trailing sub-parcel hyphen (`579-`), because the publisher stopped
  drawing the list at the printed row height. The half sub-parcel hyphen is part of the
  published truncation signature: measured 2026-10-26, 編號 1005 of the 2026-10-15 gazette
  ends `…578、579-` with 76 of its 77 declared parcels and was emitted by the earlier
  detector, which matched only separators and trailing digits.
- **Declared-count check, scoped to cells that lost their closing phrase.** When the cell's
  closing phrase (`地號等N筆土地` and its published variants, including a bare
  `地號等N筆`) is absent while the same row's 案名 declares a parcel count higher than the
  number of distinct parcels visible in the cell, the list stops short of what the row
  declares, wherever the text happens to end. This check runs for every row whose 案名
  declares a count, independently of any tail pattern, because a cut can end the cell text
  at any character (measured: a cut after `…479(部分)` ends on a CJK character no tail
  pattern matches).

A cell whose closing phrase IS present SHALL NOT be count-checked: the publisher completed
that cell, and a visible count differing from the 案名's declared count is a city-side
inconsistency between the two published fields, not evidence of a cut. Measured
2026-10-26 across seven held gazettes: 48 such rows in the 2026-10-15 gazette alone (count
typos such as a 案名 declaring 521 against a cell that declares and lists 52; multi-section
sums; `（原N筆）` renumbering; duplicated parcel numbers); none truncated. Excluding them
would discard complete records over city-side errors; flagging them is cleansing/review
concern, not extraction.

When a signal fires, the row SHALL take the publisher-truncation path: excluded and named
with its page, row and column, or completed from another approval of the same unit under
the three existing checks. The count-equal rescue precedes exclusion: a signal-firing cell
whose visible count equals its declared count lost only the closing phrase and SHALL be
emitted. A row whose 案名 declares no parcel count SHALL NOT be count-checked and keeps
the tail-pattern behaviour alone. No parcel list SHALL be inferred from the declared
count.

A completion is permitted only when all three of the following hold, and each is checked
independently:

1. **Same unit.** The candidate is in the same 行政區 and the same 段/小段.
2. **The parcels already read are preserved.** The truncated cell's own text, once
   whitespace is normalised, is a prefix of the candidate's text, **and** every parcel the
   truncated cell shows is present in the candidate. The two halves are checked separately
   and neither implies the other: spacing around `、` and around sub-parcel hyphens varies
   between publications for the same list (`332 、333` in one, `332、333` in another) and is
   presentation rather than content, so it is normalised before comparing; and a textual
   prefix can still end mid-token, so that a parcel already read is bounded differently in
   the candidate, which containment catches and a prefix test does not.
3. **The count closes.** The completed parcel count equals the count the same row's 案名
   declares. If it does not, the count is unexplained and the record stays excluded.

Where all three hold the record is emitted with the completed list and an audit entry
naming the source gazette and 編號 it was completed from. Where any one fails the record is
excluded as before.

The visible count SHALL be measured from parcel tokens as published, with these rules,
each pinned by a measured cell:

- A space standing where a separator belongs delimits two parcels (`163 164` in the
  長安段四小段140 cells is parcels 163 and 164, not the number 163164).
- A space followed by `-digits` continues the preceding token (`573 -6` in the
  雙園段二小段505 cells is the single parcel 573-6).
- Closing-phrase variants are stripped from the right before counting, so their count
  digits never enter the token set (`地號等22土地` must not count `22`;
  `地號等2筆(原17筆)土地` must not count `2` or `17`;
  `地號等 18 筆土地)等 4 筆土地` strips both chunks).

#### Scenario: Page furniture absorbed into a cell

- **WHEN** a page-number footer lies geometrically inside the last row's 地號 cell rectangle and the reader would otherwise emit it as part of the cell's text
- **THEN** the reader identifies it as page furniture and excludes it
- **AND** the cell is emitted with its published text only
- **AND** if it cannot be excluded with certainty, the run is aborted rather than emitting the cell

#### Scenario: Publisher truncates a cell at the row height

- **WHEN** a 地號 cell's text ends in a dangling separator (`、` or `，`), a trailing digit, or a half sub-parcel number such as `139-` or the measured `…578、579-`, because the publisher stopped drawing the list at the printed row height
- **THEN** the record is reported as a source fault naming its page, row and column
- **AND** if no candidate satisfies all three completion checks, the record is excluded from the emitted dataset rather than emitted with an unknown parcel set
- **AND** the run continues and the excluded count is reported
- **AND** no parcel list is inferred from the parcel count declared in the 案名, or from a wider text window

#### Scenario: A truncated cell is retained and marked under the recovery flag

- **WHEN** the run carries `--recover-truncated` and a 地號 cell is truncated by the publisher
- **THEN** the raw TSV contains the row, marked as a source fault with its surviving cells
  (核定日期, 行政區, 案名 fragment, 地號 fragment)
- **AND** the row does not reach cleansing or merge until the recovery pass resolves it
- **AND** a run without the flag still drops the row before emission, unchanged

#### Scenario: A cut with no tail-pattern ending is caught by the declared-count check

- **WHEN** a 地號 cell's closing phrase is absent, its text ends in a character no tail pattern matches (a CJK character, a closing paren, whitespace the reader stripped), and the distinct parcels visible are fewer than the count the same row's 案名 declares
- **THEN** the row takes the publisher-truncation path even though no tail pattern fired
- **AND** the record is excluded and named, or completed under the three existing checks, and the exclusion count is reported

#### Scenario: A cell that still carries its closing phrase is not count-checked

- **WHEN** a 地號 cell ends with a published closing-phrase variant and the distinct parcels visible differ from the count the 案名 declares — e.g. the 案名 declares 521 while the cell declares and lists 52, or the 案名 declares 22 while the cell lists 21 tokens because `163 164` was printed with a space for a separator
- **THEN** the record is emitted normally with no fault and no exclusion
- **AND** the publisher's own closing phrase, not the 案名's declared count, decides completeness for that cell

#### Scenario: A row whose 案名 declares no count is not count-checked

- **WHEN** a 地號 cell shows a parcel list but the same row's 案名 declares no parcel count, and no tail pattern fires
- **THEN** the record is emitted normally with no fault reported
- **AND** no exclusion is inferred from the absence of a declared count

#### Scenario: A truncated cell is completed from another approval of the same unit

- **WHEN** a 地號 cell is truncated — by the tail pattern or by the declared-count check — and another approval of the same unit elsewhere in the corpus is in the same 行政區 and 段/小段, its text begins with the truncated cell's text modulo whitespace while preserving every parcel the truncated cell shows, and its parcel count brings the truncated cell's total to exactly the count the same row's 案名 declares
- **THEN** the record is emitted with the completed parcel list rather than excluded
- **AND** the run reports that it was completed, naming the source gazette and 編號
- **AND** the completion is auditable after the fact from the run report alone

#### Scenario: A candidate is rejected because the count does not close

- **WHEN** a candidate's text begins with the truncated cell's text but completing from it yields fewer parcels than the same row's 案名 declares
- **THEN** the record is excluded and the count discrepancy is reported
- **AND** the system does not emit a parcel list it cannot reconcile with its own 案名

#### Scenario: A candidate is rejected because it drops an already-read parcel

- **WHEN** a candidate's text begins with the truncated cell's text but a parcel the truncated cell already showed is absent from the candidate — including the mid-token case where the cut leaves a half token (`…579-` reads as `579`) that the candidate bounds differently (`579-2`)
- **THEN** the candidate is a differently-bounded list rather than a continuation
- **AND** the record is excluded

#### Scenario: A candidate from a different 段/小段 is never used

- **WHEN** the only candidate sharing a prefix lies in a different 段 or 小段
- **THEN** the record is excluded
- **AND** no parcel is borrowed across a section boundary

#### Scenario: Publisher's truncation removes only the closing phrase

- **WHEN** a 地號 cell ends mid-enumeration but still shows exactly as many parcels as the same row's 案名 declares
- **THEN** the parcel list is provably whole, only the closing phrase was lost, and the record is emitted normally with no fault reported
- **AND** no parcel is inferred from another record, another gazette, or the declared count

#### Scenario: Publisher's terminal wording variations are not faults

- **WHEN** a 地號 cell ends `地號等共 57筆土地`, `地號等 18 筆土地)`, `地號等 34 筆土 地` (the word 土地 split across a line), a bare `地號等12筆` with no 土地, or a measured variant carrying a parenthetical or a second count (`地號等22土地`, `地號等2筆(原17筆)土地`, `地號等 18 筆土地)等 4 筆土地`)
- **THEN** the record is emitted normally and no fault is reported
- **AND** the fault detector does not fire on any published wording variation that carries a complete parcel list
- **AND** the count digits of those variants are not counted as parcels

#### Scenario: A partial gazette is never presented as complete

- **WHEN** one or more records were excluded as source faults, or completed from another approval
- **THEN** the run report states the number excluded and the number completed alongside the number emitted
- **AND** the emitted dataset is not described as a faithful copy of the publication

### Requirement: Extraction failures are reported with their location

The system SHALL report every structural fault it detects with enough location detail — page number, row index, and column name — for a person to find the corresponding cell in the source document without re-running the extraction.

#### Scenario: Multiple faults are reported together

- **WHEN** three pages each contain a merged cell
- **THEN** all three faults are reported in a single run rather than aborting on the first
- **AND** each names its page, row, and column

### Requirement: An emission states what the viewer can and cannot render

The system SHALL ensure the dataset it emits carries the fields the viewer reads, and SHALL report any that a rebuild dropped rather than emitting a conforming-looking dataset that cannot be rendered. A dataset missing link-derived fields SHALL be treated as a fault of the run, not as a smaller dataset.

#### Scenario: A rebuild omits link discovery

- **WHEN** a run emits a dataset in which every project carries an empty link set and no approval carries a link
- **THEN** the run reports that link-derived fields are absent, naming the fields and the affected counts
- **AND** the report states that the emitted viewer data cannot render the milestone cards, portal badges and execution-stage labels that depend on them

#### Scenario: A conforming emission is silent about it

- **WHEN** a run emits a dataset in which link-derived fields are present
- **THEN** no fault is reported on their account

#### Scenario: Link-derived fields are present for some projects only

- **WHEN** some projects carry link-derived fields and others do not
- **THEN** the run reports the count that do and does not
- **AND** does not treat the populated minority as conforming the whole

