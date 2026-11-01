## Why

Two projects carry a broken identity: their `project_id` contains a literal `?` —
`松山區-寶清段一小段-51-13地號等?筆` and
`萬華區-崇仁新村青年段一小段-711-3地號等?筆`. Both anchors (編號 838, 1375) have
`land_count: null`, so `slug_for` (`urtpe/merge.py:124`) rendered the `?` from its
`or '?'` fallback. These ids name `.link_cache/` directories, alias-table keys, and
every future diff; a `?` in a directory name is legal but hostile, and the identity
is not the land core the domain model requires. The cost of leaving it, measured:
these two projects are exactly the two with **no** `.link_cache` directory —
discovery cannot cache them, so every `--links` run re-queries both portals for
them.

The truth exists in the data: the second node of each family carries the real
count (1 and 2). The slug is derived from the anchor alone when the family holds
the answer.

The maintainers affected: the discovery runner (repeated uncached queries), the
analyst diffing consecutive payloads (a `?` id reads as corruption), and any
consumer keying on the land core.

## What Changes

- `slug_for` falls back to another family member's `land_count` when the anchor's
  is null, before rendering `?`. The fallback rule: the count of the newest
  member that carries one (the family is recno-sorted; anchor first, then the
  rest by recno).
- A review flag when **no** member of the family carries a count — the `?` then
  stands, honestly, because nothing in the data answers the question.
- Alias migration for the renamed identities so the existing cache directories
  (none exist for these two — that is the bug) and future diffs stay linked.
- No emission re-run in this change: the code change lands with tests; the
  renamed ids appear in the next scheduled emission.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `case-merging`: `project_id` derivation gains the family fallback — the slug's
  count component SHALL come from the anchor's `land_count`, or, when the anchor
  carries none, from the newest family member that has one; the `?` placeholder
  SHALL remain only when no member carries a count, and that case SHALL be
  review-flagged.

## Impact

- `urtpe/merge.py` — `slug_for` signature gains the family context (or the call
  site passes a pre-resolved count); the review flag.
- `data/project_aliases.json` — regenerated after the next emission; the two
  renamed ids have no old cache dirs, so no migration entry is needed now (the
  table records the pairing for diffs).
- The next emission renames two `project_id`s — a user-visible diff, recorded in
  the change's acceptance.
