# named-area-case-discovery

## Why

Two defects, both visible on one project
(`萬華區-崇仁新村青年段一小段-711-3地號等?筆`), and both are violations of
requirements that already exist rather than new behaviour.

**1. The second Taipei case is never found.** The platform has both cases; discovery
never asks for them.

- The gazette prints 地號 `711-3`, the city's index holds `711`. Searching `711-3`
  returns a **zero-length body**, which discovery reads as "no cases" — so the project
  silently reaches the fallback path.
- Searching `711` returns all three entries, including `R089106-01` →
  `09112121` (變更), which is missing from the emitted dataset.
- The §6.7 parcel guard then rejects both anyway: neither case name carries a 地號,
  because they name the **area** 崇仁新村. The guard's premise — "a name lacking the
  parcel marks a foreign/sibling case" — is false for a named-area unit.

**2. The timeline is ordered by 編號.** `history-graph` requires approvals "ordered by
date, with the anchor highlighted". `cli.py:95` reads `ymd` from each emitted node, but
`build_project_graph` never emits a `ymd` key, so on the `--from-js` path every node
carries `ymd = (0, 0, 0)` and `_sort`'s `(ymd, recno)` key silently degrades to 編號
order: 1362 (2008-01-02 變更) renders above 1407 (2005-02-24 擬訂).

Line 88 already computes `iso, _ = roc_to_iso(node_date)` and discards the `ymd` half of
the same tuple. This is precisely the trap `AGENTS.md` names — 編號 is a coordinate, not
an identity, and must never key anything durable. It is also self-perpetuating:
`--from-js` reads its own output, so each run re-preserves the wrong order. A full PDF
run orders correctly, which is why this surfaced only after switching to `--from-js`.

## What changes

- `search_taipei_cases_api` retries the mono stem when a hyphenated parcel returns
  nothing (`711-3` → `711`), because the city's index is systematically keyed on the
  stem while the gazette prints the post-subdivision parcel.
- The parcel guard gains a corroborated path: a case whose name declares **no** parcel
  at all is kept when its name carries a named-area token the gazette record also
  carries (崇仁新村 appears in both). A case that declares a **different** parcel is
  still rejected, so cross-family pollution does not come back.
- Guard-rejected cases keep flowing into `search_rejected`, which already feeds
  fragment detection, so a wrong acceptance is still auditable.
- `_load_projects_from_js` reconstructs `ymd` from the node's date instead of defaulting
  to `(0, 0, 0)`, restoring date ordering on the `--from-js` path.

## Why corroborated rather than blanket acceptance

Accepting every parcel-less case name would recover `09112121` but reopens the §6.7
pollution: another 更新單元 in the same 段 can also have a parcel-less name. Requiring a
shared named-area token keeps the rejection for foreign units while letting a genuinely
named-area unit through. Where corroboration is unavailable, the case stays rejected and
`search_rejected` names it, so it can be recorded by hand — this is a rare shape.

## Impact

- Affected specs: `official-link-discovery`, `history-graph`
- Affected code: `urtpe/links.py`, `urtpe/cli.py`
- Affected tests: `tests/test_taipei_search.py` (or nearest), `tests/test_graph*.py`,
  `tests/test_cli*.py`
- Emitted data changes: this project gains Taipei case `09112121` and its milestones;
  any other named-area project the retry reaches may gain cases. Node order changes for
  every project whose `--from-js` load previously degraded to 編號 order.
- Cost: one extra API call per project only when a hyphenated parcel returns zero rows.