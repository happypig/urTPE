# Design — Fix Cross-Family Case Pollution

## Context

Actors: planners reading construction history per family; maintainers
running discovery sweeps. Domain events: stage approvals (recno records),
construction events (建照/開工/使照)， carrying cases. System boundary: two
touch points — (1) `urtpe/links.py` `search_taipei_cases_api` (discovery
adapter, input side), (2) fragment detection + review flags in the
attach/emit flow (output side). Pipeline flow untouched; caches and
`schema_version` unchanged. Flow: PDF → parse → cleanse → merge →
projects.json (+ viewer); discovery feeds links per family. See proposal.md.

Current state (§6.8): the parcel search over-returns sibling/foreign cases
(§6.7 one layer earlier); last-write-wins lets their construction dates win;
162 events across 82 families render with provenance naming cases that
anchor nowhere or to other families; 112 events double-display across
fragment/main graphs. The §6.7 guard shape (case_name parcel check) was
designed but never implemented — this change implements it plus the
fragment-candidate detection the quantification motivates.

## Goals / Non-Goals

**Goals:**

- Foreign/sibling cases stop entering `city_case_ids` (search-time guard).
- Fragment families become visible as merge candidates (review flags).
- One regeneration re-merges; polluted slots drop foreign values.

**Non-Goals:**

- No automatic family merging (human decision via review flags).
- No fix for the underlying chimera merge ([2]) or count normalization ([4]).
- No retroactive per-case date restoration for B1b families beyond what the
  re-merge naturally does (drop foreign values; own-case values were already
  present and will re-win).

## Decisions

1. **Guard at search time, not merge time** — dropping foreign cases in
   `search_taipei_cases_api` keeps `city_case_ids` clean for every
   downstream consumer (merge, node anchoring, 相關連結 debug list).
   *Alternative rejected:* filtering at merge — leaves polluted
   `links.taipei` and debug output.

2. **Guard matches the anchor's named first parcel, drift-tolerant** —
   same parcel-key rule as the national strict matcher (§16.1): mono part
   (263-19 → 263), 之 ↔ - and full-width ↔ ASCII normalized. *Alternative
   rejected:* full land-list containment — the platform search response
   carries no land list; the name is the only per-case signal at this point.

3. **Fragment detection: unanimous-anchoring rule** — a family is a fragment
   candidate iff every one of its discovered cases anchors inside a single
   other family (evidence: the fragment's records live in that family's
   history — 懷生段249 中正區 → 大安區 with 26/26 parcel identity; 101地號
  等41筆 → 19-1). Mixed/nowhere anchoring stays unflagged (ambiguous).
   *Alternative rejected:* auto-merge — family identity changes are a human
   decision; the flag is review output like 臨界對.

4. **Re-merge via the standard regen** — after the guard, one
   `--links` regeneration re-runs attach from caches; foreign milestones
   drop because their cases no longer enter `city_case_ids`. No migration
   script needed (unlike §18 — nothing was wiped; values are replaced by
   the merge itself).
   *Caveat recorded:* families whose OWN cases never carried a slot will
   lose the borrowed foreign date (correct — it was another unit's date).

5. **B1b severity investigation stays in-apply** — determine 11102211's land
   list (does it include 正義段115/132/243?) via the platform detail page
   during implementation; decides whether those families' current dates are
   wrong (needs own-case restoration) or shared (misattributed only).

## Risks / Trade-offs

- [Guard over-rejects a genuine case whose name omits the parcel] → the
  name is the platform's own unit declaration (§6.7 evidence); drift
  tolerance covers notation. Residual risk: cases named after a DIFFERENT
  parcel of the same unit (101地號等41筆 pattern) — those are exactly the
  fragment cases the detection flags instead.
- [Strictness shrinks `links.taipei` and the debug 相關連結 list] → intended:
  the list stops showing other units' cases. Coverage metrics (twur etc.)
  are national-side and unaffected.
- [Re-merge drops borrowed construction dates from 55 B1b events] → correct
  direction (foreign unit's dates); families whose own cases carry dates
  re-gain them from those cases during the same merge.
- [Fragment flags add review noise] → bounded by the unanimous-anchoring
  rule; corpus scan measured 63 cross-family fragment families as the upper
  bound before the guard, fewer after (foreign cases stop entering).
