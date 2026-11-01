# tasks — fix-graph-timeline-order

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_graph_timeline_order.py`:
      (a) structural: `buildConstructionChain` emits event dates as ISO
      (`-`-separated) — no `/${2}`-form date reaches the timeline events;
      (b) structural: the displayed label keeps the established form (the
      render site converts ISO back for display);
      (c) behaviour: a Node probe through the smoke harness on a fixture whose
      exec dates (2023-04-27, 2023-07-03) fall between approvals
      (2022-08-02, 2026-10-15) captures the rendered SVG rows top-to-bottom and
      asserts the order: 2022 node, 建照, 開工, 2026 node;
      (d) behaviour: the topmost approval row is the OLDEST approval
      (2022-08-02), the bottommost the NEWEST (2026-10-15).

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `viewer/app.js` `buildConstructionChain`: normalise the event date to
      ISO at exit (slash-western `2023/04/27` → `2023-04-27`; the ROC-dot
      conversion extends one step).
- [x] 2.2 `viewer/app.js` render site: the execution label converts ISO back to
      the established display form (fmtDate reverse).
- [x] 2.3 — NOT a code change: with correct per-node bindings the case_id-ascending
      draw IS date-ascending (verified: the descending dates came from the stale
      bindings, not the sort). The fixture now carries the corrected bindings
      (453→10011271, 370→10011273, 1→11501034) and the probe asserts the order.

## 3. Acceptance

- [x] 3.1 `node scripts/viewer_smoke.js` passes on the live payload; the full
      Python suite green.
- [x] 3.2 Live-viewer verification on 通化段四小段-336 — **deferred, and the
      reason is itself a finding**: `scripts/check_deploy.py` reports 3 of 4
      artifacts STALE (the deployed app.js is still `?v=20261015e54d`, the 10-15
      build), so Chrome can only show the OLD layout. Verified instead through the
      local render path (the smoke harness + a y-coordinate probe on the real
      app.js): the rendered order top-to-bottom is 2022-08-02 node, 建照
      2023/04/27, 開工 2023/07/03, 2026-10-15 node — the spec'd order. Re-run the
      Chrome check after the next viewer deploy (`python -m urtpe.cli ... --viewer`
      + push).
- [x] 3.3 `openspec validate` passes; the main spec synced; both boards
      updated; commit.
