# tasks — refresh-case-status-and-drop-withdrawn-fields

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_gaiyao_track.py` additions (domain, D1): `schedule_from_top`
      maps `權利變換計畫階段─申請報府核定中` and
      `事業計畫及權利變換計畫階段─申請報府核定中` to 審查中; `業經本府核定` stays
      已核准; `無` stays "". RED: the two pending NAMEs fail.
- [x] 1.2 `tests/test_case_status_refresh.py` (new, domain, D2):
      `refreshed_schedule` — 68 shape (已核准 + pending NAME → 審查中); 163-2
      shape (審查中 + 無 → 審查中); 虎林 shape (已核准 + 無 + no approval date →
      ""); 施工中/已完工/完成成果備查 + approved NAME → kept; 已核准 + 無 + an
      approval date → kept. RED: the function does not exist.
- [x] 1.3 `tests/test_cache_freshness.py` additions (selector, D5): a project
      whose only awaiting cases are cached 自行撤回/已駁回 (南海687/信義142/三玉672
      shapes) is not selected; one 自行撤回 + one 審查中 awaiting case is
      selected; the existing six selector tests still pass. RED: the terminal
      project is selected today.
- [x] 1.4 `tests/test_case_status_refresh.py` (adapter, D3): `refresh_project`
      with an injected fetcher — 光華282 shape drops 申請核定日期 and reports it
      removed; a reply lacking a cached 核定日期 keeps it and reports a
      conflict; an empty reply and a raising fetcher leave the case unchanged.
      RED: the drop and the report keys fail.
- [x] 1.5 `tests/test_case_status_refresh.py` (adapter, D4): the **default**
      path — `refresh_project(tmp, pid)` with no fetcher injected, both module
      adapters monkeypatched — rewrites 已核准 → 審查中 for the 68 shape, reports
      the change with its NAME, and lists a 自行撤回 header as `closed`, not
      `still_awaiting`. RED: the default path refreshes milestones only.
- [x] 1.6 `tests/test_viewer_schedule_badge.py` (new, viewer, D6, acceptance):
      evaluates `scheduleBadgeText` from `viewer/app.js` in Node — 已核准 and
      已核定 give "", 審查中 gives ` [審查中]`, 自行撤回 gives ` [自行撤回]`. RED:
      已核定 renders a badge.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `urtpe/links.py` `schedule_from_top`: pending phrase before the
      approved test (D1).
- [x] 2.2 `urtpe/links.py` `refreshed_schedule` (pure, D2) and
      `fetch_taipei_status_api` (adapter: top.ashx → derived schedule + NAME).
- [x] 2.3 `urtpe/links.py` `refresh_project`: milestone replacement with
      `removed` / `conflicts`; status re-derivation with `status_changes`;
      `closed` bucket; `fetch_status` default per D4.
- [x] 2.4 `urtpe/links.py` `cached_cases_awaiting_approval(case_milestones,
      case_schedules=None)` skips terminal cases; the script passes the cached
      schedules.
- [x] 2.5 `scripts/refresh_awaiting_caches.py`: print status changes (was → now
      + NAME), removed labels, conflicts, and the closed bucket; summary line
      counts each.
- [x] 2.6 `viewer/app.js` `scheduleBadgeText` omits 已核定 too; spec wording
      for the vocabulary.
- [x] 2.7 Full suite green (`python -m pytest`), `node scripts/viewer_smoke.js`
      passes, `openspec validate --all` passes.

## 3. Live acceptance

- [x] 3.1 Back up `data/.link_cache` to `data/.link_cache_backup_20261102_status`;
      record the `statusChip` / never-approved project counts from the current
      payload.
- [x] 3.2 Live `scripts/refresh_awaiting_caches.py` (single writer): record the
      candidate count, every status change with its NAME, removed labels,
      conflicts, the closed bucket; confirm the 13 cases match the 2026-11-02
      manual check (8 status corrections incl. 68/128 → 審查中, 光華282 drops
      申請核定日期, 南海687/信義142/三玉672 not selected).
- [x] 3.3 Re-emit (`--from-js viewer/projects.data.js -o data --viewer viewer
      --links --recover-truncated`): exit 0, tripwire PASS, record/project counts
      unchanged (1,442 / 694); the never-approved count does not rise.
      Result: exit 0, 1,442 / 693 (the payload already read 693 before this
      run), never-approved 3 → 3, 審查中-chip projects 56 → 67, links 685 / 8 / 0.
- [x] 3.4 Chrome over `file://`: 中正段一小段-68 相關連結 shows 10406283 `[審查中]`
      and 10406282 no badge; 振興段一小段-128 shows 10304127 `[審查中]`; 南海段一小段-687
      shows 11012301 `[自行撤回]`. Done on a 127.0.0.1 server (the extension
      refuses file://), DOM-verified; also 光華282 11408032 `[審查中]` and 虎林38
      10806141 with no badge.
- [ ] 3.5 Commit, push, `python scripts/check_deploy.py` all FRESH, and repeat
      3.4 on `https://happypig.github.io/urTPE/viewer/` after a force-reload.
- [ ] 3.6 Books: archive with spec sync; append §35 to
      `docs/portal_operations_log.md`.
