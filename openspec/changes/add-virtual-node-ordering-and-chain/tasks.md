# Tasks: add-virtual-node-ordering-and-chain

## 1. Test-writing group (BDD scenarios from the spec delta — tests first)

- [x] 1.1 `tests/test_viewer_labels.py` structural: comparator uses effective
      case_id (real → `links.taipei[0]`, virtual → `case_id`) before the
      區段 tie-break; chain-edge guard (`virtual` involved pairs only, never
      real↔real, never cross-cluster)
- [x] 1.2 Ordering unit scenarios (render-logic level): attempt-twin pair
      (09902261 < 10201171) orders stable; real anchoring 09811141 sorts after
      virtual 09506200; case-less real node sorts first
- [x] 1.3 Chain-edge scenarios: consecutive virtuals in one cluster chained
      (dashed); cross-stage same-day clusters unchained; real↔real consecutive
      pairs produce no new edge

## 2. Implementation (viewer)

- [x] 2.1 `viewer/app.js` cluster member sort: effective-case_id tie layer in
      the dated-member comparator (real key = `links.taipei[0]`, virtual key =
      `case_id`, empty-key real first); 區段 ordering only between
      equal/empty keys
- [x] 2.2 `viewer/app.js` edge rendering: dashed virtual chain edges between
      consecutive virtual positions inside each cluster; skip real↔real pairs
      and cross-cluster pairs

## 3. Acceptance / verification

- [x] 3.1 Full suite green
- [x] 3.2 Live verification: 吉林段三小段1021 — 09902261 above 10201171 with
      a dashed chain edge; 吉林段四小段676 — 概要/計畫 clusters unchained;
      no duplicate edges between real members; order stable across reload
