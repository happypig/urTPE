## Purpose

Keeps land the sole identity of a renewal unit even when the source 地號 cell is malformed: parcels are recovered from the 案名 when the cell cannot supply them, and the merge weight is rebalanced so identical land keys still link across implementer changes.

## ADDED Requirements

### Requirement: Recover parcels from the 案名 when the 地號 cell is malformed

The system SHALL fall back to the normalized 案名 when the 地號 cell cannot yield a parcel list, deriving the parcel set where the name carries enough information (e.g. `125地號1筆` → `{125}`), while still recording the `缺少地號清單` review flag.

#### Scenario: Single-parcel land recovered from the name
- **WHEN** a 地號 cell reads "臺北市中山區中山段二小段1251筆土地" (missing 地號) and the 案名 reads "…中山段二小段125地號1筆土地…"
- **THEN** the record exposes parcels `{125}` derived from the 案名
- **AND** the record still carries a review flag noting the malformed source cell

#### Scenario: Name fallback preserves the land key
- **WHEN** a 案名 contains "531地號等2筆"
- **THEN** section, first_parcel (`531`), and land_count (`2`) are all preserved from the name-derived identity