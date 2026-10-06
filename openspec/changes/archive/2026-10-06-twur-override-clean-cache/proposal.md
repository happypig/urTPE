# twur-override-clean-cache

## Why

`load_project_cache` applies a recorded TWUR override from inside the branch that
requires `result.json` to already exist. On a cache with no entry it returns `None`
and the override table is never consulted, so `discover_project_links` runs as if the
record did not exist.

That contradicts the main spec, which already requires a recorded link to survive a
fresh clone (`official-link-discovery`, "A recorded link survives a fresh clone") and
to be completed from the portal page ("The record fills a gap"). The behaviour was
specified and not implemented. `data/.link_cache/` is gitignored, so a clean checkout
has no per-project entries at all and the override cannot be reached: the committed
dataset carries the link, but rebuilding it from scratch silently loses it.

This is the second miss in `twur-manual-override`, after the dropped case ids. Both
share one cause: the override was verified by checking that the *portal link appeared*
in the viewer, which is satisfied by a warm cache, so nothing ever exercised the
no-cache path.

## What changes

- `discover_project_links` consults the override table when resolving the national
  portal view id, as the last link in the chain after the portal index and the
  fallback mapping. Gap-fill semantics are unchanged: a discovered view id wins.
- The override is consulted *during* discovery rather than as a fabricated cached
  result, so Taipei search, milestones, implementation and rewards still run and the
  result is written to the cache in the ordinary shape. Returning a synthetic
  `DiscoveryResult` from `load_project_cache` would satisfy the link and leave every
  other field empty, which is the defect this change exists to prevent.
- The consultation is not gated on `portal_index` being present. Today the whole
  national-portal step is skipped when the index is empty, which would strand an
  override exactly when the index is unavailable.
- `LinksDiscovery.run` calls `unattached_overrides`, so a record naming a project
  absent from the dataset is reported rather than quietly retained. The helper
  existed and had no caller.

## Impact

- Affected spec: `official-link-discovery`
- Affected code: `urtpe/links.py` (`discover_project_links`, `LinksDiscovery.run`)
- Affected tests: `tests/test_twur_override.py`
- No emitted-field change. The committed dataset is already correct; this makes it
  reproducible.
- Network behaviour: an overridden project fetches its view page once per run where
  it previously did not, only in the case where the override is the only source of a
  view id.