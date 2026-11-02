## 1. Test writing — fully checked before implementation

- [x] 1.1 Add unit test for `nationalLabelKey`: 事業計畫核定日期 → {擬訂, 事業計畫};
  權利變換計畫核定日期 → {擬訂, 權利變換}; 第一次變更… → {變更, …}; 使用核發日期 → null.
- [x] 1.2 Add viewer smoke check: 大安區-通化段四小段-336地號等26筆 shows 國 on recno 3
  (擬訂 事業計畫 ↔ 事業計畫核定日期 111.08.02) and recno 370 (變更 事業計畫 ↔
  第一次變更事業計畫核定日期 112.03.21); no 國 on recno 1.
- [x] 1.3 Add viewer smoke check: view/621 project keeps 國 on its two view-verified nodes
  (10803151, 10105152).
- [x] 1.4 Add viewer smoke check: a project with no view-verified and no matching labels shows
  no 國 on any node.
- [x] 1.5 Add viewer smoke check: the national execution event (使用核發日期) source edge
  starts from the latest bound node, or no edge when none bound.
- [x] 1.6 Confirmed these checks fail on the current (pre-fix) viewer.

## 2. Viewer implementation

- [x] 2.1 Add pure helper `nationalLabelKey(label)` → `{stage, track}` or `null`.
- [x] 2.2 Rewrite `getNodeMilestoneBadges`: 國 when a label binds to the node (date tie-break
  when multiple), or when view_verified_case_ids applies; remove the `node.is_current` branch.
- [x] 2.3 National execution event source edge starts from the latest bound node; no edge when
  no node bound.
- [x] 2.4 Remove `callout-gutter`-era dead code if present (none; standalone change).

## 3. Verification

- [x] 3.1 `node scripts/viewer_smoke.js` passes the new checks plus the existing overlap guard.
- [x] 3.2 `python -m pytest` passes (viewer-only change).
