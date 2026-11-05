## ADDED Requirements

### Requirement: Read the 地號 cell's district from the collected district enum

The system SHALL read a record's `district_land` from the 地號 cell by matching
the cell's text against the **collected district enum** — the set of 行政區
values the corpus itself publishes (中山區 中正區 信義區 內湖區 北投區 南港區
士林區 大同區 大安區 文山區 松山區 萬華區) — rather than by requiring the cell
to print the prefix `臺北市`. The city prints three typos in this column
(`臺北大安區`, `臺北士林區` — the 市 is missing; `臺北市投區` — the 北 is
missing) and the reader must not absorb them.

The enum SHALL be collected from the corpus's own 行政區 column, so the set of
known districts is never a hard-coded list in the reader. A cell naming a
district the enum does not hold SHALL read `''`; the system SHALL NOT infer the
missing character.

Reading the district this way SHALL NOT change the record's section or its
parcel set. The section is split on the `臺北市` anchor and the parcel list is
read from the cell's own text, so both are independent of the district token.

The `行政區與地號行政區不一致` flag SHALL keep firing on a cell whose printed
district token differs from the record's 行政區, and SHALL quote the **printed**
token. The flag reports the publisher's contradiction; `district_land` reports
the normalized district. A cell reading `臺北市投區` therefore yields
`district_land = ''` **and** keeps the flag `行政區與地號行政區不一致(地號為投區)`.

The rule takes effect on a PDF ingest. A rebuild from emitted state carries the
stored `district_land` forward unchanged.

#### Scenario: A cell that omits 市 reads its district

- **WHEN** a record's 行政區 is `大安區` and its 地號 cell is `臺北大安區辛亥段四小段 496-13、196-15、507、508、509-2、510、510-1、…`
- **THEN** the record's `district_land` is `大安區`
- **AND** its section is `辛亥段四小段`
- **AND** its parcel set is unchanged

#### Scenario: A cell that omits 北 reads nothing

- **WHEN** a record's 行政區 is `北投區` and its 地號 cell is `臺北市投區崇仰段三小段 156、157、160、161、165、166、168、169、170、…`
- **THEN** the record's `district_land` is `''`
- **AND** the record carries the review flag `行政區與地號行政區不一致(地號為投區)`
- **AND** the system does NOT infer `北投區` from the cell

#### Scenario: The mismatch flag still fires on the corrected rows

- **WHEN** a record's 行政區 is `大安區` and its 地號 cell is `臺北大安區辛亥段四小段…`
- **THEN** the record carries no `行政區與地號行政區不一致` flag, because the enum read and the 行政區 agree

#### Scenario: A cell that prints the district normally is unchanged

- **WHEN** a record's 行政區 is `中山區` and its 地號 cell is `臺北市中山區長春段二小段 775…`
- **THEN** the record's `district_land` is `中山區`
- **AND** the record's section, parcels and flags are unchanged

#### Scenario: The project identity does not move

- **WHEN** the district of the 地號 cell is re-read from the enum
- **THEN** the record's `project_id` is unchanged, because the project identity is built from the 行政區 column
