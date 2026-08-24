# Sync Architecture — PDF Heartbeat + Two Living Portals

*Design exploration from the 2026-08-24/25 sessions. Companion to `docs/facts_2_portals.md`
(empirical portal findings); this doc holds the forward-looking architecture that will
become the `portal-sync` OpenSpec change plus the `official-link-discovery`
consolidation.*

---

## 0. Decisions (summary)

| Decision | Rationale | Status |
|---|---|---|
| Consolidate portal discovery **library-first** | Dual implementations drift (loose-parcel-match bug precedent, facts §6.6); config.yaml port/adapter rule | Decided — needs OpenSpec change (modifies `official-link-discovery`) |
| Targeted search enters the CLI as **opt-in `--links-targeted`** | Tempo separation: pipeline ~1 h vs portal batch ~28 h; default `--links` must stay fast | Decided — same OpenSpec change |
| Fetch script survives as the **unattended overnight wrapper** | Deadline/sleep/dry-run controls are operational, not pipeline concerns | Decided |
| Sync = **event-cascade, PDF as heartbeat** | PDF defines the project universe; portals decorate it | Decided — needs OpenSpec change (new `portal-sync` capability) |
| Refresh policy = **liveness-based** | Completed projects are frozen history; refreshing them wastes the scarce WAF-safe budget | Decided |
| **`project_id`/land-core are the only cross-PDF keys** | PDF 編號/recno shifts on every gazette update | Decided — structural constraint |
| **Single-writer rule** on `data/.link_cache` | 2026-08-24 incident: 4 concurrent writers wiped 47 caches (facts §17) | In force |

---

## 1. Source Update Characteristics

| Source | What changes | Rate | Cheap change-signal (already parsed) | Fetch cost (full pass) |
|---|---|---|---|---|
| **PDF** (核定案件一覽表) | new approvals **prepended** (編號 1 = latest); all 編號 shift | ~weekly/monthly | new top rows; `published_date` | parse ≈ minutes (local) |
| **Taipei ashx** | phase C→E, `schedule` text, milestone dates fill in | continuous, per case | `phase`, `schedule`, `NAME` (top.ashx) | ~709 × ~1 s ≈ **1 h** |
| **National portal** | revision rows grow; 使用核發 on completion; `資料更新日期` bumps | per gazette cycle | `資料更新日期` (view page) | 3-5 min/project → **28 h** (WAF-safe) |

The 28-hour national-portal pass is the scarce resource. Everything in this design
exists to spend it only where it can change the data.

---

## 2. The recno Instability (why PDF sync is not trivial)

The gazette list is newest-first (編號 1 = latest). Every new approval **prepends**
and shifts every existing 編號 by +1. The dataset's `recno` is a snapshot of the PDF
at publication time (115/8/11: recno 1419 = oldest, 2000-09-29), so:

```
PDF 115/8/11:   recno 1 = newest case X        (1419 records)
PDF 115/9/xx:   new case Y prepends
                → X is now recno 2             (1420 records)
                → EVERY old recno shifted
```

Consequences:

- `recno` is **not** a cross-PDF identity. Node-level links (recno-keyed edges,
  per-node case links) must be **re-derived from content each sync**.
- Stable keys across PDFs: `project_id` (name-core slug of the latest approval —
  append-friendly by design) and the land core. These are what the similarity merge
  and the per-project caches already key on — the existing machinery survives.
- The per-project cache dirs (`data/.link_cache/<project_id>/`) are therefore
  **sync-stable**: a PDF re-sync that doesn't change a project's anchor keeps its
  cache valid; a project whose anchor changes (rare — only if a *newer* approval
  lands on the same unit) gets a new cache key naturally.

---

## 3. Event-Cascade Sync (PDF as heartbeat)

```
                 ┌────────────────────────────────────────────┐
                 │  PDF update (download latest gazette list) │
                 └────────────────────┬───────────────────────┘
                                      ▼
                       re-parse → cleanse → similarity merge
                                      ▼
                       diff vs previous project set
      ┌───────────────────┬───────────┴───────────┬─────────────────────┐
      ▼                   ▼                       ▼                     
  NEW project        EXISTING, anchor         EXISTING, unchanged     
  (cold cache)       changed (new 變更 node)   (no new nodes)          
      │                   │                       │                    
      ▼                   ▼                       ▼                    
  Taipei discovery    re-fetch that project's   skip (caches valid)    
  (ashx, fast) +      Taipei cases + its                             
  queue for portal    portal view page                               
  targeted search                                                    

  then, independent of PDF (staleness sweeps, overnight windows):
  ────────────────────────────────────────────────────────────────────
  L1  twur-less queue   → targeted portal search      (shrinks to ~0)
  L2  in-review (C/D)   → Taipei + portal refresh     (status moves)
  L3  completed (E)     → FROZEN — never re-fetch     (static history)
```

