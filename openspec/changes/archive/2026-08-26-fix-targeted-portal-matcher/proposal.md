## Why

Maintainers running the targeted national-portal campaign (`scripts/fetch_remaining_national_portal.py`) noticed 松山區-寶清段四小段-599地號等27筆 has no twur link in the viewer even though its page exists at `twur.nlma.gov.tw/zh/urban/rebuild/view/30` — title exactly matching, milestones aligning with both gazette nodes. Investigation (2026-08-25) traced this to two latent defects in the strict matcher introduced with the §6.6 fix (commit e01fbcf): candidate parcel extraction reads the **last** enumerated parcel from the land string instead of the named first parcel, and the count comparison pits a `str` against an `int` (`'27' != 27`). Together they reject nearly every remaining candidate: of 363 projects without twur, 329 fail on parcel extraction, 349 fail on the type mismatch — only 8 could pass as written. Failures are silent (logged as ordinary no-matches), which is why coverage plateaued at 302/709 while the doc attributed the gap to a mostly-mythical "registry hole": a spot-check found portal candidates for 5 of 6 sampled 2004–05 era sections.

## What Changes

- Fix candidate keyword derivation: use the anchor node's existing `first_parcel` field (computed by the pipeline) instead of regex-extracting a positional parcel from the enumerated land string.
- Fix the strict title comparison to be type-safe (`str(t_count)` vs `count`) so counted candidates can match.
- Normalize minor notation drift before comparing parcels and counts (e.g., `520之2` ↔ `520-2`, full-width digits) so equivalent spellings don't false-reject.
- Raise the per-project view-probe cap from a hardcoded 5 to a configurable limit (default 8) so dense sections whose result sits below position 6 become reachable; request pacing intervals unchanged.
- Add regression tests covering enumerated-land extraction, type-safe count matching, notation drift, and rejection cases (wrong parcel / section / count).
- Re-run the targeted campaign after the fix to sweep the ~355 structurally-rejected candidates into caches, with a before/after coverage snapshot (twur / national_milestones / 使用核發) per the §18 regression-guard rule; refresh the viewer.
- Update `docs/facts_2_portals.md` §16 ceiling analysis to separate genuine registry absence from matcher-rejected recoverable population.

Expected outcome is provisional until the fixed run completes: the unmatched population splits into ~74 recent-era candidates (likely high hit-rate) and ~289 in the 2004–2021 cohort where the spot-check suggests many exist but true yield is unknown; plausible landing zone ~450–600 of 709, not 709 (genuine pre-registry absences remain).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `fetch-remaining-portal`: the targeted-search requirement already demands searching by "the project's section and first parcel"; tighten it into testable requirements — anchor-node first-parcel derivation, type-safe and notation-normalized strict title matching, and a configurable probe cap replacing the hardcoded first-5.

## Impact

- `scripts/fetch_remaining_national_portal.py` — `load_candidates` (keyword derivation), `view_page_matches` (comparison semantics), `find_matching_view` (probe cap), new CLI flag.
- `tests/test_fetch_remaining_portal.py` (+ fixtures if needed) — regression tests for both defects and the drift normalization.
- Data effects: one sweep run writes matches into `data/.link_cache/*/result.json` via the existing single-writer flow and regenerates `viewer/projects.data.js`; no schema changes.
- Docs: `docs/facts_2_portals.md` §0 decision table + §16 ceiling analysis revision.
- No changes to `urtpe/links.py` discovery path (matcher consolidation into the library remains §12 #3 future work).
