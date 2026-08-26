# Design — Refine Event Source Edges & Callout Details

## Context

Actors: viewer users (planners tracing construction history per renewal
family) read the graph rendered by `viewer/app.js` from the emitted links
objects. Domain events in play: stage approvals (recno nodes), construction
events (建照/開工/使照)， and their carrying cases. System boundary: the
batch pipeline (PDF → parse → cleanse → merge → `projects.json` +
`projects.data.js`) is touched only additively — one provenance map recorded
during the existing stage-milestone merge in `urtpe/links.py`; everything
else stays in the browser-viewer adapter. See proposal.md for motivation
(金華段513-3 false edge, redundant links, missing 使用分區 row).

Current state: events attribute by a plan-in-force heuristic (latest approval
dated on or before the event), which invents edges between unrelated nodes;
event labels hyperlink redundantly; badges have generic tooltips; the callout
lacks the 使用分區 row.

## Goals / Non-Goals

**Goals:**

- Edges reflect only provenance relationships (source-group model).
- Every slot's carrying case is provable at the viewer, 建照 included.
- Badges self-describe on rollover.
- Callout shows zones the way planners read them (住三/住三之一).

**Non-Goals:**

- No re-anchoring of the merged milestone values themselves (chimera fix
  stays §12 [2]); this change only names who provided each value.
- No change to fetch, cache layout, or `schema_version`.
- No new event node kinds (概要 ghost nodes etc. remain future work).

## Decisions

1. **Provenance map at the merge, not viewer guesses** — while the
   last-write-wins loop merges stage milestones, record the winning case_id
   per label into `milestones_source` (additive optional map on project
   links). Implementation-derived dates keep their existing exact-match
   proof via `implementation.case_id`. National-only slots are their own
   group (green). *Alternative rejected:* viewer-side heuristics (single
   impl case ⇒ same source) — falsified by 金華段513-3, where all five cases
   carry non-empty payloads but only one has the dates.

2. **Source-group edge model** — group events by provenance into maximal
   chronological runs; solid edge from each group's source node (owning
   record for Taipei, 現況 for national-only) to the group's first event;
   solid chain within a group; dashed between adjacent groups colored by the
   incoming group. The plan-in-force heuristic is deleted. *Alternative
   rejected:* keeping plan-in-force as a fallback for unknown-source slots —
   it is exactly the false-relationship the user rejected (797 → 使照).

3. **Hyperlinks only where they add access** — event labels link solely when
   the carrying case anchors to no record; otherwise the owning record's 北
   badge is the single access point. National-sourced events never duplicate
   the twur link (現況's 國 badge covers it).

4. **Badge tooltips carry the id** — 北 title = `案<case_id>`; 國 title =
   `view/<id>` (parsed from the twur URL). Cheap discoverability for
   sibling-record disambiguation.

5. **Zone abbreviator table** — strip parentheticals; `第N種X區` →
   X-abbr + N (住宅→住， 商業→商， 工業→工)； `第N之一種X區` keeps the
   sub-numeral (住三之一)； `第N種特定X區` prefixes 特 (特商三)； already
   abbreviated forms (商三特) pass through; `X區(特)` → 住特-style; `X用地`
   drops the suffix; unknown renders verbatim. Corpus scan (top-30 values)
   covers all observed shapes. *Alternative rejected:* full zone names in the
   callout — too wide for the 150px box.

6. **Callout selection: baseline + diff only** — render on the first carrying
   record and on diff-triggered later records; identical successors stay
   silent. Grounded on 永昌段366-3, where four carriers showed four identical
   boxes (3,056/98-style noise) — the reader needs the baseline once, then
   only the changes. Red-diff semantics unchanged on the rendered ones.
   *Alternative rejected:* collapse identical callouts after first (same
   result, weaker framing); tooltips-on-hover for the silent ones — adds an
   interaction for near-zero information.

7. **Callout visibility: own-record exclusion + viewport clamp** — the
   placement collision set excludes the callout's own record (adjacent spots
   beside its node are legitimate; the old set rejected them and pushed boxes
   to far spots, off-viewport — the clipped top-left box on 永昌段366-3).
   Candidate rects clamp into the viewBox (x ∈ [4, svgW−w−4],
   y ∈ [4, svgH−h−4]), extending svgW/svgH when clamping would otherwise
   overlap; the six-spot preference order is kept.

8. **Provenance completeness as a three-layer stack** — the invariant "no
   isolated construction dates" is expressed at three levels, each answering
   a different question: (a) BDD requirement in the spec — the contract
   (resolution chain, no heuristics); (b) corpus pytest
   (`tests/test_milestones_provenance.py`) scanning the committed
   `projects.data.js` — the guard (every slot resolvable via
   milestones_source / implementation case_id / national; failures list
   family/slot/value); (c) `scripts/inspect_slot.py` CLI — the explainer
   (per-case breakdown for one family/slot). Post-regen corpus scan measured
   1,353/1,353 slots provable, so the guard starts green and any future
   merge/emission regression flips it. *Alternative rejected:* CLI-only
   inspector — explains but never enforces.

6. **Test strategy unchanged** — pytest structural tests + one real attach
   test for the source map + browser spot-checks (金華段513-3 single group;
   北安段14-2 mixed groups).

## Risks / Trade-offs

- [`milestones_source` grows the emitted graph] → one small map (≤ a few
  dozen labels); additive optional, v1/v2 consumers unaffected.
- [建照 winner may still be an older sibling (43 known families)] → the map
  names the true winner honestly; correcting WHICH value wins stays §12 [2].
- [Dashed transitions add visual vocabulary] → documented in the spec
  scenarios; only appears in mixed-source families (~minority).
- [Zone abbreviations for unobserved forms] → verbatim fallback; the corpus
  scan covers the top-30 shapes.
