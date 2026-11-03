# Design: reject-foreign-view-cases

## Context

§8 of docs/viewer-UX.md (design settled 2026-11-03, decisions 1–2; open
question 3 has a stated default). Inspection board B7 + B8 (Appendix G). The
actors are planners reading the viewer graph: a nameless 孤 anchor or a wrong
view-verified id puts another project's 建照 / 開工 / 國 badge on this
project's graph.

Measured live (2026-11-04, at `370ddb2`):

- 146 caches hold 193 view-verified ids; 98 caches already carry `case_headers`
  (NAME only — `CASE_NAME` is read into the local `header_names` dict during
  refresh and discarded).
- The 5 §8 ids, under decision 1 (the city's case name decides), verified
  against the caches' stored `land_core` with
  `extract_landcore_from_case_name` + `compute_landcore_similarity`:
  - 10202065 on 中山254: label 辛亥163 (similarity 0.0); city name not in the
    cache (no `case_headers`) — needs a header fetch, expected mismatch.
  - 09511211 on 大安557: label 大安557 (match), city name (live in 603's
    cache) 吉林603 — similarity 0.0 → shape B reject.
  - 09807161 on 大安龍泉169: label 康寧262 (0.0); city name not in the cache —
    needs a header fetch, expected mismatch.
  - 09608220 on 信義犁和102: label 犁和165 (0.0), candidate name ALSO 犁和165
    (0.0) → shape A reject on both checks.
  - 10906092 on 中山吉林898: label 莒光519-3 (0.0) but city name = 吉林898
    (0.95) → decision-table row 4: **accept**, label error logged.
- The offer targets all resolve uniquely across the 726 caches' land cores
  (exactly 1 match each at ≥ 0.7): 10202065 → 辛亥163, 09511211 → 吉林603,
  09807161 → 康寧262, 09608220 → 犁和165. 辛亥163, 吉林603 and 康寧262 already
  hold their id in `city_case_ids`/`case_milestones`; 犁和165 already holds
  09608220. So the offer step fills recorded fields, not new fetches — except
  where the target's record is incomplete.
- A corpus-wide scan with candidate/search names over all 193 view-verified
  ids: only 09608220 fails on the name available today; the other three
  rejections need the header fetch (the city's CASE_NAME), which the refresh
  provides. 09112120 (崇仁新村) has a parcel-less name — the existing
  parcel-less rule keeps it; it is NOT view-verified in the payload (the city
  search supplied it), so the §8 gate does not touch it.

## Goals / Non-Goals

**Goals:**

- The city's own case name decides (§8 decision 1, four-row table).
- A rejected id is named and counted; never dropped silently (§8 decision 4 /
  design 4).
- A rejected id is offered to its own project by land core, never 編號 or
  `project_id` (§8 decision 2 / design 3); ambiguous → not guessed.
- One refresh + re-emit under the single-writer lock (§8 design 5).

**Non-Goals:**

- No change to the 國 badge rules (wave 4 is done; its input just gets
  cleaner).
- No full re-discovery (B1 is a separate change; this change re-checks only
  caches holding view-verified ids).
- No change to the similarity threshold or to `search_rejected` semantics.

## Decisions

### 1. The city's case name decides (§8 decision 1, restated)

| Label (check 1) | City name (check 2) | Result | Reason in `view_rejected` |
| --- | --- | --- | --- |
| match | match | accept | — |
| no match | no match | reject | label and city name name another project (shape A) |
| match | no match | reject | label is right, id is wrong (shape B) |
| no match | match | accept | — (the label error is logged in the run report) |

Check 2 compares the land core of the city's `CASE_NAME` (from
`get_project168_top`) against the project's own land core with the existing
`extract_landcore_from_case_name` + `compute_landcore_similarity` at
`LINK_THRESHOLD = 0.7`. A parcel-less city name (崇仁新村 shape — no 地號)
keeps the parcel-less rule: not decidable by land core, so it does not reject
(the §8 evidence named 09112120 as "the spec's own legitimate example, so not
a defect"). Check 1 compares the 相關連結 label the same way, for the reason
text only.

### 2. `case_headers` stores CASE_NAME (§8 design 1)

The refresh already reads each case header (`get_project168_top`). It now
persists `CASE_NAME` beside `NAME`. Storage shape: `case_headers` today maps
cid → NAME (a string). A second map would break every reader; instead a new
field `case_case_names: {cid: CASE_NAME}` rides the same refresh, saved and
round-tripped like `case_headers`. (`show-no-state-case-status` already
carries a spec delta naming "case_headers stores CASE_NAME"; that change is
mid-flight at 4/13, so this change owns the field end to end and that delta is
superseded by this one — recorded on its tasks.md.)

Alternative considered: reuse `candidate_names` — rejected: the platform
search and the header fetch disagree in exactly the cases this change catches;
mixing their provenance would make the audit trail ambiguous.

### 3. The decision pass lives in the refresh (§8 designs 2–3)

`refresh_project` gains a view-verified pass after the per-case loop, before
save: for each id in `view_verified_case_ids`, decide by decision 1, then:

- accept → keep (row 4 logs the label error into the report's new
  `label_errors` bucket);
- reject → remove from `view_verified_case_ids`, append to the new
  `view_rejected` field `{cid: {reason, label_ok, city_ok}}`;
- offer (§8 decision 2): the driver
  (`scripts/refresh_awaiting_caches.py` successor logic in the change's own
  script, task 4) owns the cross-project step — the refresh itself only
  records the rejection, because the refresh's unit is one project's cache and
  reaching into another project's cache from inside it would break the
  one-report-per-project contract. The driver collects rejections across the
  run, matches each rejected id's city-name land core against every cache's
  `land_core`, and when exactly one other cache matches: appends the id to
  that cache's `city_case_ids` (never re-ordered — the positional fallback
  binds by index), records `adopted_from_view[cid] = source_project_id` on the
  target, fetches its milestones if absent, and saves the target under the
  same lock. Zero or multiple matches → no move; the id stays only in
  `view_rejected` with reason "ambiguous owner" when multiple.

Ambiguity rule mirrors `data/project_aliases.json` (refuses ambiguous pairs).

### 4. Missing city name is no evidence (§8 open question 3 default)

When the header fetch failed or the cache has no `CASE_NAME` for the id, the
id stays view-verified, and the report marks it "label not confirmed" when its
label also mismatches. A missing header is no evidence — the rule
`header_has_no_state` already follows. The label alone never rejects.

### 5. Never drop silently (§8 design 4)

Every rejected id, and every id offered to another project, is named and
counted in the run report, the same way truncated records are named and
counted. The payload carries `links.view_rejected` and
`links.adopted_from_view` at project level beside `case_schedules`
(round-tripped through `--from-js` like `superseded_by`), so the 相關連結
section can name the rejection reason offline.

### 6. Selection: which caches the pass re-checks

The refresh's view-verified pass runs on every cache holding
`view_verified_case_ids` — not only the awaiting-approval candidates, because
a project whose cases are all approved still carries the defect (10202065's
holder 中山254 has no awaiting case). The change's driver script selects
`view_verified_case_ids` caches directly, re-runs `refresh_project` on them
(the per-case loop is a no-op re-fetch when nothing changed — the header call
doubles as the CASE_NAME harvest), then applies the offer step.

### 7. Commit order (§7 decision 4 pattern)

1. `feat:` tests first (test-writing group fully checked), then the pipeline
   change (fields + decision + offer + report + payload round-trip).
2. Run the refresh under `SingleWriterLock` on the 146 view-verified caches;
   back up the cache dir first (`data/.link_cache_backup_<stamp>_viewgate`,
   same pattern as the five existing backups).
3. `chore:` re-emit `data/` + `viewer/projects.data.js` (~23 MB diff).
4. `openspec:` archive change E and sync the three spec deltas.

## Risks / Trade-offs

- [Risk] The offer adds a foreign id to an innocent project's cache if the
  city name itself is wrong in the other direction (two projects both claim
  it). [Mitigation] Exactly-one-match rule; ambiguous → no move; both fields
  (`view_rejected`, `adopted_from_view`) record the provenance.
- [Risk] Re-checking 146 caches costs 146+ header fetches (WAF-capped).
  [Mitigation] 1 request per case id (~193), same rate the §36/§37 refreshes
  already absorbed; the driver sleeps between requests like the existing
  scripts.
- [Risk] `refresh_project` re-fetches milestones on no-op projects (146 caches
  × their case count). [Mitigation] The §8 pass reuses the existing
  per-case loop (it already replaces milestones only when the reply is
  non-empty and reports each change); a no-op refresh saves nothing when
  nothing changed.
- [Risk] Re-emission rewrites ~23 MB of tracked files.
  [Mitigation] Its own `chore:` commit; review deliberately.

## Test writing (test-first gate)

Per openspec config the test-writing group must be fully checked before any
implementation task. Group 1 below writes: pytest cases for all four rows of
the decision-1 table, the parcel-less city name, the ambiguous owner, the
missing city name, the offer (move + adopt + no-guess), the payload
round-trip of both new fields, and the report naming; plus the run-report
census assertions. The live acceptance (tasks 4/5) then runs the real refresh.
