# tasks — emit-stage-index

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_stage_index_roundtrip.py`:
      (a) `build_project_graph` emits `stage_index` on every node;
      (b) a 3-stage family with distinct `area_section` values (擬訂/變更/變更(第二次)
      × 甲/A/B) forms `section` edges on the original build;
      (c) the same document loaded through `_load_projects_from_js` and re-emitted
      forms identical `section` edges (the bug's end-to-end statement);
      (d) a node lacking the `stage_index` key derives it from stage text on load
      (no `-1` sentinel unless the original had one);
      (e) emit → load → emit is lossless for `stage_index` on every node.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `urtpe/graph.py`: `build_project_graph` adds `"stage_index":
      r.stage_index` to the node dict (beside the existing additive keys).
- [x] 2.2 `urtpe/cli.py` `_load_projects_from_js`: when the node carries no
      `stage_index` key, derive it via `cleanse_mod._stage(node.get("stage") or "")`.
- [x] 2.3 `scripts/run_links_from_js.py`: the same derivation at its `stage_index`
      read.

## 3. Acceptance

- [ ] 3.1 Full suite green; the fixture-less emission (flag-less bytes) unchanged
      apart from the new node key.
- [ ] 3.2 `openspec validate` passes; both boards updated; commit.
