## 1. Test writing — fully checked before any implementation task

- [x] 1.1 Unit tests for `pick_implementation_payload`: a plan case with fewer
  keys than a later case still supplies 開工/使照; an area split takes each
  area's dates; a field no plan case carries falls back with a flag; the
  emitted `implementation` object stays the best-populated payload.
- [x] 1.2 Attach test (德惠573 shape): milestones_taipei carries the plan
  case's 開工/使照 with milestones_source naming it.
- [x] 1.3 Confirm 1.1/1.2 fail on the current `select_best_payload` path.

## 2. Pipeline implementation

- [x] 2.1 Add `pick_implementation_payload` (plan-case-first for the date
  fields; D5 for statistics).
- [x] 2.2 Wire it into `attach_links_to_projects` (dates → milestones with
  per-field source; statistics unchanged).

## 3. Re-emit (no fetch)

- [x] 3.1 Re-run `--from-js` under the lock; confirm 8 of the 13 national-only
  projects gain 開工/使照 from their plan cases.

## 4. Verification

- [x] 4.1 pytest passes.
- [x] 4.2 scripts/viewer_smoke.js passes.
