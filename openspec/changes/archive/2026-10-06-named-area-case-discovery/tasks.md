## 1. Tests (test-first; no implementation in this section)

### Named-area discovery

- [x] 1.1 `test_the_mono_stem_is_searched_when_the_subdivided_parcel_returns_nothing`
      — parcel `711-3` returns nothing, `711` returns two cases; assert both are returned
      and that `711` was actually requested.
- [x] 1.2 `test_no_stem_retry_when_the_original_parcel_matched` — assert the retry does
      not fire, so the common case keeps its single call.
- [x] 1.3 `test_a_parcel_less_case_naming_the_same_area_is_kept` — gazette name
      `崇仁新村青年段一小段`, case name `擬訂臺北市萬華區崇仁新村土地都市更新…`; assert kept.
- [x] 1.4 `test_a_parcel_less_case_naming_a_different_area_is_rejected` — case names a
      different area; assert rejected and named in `search_rejected`. This is the §6.7
      guard's whole purpose and must not weaken.
- [x] 1.5 `test_a_case_declaring_a_conflicting_parcel_is_rejected_even_when_the_area_matches`
      — shares the area token but names another 地號; assert rejected. Guards against
      "area match alone" being read as sufficient.
- [x] 1.6 `test_the_existing_six_seven_guard_scenarios_still_hold` — foreign same-section,
      sibling R13 概要, notation drift: unchanged outcomes.
- [x] 1.7 `test_a_rejected_case_is_still_reported_in_search_rejected` — corroboration
      failed, so the case is auditable rather than vanished.
- [x] 1.8 `test_the_real_崇仁_case_ids_are_recovered` — the actual pair, asserting
      `09112120` and `09112121`, using the real names verbatim.

### Date ordering restored

- [x] 1.9 `test_from_js_load_restores_ymd` — a node carrying only `date` must load with
      `ymd == (2005, 2, 24)`, not `(0, 0, 0)`.
- [x] 1.10 `test_a_loaded_project_orders_nodes_by_date_not_recno` — members 1362 (2008)
      and 1407 (2005) in payload order; assert `build_project_graph` emits 1407 first.
- [x] 1.11 `test_ymd_never_degrades_to_zero_for_a_dated_node` — sweep every node of the
      real emitted payload; assert none has `ymd == (0, 0, 0)`.
- [x] 1.12 Confirm 1.1–1.11 fail on the current tree before any implementation.

## 2. Implementation

- [x] 2.1 `search_taipei_cases_api`: retry the mono stem when a hyphenated parcel yields
      zero rows, merging by detail case_id.
- [x] 2.2 Thread the anchor's named-area tokens into the search and accept a parcel-less
      case name only when it declares no parcel of its own and shares a token.
- [x] 2.3 `_load_projects_from_js`: take `ymd` from `roc_to_iso`'s second return value,
      which line 88 already computes and discards.

## 3. Verification

- [x] 3.1 `python -m pytest` — 606 existing plus the new tests, one skip unchanged.
- [x] 3.2 Re-run `--from-js … --links` twice; assert 0 of 709 differ between runs.
- [x] 3.3 Assert the 崇仁 project gains `09112121` and keeps `09112120`, and that its
      node order is 1407 (2005) above 1362 (2008).
- [x] 3.4 Assert no project's taipei-link count *drops* versus the committed payload.
- [x] 3.5 `openspec validate named-area-case-discovery --strict`.

## 4. Close out

- [x] 4.1 `openspec archive named-area-case-discovery` and sync both spec deltas.
- [x] 4.2 Append the finding to `docs/portal_operations_log.md`.