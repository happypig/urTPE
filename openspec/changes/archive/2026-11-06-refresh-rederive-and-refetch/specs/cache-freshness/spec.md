## ADDED Requirements

### Requirement: The refresh re-derives the merged milestone projection

After the per-case pass, the refresh SHALL re-derive the project's merged
milestone projection from the cases' own per-case milestones over the project's
case ids, and SHALL write that projection and its per-label source map into the
cache. The refresh previously rewrote each case's milestones and left the
merged projection as it was, so the two drifted apart: measured on 2026-11-06,
85 of the 719 caches that hold per-case milestones diverged from a merge over
their own case ids, 84 lost or altered a label, 66 carried a conflicting
value, and 14 projects emitted no construction date that a case actually holds
(`松山區-寶清段四小段-599地號等27筆` showed no 建照核准 date while its cache held
`2006/05/12` under case `09303270`).

The re-derivation SHALL project the cases **exactly**: a label whose value no
case carries any more SHALL be dropped from the projection, because the city
withdrew or re-dated it (`士林區-光華段四小段-282地號等2筆`'s 審議通過日期 reads
`2026/09/23` today, not the stored `2026/03/18`). The withdrawn-approval rule
(the per-case conflict rule) still governs the per-case layer and is unchanged
by this requirement.

The re-derivation SHALL NOT displace the implementation layer's dates: those
are added at emission time from the data3 payload, not from the merged
projection.

#### Scenario: A case appended after the merge reaches the projection

- **WHEN** a project's cache holds cases `11011241` and `11011242`, whose merged
  projection says `召開幹事會日期 = 2022/11/15`, and the case id `11508023` is
  appended with `召開幹事會日期 = 2026/10/02`
- **THEN** the refreshed projection holds `召開幹事會日期 = 2026/10/02`
- **AND** the source map names the case that won the label

#### Scenario: A withdrawn label leaves the projection

- **WHEN** a project's merged projection holds `公告公展日期 = 2011/01/10` and no
  case carries that label any more (`大同區-市府段二小段-220-2地號等54筆` shape)
- **THEN** the refreshed projection does not hold `公告公展日期`

#### Scenario: A re-dated label carries the new value

- **WHEN** a project's merged projection holds `審議通過日期 = 2026/03/18` and its
  case now reads `2026/09/23`
- **THEN** the refreshed projection holds `審議通過日期 = 2026/09/23`

#### Scenario: A project whose cases did not move keeps its projection

- **WHEN** the cases' per-case milestones are unchanged by the refresh
- **THEN** the refreshed projection equals the stored one

### Requirement: The refresh re-fetches the implementation layer per case

The refresh SHALL re-fetch the implementation payload (the 執行階段 endpoint) and
the rewards payload (the 獎勵資料 endpoint) for every **live** case that
carries an approval date and has no implementation entry, and SHALL store the
replies per case. The refresh previously fetched only the milestones endpoint
and the case header, so a project whose implementation payload was empty stayed
empty: `文山區-實踐段二小段-641地號等1筆` had no 開工 and no 使照 while the live
implementation endpoint for its case `09009032` holds `2004/09/24` and
`2007/10/31`.

The selection SHALL be per case, not per project: a project whose payload
holds entries for other cases still needs the missing one (`萬華區-青年段一小段-130地號等3筆`
holds payload entries for two of its three cases, and the missing one is the one
that carries the dates).

An empty reply SHALL leave the case without an implementation entry, and SHALL
NOT be stored as an empty entry.

#### Scenario: A case with no implementation entry gains one

- **WHEN** a live case carries `核定日期` and the cache holds no implementation entry for it, and the endpoint returns `{"Eng_Start_Date": "2004/09/24"}`
- **THEN** the refreshed cache holds that entry for the case
- **AND** the project's merged projection is unchanged by the fetch

#### Scenario: A case that already has an implementation entry is not re-fetched

- **WHEN** a live case carries `核定日期` and the cache already holds an implementation entry for it
- **THEN** the refresh issues no implementation request for that case

#### Scenario: An empty reply stores nothing

- **WHEN** the implementation endpoint returns no fields for a selected case
- **THEN** the cache holds no implementation entry for that case

### Requirement: A case the city emptied is labelled 無

When the refresh reads an **empty** header row **and** empty milestones for a
case, the refresh SHALL record the case's state as 無, and SHALL NOT keep the
stale state the cache held. Two empty sources in the same refresh are the
measured shape of a case the city moved (`萬華區-青年段一小段-130地號等3筆`'s
`11501041` → `11510008`; `信義區-虎林段四小段-38地號等138筆`'s `11410001` →
`11502012`).

The label SHALL NOT claim a removal: the case keeps its id, it stays in the
project's case list, it keeps its cached data, and no successor is recorded for
it. The city states nothing about a removal, so the pipeline must not claim
one. The parcel search is not part of the rule — the search omits approved ids
for known reasons, so its absence is no evidence.

A case whose header reads a **state** — including a revoked one — SHALL NOT be
labelled 無. `美仁800`'s `09707196` reads 業經本府撤銷核准 and is not this shape:
its header is not empty, so the rule does not touch it.

The refresh report SHALL name every case it labels 無.

#### Scenario: An emptied case is labelled 無

- **WHEN** a case's header row is empty and its milestones are empty, and the cache holds its state as 已核准
- **THEN** the refreshed cache records the case's state as 無
- **AND** the case keeps its id and its entry in the project's case list

#### Scenario: A revoked case is not labelled 無

- **WHEN** a case's header names 業經本府撤銷核准
- **THEN** the case's state is not 無
- **AND** the case's cached data is unchanged

#### Scenario: One empty source is not enough

- **WHEN** a case's header row is empty but its milestones are not
- **THEN** the case's state is not labelled 無 by this rule

#### Scenario: The report names every labelled case

- **WHEN** the refresh labels cases 無
- **THEN** the report names each of them with its case id
