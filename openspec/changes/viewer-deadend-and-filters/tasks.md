## 1. Tests first

- [ ] 1.1 `tests/test_viewer_labels.py`: chain-edge rule — a VM fixture with virtual 09902261 (已失效) → 10201171 (已駁回) yields no pair; a live → live pair (自行撤回 → 施工中 is a dead start — use two live members, e.g. schedule "") still chains
- [ ] 1.2 `tests/test_viewer_labels.py`: dotted-edge rule — the under-fallback is skipped for a dead-end orphan (fixture: one orphan 已失效 above one recno row → no orphan edge); a live orphan in the same shape gains the edge; the row-above branch is untouched
- [ ] 1.3 `tests/test_viewer_labels.py`: no `status-chip`/`never-badge`/`neverApproved`/`審查中` chip code remains; the dead-end badge renders after `stageBadge` and reads the is_current node's first case schedule
- [ ] 1.4 `tests/test_viewer_labels.py`: DIMS — 事業種類 options are exactly the four real tracks; the stage dimension is labelled 計畫與執行 with the ten options; `matches` gives a construction project no 計畫 option and a combined-track current node only 事業計畫、權利變換
- [ ] 1.5 `tests/test_viewer_labels.py`: the 相關連結 "未曾核定" note is gone
- [ ] 1.6 Run the new tests, record the expected failures

## 2. Implementation (viewer only)

- [ ] 2.1 `viewer/app.js`: `isDeadEnd` helper; `virtualChainPairs` skips dead-end upstream members (design D2)
- [ ] 2.2 `viewer/app.js`: §4 dotted-edge under-fallback gated on `!isDeadEnd(schedule)` (design D3)
- [ ] 2.3 `viewer/app.js`: replace `statusChip`/`neverChip` with `deadEndChip` after the construction badge; delete `neverApproved`, `familyScheds`, `NO_STATE_FAMILY`, the scheduleBadgeText family use in the list (keep per-case 相關連結 badges) (design D4)
- [ ] 2.4 `viewer/app.js`: remove the "未曾核定… 無國土管理署入口網頁" note (spec viewer-related-links)
- [ ] 2.5 `viewer/app.js`: DIMS — drop 其他/都市更新計畫, rename 施工階段 → 計畫與執行, ten options, exclusive state match in `matches` (design D5)
- [ ] 2.6 Full suite `python -m pytest` green; `node scripts\viewer_smoke.js` green; AGENTS.md collected count refreshed if tests changed

## 3. Archive

- [ ] 3.1 `openspec archive viewer-deadend-and-filters` (syncs the six deltas)
- [ ] 3.2 Board: D4b–d marked done with the commit SHA
