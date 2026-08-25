## Context

Pipeline boundary for this change: `merged.tsv -> projects.json (+ viewer)` already happened; downstream, the targeted fetch script (`scripts/fetch_remaining_national_portal.py`) reads candidates from `viewer/projects.data.js`, queries the national portal (`twur.nlma.gov.tw`, WAF-protected), and writes matches into `data/.link_cache/<project>/result.json` under the single-writer rule. Actors: maintainers run the campaign as an unattended overnight job; the viewer consumes regenerated data; the portal serves HTML pages whose `<title>` carries the authoritative land tuple.

Current state: 302/709 projects carry twur links. The strict matcher added in §6.6 (commit e01fbcf) has two latent defects — positional parcel extraction grabs the last enumerated parcel (`623` instead of `599`), and count comparison pits `str` against `int` — leaving only ~8 of 363 remaining candidates passable. Failures surface as ordinary no-matches, so the §16 ceiling analysis mistook self-inflicted rejection for registry absence. A live probe confirmed view/30 exists, is searchable, and rejects only on these defects. See proposal.md — Why.

## Goals / Non-Goals

**Goals:**
- Make the strict matcher accept every page that genuinely belongs to the candidate (title-derived identity), reject everything else, and do so observably.
- Recover the blocked population with one polite sweep run after the fix, guarded by before/after coverage counters.
- Keep the defect classes unit-testable at their current home in the fetch script.

**Non-Goals:**
- Moving the matcher into `urtpe/links.py` (§12 #3 library-first consolidation — separate change).
- Tolerating *genuine* count drift (金華段 11 vs 13 筆) — that is §12 #4 land-count normalization; normalization here means notation equivalence only (`520之2` ≡ `520-2`).
- Multi-page search-result handling (page 2+ of `?title=` results stay unread).
- Any change to Taipei-side search or emission/viewer logic.

## Decisions

### D1 — Parcel keyword comes from the anchor node's `first_parcel`
`load_candidates` currently regex-extracts `(\d+(?:-\d+)?)地號` from the land string; on enumerated lands ("599、599-1、…、623地號等27筆") this yields the last item. The pipeline already computes `first_parcel` from the case name — the same parcel a human would search by — and every anchor node carries it in `viewer/projects.data.js`. Use it directly; fall back to "first token of the enumeration" only when `first_parcel` is empty.
*Alternative considered*: patching the regex to take the first enumerated token — rejected as primary because it duplicates parsing logic the pipeline already owns and silently diverges again when formats drift.

### D2 — Local type-safe, normalization-aware comparison in the matcher
`parse_name_id` returns count as `int` by design (land-core keys rely on it elsewhere); changing its signature ripples into land-identity semantics. Instead, the matcher compares `str(t_count)` against the candidate count and normalizes both parcels/counts through one small helper (full-width→ASCII digits, `之`→`-`) before equality. Section comparison stays exact-string (district typos are cleansed upstream).
*Alternative considered*: making the helper a shared utility in `urtpe/cleanse.py` now — deferred; it migrates with the matcher during §12 #3, keeping this change's footprint in the script + tests. This preserves the repo's lightweight port/adapter split: comparison logic stays pure and unit-testable, separate from the fetch/CLI adapter surface around it.

### D3 — Probe cap 5 → 8, configurable via `--max-probe`
Each probe is a full view-page fetch against the WAF. The final campaign run measured zero resets at 1–3 min intervals with up to 6 requests/project; a default of 8 roughly preserves that envelope while covering dense sections observed at exactly the old cap (大業段三小段 returned 5). Page-1-only stays: pagination needs an endpoint-contract decision belonging to the consolidation work.

### D4 — Sweep run wrapped in the §18 rules
Sequence: back up `data/.link_cache` → snapshot coverage counters (twur / national_milestones / 使用核發 / Taipei resolved) → fixed-script run (standing calibrated intervals, 07:00 deadline, ledger active) → re-snapshot and require increases only → regenerate viewer once at completion. The ledger is effectively empty (only acceptance-test entries), so nothing suppresses the sweep; new negatives recorded during it are real observations, not artifacts.

### D5 — Offline verification before any network run
The matched view pages are cached (`view.html` persisted since §16). Regression tests and a pre-sweep spot check replay the matcher against cached pages — 寶清段四小段-599 must flip from reject to accept offline — so the first network request of the sweep happens only after behavior is proven.

## Risks / Trade-offs

- [WAF reset mid-sweep] → standing 1–3 min match / 15–45 s skip intervals, deadline stop, ledger-persisted negatives; resume next night loses nothing.
- [`first_parcel` absent on exotic nodes] → documented fallback (first enumeration token); residual failures land in the ledger with `view_ids_checked` for inspection rather than vanishing.
- [Recovery yield unknown for 2004–21 cohort] → acceptable: the sweep itself is the measurement; truncation notes + ledger give the evidence base for whatever lever comes next.
- [Probe cap still hides matches at position ≥9] → `--max-probe` raises it per run without code change; truncation is now visible instead of silent.
- [Normalization too loose?] → it equates only notation variants, never numeric values; wrong-number rejections are covered by regression tests.
