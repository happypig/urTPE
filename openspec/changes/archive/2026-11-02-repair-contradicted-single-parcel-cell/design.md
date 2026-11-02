# Design — repair-contradicted-single-parcel-cell

## Context

Actors and flow: the publisher prints the gazette PDF; the reader
(`urtpe/extract.py`) turns ruled cells into `raw.tsv`; cleansing
(`urtpe/cleanse.py`) normalizes rows into `CleanRecord`s (`clean.tsv`);
merge (`urtpe/merge.py`) clusters records into families by weighted
similarity (LINK_THRESHOLD 0.7) and slugs `project_id`; the link caches and
viewer consume the emitted graph. The system boundary for this change is
cleansing only — pure logic, no I/O adapter, no network.

Domain event: the publisher printed one row whose 地號 cell (`… 1
地號1筆土地`) contradicts its own 案名 (`…615地號1筆土地…`). The
platform API and the national portal both carry 615 for the same case
(10410272, 核定 2019-10-16), so the cell is the outlier — a publisher
defect of the same family as 臺北市投區 and 計劃, not a reader fault and
not a truncation.

Existing behaviour: cleansing already treats the 案名 as the identity
authority — `parse_name_id` drives `section`, `first_parcel`,
`land_count` (`urtpe/cleanse.py:249-261`), and when the cell yields no
parcel list at all the 案名 seeds the set (`cleanse.py:256-259`, spec
`land-identity-fallback`). Only the *contradicted* cell keeps its tokens.
Merge then scores the disagreeing record against its own family at 0.65 —
below the threshold by exactly the parcels weight.

## Goals / Non-Goals

- Goal: a single-count unit's parcel set must not contradict the 案名
  that names its one parcel.
- Goal: the repair is visible (auto_fix + review flag) and auditable.
- Non-Goal: no change to `merge.score`, its weights, or the 0.7
  threshold — the repair fixes the input, not the scorer.
- Non-Goal: no multi-parcel repair. A cell listing parcels the 案名
  does not name is a different shape (coverage change, cross-section
  list, merge history) and stays as published.
- Non-Goal: no network dependency in cleansing. The platform probe is
  evidence in this document; the rule runs offline.

## Decisions

### D1. The rule fires only on the strict contradiction

Condition (all must hold):

1. the 案名 parses (`parse_name_id`) with declared count == 1;
2. the 地號 cell yields exactly one parcel token;
3. that token differs from the named parcel.

Then `parcels = [named_parcel]`. Census over 1,442 records: exactly one
fire (759). The two other disagreeing single-count cells (269
cross-section, 957 merge-history) fail condition 2 — their cells list
dozens of tokens — and are untouched. 112 of 115 parseable single-count
cells already agree; the rule cannot disturb them.

### D2. Record the repair twice: auto_fix and review flag

`auto_fixes` gains `地號欄單筆地號與案名矛盾→依案名` (the established
auto-fix idiom: what was wrong, what won). `review_flags` gains
`地號欄印1(案名為615)…`-style text naming the printed cell verbatim, so
the review report shows the published defect next to the repair. This
follows the spec's "Auto-fix obvious, flag ambiguous" requirement — the
fix is obvious (two official sources vs one printed digit), but the
source cell is still a published fact worth surfacing.

### D3. Repair at cleansing, not at merge

The parcel set is a cleansing product; merge must stay a pure function
of cleansed records. Repairing in `cleanse()` also repairs the identity
every downstream consumer reads (slug, land core, caches, viewer) and
keeps merge untouched — no scorer change means no threshold-governance
change and no spec delta on `case-merging` rules.

### D4. The platform API is evidence, not a dependency

Live probe 2026-11-02: `Get_updcase_list(文德段二小段, 615)` returns 4
cases, all printing 615 in their names, including 10410272 — the very
case whose gazette row prints 1. view/686 (national) matched the unit on
615. The rule itself keys on the 案名 + cell contradiction only: adding
an API round-trip to cleansing would break the offline property of the
suite (all 796 tests run offline) for a rule that fires once per corpus.
The cached `candidate_names` in the project's `result.json` carry the
same witness offline.

### D5. Cache migration follows the standing alias mechanism

The `-2` project dissolves; its cache dir
(`data/.link_cache/內湖區-文德段二小段-615地號等1筆-2`) becomes an
orphan on the next run. `data/project_aliases.json` exists exactly for
this (`project_id` churn migration, ambiguous pairs refused). The next
`--links` run merges the twin's cache into the main family's; no new
mechanism is introduced.

## Risks / Trade-offs

- **A future city fix to the PDF** (they reprint the cell as 615): the
  rule simply stops firing — the cell then agrees with the 案名. No
  migration needed.
- **A future 案名 typo of the mirrored kind** (案名 prints 1, cell
  prints 615): the rule would "repair" the cell to the wrong value. Risk
  accepted and guarded: the rule fires only at count==1, the platform
  probe is the documented second witness for any flagged record, and the
  review flag makes every firing visible in the report. Census shows no
  such row today.
- **[POC-covered risk: threshold behaviour]** The repair moves one pair
  from 0.65 (flag band) to 0.95 (link). Simulated full re-merge over the
  1,442-record corpus: exactly one project_id changes. No borderline
  band movement elsewhere.

## Migration Plan

1. Land the rule + tests; full suite green.
2. Re-run the pipeline over the current gazette (single-writer lock,
   tracked-file rewrite as always).
3. The twin project disappears from emission; `project_aliases.json`
   regenerated by `scripts/build_project_aliases.py` if cache dirs
   churn.
4. Refresh + re-emit viewer data; the `-2` viewer project disappears.

## Open Questions

None. The maintainer approved the openspec-workflow route; the API-as-
authority question is settled as D4 (evidence, not dependency).
