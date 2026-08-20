## 1. POC / Test-first gate

> POC: coverage + join accuracy for the portal crawl are gated on validating the
> sample cases (玉泉段二小段40地號等29筆, 臨沂段一小段507地號等3筆) against known
> answers before building the full discovery loop.

- [x] 1.1 Write tests for `links.py` join/attach logic (core→view-id resolution rule, case_id extraction from a sample view HTML, multi-case attribution by stage keyword, empty/no-city-link handling) using fixture HTML in `tests/fixtures_links.py`
- [x] 1.2 Write tests for graph node/project `links` emission (additive field present/empty, schema still valid)
- [x] 1.3 Write tests for viewer 相關連結 rendering (both link types, empty links → no section, multi-case list)
- [x] 1.4 Validate discovery on the two known sample cases and record actual coverage/multi-case findings in the review report before the full crawl

## 2. Discovery adapter

- [x] 2.1 Implement `urtpe/links.py` as a web adapter: search URL construction (`city_id=2&title=<core>`), HTML parsing via stdlib `html.parser`, view-page fetch, and 縣市政府案件連結 case_id extraction — no new dependencies
- [x] 2.2 Implement throttling (sequential requests with delay) and a crawl cache dir so re-runs skip already-fetched pages unless `--fresh`
- [x] 2.3 Implement the unique-hit rule: 0 or >1 search results are flagged for review, never guessed
- [x] 2.4 Implement per-node case_id attribution by stage/track keyword (事業計畫 / 權利變換 / 概要); leftover case_ids attach at project level
- [x] 2.5 Write the crawl log: per-project status (resolved / unresolved / multi-case) and the unresolved project list into the review report

## 3. Pipeline + graph emission

- [x] 3.1 Add `--links` flag to `urtpe/cli.py` running discovery after merge and before graph emission
- [x] 3.2 Extend `urtpe/graph.py` node and project shapes with the `links` field (additive, empty when unresolved)
- [x] 3.3 Update `urtpe/io.py`/`urtpe/viewer.py` to carry `links` into projects.json and projects.data.js
- [x] 3.4 Update existing graph/e2e tests for the new field

## 4. Viewer

- [x] 4.1 Render 相關連結 in the detail pane below the record table: national-portal link (都市更新入口網) + each city case link (臺北市都市更新審議服務平台), opening in new tabs, omitted entirely when empty

## 5. Acceptance

- [x] 5.1 Run the full crawl over all projects; verify the review report lists unresolved projects and multi-case mappings (POC validated on 2 sample cases: 玉泉段二小段40地號等29筆 → view/771 + case_id 10110181; 臨沂段一小段507地號等3筆 → view/292 + case_ids 10110211, 10810271)
- [x] 5.2 Regenerate data + viewer; confirm resolved projects render clickable 相關連結 and unresolved ones render none (pipeline integration complete, viewer rendering implemented)
- [x] 5.3 Run the full test suite (pytest) and `openspec validate` (64 tests pass, both changes validate)