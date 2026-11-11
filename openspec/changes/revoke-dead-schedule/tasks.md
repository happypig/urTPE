# Tasks: revoke-dead-schedule

## 1. Tests first (test-first gate)

- [x] 1.1 `tests/test_links.py` (or a new `tests/test_revoke_schedule.py`):
  `schedule_from_top` maps `NAME` = 業經本府撤銷核准 → 已撤銷; a `NAME`
  holding 撤回 still maps 自行撤回; an ordinary 核定 NAME still maps 已核准.
- [x] 1.2 `TERMINAL_SCHEDULES` contains 已撤銷; a case cached 已撤銷 is not
  re-selected by the awaiting-approval selection (reuse the existing
  selection test shape in `tests/test_refresh_awaiting_caches.py`).
- [x] 1.3 `_DEAD_SCHEDULES` / `filter_live_cases`: a same-name pair where one
  case is 已撤銷 and the other is approved binds the approved one (the
  東湖34 / 吉林705 test shape, with 撤銷 in place of 撤回).
- [x] 1.4 Viewer: `isDeadEnd('已撤銷')` is true — pinned in
  `tests/test_viewer_labels.py` alongside the existing dead-end chain pins
  (the file holds node/DOM-stub tests; add the schedule-word pin there).

## 2. Implementation

- [x] 2.1 `urtpe/links.py` `schedule_from_top`: the 撤銷 branch, placed
  before the 核定/核准 checks (撤銷核准 contains 核准; the branch must win).
  Cite this change's reason.
- [x] 2.2 `urtpe/links.py`: `TERMINAL_SCHEDULES` and `_DEAD_SCHEDULES` gain
  已撤銷.
- [x] 2.3 `viewer/app.js` `isDeadEnd` gains 已撤銷, with the comment naming
  the measured corpus (7 cases).

## 3. Verify

- [x] 3.1 `python -m pytest` — full suite green. *(1194 passed / 1 skipped)*
- [x] 3.2 `node scripts/viewer_smoke.js` — green. *(after the smoke's DEAD set gained 已撤銷 to match)*
