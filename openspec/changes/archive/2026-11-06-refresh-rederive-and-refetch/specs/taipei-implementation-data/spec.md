## ADDED Requirements

### Requirement: A 無 case's payload never wins the selection

When a project's cases are ranked for the implementation and rewards payloads,
a case whose recorded state is 無 SHALL NOT be ranked, and its payload SHALL
NOT supply any date. The rule applies to **both** selection layers:

- the key-count pick — the payload with the most keys wins;
- the plan-case date collection — the dates are gathered over every 擬訂 plan
  case, and a field no plan case carries falls back to the key-count pick.

A 無 case's payload is a stale copy: the city moved the case to a new id and
emptied the old one, so the cached copy holds values the live case no longer
has (`萬華區-青年段一小段-130地號等3筆`'s `11501041` copy says
`Settle_Old_Doors = 0.0`, the live `11510008` says `140.0`). Measured offline
on 2026-11-06, a 無 case already wins the pick in 4 projects
(`信義區-雅祥段一小段-227-4地號等10筆`, `北投區-立農段五小段-163-2地號等4筆`,
`萬華區-萬華段二小段-894地號等22筆`, `中山區-吉林段四小段-705-3地號等14筆`).

The rule SHALL apply even when the live sibling's payload is **smaller** than
the 無 case's. A near-empty live payload is the live answer, and the
refresh's report names the case, the before size and the after size, so the
shrink is visible rather than silent. Keeping the stale copy when it is
larger would let the defect the rule exists to fix keep winning.

The conflict flags that name a 無 case SHALL stay: they report the
disagreement honestly.

#### Scenario: A 無 case's larger payload does not win

- **WHEN** a project holds case `11009142` with a 26-key implementation payload
  recorded as 無, and case `11009141` with a 1-key payload recorded as live
- **THEN** the project's implementation payload comes from `11009141`

#### Scenario: A 無 case supplies no date

- **WHEN** a project holds a 擬訂 plan case recorded as 無 and another 擬訂 plan
  case recorded as live
- **THEN** the dates are gathered over the live case only
- **AND** the 無 case supplies no date

#### Scenario: A project whose only case is 無 keeps the empty answer

- **WHEN** every case of a project is recorded as 無
- **THEN** the project carries no implementation payload
- **AND** no case is credited for a date

#### Scenario: The conflict flag that names the 無 case stays

- **WHEN** a 無 case's payload disagrees with a live case's payload on a field
- **THEN** the flag naming the disagreement is still emitted
