# official-link-discovery — Delta: Taipei case search strictness

## ADDED Requirements

### Requirement: Taipei case search rejects cases outside the searched parcel

`search_taipei_cases_api` SHALL keep a searched case only when the case's own
`case_name` contains the searched parcel — the anchor record's named first
parcel (mono part; sub-parcel suffix tolerated in 之 ↔ - and full-width ↔
ASCII forms) — extending the §6.7 guard to all cross-family pollution.
Cases whose name lacks the searched parcel (sibling R13 概要 cases, foreign
same-section cases) SHALL NOT enter `city_case_ids`, and therefore SHALL NOT
contribute milestones to the project's merged timeline.

#### Scenario: Own-family cases survive the guard
- **WHEN** the search for 寶清段一小段 parcel 57-13 returns 10212211
  (擬訂…57-13地號等1筆…) and 10212212/10212214/11412018 (…57-13地號等1筆…)
- **THEN** all four remain in `city_case_ids`

#### Scenario: Foreign same-section case rejected
- **WHEN** the search for 正義段四小段 parcel 115 returns case 11102211
  (擬訂…正義段四小段**133地號**1筆…)
- **THEN** 11102211 is dropped — its name lacks parcel 115

#### Scenario: Sibling R13 概要 case rejected
- **WHEN** the search for 南港段一小段 parcel 520-2 returns 概要 cases on
  522等45筆 / 467等41筆 / 403-2等28筆 / 561等5筆 (§6.7)
- **THEN** the four siblings are dropped; 09407070/71/73 (520-2等18筆) remain

#### Scenario: Notation drift tolerated
- **WHEN** the searched parcel is 263-19 and a case name writes 263之19
- **THEN** the case is kept (drift-tolerant comparison, same rule as the
  national strict matcher)
