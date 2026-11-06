## ADDED Requirements

### Requirement: A truncated date cell is recovered from the name alone

A record whose 核定日期 cell is **empty** in the publication SHALL be recovered
by re-identifying its case from the record's own **案名**, and the recovered
case's own approval date SHALL be written into the record.

The candidate SHALL be chosen by **all** of the following, each checked
independently:

1. **Same unit.** The candidate's district and 段/小段 match the row's.
2. **The declared count agrees.** The count the row's 案名 declares equals the
   count the candidate's name declares. The counts are compared as **numbers**,
   not as text: the city writes the count as `等N筆` in some names and
   `地號N筆` in others, on both sides of the comparison, so a text comparison
   would refuse rows that agree.
3. **The stage ordinal agrees.** The ordinal the row's 案名 carries at its head
   — `擬訂`, `變更`, `變更(第二次)`, … — equals the candidate's. The ordinal is
   what separates a unit's successive revisions, which each carry their own
   approval date.
4. **The track set equals the row's.** The set of tracks the row's 案名 names
   (事業計畫 / 權利變換, one or both) **equals** the candidate's. Equality, not
   a subset relation: a subset admits the area-split twin of a combined-track
   case, which carries a different approval date.

The accepted candidates SHALL then carry **exactly one** approval date between
them. **Zero** or **several** SHALL leave the row a residual — excluded and
named — because the date would be a guess.

The names on both sides SHALL be compared after **NFKC** normalisation. The
city writes some characters as CJK compatibility ideographs (measured: 利 as
U+F9DD in one case name), which render identically but do not match a keyword
such as `權利變換`.

The recovered date SHALL come from the **city platform's** own approval date —
the case's `uro_chk_date` or `uro_chk_date2`, or its data2 核定日期. Where the
publication's own date is present, it is the authority; where it is empty, the
platform's date is what the record carries.

#### Scenario: An emptied date cell is recovered and dated

- **WHEN** a publication prints an empty 核定日期 for
  `變更(第二次)臺北市大安區通化段四小段336地號等26筆（原22筆）土地都市更新事業計畫案`
  and the city's case `11501034` carries `uro_chk_date = 2026-10-15`
- **THEN** the record's 核定日期 is `2026-10-15`
- **AND** the record is emitted into the merge with provenance naming case `11501034`
- **AND** the run report names it as recovered

#### Scenario: The candidates must agree on one date

- **WHEN** the name rule leaves two approved candidates carrying different
  approval dates
- **THEN** the row is a residual: excluded and named
- **AND** no date is written

#### Scenario: A count disagreement refuses

- **WHEN** the row's 案名 declares `等12筆` and the only candidate's name
  declares `等13筆`
- **THEN** the row is a residual
- **AND** no date is written, because the two describe different parcel counts

#### Scenario: A stage disagreement refuses

- **WHEN** the row's 案名 carries the ordinal `變更` and the only candidate with
  the right unit and count is a `擬訂` case
- **THEN** the row is a residual

#### Scenario: A track disagreement refuses

- **WHEN** the row's 案名 names the track 權利變換 alone and the only candidate
  with the right unit, count and ordinal names both tracks
- **THEN** the row is a residual

#### Scenario: A compatibility ideograph does not hide the track

- **WHEN** the candidate's name writes 利 as U+F9DD, so the keyword `權利變換`
  does not match the raw text
- **THEN** the comparison after NFKC normalisation matches it
- **AND** the candidate is not lost

### Requirement: The 核定公告 date is a flag, not the recovered date

The city's 168 case list carries a `MEMO` field holding the **核定公告** date —
the day the city **announced** an approval. That is a **different date** from
the approval date: measured over the 109 rows where both are readable, they
agree in 99 and differ in 10, by weeks or months. The list also holds a date
for only 146 of its 466 rows, and it is empty for **every** case where the
publication's date and the platform's date disagree.

The 核定公告 date SHALL therefore NOT be used as the recovered date. It SHALL be
used as a **second confirmation**: where the list holds the case and its
`MEMO` carries a date, that date SHALL be compared with the recovered date,
and a disagreement SHALL be recorded as a review flag on the record. The
recovered date itself SHALL come from the city's platform.

#### Scenario: An agreeing 核定公告 date is a confirmation

- **WHEN** the 168 list holds the recovered case with a `MEMO` date equal to
  the recovered date
- **THEN** the record carries no 核定公告 flag

#### Scenario: A disagreeing 核定公告 date is flagged

- **WHEN** the 168 list holds the recovered case with a `MEMO` date that
  differs from the recovered date
- **THEN** the record carries a review flag naming the 核定公告 date and the
  recovered date
- **AND** the recovered date is unchanged

#### Scenario: The list's silence is not a disagreement

- **WHEN** the 168 list does not hold the recovered case, or holds it with an
  empty `MEMO`
- **THEN** the record carries no 核定公告 flag
- **AND** no date is taken from the list
