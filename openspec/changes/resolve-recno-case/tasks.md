# Tasks: resolve-recno-case

## 1. Tests (test-first — all checked before any implementation task)

- [x] 1.1 Unit tests for the name tiers: exact (spaces ignored), loose
      (等, `(原N筆)`, 擬定↔擬訂, area suffix, `權利變換案`→`權利變換計畫案`,
      `案及`), stage-with-ordinal + plan type (`(含釐正圖冊)` ignored) —
      `tests/test_resolve_node_case.py::TestNameTiers`
- [x] 1.2 Unit tests for the live-set filter: 自行撤回/已駁回/已失效 excluded;
      a 無 case yields to an approved same-name sibling (東湖34 shape);
      approved siblings preferred when 2+ live remain —
      `TestLiveSet`
- [x] 1.3 Unit tests for the area-split rule: distinct non-empty area
      suffixes on every live match → all cases bind (吉林508 11011241+11011242,
      榮星53 北區/南區 pairs); same suffix or empty suffix on any match → no
      split bind — `TestAreaSplit`
- [x] 1.4 Unit test for the same-day id probe: acceptance requires CASE_NAME
      matching the node's 案名 AND the header date matching the node's date;
      a city-wide serial sibling (10203252 = 中山111) never binds; an
      accepted id is appended to `city_case_ids`, gains milestones, name and
      header — `TestSameDayProbe`
- [x] 1.5 Unit tests for the header-date step: a cached case binds on its
      header `uro_chk_date` when data2 carries another case's date (玉泉11
      shape); bounded 10-day drift binds on an equal stage-with-ordinal
      (康寧626 shape); a mismatched stage does not bind —
      `TestHeaderDateStep`
- [x] 1.6 Unit test for the all-parcel step: the parcel search runs on every
      parcel of the node (南港566 parcel 567 shape), accepted on name + date;
      a wrong-name result does not bind — `TestAllParcelStep`
- [x] 1.7 Test that a node every step misses gains the review flag and the
      run-report name, and carries no positional binding — `TestUnplacedNode`
- [x] 1.8 Integration test: `attach_links_to_projects` with a dict-shim disc
      binds a fallback node by the resolver instead of `city_case_ids[0/1]`,
      and the 1,356 date-matched nodes keep their binding (the matcher is
      untouched) — `TestAttachIntegration`; the fixtures that pinned the
      positional fallback in `tests/test_links.py` and
      `tests/test_gengxin_links.py` now bind by date/name (the evidence the
      resolver requires)
- [x] 1.9 Test that the refresh stores `uro_chk_date`/`uro_chk_date2` beside
      `NAME` in `case_headers` (both-shape reader: old string caches keep
      working) — `tests/test_cache_freshness.py::TestHeaderApprovalDates`

## 2. Implementation

- [x] 2.1 Add the tier functions and the live-set filter to `urtpe/links.py`
      (pure, exported): `node_name_key`, `node_name_loose`, `node_stage_kind`,
      `filter_live_cases`
- [x] 2.2 Add `resolve_node_cases(member, disc, fetch_header=None,
      fetch_milestones=None, search=None, sleep=None, probe_headers=None)` —
      the 4 steps in order, network adapters injected; offline by default
      (D7: the emission-side attach reads the caches only)
- [x] 2.3 Replace the positional fallback in `attach_links_to_projects` with
      the resolver call; keep `_match_case_by_date` as the first binder; the
      orphan gate reads `search_rejected` via getattr (a Disc double without
      it no longer crashes when a node stays unanchored)
- [x] 2.4 Extend `fetch_taipei_case_header_api` consumers: the refresh and
      the probe persist `uro_chk_date`/`uro_chk_date2` into `case_headers`;
      readers accept the legacy string shape (`case_header_entry`,
      `header_name`, `header_approval_dates`)
- [x] 2.5 All-parcel search: the resolver iterates `member.parcels` with the
      standing `search_taipei_cases_api`
- [x] 2.6 The unplaced-node report: review flag on the member (idempotent)
      `節點未能對應平台案件(案名:…, 日期:…)`; the sweep driver prints each
      unresolved node
- [x] 2.7 `scripts/resolve_fallback_nodes.py` — the live sweep driver
      (task 3.3): re-runs the resolver for every fallback node with the real
      adapters, writes accepted finds into the caches (append-only), prints
      the resolved/unresolved counts

## 3. Verification

- [x] 3.1 `python -m pytest` — full suite green
- [x] 3.2 Simulate the resolver over the payload's 71 fallback nodes
      (offline steps only) and confirm the name/header steps resolve the
      expected 54 without network
- [x] 3.3 Live run: probe + all-parcel steps over the 51 fallback projects
      (~230 gis.uro requests, read-only); record the finds in the caches
- [x] 3.4 Re-emit (`python -m urtpe.cli --from-js viewer/projects.data.js -o
      data --links`); confirm 0 positional-fallback nodes remain and the
      smoke + baseline checks pass
- [x] 3.5 `openspec validate --all` green; archive the change and sync the
      deltas
