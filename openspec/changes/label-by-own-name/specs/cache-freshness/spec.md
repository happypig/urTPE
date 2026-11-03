## ADDED Requirements

### Requirement: The emitted payload carries the national page's own name

The pipeline SHALL store the project's national view page `<title>` 案名 as `twur_name` in the cache and the emitted payload, parsed from the cached `view.html` at absorb time (re-parse, no request). The title is the portal's own name for the project — its first 擬訂 case — and the viewer labels the 國 entry with it (C10: 452 of 632 projects with a cached page showed the wrong name under the current-node rule). A cache without `view.html` emits without the key.

#### Scenario: twur_name reaches the payload
- **WHEN** a project's cached `view.html` `<title>` reads "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案-都更查詢-內政部國土管理署都市更新入口網"
- **THEN** `links.twur_name` carries "擬訂臺北市中山區吉林段四小段705地號等47筆土地都市更新事業計畫案"

#### Scenario: A cache without a view page emits without the key
- **WHEN** the cache holds no `view.html`
- **THEN** the payload carries no `twur_name` key for the project
