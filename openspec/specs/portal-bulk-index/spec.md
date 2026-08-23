# portal-bulk-index Specification

## Purpose
Build and cache a local index of all national-portal (內政部國土管理署都市更新入口網) Taipei rebuild cases — each case's view_id paired with its normalized land-identity core — from a single bulk crawl of the portal list pages, so projects can be joined to the portal offline without per-project searches.
## Requirements
### Requirement: Crawl all portal list pages into a local index

The system SHALL crawl the national portal's rebuild-case list restricted to 臺北市 (`city_id=2`) across all list pages in one bulk pass, and SHALL parse every case row into an index entry carrying the case's view_id and its normalized land-identity core derived from the case title.

#### Scenario: Bulk crawl covers all pages
- **WHEN** the index build runs against the portal
- **THEN** it requests list pages until an empty or non-existent next page is seen
- **AND** the resulting index contains one entry per case row found across all pages

#### Scenario: Land-identity core is normalized from the case title
- **WHEN** a list row's title is "擬訂臺北市大同區玉泉段二小段40地號等29筆土地都市更新事業計畫及權利變換計畫案"
- **THEN** the index entry's core is derived from the same district + section + first parcel + count normalization the pipeline uses, independent of the 擬訂/變更 stage prefix

#### Scenario: Duplicate cores are preserved for review
- **WHEN** two distinct portal cases normalize to the same land-identity core
- **THEN** both entries are kept in the index
- **AND** the join step treats that core as ambiguous (multiple candidates) rather than silently picking one

### Requirement: Persist and reuse the index across runs

The system SHALL persist the built index to a JSON file (`portal_index.json`) in the output directory, and SHALL reuse the persisted index on subsequent runs instead of re-crawling, unless a fresh rebuild is explicitly requested.

#### Scenario: Cached index skips the bulk crawl
- **WHEN** discovery runs and a valid `portal_index.json` exists
- **THEN** no list-page HTTP requests are made
- **AND** the join uses the cached entries

#### Scenario: Fresh rebuild replaces the cache
- **WHEN** discovery runs with the fresh option set
- **THEN** the list pages are re-crawled and `portal_index.json` is overwritten

#### Scenario: Missing or corrupt index triggers rebuild
- **WHEN** `portal_index.json` is absent or cannot be parsed
- **THEN** the bulk crawl runs again to regenerate it

