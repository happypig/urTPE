## 1. Test writing — fully checked before any implementation task

- [x] 1.1 Add a pytest case that extracts `bindNationalLabels` + `nationalLabelKey` +
  `trackMatches` from app.js and runs them under node: single-candidate label
  binds its node whatever the date; multi-candidate label with distinct dates
  binds by exact date; ±1-day window decides the near case; a tie ±1 day
  cannot break binds nothing; 使用核發日期 / application dates bind nothing.
- [x] 1.2 Add a smoke check naming 文林64 (recnos 1086, 693) and 潭美579-2
  (recnos 673, 627, 618): before the fix both projects badge more nodes than
  labels bound; after, the count of 國 from label binding equals the count of
  bound labels.
- [x] 1.3 Confirm the new tests fail on the current viewer
  (`nationalBoundTo` scores per node).

## 2. Viewer implementation

- [x] 2.1 Add `bindNationalLabels(project)` → {recno: [labels]} (per-label
  decision: exact, ±1 day, nothing on 0 or 2+ survivors).
- [x] 2.2 Rewrite `getNodeMilestoneBadges` to consult the binding map (keep
  the `view_verified_case_ids` source; keep one 國 per node).
- [x] 2.3 Remove `nationalBoundTo`.

## 3. Verification

- [x] 3.1 `python -m pytest` passes (viewer-only change).
- [x] 3.2 `node scripts/viewer_smoke.js` passes all checks, including the new
  per-label binding assertions.
