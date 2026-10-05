# urtpe.cli Flow (v2)

Updated for the current implementation: Taipei-first link discovery via the
platform's JSON API, portal bulk index with resume cache, per-project result
caching, and new CLI flags (`--playwright`, `--fresh`, `--add-mapping-file`).

```mermaid
flowchart TD
    subgraph CLI["urtpe.cli entry point"]
        A[Parse CLI args] --> B{--add-mapping-file?}
        B -->|Yes| M[add_fallback_mapping<br/>update data/taipei_case_ids.json<br/>write add_mapping.log]
        M --> M2[return 0]
        B -->|No| C{--from-js?}
        C -->|No| D[PDF Path]
        C -->|Yes| E[projects.data.js]
    end

    subgraph PDF_PIPELINE["PDF Pipeline (default)"]
        D --> F[extract_pdf_with_meta]
        F --> G[to_raw_records]
        G --> H[cleanse_all]
        H --> I[merge]
        I --> P1[Projects + meta<br/>published_date from PDF]
    end

    subgraph JS_LOAD["Load from JS (--from-js)"]
        E --> J[_load_projects_from_js<br/>reconstruct Project + CleanRecord]
        J --> P2[Projects + meta from JS<br/>skip extract/cleanse/merge]
    end

    subgraph LINKS["Link Discovery (--links, Taipei-first)"]
        P1 --> K{--links?}
        P2 --> K
        K -->|No| K1[link_results = empty]
        K -->|Yes| L[LinksDiscovery.run<br/>cache_dir=outdir/.link_cache]
        L --> L1{--fresh?}
        L1 -->|Yes| L2[wipe cache dir]
        L1 -->|No| L3[build_portal_index<br/>crawl national portal list pages<br/>cached as portal_index.json]
        L2 --> L3
        L3 --> L4[For each project<br/>sorted by project_id]
        L4 --> N[build_land_core_key<br/>from anchor record]
        N --> O{per-project cache<br/>result.json hit?}
        O -->|Yes| O1[reuse cached DiscoveryResult]
        O -->|No| Q[Step 1: Taipei JSON API search<br/>Get_updcase_list.ashx<br/>by section + first_parcel]
        Q --> R[Step 2: for each case_id<br/>Get_project168_second.ashx<br/>milestones via STAGE_FIELD_MAP]
        R --> S[Step 3 supplementary:<br/>lookup land_core in portal_index<br/>fallback data/taipei_case_ids.json]
        S --> T{view_id found?}
        T -->|Yes| U[fetch national view page<br/>extract 推動歷程]
        T -->|No| V[skip national milestones]
        U --> W{status}
        V --> W
        W -->|city_ids + milestones| X[resolved]
        W -->|city_ids only| Y[resolved_no_city]
        W -->|no city_ids| Z[unresolved]
        X --> AA[save project cache]
        Y --> AA
        Z --> AA
        O1 --> AB
        AA --> AB[write_crawl_log<br/>crawl_log.tsv + stats printed]
    end

    subgraph OUTPUT["Output Generation"]
        AB --> BB[review_report]
        K1 --> BB
        BB --> BC[review_report.txt]
        BB --> BD[build_graph_document<br/>attach_links_to_projects]
        BD --> BE[projects.json]
        BE --> BF{--viewer DIR?}
        BF -->|Yes| BG[write_projects_js<br/>viewer/projects.data.js]
        BE --> BH{--no-tsv or --from-js?}
        BH -->|No| BI[raw.tsv / clean.tsv / merged.tsv]
    end
```

## CLI options (`main`)

