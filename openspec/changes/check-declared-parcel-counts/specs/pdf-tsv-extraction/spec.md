# pdf-tsv-extraction — delta for check-declared-parcel-counts

## MODIFIED Requirements

### Requirement: Distinguish reader faults from source faults in cell content

The system SHALL classify every fault found in a cell's text by whether the reader or the
publisher caused it, because the two demand opposite responses. A fault the reader could
have prevented SHALL abort the run and write no output. A fault the publisher introduced
SHALL NOT abort the run: the record SHALL either be excluded and named with its page, row
and column, or — where every check below is satisfied — completed from another approval of
the same unit and recorded with its provenance. In either case the affected count SHALL be
reported, so that a gazette missing records is never presented as complete.

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

## REMOVED Requirements

*(none — the previously proposed ADDED requirement "Every 地號 cell is reconciled with its
declared parcel count" is withdrawn before implementation: the 2026-10-26 census measured
that an every-row count check excludes ~44 complete-as-published records per Gregorian
gazette. Its enforceable content is folded into the MODIFIED requirement above, scoped to
cells that lost their closing phrase; see `poc_findings.md`.)*
