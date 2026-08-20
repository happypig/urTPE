## MODIFIED Requirements

### Requirement: Extract all records as raw TSV rows

The system SHALL convert the source PDF into a raw TSV with one row per approved case (1,419 rows) plus a header, preserving the original cell text verbatim without normalization.

#### Scenario: Full extraction of the PDF
- **WHEN** the pipeline processes the source PDF
- **THEN** the raw TSV contains exactly the 1,419 data rows found in the document plus one header row
- **AND** each row has the 7 columns 編號, 核定日期, 行政區, 案名, 地號, 實施者, 更新規劃單位

#### Scenario: Line-wrapped cells are re-joined
- **WHEN** a cell is wrapped across multiple lines by the PDF layout (e.g. 實施者 "嘉興發股份有限公" + "司")
- **THEN** the cell is emitted as one continuous value ("嘉興發股份有限公司") with no mid-cell newline

#### Scenario: Raw text is verbatim
- **WHEN** the source contains a known data error (e.g. district "松化區" or name fragment "權利變換計劃案")
- **THEN** the raw TSV preserves it unchanged, because normalization belongs to the cleansing step

### Requirement: Exclude page furniture

The system SHALL exclude repeating page headers, footers, titles, and page numbers from the data rows.

#### Scenario: Header and footer lines are dropped
- **WHEN** a page repeats the column header (編號…單位), the title "臺北市都市更新核定案件一覽表", "統計至…", or a page number
- **THEN** none of these appear in any data row

### Requirement: Report extraction failures

The system SHALL flag any record it cannot parse with the standard layout instead of silently dropping or corrupting it.

#### Scenario: Non-conforming record is flagged
- **WHEN** a record's 地號 cell does not follow the expected start pattern
- **THEN** the record is still emitted with a parse-error marker in a dedicated column
- **AND** the extraction report lists the record 編號 and the reason

## ADDED Requirements

### Requirement: Capture the official published date from PDF header

The system SHALL extract the "統計至115年8月11日" line from PDF page 1 (y≈60) and emit it as metadata alongside the raw TSV, without treating it as furniture.

#### Scenario: Published date is extracted from page 1
- **WHEN** the PDF is processed
- **THEN** the metadata includes `published_date: "統計至 115年8月11日"` (or equivalent ISO/Roc date)
- **AND** the date is not present in any data row

#### Scenario: Published date threads through pipeline meta
- **WHEN** the CLI runs with the extracted published_date
- **THEN** it appears in the pipeline meta dict, projects.json, and projects.data.js
- **AND** the viewer header displays "統計至 115年8月11日" instead of generated_at