| Flag | Effect |
| --- | --- |
| `pdf` (positional, optional) | Source PDF; required unless `--from-js` |
| `-o, --outdir` | Output directory (default `data`) |
| `--no-tsv` | Skip TSV outputs, JSON graph only |
| `--viewer DIR` | Also write `DIR/projects.data.js` |
| `--links` | Enable official link discovery (fallback JSON mapping, recommended) |
| `--playwright` | Use Playwright-based link discovery (experimental) |
| `--fresh` | Force re-crawl of portal index and cached pages; wipes `.link_cache` |
| `--from-js PATH` | Load projects from existing `projects.data.js`, skip PDF parsing |
| `--add-mapping-file PATH` | Early-exit: add fallback mapping `{land_core, view_id, case_id}` to `data/taipei_case_ids.json` and return |

## Link discovery detail

- **Portal bulk index**: `build_portal_index` paginates the national portal
  list (`city_id=2`, `?page=N`), parses title into a land core
  (`parse_name_id`), and persists `portal_index.json` in the cache dir for
  resume; `--fresh` rebuilds it.
- **Per-project cache**: each project's `DiscoveryResult` is cached at
  `.link_cache/<project_id>/result.json` (plus `view.html`), so re-runs only
  fetch missing projects.
- **Taipei-first**: search + milestones come from the Taipei platform's ashx
  JSON API (`Get_updcase_list.ashx`, `Get_project168_second.ashx`); only
  r_progress_detail cases with numeric case_ids are kept. The national portal
  view page is fetched only to supply the `twur_url` and 推動歷程 milestones.
- **Status values**: `resolved` (city case ids + Taipei milestones),
  `resolved_no_city` (ids but no milestones), `unresolved` (no ids); network
  failures set `error` without aborting the run.
- All HTTP fetches use browser-like headers, retry with exponential backoff,
  and transparent gzip/deflate decoding (`fetch_url`, `_post_taipei_api`).

## Key differences from v1

1. Discovery order inverted: Taipei JSON API first, national portal
   supplementary (v1 searched the national portal first and scraped Taipei
   case pages as HTML).
2. Portal bulk index with `portal_index.json` resume cache replaces
   per-project national portal searches.
3. Per-project result caching; `--fresh` wipes the whole cache.
4. New statuses `resolved_no_city` (v1 had `unresolved`/`resolved`/`error`
   only).
5. `crawl_log.tsv` written to outdir; `--add-mapping-file` early-exit mode.
6. `--from-js` now also suppresses TSV outputs (raw/clean/merged come from the
   PDF pipeline only).

## Companion script: `scripts/fetch_remaining_national_portal.py`

Time-bounded backfill for projects still missing `twur` links after a normal
run. It writes into the same `.link_cache` per-project cache the CLI reads, so
its results are picked up on the next `--links` run.

Usage:

```
python scripts/fetch_remaining_national_portal.py [--dry-run] [--max-projects N] [--max-probe N] [--reprobe-days N]
```

