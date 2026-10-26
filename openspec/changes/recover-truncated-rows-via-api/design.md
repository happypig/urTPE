# design — recover-truncated-rows-via-api

## Context

Actors and systems: the city publishes the gazette PDF (the core, per
`docs/sync_architecture.md` — "PDF defines the project universe; portals decorate it"); the
`gis.uro.taipei/ashx/` case APIs hold per-case identity and dates; the UDD GeoServer WFS at
`zonegeo.udd.gov.taipei/geoserver/Taipei/wfs` holds case-boundary polygons and the full
cadastral parcel layer; this pipeline ingests, archives, merges, and emits. Flow: PDF →
extract.py → raw.tsv → cleanse → merge → merged.tsv → projects.json (+ viewer), with
`.link_cache` per project and the single-writer lock around every run.

The recovery pass is a new adapter sitting between extraction and merge, active only under
`--recover-truncated`. Port/adapter split per config: matching and list-reconstruction
logic is pure; the two HTTP surfaces are adapters.

### Exploration evidence (2026-10-25/26 probes — the handoff for implementation)

All numbers below were measured live; probe scripts are archived with this change
(`probes/`, see tasks 1.1).

**The 15 truncated rows of the 2026-10-15 gazette** (編號 67, 79, 570, 672, 719, 796, 851,
863, 902, 912, 919, 930, 944, 997, 1131) cover 8 units; every row's 案名 is complete
(section + first parcel + declared count survive; only the parcel list tail is lost).
Declared/visible: 138/113, 74/72, 101/60, 98/69, 72/59–64, 110/80, 77/66, 105/71.

**Identity recovery: 15/15 rows matched an API case with the exact gazette date**
(POC matrix 2026-10-26, `poc_findings.md` T1 — the exploration's 14/15 was a
probe gap; the full matrix recovers every row, keyed from its own 案名).

| Unit (declared) | Row → API case | Date check |
|---|---|---|
| 虎林段四小段38 (138筆) | 796→`R089601-01` · 570→`R089601` · 67→`R089601` 變更(第二次) | exact (2019-05-28 / 2021-07-20 / 2026-03-12) |
| 美仁段二小段694 (74筆) | 79→`R098505` | exact; `CASE_NAME` == 案名 char-for-char |
| 振興段一小段2-6 (101筆) | 672→`R089B06-01` | exact 2020-07-14 |
| 雙連段二小段203-1 (98筆) | 919→`R089305-07` · 719→`R089305` | exact |
| 雙連段一小段197 (72筆) | 997→`09902025` · 912→`09902026` · 851→`09902027` | exact, in `uro_chk_date2` |
| 漢中段二小段328 (110筆) | 944→`09703202` · 902→`09703203` · 863→`09703204` | exact |
| 雙園段二小段505 (77筆) | 930→`09610233` **or** `09610237` | exact both — zone pair |
| 南港段一小段720 (105筆) | 1131→`R091007-02` | exact 2014-04-25 |

Traps confirmed live: the date sits in `uro_chk_date` **or** `uro_chk_date2` (權變 stages
use date2); the land list is not sorted from the 案名's parcel (row 1131: 案名 says 720地號,
cell starts `710-3`); `Get_updcase_list` answers at unit granularity (every parcel inside a
unit returns the whole case family; `sectstr`-only returns 0 bytes; parcels are mandatory);
`GetUpdQuery` name-search returns empty even for known names (dead end).

**A/B zone census** (sweep of all 692 gazette-known parcels → 2,408 cases): ~55 true
zone-marked cases (`-A/B區` 49, `(甲/乙區段)` 2, `B基地` series), across ~15 units, nearly
all gazette-included; ~37 further `(原XX基地)` hits are named anchors, not zones. Polygon
behaviour varies by unit: disjoint (南港528: A∩B=2), identical (玉成段166: A∩B=34), nested
(華中段 B⊃A). Both zone names carry the *unit* count. → zone attribution is not needed; the
row attaches all same-date cases.

**GeoServer WFS** (`Taipei:uro-redevelop-ALL-5`, 7,588 case boundaries, ids are R-form —
`R106201`, never numeric; `Taipei:LAND-ALL-TWD97`, 421,857 parcels with
`sect_name/land_no/land_pnum/land_snum`):
- 虎林段 `R089601`: candidates 148 → true 138 = PDF 113 + tail `93-17…93-41`; the 10 surplus
  are exactly the skip-pattern numbers visible in the PDF list (38、41、**45**… skips 42-44…).
