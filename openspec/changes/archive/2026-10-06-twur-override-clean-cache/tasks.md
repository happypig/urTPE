## 1. Tests (test-first; no implementation in this section)

- [x] 1.1 `test_override_applies_with_no_cache_entry` — a cache directory holding only
      the tracked override table, no `result.json`, yields a project whose
      `twur_view_id` is the recorded one after `discover_project_links`.
- [x] 1.2 `test_override_does_not_short_circuit_taipei` — same setup, with the Taipei
      search stubbed to return a case; assert `city_case_ids` is populated and not
      empty. Guards the tempting fix of returning a synthetic `DiscoveryResult` from
      `load_project_cache`, which would pass 1.1 and fail this.
- [x] 1.3 `test_override_applies_when_portal_index_empty` — `portal_index=[]`; the
      override still applies. Guards the `if portal_index:` gate.
- [x] 1.4 `test_override_still_yields_to_a_discovered_view_id` — portal index resolves
      a different view id; the index wins. Preserves gap-fill semantics.
- [x] 1.5 `test_override_survives_an_empty_cache_run` — full `LinksDiscovery.run` over an
      empty cache dir with the table beside it; assert the emitted result carries the
      link and a `result.json` was written. This is the fresh-clone path end to end.
- [x] 1.6 `test_unattached_override_is_reported` — `LinksDiscovery.run` over a project
      set that excludes an overridden project; assert the id is reported.
- [x] 1.7 Confirm each new test fails on the current tree before any implementation.

## 2. Implementation

- [x] 2.1 In `discover_project_links`, resolve the view id through portal index →
      fallback mapping → recorded override, and drop the `if portal_index:` gate around
      the fetch so an override is reachable with no index.
- [x] 2.2 Call `unattached_overrides` from `LinksDiscovery.run`.
- [x] 2.3 No change to `load_project_cache`: its gap-fill stays for the case where an
      entry exists, and it must keep returning `None` when there is none so discovery
      runs.

## 3. Verification

- [x] 3.1 `python -m pytest` — 597 existing plus the new tests, one skip unchanged.
- [x] 3.2 `python -m urtpe.cli --from-js viewer/projects.data.js -o data --viewer
      viewer --links` twice; assert 0 of 709 projects differ between runs, coverage
      still 635/709, and the target still carries both the TWUR link and Taipei case
      `09112120`.
- [x] 3.3 Clean-cache reproduction in a temp tree with the table placed beside
      `.link_cache` (the earlier simulation put it one level too high, which is why it
      proved nothing): assert the target gains its link with no pre-existing
      `result.json`.
- [x] 3.4 `openspec validate twur-override-clean-cache --strict`.

## 4. Close out

- [x] 4.1 `openspec archive twur-override-clean-cache` and sync the spec delta.
- [x] 4.2 Append the finding to `docs/portal_operations_log.md`.