```mermaid
flowchart TD
    S0["Start<br/>parse --dry-run, --max-projects,<br/>--reprobe-days, --max-probe"] --> S1["load_ledger<br/>data/.link_cache/no_match_ledger.json<br/>corrupt file → quarantine .corrupt"]
    S1 --> S2["sweep_matched_entries<br/>clear ledger entries for projects<br/>whose cache gained twur elsewhere"]
    S2 --> S3["load_candidates from<br/>viewer/projects.data.js:<br/>links.twur empty + is_current node<br/>yields section + first_parcel (+ 等N筆 count)<br/>sort by 現況 date desc"]
    S3 --> S4["filter_candidates:<br/>skip probed within --reprobe-days (14)<br/>0 disables skipping"]
    S4 --> S5{"candidates left?"}
    S5 -->|"no"| S5X["print 'No candidates to process'<br/>exit"]
    S5 -->|"yes"| S6{"--dry-run or<br/>--max-projects?"}
    S6 -->|"yes"| S7["truncate list<br/>(dry-run → first 3)"]
    S6 -->|"no"| S8["keep all"]
    S7 --> LOOP["for each candidate"]
    S8 --> LOOP
    LOOP --> D1{"is_past_deadline?<br/>DEADLINE_HOUR/MINUTE (default 07:00)<br/>_next_deadline: target at/before launch<br/>rolls to tomorrow (cross-midnight OK);<br/>run_sweep_until.py overrides the pair"}
    D1 -->|"yes"| SUM
    D1 -->|"no"| F1["find_matching_view:<br/>search_portal ?title=section, city_id=2<br/>collect /view/NNN ids"]
    F1 --> F2["probe up to --max-probe (default 8):<br/>fetch view page, view_page_matches<br/>strict section+parcel+count equality,<br/>notation-normalized (之 ↔ -, full-width)"]
    F2 --> F3{"match found?"}
    F3 -->|"no"| NM["record_no_match + save_ledger<br/>immediately (design D3:<br/>a deadline kill keeps tonight's negatives)"]
    F3 -->|"yes"| UP["update_project_cache:<br/>merge national_milestones (new wins),<br/>set twur_view_id + twur_url,<br/>write result.json + view.html,<br/>clear ledger entry + save (design D4)"]
    UP --> UPOK{"cache updated?"}
    UPOK -->|"yes"| INC["updated++<br/>processed++"]
    UPOK -->|"no (no cache / IO error)"| NM2["failed++<br/>record_no_match + save_ledger"]
    NM --> INC2["processed++"]
    NM2 --> INC2
    INC --> D2{"is_past_deadline?"}
    INC2 --> D2
    D2 -->|"yes"| SUM["print summary:<br/>total / skipped as recently probed /<br/>processed / updated / failed"]
    D2 -->|"no"| SL{"more candidates<br/>and not dry-run?"}
    SL -->|"yes"| SLP["sleep: match 60-180 s<br/>skip 15-45 s"]
    SLP --> LOOP
    SL -->|"no"| SUM
    SUM --> RG["regenerate_viewer (subprocess):<br/>python -m urtpe.cli --from-js<br/>viewer/projects.data.js -o data<br/>--viewer viewer --links<br/>output → regen_log.txt, timeout 1800 s"]
    RG --> DONE["Done"]
```

Details:

- **Candidates**: projects in `viewer/projects.data.js` whose `links.twur` is
  empty and whose anchor (`is_current`) node yields both a `section` and a
  first parcel parsed from the `land` string (`(\d+(?:-\d+)?)地號`), sorted by
  current date descending.
- **Matching**: searches the national portal by section title, then probes up
  to `--max-probe` (default 8) view pages, accepting the first that passes
  `view_page_matches` — strict `<parcel>地號` body check + parsed-title
  section/parcel/count equality (post `fix-targeted-portal-matcher`; see
  facts §16.1 for the two defects this replaced).
- **No-match ledger**: every negative is recorded to
  `data/.link_cache/no_match_ledger.json` (atomic write, corrupt-file
  quarantine) and candidates probed within `--reprobe-days` (default 14,
  `0` disables skipping) are excluded at load; entries clear on match and a
  run-start sweep drops projects that gained twur elsewhere.
- **Cache update**: merges new `national_milestones` over existing ones (new
  wins on overlap) and sets `twur_view_id`/`twur_url` in the per-project
  `result.json`; projects without an existing cache entry are skipped.
- **Politeness / deadline**: sleeps 60–180 s after matches and 15–45 s after
  skips (both bypassed in dry-run and after the last candidate) and stops at
  the deadline pair `DEADLINE_HOUR`/`DEADLINE_MINUTE` (default 07:00),
  finishing the current fetch first. Deadline resolution rolls to tomorrow
  when already past at launch (`_next_deadline`), so cross-midnight targets —
  e.g. `python scripts/run_sweep_until.py 6 0` — work; see facts §16 run log.
- **Viewer regeneration**: on completion runs the CLI in `--from-js --links
  --viewer viewer` mode as a subprocess so `projects.data.js` reflects the
  backfilled links. Failed cache updates are counted in the summary;
  `log_failure` (appending JSON Lines to
  `data/.link_cache/fetch_failures.json`) exists but is not currently wired
  into `main`.

