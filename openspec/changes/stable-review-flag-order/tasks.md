## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 Two orphan flags naming case ids are emitted in case-id order, whatever order they were raised in
- [x] 1.2 Raising the same flags in the reverse order produces the same emitted list
- [x] 1.3 A flag that names no case id sorts before the flags that do
- [x] 1.4 The flag SET is unchanged by the sort: no flag is added, lost, or duplicated
- [x] 1.5 A node with a single flag is unaffected
- [x] 1.6 The 大龍265-7 node 1242 shape: three orphan flags are emitted in case-id order

## 2. Implementation

- [x] 2.1 `urtpe/graph.py` — the emitter sorts a node's `review_flags` by (case id, text) after the duplicate collapse

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1020 passed, 1 skipped
- [x] 3.2 `scripts/probe_d15_flag_shapes.py` loads the live payload through the real `--from-js` loader and re-emits it: **20** nodes' flag order changes, **0** nodes' flag set changes, **0** nodes' flag count changes
- [x] 3.3 The board row for D9g step 12 is marked done with the measured counts
