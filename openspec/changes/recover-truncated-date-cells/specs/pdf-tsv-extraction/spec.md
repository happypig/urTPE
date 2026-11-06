## ADDED Requirements

### Requirement: An empty 核定日期 cell is a source fault the recovery pass owns

A record whose 核定日期 cell is **empty** in the publication SHALL be
classified as a **source fault** — the publisher printed a row with no
approval date — and not as a reader fault. The reader's output for that cell
is correct: there is nothing in the cell to read.

When the run carries `--recover-truncated`, such a record SHALL be retained in
the raw TSV, marked as a source fault, and SHALL carry its surviving cells
(行政區, the 案名, the 地號 cell, the 實施者 and the 更新規劃單位) so that the
recovery pass can re-identify it and recover the date. The marked row SHALL NOT
reach cleansing or merge until the recovery pass resolves or abandons it.

Without the flag the record SHALL be dropped before emission, and the run
SHALL report it: a publication whose row count is short of its 編號 range is
incomplete, and the tripwire's date rule SHALL refuse the emission.

The marker SHALL be distinct from the 地號 truncation marker, so the two
defects are told apart in the raw TSV and in the report.

#### Scenario: The emptied row is retained for the recovery pass

- **WHEN** a publication prints an empty 核定日期 cell and the run carries
  `--recover-truncated`
- **THEN** the raw TSV holds the row, marked as a source fault, with its
  surviving cells
- **AND** the row does not reach cleansing or merge

#### Scenario: The tripwire refuses an unrecovered empty date

- **WHEN** a publication prints an empty 核定日期 cell and the run does not
  carry `--recover-truncated`, or the recovery pass leaves the row a residual
- **THEN** the tripwire names the record as having an unparsed 核定日期
- **AND** no artifact is written