> **Diagram updated (2026-08-26)**: the flowchart now reflects the no-match
> ledger lifecycle (load/quarantine, matched-entry sweep, `--reprobe-days`
> filter, immediate negatives — design D1–D5), the strict matcher
> (`fix-targeted-portal-matcher`, facts §16.1), the cache-update failure path
> (counted as failed and ledger-recorded), the double deadline check per
> iteration, and the `_next_deadline` cross-midnight roll used by the
> deadline-overriding wrapper `scripts/run_sweep_until.py HH MM`.

## Companion script: `scripts/regen_links_2026_08_26.py`

One-shot §6.8 re-merge pass for the `fix-cross-family-case-pollution` change:
refreshes every per-project cache after the §6.7/§6.8 parcel-guard
strictness change, so polluted slots re-resolve from the live Taipei API
while all expensive national-portal artifacts stay cached.

Usage:

```
python scripts/regen_links_2026_08_26.py [delay_seconds]
```

```mermaid
flowchart TD
    R0["Start<br/>delay = first CLI arg, default 0.25 s"] --> R1["_load_projects_from_js<br/>viewer/projects.data.js"]
    R1 --> R2["clear phase: unlink every<br/>data/.link_cache/*/result.json<br/>keeps view.html, portal_index.json,<br/>no_match_ledger.json, logs"]
    R2 --> R3["LinksDiscovery(cache_dir,<br/>delay).run(projects)"]
    R3 --> R4["build_portal_index<br/>portal_index.json cache hit →<br/>no national list crawl"]
    R4 --> R5["for each project<br/>(sorted by project_id;<br/>result.json just cleared → cache miss)"]
    R5 --> R6["Step 1: Get_updcase_list.ashx search<br/>§6.7/§6.8 guard keeps case_names<br/>carrying the searched parcel;<br/>rejects → search_rejected"]
    R6 --> R7["Step 2: per case_id —<br/>second.ashx milestones,<br/>third.ashx implementation,<br/>fourth.ashx rewards<br/>sleep(delay) between calls"]
    R7 --> R8["Step 3 supplementary:<br/>portal index → fallback mapping → view_id<br/>fetch view page (cached view.html<br/>served from disk) → national milestones"]
    R8 --> R9["resolve status<br/>save result.json"]
    R9 --> R10{"more projects?"}
    R10 -->|"yes"| R5
    R10 -->|"no"| R11["print summary:<br/>done: N projects,<br/>resolved / unresolved / errors"]
    R11 --> R12["Done — caches only:<br/>no crawl_log / projects.json /<br/>viewer write. Re-emit with<br/>urtpe.cli --from-js --links --viewer<br/>(cache-fed, no network)"]
```

Details:

- **Clear phase deletes ALL `result.json` up front** — despite the script
  docstring's "resumable" claim, an interrupted rerun starts from scratch
  (the clear phase is unconditional in `main`). Resumability is a property
  of the CLI `--links` run, not of this script.
- **What survives the clear**: cached `view.html` pages,
  `portal_index.json`, and `no_match_ledger.json` — so the national half of
  each discovery is disk-served and the run stresses only the Taipei ashx
  APIs (no twur WAF exposure beyond stray view_id misses).
- **Caches only, no emission**: the script stops after the summary print;
  `projects.json` / `viewer/projects.data.js` / `crawl_log.tsv` are refreshed
  by a subsequent CLI pass, which reads everything from the fresh caches.
- **Delay parameter**: per-call `time.sleep(delay)` between Taipei API
  requests (search + milestones + implementation + rewards per case).

## Data flow — where data lives

Correct mental model: the PDF is parsed only on full runs; routine
regenerations rebuild from `viewer/projects.data.js` plus the per-project
caches and hit the network only on cache misses. Both portals' results share
one cache file per project.

