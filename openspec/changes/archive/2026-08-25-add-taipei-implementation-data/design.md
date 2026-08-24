# Design — add-taipei-implementation-data

## Context

Actors and system boundaries: **discovery** (Python batch job, `urtpe.links`) reads
two government portals — the Taipei platform (JSON ashx endpoints, no WAF) and the
national portal (HTML, WAF-protected, read-only here) — and writes per-project
caches; the **emitter** (`urtpe.cli` → graph/viewer emission) turns caches into
`projects.json` + `viewer/projects.data.js`; the **viewer** (`viewer/app.js`, static
browser page) renders those files for researchers, renewal reviewers, and residents
tracking a case. Domain events flow through the batch pipeline:

```
PDF -> positional parse -> raw.tsv -> cleanse -> clean.tsv
    -> similarity merge -> merged.tsv -> projects.json (+ viewer)
                    ↑
        link discovery (this change extends it: second.ashx today,
        + third.ashx 執行階段 / fourth.ashx 獎勵資料 tomorrow)
```

Discovery currently POSTs each Taipei case_id to `Get_project168_second.ashx` only
(`fetch_taipei_milestones_api`, urtpe/links.py). `Get_project168_third.ashx`
(執行階段) and `Get_project168_fourth.ashx` (獎勵資料) are documented
(facts §11) and live-probed (`scripts/probe_third_6projects.py`, facts §10.4–10.5):
only the *completed* case carries values; revision cases return all-empty. The
portal's own detail page (r_progress_detail.aspx) embeds the authoritative
field→label map as `id="detail_<field>"` next to each label — captured for 86
fields during exploration, including `Eng_Start_Date` = 開工日期,
`Ulic_Date` = 使照核發日期, `Report_Date` = 成果報備日期. Caches are
cache-first: `result.json` written before a code change keeps serving until
deleted, so this change must land BEFORE the bulk discovery refresh
(facts §12 sequence) to avoid a second ~1,400-case sweep.

## Goals / Non-Goals

**Goals:**
- One bulk pass captures milestones + implementation + rewards (bundled with the
  pending cache refresh).
- Additive schema v2: old caches and version-1 consumers keep working.
- Viewer mirrors the portal's own tab structure (執行階段 / 獎勵資料 cards).

**Non-Goals:**
- No per-node attachment of implementation data (project-level only — see D2).
- No fourth.ashx reward-flag label mapping (site JS needed, facts §12.5).
- No changes to `fetch_remaining_national_portal.py` or national-portal behavior.
- No backfill script for third/forth data outside the discovery flow (the bulk
  refresh is the backfill).

## Decisions

### D1: Fetch third/fourth for EVERY discovered case, not just the anchor
We cannot know which case is "completed" without asking. Probing all cases costs
+2 POSTs/case (~2,800 total on the bulk pass at 1s delay ≈ +50 min, Taipei has no
WAF); probing only the newest case would miss projects whose final case is an
older attempt (e.g. 254 family: implementation lives on 09811141, not on the
anchor's 09811144). *Alternative rejected:* heuristics by `phase`/`schedule` —
undated and unreliable (facts §6.5).

### D2: Project-level attachment with case provenance
Implementation describes the built outcome of the whole renewal unit, and only
one case per family ever carries values (facts §6.4). Attaching at project level
avoids inventing node-placement rules for data that conceptually has no stage.
The carrying `case_id` is stored inside the emitted object for provenance.
*Alternative rejected:* node-level attachment — would imply a fake "execution
stage" node in the history graph.

### D3: Dates go through `milestones_taipei`; stats go into new objects
開工日期 / 使照核發日期 / 成果報備日期 are dates, so they flow through the
existing milestone pipeline (labels from the captured DOM map) and render in the
current milestone cards with zero viewer changes. Non-date statistics get a new
`implementation` object; fourth.ashx gets `rewards`. *Alternative rejected:*
stuffing everything into milestones — milestone cards are date lists; statistics
there would be unrenderable noise.

### D4: Cache shape mirrors `case_milestones` (per-case dicts)
`DiscoveryResult` gains `implementation: dict[case_id, dict]` and
`rewards: dict[case_id, dict]`, persisted additively like `case_milestones`
(§6.6 pattern). Old caches load with the fields absent → empty. Emission picks
the non-empty payload (if several, the one with the most populated fields; ties
broken by newest 核定日期) and records its case_id.

### D5: Emission picks values; it does not merge them
Only one case per family should carry values; if the data ever contradicts this
(two cases with different `Ulic_Date`), emission takes the best-populated
payload whole rather than field-merging, and the project is flagged for review —
mixed provenance inside one outcome object would be silently misleading.

### D6: `schema_version` 1 → 2, additive only
Both `data/projects.json` and `viewer/projects.data.js` carry `schema_version`
(today 1 — correcting facts §12.7). All v2 fields are optional; a v1 consumer
ignores unknown keys. Rollback = re-emit with the previous emitter; caches keep
the raw payloads either way.

### D7: Viewer cards mirror the portal's tabs, render-only-when-populated
Two new optional cards (執行階段, 獎勵資料) in `renderDetail`, styled like the
existing milestone cards (`<details class="milestone-card">`). Labels come from
the captured DOM map (86 fields) — stored as a label table in `app.js`, not
fetched at runtime. Cards hidden when the object is absent, following the
existing "absence looks like no data" convention.

### D8: Politeness — discovery keeps `delay=1.0s`; no random interval
The 3–5 min random interval is a `fetch-remaining-portal` spec requirement for
sustained national-portal campaigns. Taipei ashx has shown no WAF; discovery's
national exposure stays 0–1 cached view fetch per project. Recorded here so it
is not re-litigated.

### D9: Port/adapter placement (lightweight split, per repo convention)
The POST calls (`fetch_taipei_implementation_api` / `fetch_taipei_rewards_api`,
cache read/write, viewer DOM) are I/O adapters. The selection/derivation logic —
"pick the best-populated payload, record provenance, flag conflicts" (D5) and the
milestone-label extraction — is pure pipeline logic kept as standalone functions
operating on plain dicts, unit-testable without network. This preserves the
repo's deliberate minimal port/adapter split: no new layering beyond what
`links.py` already uses (fetch adapters + pure parse/attach helpers).

## Risks / Trade-offs

- [Bulk pass latency grows ~50 min] → Acceptable; one-time, Taipei-side only.
- [Two cases in one family both carry implementation values (contradiction)]
  → D5: whole-payload selection + review flag, never field-merge.
- [fourth.ashx field semantics unverified for non-empty values (all probes empty)]
  → Store raw values; viewer labels from DOM map; treat semantics as provisional
  until a populated case is seen (same stance as phase A/B/D, facts §6.5).
- [Old caches without the new fields] → Additive defaults; no migration needed.
- [Label drift if the portal renames fields] → Labels live in one table in
  `app.js` + the DOM remains the source of truth; re-capture is a 5-minute probe.

## Migration Plan

1. Land this change + the STAGE_FIELD_MAP round-2 corrections (facts §6.2/§16).
2. Bulk discovery refresh (delete per-project `result.json`, re-run `--links`):
   caches gain `case_milestones` + `implementation` + `rewards`; re-emit as
   schema_version 2.
3. Rollback: re-emit with the pre-change emitter (v1 output); caches may keep the
   extra fields (ignored by the old emitter). No portal data is mutated at any
   point (read-only POSTs).

## Open Questions

- None blocking. `Report_Date` semantics (成果報備日期?) remain an investigation
  (facts §12.2) — the field is stored and labeled regardless.