### Liveness economics (why L3 freezing matters)

Current cohort (2026-08-25 baseline): 709 projects, 292 with portal coverage,
58 with 使用核發. Completed projects (phase E + occupancy on record) are static
history — the national portal will never add anything but a rare late 變更 row.
Freezing them concentrates the 3-5-min-interval budget on:

- the ~373-candidate un-coverage queue (L1), and
- in-review projects whose timelines genuinely move (L2).

### Change-detection without re-fetching

Both portals expose cheap signals we already parse:

| Signal | Source | Detects |
|---|---|---|
| `phase` / `schedule` / `NAME` | Taipei `top.ashx` | status transitions (審議中 → 執行 → 完成) |
| milestone count delta | Taipei `second.ashx` | timeline growth |
| `資料更新日期` | national view page | any portal-side edit |

Refresh pass = fetch → compare signal → keep newer → update `fetched_at`.
Discard-on-unchanged keeps writes (and the single-writer window) minimal.

---

## 4. Library-First Consolidation (Q1 resolution)

```
urtpe/links.py  (library — ONE implementation, tested)
  ├─ search_portal(section) -> [view_ids]
  ├─ view_page_matches(html, section, parcel, count) -> bool
  ├─ fetch_and_parse_view(view_id) -> (milestones, city_ids, html)
  ├─ update_project_cache(...)                ← single write path (incl. view.html)
  ├─ LinksDiscovery            (existing)     ← Taipei-first, pipeline tempo
  └─ TargetedPortalDiscovery   (new class)    ← ?title= search, batch tempo
        ▲                              ▲
        │                              │
scripts/fetch_remaining_…py            urtpe.cli --links-targeted
(overnight wrapper: deadline,          (explicit opt-in; processes twur-less
 3-5 min sleeps, dry-run)               candidates; default --links untouched)
```

Rationale recap: the fetch script's loose `parcel in html` match produced
wrong-project matches (263-19 ↔ 209-19; 444等7筆 vs 444等17筆) that had to be
fixed with strict matching (facts §6.6). Every duplicated discovery path is a
future divergence — fixes must land once, in the library, and both entry points
inherit them.

**OpenSpec mapping**: one change, two capabilities touched —
`official-link-discovery` (MODIFIED: targeted search as fallback when index
misses, flag-gated) + `fetch-remaining-portal` (MODIFIED: script thin-wraps the
library).

---

## 5. Roadmap

### Near-term (current tooling, no new code)

1. **One orchestrator command** (`scripts/sync_all.py` or documented sequence):
   PDF → pipeline → targeted fetch (deadline-bounded) → regenerate. Strictly
   sequential — the single-writer rule becomes structural.
2. **`fetched_at` per source in `result.json`** — file mtime approximates it
   today; make it explicit per source (taipei_at, portal_at) so L2 sweeps can
   select by age.
3. **Freeze list** — skip phase-E projects in refresh passes (derivable from
   cached `implementation`/top data; no network).
4. Resume the L1 campaign (facts §16): ~373 candidates, 2-3 overnight windows.

### Long-term (OpenSpec `portal-sync`)

5. `--links-targeted` CLI flag (consolidation above).
6. **Sync manifest** `data/sync_state.json`: per-source last-sync timestamps,
   PDF `published_date`, per-project phase snapshot → "what changed since last
   sync" without re-fetching.
7. `generated_at` hygiene: `--from-js` currently preserves the loaded file's
   `generated_at` (viewer showed 2026-08-23 after 8/24 writes) — regenerate it
   per emission or drop it in favor of the manifest.
8. ~~`regenerate_viewer` hardening~~ **done (2026-08-25)**: log-file redirect
   instead of `capture_output` pipes + timeout 300 s → 1800 s — orphaned
   children can always finish writing and stay observable; slow regenerations
   don't time out silently (facts §17.3, mechanism corrected 2026-08-25).

---

## 6. Baseline for sync (2026-08-25)

| Metric | Value |
|---|---|
| Projects | 709 |
| `twur` / `milestones_national` | 292 (41%) |
| `使用核發日期` | 58 (8%) |
| L1 queue (twur-less) | ~373 |
| Schema | v2 (`add-taipei-implementation-data`: implementation/rewards cached + emitted, viewer cards live) |
| Known static (freezable) | grows with every 使用核發 discovery — 58 and counting |

---

*Sources: sync-architecture + CLI-consolidation exploration 2026-08-24/25
(conversation); incident context from facts_2_portals.md §17; coverage baseline
from `viewer/projects.data.js` + cache scan 2026-08-25.*