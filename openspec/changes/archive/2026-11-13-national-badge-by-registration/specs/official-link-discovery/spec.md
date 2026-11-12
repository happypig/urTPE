## MODIFIED Requirements

### Requirement: Emit links into the graph document

The system SHALL include a `links` object in the emitted project graph JSON
carrying the national-portal URL and the city-platform case URLs, without
breaking consumers of the existing schema. The `links` object SHALL also
carry `view_verified_case_ids` — the case ids the project's own national view
page names in 相關連結 **and whose city case name confirms the unit** — when
the discovery result holds them; a result without the field (legacy
cache) emits without the key. The `links` object SHALL also carry
`view_rejected` (rejected id → reason) and `adopted_from_view` (adopted id →
source project) so a rejection is auditable offline, round-tripped through a
`--from-js` reload like `superseded_by`; a result without either field emits
without the key.

The emission SHALL also resolve the 國 badge per node and carry the result on
the node itself (national-badge-by-registration, user decision 2026-11-12): a
recno node carries `national_badges: true` when the national view page names
it — by case registration (`view_verified_case_ids`), by exact name (the
node's 案名 equals `links.twur_name`), or through the 擬訂 section+parcel
fallback — and never by a national label's date matching the node's date. A
project whose `links.twur` is empty emits no `national_badges` on any node.

#### Scenario: Link field present on projects with a resolution
- **WHEN** projects.json is generated after discovery
- **THEN** each resolved project carries a `links` object with its twur URL and any city case URLs
- **AND** projects with no resolution carry an empty `links` object

#### Scenario: View-verified ids reach the payload (view/621 shape)
- **WHEN** 北投區-關渡段二小段-303's discovery result carries
  `view_verified_case_ids: ["10803151", "10105152"]` (its view page view/621
  names both cases in 相關連結， both confirmed by their city case names)
- **THEN** the emitted project's `links.view_verified_case_ids` lists both ids
- **AND** the graph viewer can distinguish portal-asserted cases from
  parcel-search-only cases

#### Scenario: A rejected id reaches the payload with its reason
- **WHEN** a project's cache records 09511211 in `view_rejected` with reason
  "label is right, id is wrong (shape B)"
- **THEN** the emitted project's `links.view_rejected` carries that entry
- **AND** the id is absent from `links.view_verified_case_ids`

#### Scenario: An adopted id reaches the payload with its provenance
- **WHEN** a project's cache records `adopted_from_view: {"10202065": "中山區-中山段一小段-254地號等13筆"}`
- **THEN** the emitted project's `links.adopted_from_view` carries that entry

#### Scenario: The rejection record survives a reload
- **WHEN** a payload carrying `links.view_rejected` is reloaded with `--from-js` and
  emitted again
- **THEN** the second payload carries the same `links.view_rejected`

#### Scenario: A legacy cache without the fields
- **WHEN** a cache predates the fields
- **THEN** the payload emits without the keys and nothing fails

#### Scenario: The resolved 國 binding rides the node
- **WHEN** the graph document is built for a project with a national page
- **THEN** each node the view page names (registration, exact name, or the
  擬訂 fallback) carries `national_badges: true`
- **AND** no other node carries the field
