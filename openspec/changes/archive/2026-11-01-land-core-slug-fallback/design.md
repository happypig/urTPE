# Design — land-core-slug-fallback

## Context

`slug_for(anchor)` builds the slug from the anchor record alone. The two broken
identities have anchors with `land_count: null` and non-anchor members holding
1 and 2. `merge()` calls `slug_for(anchor)` inside the clustering loop, so the
family context is available at the call site.

## Goals / Non-Goals

Goals:

1. The count component falls back to the newest member that carries one.
2. A no-count-anywhere family keeps `?` and gains a review flag.
3. Deterministic: the same family always yields the same slug.

Non-Goals:

- No change to the slug format itself (district-section-parcel-等N筆).
- No cache migration in this change (the two identities have no dirs to migrate).

## Decisions

### D1 — Fallback order: anchor first, then members by 編號 ascending

The family is deterministically ordered; scanning from the anchor's recno
outward gives the *closest* record that answers the question, and 編號 order
makes it reproducible. The anchor's own null is skipped trivially (it is where
the scan starts). Alternative rejected: the *largest* count in the family —
that would couple the identity to whichever approval covered the most land, not
to the family's own history.

### D2 — `slug_for` gains an optional family parameter, defaulting to None

The signature stays call-compatible for any other caller; `merge()` passes the
member list. The fallback lives inside `slug_for` so the rule and the `?`
placeholder stay in one place.

### D3 — The review flag rides the existing flag channel

`review_flags` on the anchor record, appended in `merge()` after clustering —
the same channel the fragment-family detector uses. Text:
`案名未申報地號數(名稱核等你?)` — no: keep it ASCII-safe and factual:
`family carries no land count; project_id keeps the ? placeholder`.

## Risks / Trade-offs

- **Two project_ids change in the next emission.** That is the point; the alias
  table regeneration (a scheduled `build_project_aliases.py` run) records the
  pairing, and the change's acceptance names both new ids.
- **A family whose anchor null-count is *correct* would be renamed.** No such
  case exists (a 案名 without a count is a truncation artifact, not a fact —
  the declared-count census proved 48 rows disagree with their 案名, never the
  reverse); the review flag makes any future such case visible.

## Open Questions

(none)