- 美仁段 `R098505`: candidates 89 vs declared 74 — the calibrated membership rule
  refuses (72 fragment + 3 tail candidates = 75 ≠ 74) → fragment+partial. GIS also
  resolves the city typo `78-1`→`718-1`.
- Numeric-form ids have **no** polygons on 8 probed layers — 雙園段/漢中段/雙連段一小段 units
  stay fragment+partial.
- CQL `BBOX` evaluates in native TWD97 meters (a lat/lon bbox silently matched nothing);
  pull whole sections instead.
- Document route (`Get_project168_eighth` → `DownloadODFile`) returned **0 documents** for
  the A/B cases — not a recovery source.

### POC conclusions (2026-10-26 — tasks 1.2–1.7; full record in `poc_findings.md`)

These close the calibration gaps the exploration left open and supersede any
provisional wording above:

- **T1: 15/15 rows recover with an exact-date candidate**, keyed from each row's own
  案名. The address core is a *raw* substring of the accepted `CASE_NAME` for all 15;
  normalized equality holds for 13/15 (930's two zone-suffixed cases are the exceptions).
  權變 stages close in `uro_chk_date2` alone (851, 863, 902, 912, 930, 997).
- **T2: normalization table** (whitespace, （）→(), 計劃→計畫, ㄧ→一) is defensive only on
  this gazette; the similarity fallback band stays 0.7 / 0.5–0.7 and was exercised 0
  times (accepted pairs ≥ 0.965).
- **T8: the overlap test is positional, not a fraction threshold.** Pure vertex-fraction
  thresholds cannot separate the anchors (in-gap parcels at 0.6 interleave tail members at
  0.6). Calibrated rule: reconstructed = fragment ∪ {candidates sorting after the
  fragment's last visible parcel with ≥1 ring vertex inside the boundary}; accept iff the
  count closes to the declared count, else refuse → fragment+partial. 虎林段 closes at
  exactly 138 (113 fragment + 25 tail, min tail fraction 0.2); 美仁段 refuses (75 ≠ 74).
  Centroid-in must never be a containment signal (17 far-parcel artifacts measure 0.0).
- **T4: the APIs cover the corpus's entire date range** — 6/6 pre-2006 samples (back to
  2002-03-21) return exact-date cases; on the oldest archived gazette (ROC-dated cells) 8/9
  truncated rows recover exact and 1 is a genuine residual. No ROC-era *publication* is
  archived; the premise was adapted, not skipped.
- **T5: budget** — probe ceiling 187 requests / 50 s; the product pass needs ≤ 83
  (8 unit-keyed lookups + 68 name-hit top-calls). One transient timeout in ~300 requests;
  the adapter retries 4× with backoff.
- **T10: the R-form id space is group-level.** `ID='R089305'` returns two polygons, neither
  the 203-1 unit's boundary (overlap 9/97 and 0/97); the id spans sibling units
  (190/203-1/208/219/517). The triple check refuses both → fragment+partial. The adapter
  unions multi-feature returns and relies on the checks, never on 1 feature = 1 case.

## Goals / Non-Goals

**Goals:**

- Recover excluded truncated rows with auditable provenance, under an opt-in flag.
- Two-tier list completion: GIS reconstruction (R-form) or fragment+partial.
- Report shape that keeps the not-a-faithful-copy guarantee.

**Non-Goals:**

- Zone-level parcel attribution (U1 — polygons don't distinguish zones reliably).
- Whole-corpus list backfill beyond recovery rows (D11).
- Any change to the default (flag-less) pipeline.
- Replacing the PDF as core; no enumeration of the case universe (impossible via these APIs).

## Decisions

- **D-A: Recovery is a parse-time pass inside the ingestion run**, not a separate script —
  the single-writer lock already serialises writers, and change_sets are keyed by
  publication, so archive re-ingestion with the flag rewrites that publication's conclusion
  by design (D6).
- **D-B: Identity from the row's own 案名, never from a sweep.** The four checks reuse the
  discipline of `complete_truncated_cell` (same unit / containment / count closes) plus the
  date check; the similarity fallback band reuses the link thresholds (0.7 link, 0.5–0.7
  flag) — POC-calibrated 2026-10-26 (T2): unchanged, and exercised 0 times on the current
  gazette (containment held raw for all 15 rows).
- **D-C: Land core comes from the row's own complete 案名** — the API only confirms it.
  This is why a recovered row joins the merge normally and why 930's zone split cannot split
  a land core.
- **D-D: List completion is two-tiered (D8)**: GIS reconstruction only for R-form ids with
  a polygon, gated on the triple check — count closes, fragment ⊆ GIS, and the calibrated
  membership rule (positional tail: candidates sorting after the fragment's last visible
  parcel with ≥1 ring vertex inside the boundary; T8 — a fraction threshold alone cannot
  separate the anchors); otherwise fragment+`partial` (D3). The declared count alone
  never produces a list, and a failing reconstruction is never repaired by picking a
  subset to force the count (美仁段: 75 ≠ 74 → refuse).
- **D-E: Multi-case attachment (D2)**: all same-unit same-date candidates attach, flagged
  `ambiguous-zone`; provenance lists every case id.
- **D-F: Typo repair (D9)**: a fragment token contradicted by both the cadastre and the
  API's own unit name (`78-1`→`718-1`) is repaired and flagged `normalized`.
- **D-G: Named-anchor discrimination (T11)**: zone-marker matching covers `-A區`,
  `(甲/乙區段)`, `(X基地)` but excludes `(原XX基地)` patterns, which the domain treats as
  anchors, not zones.
- **D-H: GeoServer section pulls over bbox filters** (T9): CQL BBOX evaluates in native
  TWD97; pulling the whole 段/小段 (≤ ~3,000 features) and testing containment in-process
  avoids the SRS trap entirely.
- **D-I: Docs (D10)**: `docs/urotpe_api.md` gains the GeoServer section (two layers, R-form
  id space, SRS trap, document-route absence).

## Risks / Trade-offs

- [Name drift between gazette 案名 and API `CASE_NAME`] → normalization table (計劃→計畫,
  簡寫 additions) + similarity fallback band; calibration is a POC task (T2).
- [Polygon vintage mismatch — boundary may reflect a different stage than the recovered
  row] (T10) → the count-closes check catches gross mismatches; mismatches fail safe to
  fragment+partial.
- [`LAND-ALL-TWD97` freshness for historical approvals] (T12) → fragment ⊆ GIS containment
  check detects drift; failures degrade to partial, never to wrong data.
- [Request volume on archive re-ingestion] (T5) → parcel-keyed only, ~2-3 requests/row;
  measured budget recorded by the POC; gis.uro has shown no WAF (facts_2_portals §1).
- [+5 new project identities on the current gazette] → coverage guard must observe
  additions, not a re-key; verified in tasks.
- [Double-handling with `check-declared-parcel-counts`] → sequenced after it; both changes
  route through the same flagged-row path.

## Migration Plan

Land after `check-declared-parcel-counts`. Ship the flag default-off; run once on the
current gazette into a temp tree; review the RECOVERED/INCOMPLETE report; only then enable
in normal runs. Rollback = drop the flag; recovered rows disappear and residuals return to
the plain exclusion list.

## Open Questions

- ~~T1/T2~~ Resolved 2026-10-26: 15/15 identity matrix; normalization table defensive;
  band unchanged (`poc_findings.md` T1/T2).
- T3: hyphen-cut census feeds `check-declared-parcel-counts`, not this change.
- ~~T4~~ Resolved 2026-10-26 with an adapted premise (no ROC-era publication is archived):
  API coverage confirmed back to 2002-03-21; ROC→ISO stays in extraction
  (`poc_findings.md` T4).
- ~~T8~~ Resolved 2026-10-26: calibrated membership rule is positional + vertex
  containment + count-closes; refuse-to-ambiguous = never subset-to-count
  (`poc_findings.md` T8).
- ~~T10~~ Resolved 2026-10-26: premise dissolved — the R-form id space is group-level and
  the triple check refuses wrong-unit polygons (`poc_findings.md` T10).
- T12: `LAND-ALL` freshness — answerable by checking whether parcels renamed in the
  gazette (`689地號(原726地號)`) appear under both numbers; the fragment ⊆ GIS
  containment check degrades to partial on drift either way.
