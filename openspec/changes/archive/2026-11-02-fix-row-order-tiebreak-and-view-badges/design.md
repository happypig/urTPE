# Design — fix-row-order-tiebreak-and-view-badges

## Context

Flow: `discover_project_links` returns the cache early on a hit; nodes bind via
`_match_case_by_date` with the positional fallback
(`urtpe/links.py:1736-1744`); the viewer orders rows family-wide by effective
case_id then `String(recno)` (`viewer/app.js:836-842`); `getNodeMilestoneBadges`
renders 北 per anchored case and 國 on the is_current node only
(`viewer/app.js:98-114`).

Evidence, all measured 2026-11-02:

- 303 (關渡段二小段-303地號等5筆)： cache written 2026-08-30; node 5
  (2026-09-30) matches no cached approval; live API
  (`fetch_taipei_milestones_api('11505020')`) returns 核定日期 2026/09/30
  today; the positional fallback binds node 5 to 10803151 — the same case
  node 669 date-matched; the recno tie-break renders 5 above 669.
- Corpus census (all 694 projects / 1,442 records): 39 same-case_id groups
  with ≥2 differing real dates; 30 render non-chronologically. By cache
  state: 13 have a newest-node date absent from every cached approval
  (refresh-fixable — 303 and 大業段314 live-verified; 11505020 and 11507024
  now carry the missing approvals); 17 hold every date but an older node's
  gazette date matches no approval (date drift beyond ±1 day: +2d 大同447-2,
  −2d 瑞安838, +6d 南海164-2, +7d 學府125 …; or the case was never
  discovered).
- Selector: 303's 2026 cases carry only 申請計畫日期/申請權變日期 — the
  archived selector (申請核定日期/權變申請核定日期 only) skips it.
  Widening to any 申請\* field catches both 303 and 大業段314 (2 of the 13
  stale families); corpus-wide it selects 177 projects, most long-pending —
  bounded cost, reported per project.
- view/621 (303) names 10803151 + 10105152 in 相關連結； view/900 (336)
  names 10011273. `view_verified_case_ids` exists on `DiscoveryResult`
  (urtpe/links.py:320), is set by `_absorb_view_case_ids` (links.py:710), is
  persisted by `save_project_cache` via `asdict` — but 336's refreshed cache
  carries `[]` (its cache predates the field; refresh preserved the default)
  and the payload never emits it.

## Goals / Non-Goals

Goals:

1. Two real nodes sharing one anchored case render in approval-date order.
2. A refresh finds the caches whose newest approval postdates the cache
   (303's shape), including plan-change applications.
3. The viewer links the national page from every node whose case the
   national page itself names.
4. The 336 target order and the 603 pinned order stay exactly as archived.

Non-Goals:

- No change to the matcher (`_match_case_by_date`) or the positional
  fallback — §31/§32 established both correct; the failure is upstream
  (cache freshness) or in the viewer sort.
- No automatic refresh inside emission (AGENTS.md separation stands).
- No per-node national-milestone attribution change (the 國 badge is a link,
  not a milestone source).
- No date-drift widening of the matcher's ±1-day tolerance (17 families have
  drift up to ±7 days; widening is a matcher change with false-positive risk
  — out of scope, recorded as an open issue for the ops log).

## Decisions

### D1 — Tie-break: case_id, then node date, then recno

The allMembers comparator becomes: effective case_id ascending → (both real,
same key) node date ascending → `String(recno)`. Undated members keep their
position after dated ones within the same key (empty date sorts last within
the key, mirroring the cluster rule). Measured on the corpus: 30 inversions
before, 0 after; no distinct-case_id ordering changes (the tie-break only
fires within one key). The 603 scenario (all distinct case_ids) and the 336
target never reach the tie-break layer.

Alternative rejected: sort by date before case_id — that would reorder
cross-case rows and break the pinned 603 case_id-interleave order (case_id
ordering is the D12 decision; dates disagree with it by design, e.g. 已駁回
11007262 before 已核准 11501016).

### D2 — Selector: any application-type date with no approval

`_APPLICATION_FIELDS` widens to 申請核定日期 / 權變申請核定日期 /
申請計畫日期 / 申請權變日期 / 申請概要核准日期. The signal stays
offline-computable from the cache alone (D1 of the archived change). The
semantic: a case between applying and receiving approval, whatever the
application track. 177 candidates measured — the report keeps the pass
reviewable, and `--dry-run` lists them.

### D3 — Refresh re-absorbs the view page

`refresh_project` currently re-fetches per-case milestones only. It SHALL
also re-run the view-page absorb (fetch the project's `twur_url` page,
`extract_case_ids_from_view`, merge any case ids the parcel search missed,
resolve their milestones) so a backfilled cache gains
`view_verified_case_ids`. Rationale: the 303 cache predates the field; a
milestone-only refresh would never add it, and the badge fix (D4) needs the
list. The absorb already exists (`_absorb_view_case_ids`) — the refresh
calls the same code path instead of duplicating it. Cost: one view-page
fetch per selected project.

### D4 — 國 badge: view-verified nodes + 現況 (unchanged)

The pipeline emits `links.view_verified_case_ids` into the payload (one key
beside `case_schedules`, project level). The viewer adds the 國 badge to an
approval node when `node.links.taipei[0]` is in that list; the existing
is_current rule stays. For 303: nodes 829 and 669 gain 國 → view/621. For
336: node 370 gains 國 → view/900; node 1 keeps it via is_current.
Deduplication: a node qualifying both ways renders one 國 badge.

### D5 — Fixture: the 254/614/639 shape pins the tie-break

The chip fixture already carries three same-case families (254地號： 1232
2012-08-27 + 1039 2016-08-23 both on 09811141; 614地號： 1216 + 1098 + 906 on
09812231; 639地號： 862 + 580 on 10511291) — the probe currently renders all
three inverted. Tests pin: 1232 above 1039 (2012 before 2016), 1216 above
1098 above 906, 862 above 580 — plus 336's order unchanged.

## Risks / Trade-offs

- **Widened selector's 177 candidates**: mostly long-pending applications;
  the refresh reports them unchanged (one API call each, ~3 minutes
  corpus-wide at the existing delay). Acceptable; the per-project report
  keeps it honest.
- **The tie-break fires only within one case_id**, so no cross-case row can
  move: the 603 and 336 pins are safe by construction, and the corpus
  simulation shows 0 residual inversions.
- **17 families remain inverted in binding** (older node fell back; its date
  matches nothing in the cache even after refresh). The tie-break fixes
  their RENDER order; the badge may still name the fallback case on the
  older node. Fixing those bindings needs matcher or discovery work —
  recorded as an open issue, not smuggled in here.
- **Caches predating `view_verified_case_ids`** render no view-verified 國
  badges until refreshed — acceptable: the badge is additive, and the
  widened refresh backfills the selected set.

## Open Questions

- Whether the 17 drift families warrant a matcher change (e.g. extend the
  ±1-day tolerance to ±7 for the 權變 track) — needs its own measurement
  pass; not decided here.