```mermaid
flowchart TD
    subgraph SRC["Sources"]
        PDF["gazette source.pdf<br/>recno rows + milestone dates"]
        ASHX["Taipei ashx JSON APIs<br/>updcase_list / second / top / third / fourth"]
        TWUR["national portal twur.nlma.gov.tw<br/>list pages + view/N pages"]
    end

    subgraph CACHE["data/.link_cache — durable middle layer"]
        RJ["per-project result.json<br/>status + case_ids<br/>milestones_taipei + case_milestones<br/>implementation + rewards<br/>twur_view_id + twur_url + milestones_national"]
        VH["per-project view.html<br/>matched national page"]
        PI["portal_index.json<br/>bulk index, ~110 entries"]
        LEDGER["no_match_ledger.json<br/>sweep negatives, 14-day TTL"]
    end

    CURATED["data/taipei_case_ids.json<br/>curated fallback mapping"]

    subgraph EMIT["Emitted artifacts"]
        PJ["data/projects.json"]
        PJS["viewer/projects.data.js<br/>window.PROJECTS, schema v2"]
        REP["review_report.txt + crawl_log.tsv"]
    end

    PDF -->|"full run:<br/>extract cleanse merge"| FULL["initial emission"]
    FULL -.-> PJS
    FULL -.-> PJ

    ASHX -->|"discovery, cache-miss only"| RJ
    TWUR -->|"build_portal_index"| PI
    TWUR -->|"fetch_view_page /<br/>sweep strict match"| VH
    VH -->|ViewPageParser| RJ
    PI -->|land_core lookup| RJ
    CURATED -->|fallback lookup| RJ
    LEDGER -.->|suppress re-probes| TWUR

    subgraph SWEEP["fetch_remaining_national_portal.py"]
        PJS -->|"candidates: twur empty<br/>minus ledger skips"| MATCH["search + strict match<br/>update_project_cache"]
        MATCH -->|"merge national half only"| RJ
        MATCH -->|negatives| LEDGER
        MATCH -->|exit: spawn regen| REGEN0
    end

    subgraph REGEN["urtpe.cli --from-js --links --viewer (cache-first)"]
        REGEN0["reload projects<br/>skip PDF"] --> ATTACH["attach_links_to_projects<br/>date-aligned anchoring<br/>onto recno nodes"]
        RJ -->|"cache hit = no network"| ATTACH
        ATTACH --> PJS
        ATTACH --> PJ
        ATTACH --> REP
    end
```

Reading the diagram:

- **`result.json` is the single source both writers converge on**: CLI
  discovery fills the Taipei half (+ national when the portal index resolves a
  view_id); the sweep merges only the national half. Whoever runs second must
  respect the single-writer rule (facts §17).
- **`viewer/projects.data.js` is both input and output** of regeneration:
  `--from-js` loads it, discovery/cache refresh the link layers, and the CLI
  rewrites it with links anchored onto recno nodes. That is why a bad emission
  can propagate (load → save round-trip) — treat it as state, not scratch.
- **Network is exceptional during regen**: any `<project>/result.json` hit
  means zero HTTP calls for that project. Live calls happen only on cache
  misses (new/corrupt projects) or inside sweeps.
- **`portal_index.json` covers only ~110 newest entries** (WAF-capped crawl);
  everything older reached the cache via sweeps, so deleting per-project
  caches cannot be healed from the index alone — see facts §18 before any
  destructive job.

## Document history

- `docs/cli_flow.archive.md` — the v1 diagram this file replaced (archived
  2026-08-24). It is retained for history and is **not** current; its
  national-portal-first discovery order no longer matches the code.
- This file grew by accretion: the main CLI flow (2026-08-24), then the
  `fetch_remaining_national_portal.py` sweep, then the "Data flow — where
  data lives" section, then `regen_links_2026_08_26.py` (all 2026-08-26). Line
  numbers are referenced from outside, so append new material at the end
  rather than inserting above the CLI options table — e.g.
  `openspec/changes/archive/2026-10-05-no-silent-data-loss/proposal.md` pins
  the `--links` row at line 83, and `scripts/baseline_silent_failures.py`
  asserts that row still reads "recommended".
