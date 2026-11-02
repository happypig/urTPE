# Delta: data-cleansing

## ADDED Requirements

### Requirement: Repair a single-parcel 地號 cell that contradicts its own 案名

When the 案名 declares exactly 1 筆 and names its exact parcel, and the 地號
cell yields exactly one parcel token that differs from the named parcel, the
system SHALL set the record's parcel set to the named parcel. The system
SHALL record the repair in `auto_fixes` (`地號欄單筆地號與案名矛盾→依案名`)
and SHALL flag the record quoting the printed cell. Cells yielding more than
one token (cross-section lists, merge histories), cells agreeing with the
案名, and multi-count 案名 SHALL NOT be repaired. The rule runs offline at
parse time; no network request participates in the decision.

#### Scenario: The 615 row's parcels follow the 案名

- **WHEN** a record's 案名 is `擬訂臺北市內湖區文德段二小段615地號1筆土地都市更新事業計畫案` and its 地號 cell is `臺北市內湖區文德段二小段 1 地號1筆土地`
- **THEN** the record exposes parcels `{615}` and `first_parcel = 615`
- **AND** `auto_fixes` carries `地號欄單筆地號與案名矛盾→依案名`
- **AND** a review flag quotes the printed cell

#### Scenario: A cross-section list is untouched

- **WHEN** a record's 案名 declares 1 筆 on 446-1 but its cell lists 40 parcels across two sections (recno 269 shape)
- **THEN** the cell's parcel list is emitted as published
- **AND** no repair flag or auto_fix is added

#### Scenario: A merge-history cell is untouched

- **WHEN** a record's 案名 declares `518地號1筆(原15筆)` and its cell lists the 14 absorbed parcels (recno 957 shape)
- **THEN** the cell's parcel list is emitted as published

#### Scenario: An agreeing cell gains nothing

- **WHEN** a single-count 案名 names parcel X and the cell's single token is X
- **THEN** no auto_fix and no flag are added

#### Scenario: A multi-count 案名 is untouched

- **WHEN** the 案名 declares 等N筆 with N > 1 and the cell's first token differs from the named parcel
- **THEN** the parcels are emitted as parsed from the cell
