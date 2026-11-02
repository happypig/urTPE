# official-link-discovery Delta

## MODIFIED Requirements

### Requirement: Emit links into the graph document

The system SHALL include a `links` object in the emitted project graph JSON
carrying the national-portal URL and the city-platform case URLs, without
breaking consumers of the existing schema. The `links` object SHALL also
carry `view_verified_case_ids` — the case ids the project's own national view
page names in 相關連結， which the portal itself asserts belong to the unit —
when the discovery result holds them; a result without the field (legacy
cache) emits without the key.

#### Scenario: Link field present on projects with a resolution
- **WHEN** projects.json is generated after discovery
- **THEN** each resolved project carries a `links` object with its twur URL and any city case URLs
- **AND** projects with no resolution carry an empty `links` object

#### Scenario: View-verified ids reach the payload (view/621 shape)
- **WHEN** 北投區-關渡段二小段-303's discovery result carries
  `view_verified_case_ids: ["10803151", "10105152"]` (its view page view/621
  names both cases in 相關連結)
- **THEN** the emitted project's `links.view_verified_case_ids` lists both ids
- **AND** the graph viewer can distinguish portal-asserted cases from
  parcel-search-only cases
