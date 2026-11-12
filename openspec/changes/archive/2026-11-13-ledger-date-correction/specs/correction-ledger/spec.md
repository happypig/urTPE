## ADDED Requirements

### Requirement: Correct a printed approval date

The ledger SHALL accept a correction whose field is the record's ISO approval
date (`iso_date`). The entry SHALL name the record by its land cell and the
approval date **as printed**, so that the match key stays the gazette's own
content and the entry keeps matching on every rebuild. Applying the entry
SHALL replace the record's `iso_date` with the corrected day and set the
record's year-month-day tuple to match; the printed date text SHALL be kept
unchanged, because it is what the gazette says. Every later step — merge,
member order, the node's date in the graph, the dashboard's figures — SHALL
read the corrected day.

The corrected value SHALL be a calendar day in ISO form (`YYYY-MM-DD`); an
entry with any other value SHALL be refused when it is created, as an entry
naming an unknown field is refused.

#### Scenario: A printed year is corrected

- **WHEN** a ledger entry names a record by its land cell and printed date 2017-05-10 and sets `iso_date` to 2018-05-10
- **THEN** after the ledger applies, the record's `iso_date` is 2018-05-10, its year-month-day tuple is (2018, 5, 10), and its printed date text is unchanged

#### Scenario: Another correction on the same record still matches

- **WHEN** the same record also has a ledger entry for its stage, keyed on the same printed date
- **THEN** both entries apply, because matching uses the printed date and not the corrected one

#### Scenario: A malformed date is refused

- **WHEN** an entry sets `iso_date` to `2018/5/10` or to `2018-02-30`
- **THEN** creating the entry raises an error and nothing is appended
