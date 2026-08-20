## MODIFIED Requirements

### Requirement: Derive structured fields

The system SHALL derive and expose structured fields per record: 段X小段, first parcel, full parcel set with 原地號 aliases, parcel count, original count (原N筆), named anchor (原XX基地/國宅/整宅), 區段 (甲/A/B), stage (擬訂/變更/變更(第N次)), and plan track (事業計畫/權利變換).

#### Scenario: Parcel and count parsing
- **WHEN** a 地號 cell is "臺北市北投區奇岩段三小段 1-1、85、86、…地號等11筆土地"
- **THEN** clean.tsv exposes section="奇岩段三小段", first_parcel="1-1", parcel set {1-1,85,86,…}, and land_count=11

#### Scenario: Coverage change annotation captured
- **WHEN** a 案名 contains "(原10筆)"
- **THEN** the original count (10) is captured in orig_count separately from the current count

#### Scenario: Parcel renumbering alias captured
- **WHEN** a 地號 cell is "689地號(原726地號)等40筆土地"
- **THEN** the parcel set includes alias 726 for parcel 689

#### Scenario: Named anchor captured
- **WHEN** a 案名 references "原東星大樓基地"
- **THEN** the named_anchor field is populated with that anchor

#### Scenario: Stage and track derived
- **WHEN** a 案名 is "變更(第二次)…都市更新權利變換計畫案"
- **THEN** stage="變更(第二次)" and track="權利變換" are derived

#### Scenario: Parcels derived from the 案名 when the 地號 cell is malformed
- **WHEN** a 地號 cell cannot supply a parcel list (e.g. "…1251筆土地" missing 地號) but the 案名 identifies the parcel (e.g. "…125地號1筆土地…")
- **THEN** the parcel set is populated from the 案名
- **AND** the malformed source cell is still flagged in review_flags