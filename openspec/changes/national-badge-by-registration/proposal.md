# Proposal: national-badge-by-registration

## Why

The 國 badge on a recno node attaches by two routes today: per-label
stage+date binding (the C1 rule) and `view_verified_case_ids`. The user's
review (2026-11-12, `docs/inspection-batchE.md` E4) found the binding route
imprecise: a 國 badge should mean "the national view page names this", not
"a national label's date happened to match this node's date".

Two counter-examples name the rule:

- **文林838-1 node 433** carries 國 today only through per-label binding
  (兩 labels, both 111.09.20, hit its exact date). Its case `10611282` is
  NOT registered by view/766, and its 案名 differs from the title. It must
  lose the badge.
- **大安590's current node (recno 90)** carries no 國 today and must carry
  none: its case `11411007` is not view-verified. The rule's ceiling: a node
  qualifies only through the view page naming it.

**Measured** (680-project payload, 2026-11-12): 1,186 nodes carry 國 today;
the narrowed rule keeps **735** and removes **451**; no node gains one (the
name-route nodes are all already bound today).

## What Changes

- **The pipeline computes the rule once, at graph build**, and the payload
  carries the result per node: `national_badges: true` on a node whose
  anchored case is in `links.view_verified_case_ids`, whose 案名 equals the
  project's `twur_name`, or which qualifies through the 擬訂 section+parcel
  fallback. The per-label stage+date binding is retired from the pipeline.
- **The fallback (decided: 嚴格 + 擬訂區段後備)** — a 擬訂 node whose
  (section, first-parcel) matches the `twur_name`'s land core keeps the
  badge (大安590 node 884, the 權利變換 擬訂 whose 案名 differs from the
  title by one word).
- **The viewer renders from the field.** `bindNationalLabels` /
  `nationalLabelKey` (`viewer/app.js:149-172`, `:25-35`) retire; the
  stage+date matcher is gone, not re-implemented client-side.

## Capabilities

### Modified Capabilities

- `history-graph`: the 國-binding requirement is replaced — the badge reads
  the pipeline's resolved `national_badges` field; the per-label matcher's
  scenarios are retired with their rule.
- `official-link-discovery`: the emission requirement gains
  `national_badges` (the resolved binding) on each node.
- `viewer-related-links`: the graph-links requirement's badge routes are
  re-stated (registration + name + fallback; the 現況 rule stays retired).

## Impact

- Code: `urtpe/graph.py` (the emission), `urtpe/links.py` (the round-trip
  for the new node field), `viewer/app.js` (the render + the retired
  matcher), `viewer/dashboard.js` (it links by project only — untouched).
- Payload: one boolean per node (≈16 KB on a 9.3 MB payload); one re-emit.
- Tests: the binding rule pinned in pytest (the pipeline is now the rule's
  home); the harness's national-binding check re-targets the field.
