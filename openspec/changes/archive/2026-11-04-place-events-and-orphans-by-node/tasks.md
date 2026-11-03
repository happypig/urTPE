## 1. Test writing (overlap guard + orphan edge) — fully checked before any implementation task

- [x] 1.1 Extend smoke guard rect sources: include orphan virtual-node label rects and nameless-orphan rects (shifted 32px right) in `layoutRects` consumption.
- [x] 1.2 Add smoke check that each orphan (named virtual node) renders a dotted `edge orphan` line to its nearest recno node in time.
- [x] 1.3 Extend overlap guard check 1 (no intersecting rects) to run on every project with callouts OR orphans (not only callouts).
- [x] 1.4 Confirm checks fail on 北投區-關渡段二小段-303地號等5筆 with current layout (orphan on track line, no dotted edge).
- [x] 1.5 pytest viewer labels/structural tests still pass.

## 2. Viewer implementation — §3 events ½ row under nearest node

- [x] 2.1 Row pitch: approval→event advances NODE_ROW/2 (32px); event→approval keeps NODE_ROW (64px); approval→approval NODE_ROW; event→anything EVENT_ROW.
- [x] 2.2 CSS: no new style needed for events (existing event layout).

## 3. Viewer implementation — §4 orphans dotted edge + by-date placement

- [x] 3.1 Named orphans: dotted `edge orphan` to nearest recno node in time; 32px right shift when in a track column; label rect uses shifted x.
- [x] 3.2 Nameless orphans: by-date row in nearest recno node's column + 32px right shift + dotted edge; no date → no row (current corpus has none with a date).
- [x] 3.3 Remove interim ghost column machinery (`interimOrphans`, `ghostPosRaw`, `ghostColX`, `ghostRows`, orphan anchor rendering block).
- [x] 3.4 CSS: add `.edge.orphan` dotted style.

## 4. Verification

- [x] 4.1 `node scripts/viewer_smoke.js` passes guard checks 1–3 on every project with callouts or orphans.
- [x] 4.2 `python -m pytest` passes (viewer-only change).
- [x] 4.3 Manual: 336 建照 sits 32px under node 370; 303 orphan 32px right of 權利變換 track with dotted edge; nameless anchors gone from their ghost column.
