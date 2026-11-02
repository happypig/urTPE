# tasks — fix-row-order-tiebreak-and-view-badges

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_row_order_same_case.py` (new): the 254 shape — nodes
      1232 (2012-08-27) and 1039 (2016-08-23) share case 09811141 — renders
      1232 above 1039; the 614 shape renders 1216 → 1098 → 906; the 639
      shape renders 862 → 580; the 336 order (453 → 370 → 建照 → 開工 → 1)
      is unchanged. RED: 3 fail (probe renders all three inverted), the 336
      pin passes.
- [x] 1.2 `tests/test_cache_freshness.py` additions: the widened selector
      (a) selects a case carrying only 申請計畫日期/申請權變日期 with no
      approval (the 303 shape), (b) selects 申請概要核准日期 too, (c) still
      skips a case with any approval date, (d) still skips a cache with no
      cases. RED: 2 fail; the pre-existing 4 selector tests still pass.
- [x] 1.3 `tests/test_refresh_binding_effect.py` additions: the 303 shape —
      before the refresh `_match_case_by_date('2026-09-30')` misses (positional
      fallback would bind 10803151), after it binds 11505020, the older nodes
      stay correct, and no two nodes share a key. GREEN by design, like the
      archived change's 1.2: the matcher is already correct; the refresh
      (not a matcher change) supplies the missing date.
- [x] 1.4 `tests/test_refresh_view_absorb.py` (new): `refresh_project` with a
      stubbed view-page fetch (a) merges `view_verified_case_ids` into the
      cache, (b) adds a case id the page names that the parcel search missed
      and fetches its milestones, (c) leaves an already-complete cache's
      list untouched (green-now; becomes a real merge-preserve pin once the
      absorb persists on every refresh).
- [x] 1.5 `tests/test_view_verified_emission.py` (new): the payload's
      project-level `links` carries `view_verified_case_ids` from the
      discovery result (present when set, absent-key tolerated on legacy
      caches, empty list emitted as the discovery fact it is). RED: 2 fail.
- [x] 1.6 `tests/test_view_verified_badge.py` (new, fixture probe +
      `view_badge_fixture.data.js` carrying the 303 shape plus a both-ways
      566-2 shape): a node whose anchored case appears in
      `links.view_verified_case_ids` renders the 國 badge linking the
      project's twur URL (RED — the rule does not exist); a node not in the
      list does not (green: pins current behaviour); the 現況 badge rule is
      unchanged (green: pins current); a node qualifying both ways renders
      exactly one 國 badge (green: pins current). The shared probe gained a
      `badges` dump mode (argv[4]; one line per badge, per-node y from the
      row lines) alongside the row dump.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `viewer/app.js` allMembers comparator: same-key real-node pairs
      tie-break by node date ascending (undated last), then
      `String(recno)`; cross-key ordering untouched (D1). Probe-verified on
      live data: 303 renders 829 (2019) → 669 (2020) → 5 (2026); the 336
      order is unchanged.
- [x] 2.2 `urtpe/links.py` `cached_cases_awaiting_approval`: widen
      `_APPLICATION_FIELDS` to the five application-type fields (D2).
- [x] 2.3 `urtpe/links.py` `refresh_project`: re-run the view-page absorb
      for the project (same `_absorb_view_case_ids` path, view id from the
      cache's `twur_view_id`/`twur_url`), merging `view_verified_case_ids`
      and any newly-named case ids + their milestones (D3). The absorb's
      page-order list is MERGED into the cached list (never replaces it —
      pinned by 1.4(c)); the cache persists when milestones changed or the
      absorb produced a list; an absorb failure is reported in the report's
      `error` without aborting the refresh.
- [x] 2.4 `urtpe/links.py` attach/emit: write
      `project.links["view_verified_case_ids"]` from the discovery result
      into the payload (D4). The dict-shim path passes the key through only
      when the payload carries it (a legacy payload emits without the key);
      a dataclass result always carries the field (dataclass default).
- [x] 2.5 `viewer/app.js` `getNodeMilestoneBadges`: render the 國 badge when
      the node's anchored case is in `links.view_verified_case_ids`,
      deduplicated with the is_current rule (D4). Live probe: 336's 現況
      node keeps 國 → view/900; the badge fixture shows 國 on the
      view-verified nodes.

## 3. Acceptance

- [ ] 3.1 Full suite green; `node scripts/viewer_smoke.js` passes.
- [ ] 3.2 Run the widened refresh against the live cache; report the
      per-project before/after; confirm 303's 11505020 gains 核定日期
      2026/09/30 and 303's cache gains `view_verified_case_ids:
      ["10803151", "10105152"]` (plus 大業段314's 11507024 → 權變核定
      2026/09/17).
- [ ] 3.3 Re-emit with `--links`: 303's rows render 829 (2019-02-14) → 669
      (2020-07-28) → 5 (2026-09-30) with badges 北10105152 / 北10803151 /
      北11505020 and 國 on 829 + 669; the 336 order stays 453 → 370 → 1.
- [ ] 3.4 Live-viewer check on the deployed page after the push: 303's
      order, the three 北 badges, and 地 on the view-verified nodes.
- [ ] 3.5 `openspec validate` passes; the four main specs synced; both
      boards updated; commit.

---

Notes (test-group status, 2026-11-02):
- 1.1's fixture projects already render inverted (probe verified before
  writing: 1039 above 1232, 1098 above 1216, 580 above 862) — 3 RED, the 336
  pin passes.
- 1.2 is RED (the widened field list does not exist).
- 1.3 PASSES against the current matcher — deliberately, mirroring the
  archived change's 1.2: it pins that the matcher is already correct and the
  refresh supplies the missing date.
- 1.4: 2 RED; the merge-preserve test passes vacuously now and pins the
  merge-once-absorb-runs behaviour after 2.3.
- 1.5: 2 RED; the legacy-tolerance test passes (the key is absent today).
- 1.6: 1 RED (the view-verified rule does not exist); the other 3 pin the
  existing 現況/no-inference behaviour so the new rule cannot regress them.
- The 17 drift families (older node's date matches nothing; ±2–7 days) stay
  as-is — their render order is fixed by 2.1, their binding is an open
  issue for the ops log, not this change.
