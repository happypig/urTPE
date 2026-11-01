# tasks — viewer-stage-chip-coverage

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_viewer_stage_chip.py` (structural, over app.js):
      (a) a `statusChip`-equivalent derivation exists and reads
      `case_schedules`;
      (b) the grey chip renders 審查中 when a schedule holds 審查中 and no
      construction stage exists;
      (c) it renders 撤回 when schedules are 自行撤回/已駁回/已失效 only;
      (d) a construction stage suppresses the status chip;
      (e) no schedules → no chip.
      Exercised through the smoke harness (render app.js against a fixture
      dataset), asserting DOM output.
- [x] 1.2 `tests/test_viewer_cell_format.py` (same harness):
      (a) the 地號清單 cell renders `、`-joined prose;
      (b) empty dict/list and null render —;
      (c) the three date forms render ISO in the detail pane
      (`2026-10-15`, `2011/11/27`, `100.12.20` → ISO).

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `viewer/app.js`: the status-chip derivation + render in `renderList`.
- [x] 2.2 `viewer/app.js`: `fmtCell` applied to the table columns; `fmtDate`
      applied at the detail pane's date sites.

## 3. Acceptance

- [ ] 3.1 `node scripts/viewer_smoke.js` passes on the live payload; the full
      Python suite green (structural tests included).
- [ ] 3.2 `openspec validate` passes; both main specs synced; both boards
      updated; commit.
