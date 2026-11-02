## Why

The 336 fix (refresh-awaiting-approval-caches, archived 2026-11-02) closed one
stale-cache shape and the maintainer then reported the next one live: on
北投區-關渡段二小段-303地號等5筆， node 5 (2026-09-30, 變更 權利變換) renders
ABOVE node 669 (2020-07-28) — the legend promises 核定時序 (approval
chronology) and the rows read backwards. Measured corpus-wide (offline census
over all 694 projects / 1,442 records, 2026-11-02): **39 groups of real nodes
share one anchored case_id with differing dates, and 30 of them render
newer-above-older.**

Two stacked causes, both proven:

1. **The row sort tie-breaks on recno-string, not date.** The D12 Amendment 3
   family-wide interleave (`viewer/app.js` allMembers sort) orders rows by
   effective case_id ascending, then `String(recno)`. Two real nodes sharing
   one case_id therefore fall to the recno tie-break, and 編號 is a
   newest-first coordinate (app.js:836-842) — so the newer gazette row renders
   above the older one. Dates never enter the comparison. The 336 fix worked
   only because its three rows carry three distinct case_ids whose ascending
   order happens to equal date order.
2. **The newest node often cannot date-match at all.** For 303, the cache
   (written 2026-08-30) predates case 11505020's approval (核定 2026/09/30,
   live-verified via `fetch_taipei_milestones_api` today), so
   `_match_case_by_date('2026-09-30')` misses, the positional fallback binds
   node 5 to `city_case_ids[1]` = 10803151 (urtpe/links.py:1741) — the same
   case node 669 date-matched — and cause 1 inverts the pair. The
   awaiting-approval selector did not select 303's cache: its two 2026 cases
   carry only 申請計畫日期/申請權變日期 (plan-change applications), not the
   申請核定日期/權變申請核定日期 the selector watches.

Separately, the maintainer reported: **view/621 should connect to 10105152**.
The project's national page (`twur.nlma.gov.tw/zh/urban/rebuild/view/621`)
names cases 10803151 and 10105152 in its 相關連結 block — the portal itself
asserts the pairing — but the viewer renders the 國 badge only on the 現況
node (`viewer/app.js:108`, is_current only), so node 829 (anchored 10105152)
carries no path to the national page that names its case. For 336 the same
gap sits on node 370: view/900 names 10011273, yet only node 1 (現況) carries
the 國 badge. The payload cannot express "this case is named on the national
page": `view_verified_case_ids` exists in `DiscoveryResult`, is emitted to the
cache only by the absorb path (and most caches predate the field), and never
reaches `links` in the payload.

The actors: the maintainer reading the graph (wrong order, missing national
path), and the pipeline (a selector too narrow to select the caches a refresh
must fix).

## What Changes

- **Viewer tie-break by date** (`viewer/app.js`): when two real nodes share
  one effective case_id, the row tie-break SHALL compare node dates (then
  recno) instead of `String(recno)` alone. Measured on the corpus: this alone
  fixes all 30 inversions, including the 8+9 families whose caches already
  hold every approval date (a refresh cannot move those).
- **Refresh selector widened** (`urtpe/links.py` + the standing tool): the
  selector ALSO catches a case carrying any application-type date
  (申請計畫日期 / 申請權變日期 / 申請概要核准日期, alongside the existing
  申請核定日期 / 權變申請核定日期) with no approval date. Measured: this
  adds 北投區-關渡段二小段-303 and 北投區-大業段三小段-314 to the candidates
  (2 of the 13 stale-binding families; live-verified that 11505020 and
  11507024 now hold the missing approvals).
- **View-verified national badges** (`urtpe/links.py` emit + `viewer/app.js`):
  the pipeline emits `links.view_verified_case_ids` (the cases the project's
  own national view page names in 相關連結)， and the viewer renders the 國
  badge on any approval node whose anchored case is in that list — in
  addition to the existing 現況-node badge. Caches predating the field are
  backfilled by the widened refresh (which re-runs the view-page absorb).
- **Refresh re-absorbs the view page**: `refresh_project` re-runs
  `_absorb_view_case_ids` logic for its project so a backfilled cache gains
  `view_verified_case_ids` and any case ids the page names that the parcel
  search missed.

## Capabilities

### Modified Capabilities

- `virtual-milestone-nodes` — MODIFIED: the ordering requirement's tie-break
  for members sharing one effective case_id gains a date layer before the
  recno-string comparison (real-node pairs on one case render in approval-date
  order; undated members keep their tail position).
- `cache-freshness` — MODIFIED: the awaiting-approval selector widens from
  approval applications only to any application-type date without an approval;
  the refresh re-absorbs the view page.
- `viewer-related-links` — MODIFIED: the 國 badge renders on every node whose
  anchored case is view-verified (named on the national page), not only on
  the 現況 node.
- `official-link-discovery` — MODIFIED: `links.view_verified_case_ids` is
  emitted into the payload beside `case_schedules` (the cache field already
  exists in `DiscoveryResult`).

## Impact

- `viewer/app.js`: the allMembers comparator (one comparison layer) + the
  badge rule in `getNodeMilestoneBadges`.
- `urtpe/links.py`: `cached_cases_awaiting_approval` (field lists),
  `refresh_project` (view absorb), the payload emit (one links key).
- `scripts/refresh_awaiting_caches.py`: no structural change (its selector
  call site gains the widened signal automatically).
- Live cache: 13 project caches gain re-fetched milestones + view absorb; the
  per-project before/after report keeps the pass auditable.
- Emission + viewer order: 30 inverted groups read chronologically; the 336
  target order (453 → 370 → 1) is unchanged (distinct case_ids, tie-break
  never fires).
- Risk: 177 projects match the widened selector corpus-wide (most are
  long-pending applications the refresh will find still-unapproved and report
  unchanged) — the pass costs ~1–3 API calls per selected project, bounded
  and reported, consistent with the archived change's D1.
