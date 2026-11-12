# Tasks: joined-node-section-callouts

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_joined_node_callouts.py` — the per-case emission: a
  node anchoring 2+ cases whose implementation payloads exist carries
  `implementation_by_case` keyed by case id (the 敦化363-1 shape: -A
  Ulic_Date 2025/04/29, -B 2025/05/06); a single-case node does not carry
  the key.
- [x] 1.2 `tests/test_joined_node_callouts.py` — the round trip:
  `implementation_by_case` survives `--from-js` (the D6 contract).
- [x] 1.3 `tests/test_joined_node_callouts.py` — the counters on the live
  payload: 30 nodes carry 2+ case ids, 28 of them area pairs; after the
  re-emit, 30 nodes carry `implementation_by_case` where ≥2 anchored cases
  hold payloads.
- [x] 1.4 `tests/test_viewer_labels.py` — the badge render: a joined node
  renders one 北 badge per anchored case, each with its own case_id link,
  and the `[A區]` label from the case name's suffix; a single-case node
  renders one badge, no label.
- [x] 1.5 `scripts/viewer_smoke.js` — the callout sizing: no box exceeds the
  widest row's natural width (the no-wrap rule); `CALLOUT_GUTTER_CAP` is
  absent.

## 2. Implementation

- [x] 2.1 `urtpe/links.py` — the per-record snapshot loop collects ALL
  anchored cases' payloads into `implementation_by_case` when 2+ exist.
- [x] 2.2 `urtpe/cli.py` — the loader reads `implementation_by_case` back.
- [x] 2.3 `viewer/app.js` — the joined node renders one 北 badge per case
  with the `[A區]` label (suffix from `candidate_names`); the callout
  renders one box per section on joined nodes, diff compared within a
  section; the sizing drops the cap and the wrap model.
- [x] 2.4 Re-emit the payload.

## 3. Verify

- [x] 3.1 `python -m pytest` — full suite green. *(1314 passed / 1 skipped)*
- [x] 3.2 `node scripts/viewer_smoke.js` — green.
- [x] 3.3 The named examples hold in the payload: 敦化363-1 node 537 carries
  both -A and -B payloads keyed by case id; the 民生134-6 triple likewise.
