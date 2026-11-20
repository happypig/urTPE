# Project inspection — Batch F · collected 2026-11-15 (F1–F9)

Nine items. F1–F3 are the user's three follow-up points after the
`section8-gate-anchor-parcel-drift` change (2026-11-15): one decision with two
implementations, a cross-route test, and an explicit dependency. F4–F6 are the
three items that change left open (懷生16's missing case, 市府220-2's land core,
the limit of the rejected-id count). F7 records what the exploration found
**against the change that just shipped**. F8 and F9 came from the user's next
two questions the same day: the 北 badges against the 相關連結 list, and the
section labels of 文山區-木柵段三小段-623. The board follows the
`docs/inspections/inspection-batchE.md` structure: findings, then the plan, then the
decisions that gate execution.

**Source and state.** Everything below was measured on the payload at
`e169d2f`: **1,444 records / 675 projects**, 統計至 2026-10-28, with the
caches as they stood after that change's refresh. The measurements are offline
unless a section says it made requests. One section does (F4): **63 live
read-only header requests to the city API, 0 errors, 1 s apart.** The scripts
were ad-hoc. The method of each measurement is in the Appendix, so any figure
can be reproduced.

**No change is open.** Each item below is a recommendation. The standing rule
holds: an openspec change opens on the user's word, one item at a time. A
recommended option is not a decision.

**What this board corrects.** Two claims in `docs/inspections/inspection-batchE.md` E10 are
superseded by F4: "the sibling-source gap is unmeasurable offline", and "the
sibling ids come from the national view page". The source is the **id-stem
walk**. F4 measures it. F7 records two things the archived change's design did
not state.

---

## F1 — one decision, many implementations (user, item 1)

**The question every site answers:** *does this case belong to this unit?* The
code answers it in seven places. Each place uses different evidence and a
different rule. Measured by grepping every call of the three predicates
(`compute_landcore_similarity`, `_case_name_carries_parcel`,
`extract_landcore_from_case_name`) in `urtpe/links.py`.

| # | Site | Route it serves | Rule | Parcel list? |
| --- | --- | --- | --- | --- |
| S1 | `_case_name_carries_parcel` (guard in `_search_taipei_raw`) | city parcel search | the name carries the searched parcel, or one of the unit's own parcels | **optional**: the refresh passes it, **discovery does not** |
| S2 | `verify_view_verified_ids` (the §8 gate) | national view page | land core ≥ 0.7, **or** same section text and an own parcel (shipped 2026-11-15) | optional, from the cache |
| S3 | `offer_rejected_ids` | a rejected id looking for its owner | land core vs every cache's core ≥ 0.7 | none |
| S4 | tier-3 case→node match (`_name_tier_hits`) | name over cached cases | similarity ≥ 0.85, with `node_parcels` inside the score | **third own-parcel implementation** |
| S5 | the orphan name branch (`links.py` ~4301) | a held case no node anchors | similarity ≥ 0.7, **no** parcel list | none |
| S6 | twin-bridge gate | an orphan with no name | ≥ 3 shared dates with anchored cases | n/a |
| S7 | `_corroborated_area` | a parcel-less named area | shared area words with the anchor name | n/a |

Three rules for "the same section" also exist: `_section_text` equality (S2),
`landcore_sections_match` (inside the similarity score, which also accepts a
段-only reading), and the search's `extra_sections` forms (S1). They do not
agree. `landcore_sections_match` matched 中正段**一**小段 with 中正段**三**小段;
`_section_text` correctly refused that pair.

**Measured disagreement, S1-style guard against S5-style similarity.** All 675
projects, every case with a parseable name (3,080 pairs). The guard side is the
own-parcel test plus a section check, as the shipped gate runs it.

| Verdict | Pairs |
| --- | --- |
| both accept | 1,963 |
| both refuse | 1,024 |
| **guard accepts, similarity refuses** | **86** (49 projects) |
| similarity accepts, guard refuses | 7 (2 projects) |

The 86 split by what the pipeline holds today:

| Status | Pairs | Equal declared count |
| --- | --- | --- |
| held by this project | 26 | 13 |
| held by another project | 7 | 0 |
| **held by no project** | **53** (38 projects) | 6 |

Call the 53 **candidates under the own-parcel rule**. They are not proven
misses. Many look like 事業概要 precursors of a wider or narrower scope
(`419地號等9筆` against `418地號等10筆`; `48地號等133筆` against
`46-4地號等117筆`) or like overlapping units. Only the user can decide that.
The 7 held-elsewhere pairs sit in 長春773/775, 南港366/560/522 and 雙連: the
unit's own parcel appears in a neighbouring unit's case name.

**The two discovery routes of S1 also disagree.** Discovery calls the search
without `own_parcels`. The refresh calls it with them. One predicate, two
inputs, two answers.

**Why a straight merge is unsafe.** It changes the verdict on 93 pairs (86 + 7).
The sites also rest on different evidence: the portal asserts S2's ids, the
search returns S1's, and S5 has only a name. Merging them into one function
without phasing would move the payload and hide which change moved it.

**Proposed form — two phases, each pinned:**

1. **A behaviour-preserving refactor.** One function takes the case name and a
   unit (land core, own parcels, section forms) and returns a verdict with a
   reason. Every site calls it with its own current rule as a named policy. A
   golden table pins today's verdict per site over the 3,080 pairs. The
   refactor passes only if every pair keeps its verdict.
2. **Each unification, one user decision at a time.** For example: "S5 adopts
   the own-parcel rule" changes up to 86 pairs. Each gets its own change, its
   own measured population and its own re-emit.

**Phase 1 done 2026-11-15 (Order step 5, no spec change).** `Unit`, `Verdict` and
`membership_verdict(case_name, unit, policy)` in `urtpe/links.py`. Five named
policies: `search_guard` (S1, with its sub-rules `exact`, `stem`, `own_parcel` and
`corroborated_area`; the legacy stem rule is now a named rule of its own, F8),
`gate` (S2), `offer` (S3), `orphan_name` (S5) and `node_tier3` (S4, three call
sites). S6 (shared dates) and S7 (shared area words) rest on different evidence,
not a case name against a unit, and are left out on purpose. Each site calls the
function with its own current rule: **no verdict moved**.

| Proof | Result |
| --- | --- |
| Golden table (`tests/fixtures/membership_golden.json`, 1.1 MB, frozen inputs) | 3,094 (unit, name) pairs at S1, S2, S3, S5 and 7,328 (node, name) pairs at S4: every bit unchanged. S3 and S5 agree on all 3,094 pairs. |
| One site at a time | The table was replayed after each move (S1, S3, S5, S4). |
| End to end | A re-emit left `viewer/projects.data.js` and `data/projects.json` byte-identical (md5), which covers the attach-side sites. |
| Source pins | S1, S3 and S4 call the function and hold no expression of their own; the orphan branch holds none. |

The golden table is a **characterization test**: it was captured from the
pre-refactor code, so it cannot go red first. The frozen inputs (not live caches)
keep it from reading a data change as a refactor bug.

**F2 tier 1 landed with it** (`tests/fixtures/membership_tier1.json`, three
hand-checked units, 24 held cases). Disagreements today, each a strict xfail naming
F1 phase 2: **S3 and S5 refuse all 7 cases of 華中247 and all 6 of 吳興163-2**
(the F2 table named only 華中247; 吳興163-2 has the same anchor-parcel drift).
S1, S2 and the node tier-3 agree on all of them; 懷生16 agrees everywhere.

**Not measured:** how many of the 86 would create a *ghost node* if S5 adopted
the rule (the graph effect). That is phase 2's measurement.

---

## F2 — the cross-route test (user, item 2)

**What exists.** A "known set of cases" for a unit does not exist as ground
truth. The cached names are what the routes themselves produced. Only three
units are hand-checked: 華中247, 懷生16 and 吳興163-2. The test therefore has
two tiers.

**Run on 華中247 (2026-11-15), each route on each of its seven cases:**

| Route / rule | Verdicts (7 cases) |
| --- | --- |
| S1 search guard | 7 accept |
| S2 §8 gate, **old** (no parcel list) | **0 accept, 7 refuse** |
| S2 §8 gate, today | 7 accept |
| S5 orphan name branch | **0 accept, 7 refuse** (score 0.45 < 0.7) |
| S4 tier-3 node match (with node parcels) | 7 accept |
| S3 offer step (owner of a drifted id) | **no owner found** (0.45; "zero hits, never guess") |

**Two claims, stated plainly.** (1) Against the gate as it was **before** the
shipped change, the test fails on 7 of 7 cases: it would have caught 華中247 on
day one. (2) Against **today's** code it **still fails**: S5 and S3 disagree
with S1, S2 and S4. A live instance is on screen. 華中247 holds `09305080` (the
概要 case) in 相關連結, and the orphan flag on node 14 records that S5 refused
it at 0.45. No stale flag contradicts a fixed node: none of the flagged ids in
the payload is view-verified.

**Tier 1 — synthetic, hand-checked units (lands with F1 phase 1).** Fixtures
for 華中247, 懷生16 and 吳興163-2 carry the full parcel cell, the case names
and the expected verdict. Every site must give the expected verdict. It is
red today on S3 and S5 for 華中247. It goes green when F1's policies agree, or
when each disagreement is a named, decided exception.

**Tier 2 — live, over the payload (lands last).** For every project and every
case with a parseable name, compute the verdict of each site. Assert that the
set of disagreeing pairs **equals a pinned list**: 93 pairs today. The list
may only shrink. A new disagreement fails the test and names the pair. The
assertion text names the drift, as `test_national_badge.py` does.

**Dependency.** Tier 2 cannot land before F1 phase 2 decides what to do with the
93 pairs, or it lands with the pinned list as the honest record of the open
disagreement.

---

## F3 — make the dependency explicit (user, item 3)

**Done by the shipped change.** The cache carries `own_parcels`. 569 caches
that hold view ids were backfilled from the payload (backup
`data/.link_cache_backup_20261115_045523_ownparcels`). The gate reads the key's
list first, then the cache's. Six callers reach it; two pass no key at all.

**Residuals, all measured 2026-11-15:**

| Residual | Measured |
| --- | --- |
| Caches without `own_parcels` | **106** payload-project caches. None holds view ids today, so none is gated. A later absorb that adds view ids to one would gate it with an empty list, silently, by the old rule. |
| Caches with view ids and no payload project | **26** of 52 non-payload cache dirs (50 are not `-N` twins of a payload project; 2 are). The backfill named and skipped them. |
| Discovery's search call | passes **no** `own_parcels` (F1, S1). |
| The cached-result path in discovery | returns the cache and **never refreshes** the field. |
| Equality with the payload | nothing keeps `own_parcels` equal to the payload's anchor parcels after `project_id` churn. |
| Empty list | silently means "use the old rule". It is not a named state. |

**Proposed form (a direct fix plus a live pin, no openspec change needed unless
the user wants the spec to state it):**

1. Backfill all 675 caches, not only the view-holders. The backfill script
   exists (`scripts/backfill_own_parcels.py`); the selector widens.
2. Discovery passes the unit's parcels to the search call.
3. An empty `own_parcels` becomes a **named report entry** (`view_gate_no_parcels`)
   instead of a silent fallback. The gate result is unchanged; the silence goes.
4. A live pin: for every payload project, the cache's `own_parcels` equals the
   anchor's parcels (first parcel first). It names the project on a mismatch.

**Done 2026-11-15 (Order step 1, direct fix, D8 = A).**

| Item | Result |
| --- | --- |
| Backfill | `scripts/backfill_own_parcels.py` now selects every cache. Run: 727 readable caches, **106 written**, 569 unchanged, 52 non-payload caches named and skipped. Backup `data/.link_cache_backup_20261115_083540_ownparcels`. |
| Discovery's search call | passes `own_parcels` (the refresh already did) |
| Discovery's cached path | follows the anchor: it writes the field when it is missing or differs, and writes nothing when equal |
| Empty list | the refresh report names the ids the gate decided without parcels (`view_gate_no_parcels`). The verdict is unchanged. |
| Live pin | `test_every_payload_project_cache_holds_the_anchor_s_parcels`: 0 missing, 0 stale across 675 caches |
| Tests | 8 new, 1 renamed. Full run: 1368 passed, 1 skipped. |

The earlier counts for the single count rule are **not** stored yet. They need
no new backfill: the F7 change reads them from the payload's nodes (condition 2
of the single count rule) and gets its own pin.

**Not measured:** how often the anchor's parcel list changes between two
approvals of one unit. A change makes a cached list stale; the live pin catches
it but does not size it.

---

## F4 — 懷生16's missing case and the id-stem walk (open item 1)

**This supersedes E10's two claims.** The source is not the view page, and the
gap is not unmeasurable. City case ids are `<7-digit stem><1 digit>`. Cases of
one unit sit in one or two adjacent stems. The existing probe walks those stems
(`resolve_node_cases` step 2, "the same-day id probe"), but only for a node the
city search left **unplaced**, and only live, by hand
(`scripts/resolve_fallback_nodes.py`). 懷生16's nodes are placed by other
cases, so the walk never runs for them.

**The measurement.** For every project, take the held ids per stem. An
**interior gap** is a digit between the lowest and highest held digit of one
stem that no project holds. There are **63** such ids in **52** projects. All 63
were probed once (`get_project168_top`, read-only, 63 requests, 0 errors).

| Probe result | Ids |
| --- | --- |
| no such case | 15 |
| case exists, **same unit** (land core ≥ 0.7) | **7** in 4 projects |
| case exists, same unit by the own-parcel rule only | **1** (see F7) |
| case exists, another unit (the gate refuses) | 40 |

The seven same-unit ids:

| Project | Ids |
| --- | --- |
| 大安區-懷生段二小段-16 | **09503201**, 09503202, 09503207 (all -A區 plan cases) |
| 文山區-萬隆段二小段-463 | 09205141 (A區), 09205142 (B區) |
| 士林區-百齡段五小段-342 | 10405264 |
| 萬華區-雙園段二小段-505 | 09610232 (A區) |

The user named `09503201`. The walk found `09503202` and `09503207` beside it
and four more projects with the same shape.

**Limit.** This is a lower bound. It counts interior gaps only. It does not
probe an id **beyond** a stem's lowest or highest held digit, and it does not
probe another stem of the same filing day. The true gap is larger.

**Does the existing walk already reach these ids?** The walk's candidate
generation is right: it builds the stems from every known id. Its **trigger** is
wrong for this gap: it runs per unplaced node, not per unit. Its **acceptance**
(CASE_NAME against the node's 案名 *and* the header date against the node's
date) does not fit a sibling, which has no node of its own and its own date.
So the answer is: extend the candidate generation, change the trigger and
change the acceptance. The acceptance the §8 gate already runs (the city's own
case name against the unit) fits.

**Options:**

| Option | What | Effect |
| --- | --- | --- |
| A | Extend the step-2 walk into a **unit-level sibling sweep**: walk every held id's stem, confirm each hit with the §8 gate rule | reuses the code; adds up to 63 requests per full sweep; confirms by one predicate (F1) |
| B | A new source script, separate from `resolve_node_cases` | a second implementation of the same decision (the thing F1 removes) |
| C | Do nothing; add the 8 ids by the ledger | 懷生16 fixed once; the other three projects stay open |

**Recommendation: A**, after F3. It lands one candidate rule instead of a
second one.

**Done 2026-11-15 (Order step 2, change `unit-sibling-id-walk`, D3 = A, D4 = A).**
`walk_unit_siblings` and the shared predicate `unit_accepts_case_name` landed;
`scripts/walk_unit_siblings.py` ran live once. The dry run listed **63** ids in
52 projects, the same as the F4 probe pass.

| Measure | Before | After |
| --- | --- | --- |
| Requests (read-only headers, 1 s apart) | — | 63, 0 errors, cap not hit |
| Ids added | — | **7** in 4 projects (懷生16 ×3, 萬隆463 ×2, 百齡342, 雙園505) |
| Recorded in `sibling_probed` | — | 56 (`none` and `other_unit`) |
| 相關連結 list entries | 2,015 | 2,022 |
| Node 北 badge ids | 1,478 | 1,484 (the 7th id, `10405264`, is a drawn orphan node) |
| Nodes carrying two or more cases | 32 | **37** (area pairs 30 → 35; with by-case payloads 30, unchanged) |
| Orphan-flag mentions (孤兒案件未達相似度門檻) | 17 | 17 |
| Ids listed under two projects | 9 | 9 |
| 國 badged nodes | 808 | 808 |

The walk held `09012312` (長春559-5, counts 69 against 80) back by the
equal-count keyword, as designed: the walk recorded it `other_unit`. **F7 must
clear that record**, or the walk will never retry the id under the single count
rule. The 40 other refused ids are foreign cases (other sections and districts).

**A second definition of `own_parcels` surfaced.** F3's live pin failed after the
re-emit: discovery's `own_parcels_of` kept the 地號 cell's order, and the backfill
and the pin put `first_parcel` first. 40 caches flipped on the re-emit. The fix
is one definition (first parcel first); both writers use it and the payload is
byte-identical across two re-emits.

**Not measured:** ids beyond a stem's lowest or highest held digit, and other
stems of the same filing day.

---

## F5 — 市府220-2's land core (open item 2)

**What happened.** `09609301` was a correct case of 大同區-市府段二小段-220-2:
its city name is the unit's own title. The §8 gate refused it because the
cache's `land_core` reads **中正區**市府段二小段220-2地號等54筆. The district
differs, so the similarity is 0.0 and the shipped own-parcel rule refuses it
too (the section text includes the district).

**Dated by the backups.** The wrong district is in every backup that holds the
cache, back to `.link_cache_backup_20260824` (the earliest). The case count
fell from 3 to 2 between `…20261104_viewgate` and `…20261106_rederive`. The §8
gate's first full run happened between those two backups, so the removal fits
that run. The backups do not show the removal itself. The origin of "中正區" is
**not established**: the earliest backup already has it. The
payload says 大同區 on both the project and its nodes.

**A twin cache keeps the right data.** `大同區-市府段二小段-220-2地號等54筆-2`
has the correct land core and holds all three cases, `09609301` view-verified.
It has no payload project.

**Population, measured:** only **3** of 675 caches have a `land_core` that
differs from the project id's parts.

| Cache | Difference |
| --- | --- |
| 大同區-市府段二小段-220-2地號等54筆 | **wrong district** (中正區) |
| 松山區-寶清段一小段-51-13地號等1筆 | land core lacks `地號等1筆` |
| 萬華區-崇仁新村青年段一小段-711-3地號等2筆 | land core lacks `地號等2筆` |

It is one case, not a pattern. Of the 52 non-payload cache dirs, 2 are `-N`
twins of a payload project, and only this one disagrees with its project.

**Options:**

| Option | What |
| --- | --- |
| A | Rewrite the 3 land cores from the project id, with a backup, and add a live pin that every cache's land core equals its project id's parts |
| B | Make the gate read the project's land core from the payload, not from the cache's copy (removes the dependency, as F3 does for parcels) |
| C | Both |

**Recommendation: C.** A repairs the 3 caches and the pin guards the next one.
B stops the next wrong copy from deciding a case. After A, `09609301` returns on
the next refresh, because the gate's re-decision step already lifts it.

**Part A done 2026-11-15 (Order step 3, direct fix, D5 = C).**
`scripts/repair_land_cores.py` rewrote the 3 land cores from the project id (dry
run named exactly the 3; backup `data/.link_cache_backup_20261115_085523_landcore`).
One `refresh_project` call on 市府220-2 lifted the rejection of `09609301` (the
re-decision step worked as predicted). A live pin now holds: every payload
project's cache `land_core` equals its project id's parts (the script skips ids
that are not unit ids: `-2` twins, `未解析-N`, `地號等?筆`; the pin skips them too).
Re-emit effect: 相關連結 list 2,022 → 2,023; node badge ids 1,484 (the node
already carried the badge: F8's one badged-but-unlisted case is closed);
rejected ids in the payload 8 in 8 projects → 7 in 7.

**Part B done 2026-11-15 (change `gate-reads-project-land-core`).** `refresh_project`
now derives the core from a unit's project id (`expected_land_core_of_project_id`,
the one definition the repair script imports), heals a cache core that
contradicts it before the re-decision and the gate read it, and names the heal in
the report (`land_core_healed`). A `-N` twin or non-unit id keeps the cache's own
core. No payload change: part A had already repaired the 3 caches.

---

## F6 — the limit of the rejected-id count (open item 3)

The shipped change counted **recorded** rejections only (11 ids in 10
projects). A view-named id that no cache recorded would be missing.

**Re-measured 2026-11-15, after the refresh.** All 653 cached `view.html`
pages were read. **0** ids that a page names are missing from its own cache's
`city_case_ids`, `view_verified_case_ids` and `view_rejected`. The earlier
scan found 2 (華中247's). The limit is closed for the cached pages.

**What stays unmeasured.** Projects with no cached view page: the 53 twur-less
projects and the 514 view ids that the index lacks. They are E13's phases 2–3.
The sweep that ran on 2026-11-14 matched 5 of 39 and did not change this.

**Form:** no change. Re-run the same scan after each nightly sweep. The scan is
a one-screen script (Appendix).

---

## F7 — findings against the shipped change (`section8-gate-anchor-parcel-drift`)

The exploration measured two things that the archived design did not state. The
board records them plainly.

**1. The own-parcel rule is wider than its evidence.** The rule has no
declared-count condition. The three ids it returned all have an **equal**
declared count (26 = 26; 2 = 2). Across the 86 guard-only pairs (F1) only **19**
have an equal count; **67 differ**. The probe's own-parcel accept, `09012312`
(長春559-5, `635地號等69筆` against `559-5地號等80筆`, a 概要案), passes with
no count match. Whether it is the unit's case is not known. The rule did not
admit anything wrong in production: it ran on 3 ids and all 3 were right. It
**would** admit up to 67 unproven pairs if it ran on them.

Among the 19 equal-count pairs, 13 are in the two hand-checked units. **6 are
held by no project**, in 5 projects, and look like the same drift: 潭美579-2
(`580地號等21筆`), 光華508-6 (`524地號等29筆`), 雙連197 (`198地號等72筆`, 2 cases),
雙連407 (`410地號等13筆`), 大安590 (`614地號等18筆`).

**2. The section test is stricter than the other two section rules.** The
河堤五小段 / 河堤段五小段 units spell their section in two forms. A drifted case
there would be refused by the exact `_section_text` test, while the similarity
score accepts the pair. The population today is **0**: the three pairs the
check found were foreign cases (中正段 一小段 against 三小段; 河堤段 二小段
against 四小段) that the exact test rightly refuses. It is a known gap of the shipped change, not an active defect.

**Options for the count (a decision for the user):**

| Option | Effect |
| --- | --- |
| A | Add "equal declared count" to the rule. Keeps all 3 shipped ids; refuses `09012312` until decided. Risk: a real scope change (`13筆(原11筆)`) is refused. |
| B | Keep the rule; rely on the case-name evidence |
| C | Equal count, **or** the name's `原N筆` equals the unit's count |

**Recommendation: A**, then measure how many true scope changes the `原N筆`
tolerance (C) would add before widening. The measured evidence supports an equal
count; it does not support more.

### F7 outcome — the single count rule landed (2026-11-15, change `unit-count-rule`)

**Order step 4, D1 and D2.** One predicate, `unit_accepts_case_name(own_land_core,
case_name, own_parcels, own_counts)`, serves the §8 gate, the sibling walk and the
admission command. The walk's provisional `require_equal_count` keyword is gone.
`own_counts` is a persisted, required cache field (backfilled for all 675 caches,
backup `data/.link_cache_backup_20261115_090919_ownparcels`; discovery sets it on
both paths; a live pin keeps it equal to the payload's). An empty list is named in
the refresh report (`view_gate_no_counts`) and means the narrower equal-count rule.

| Measure | Result |
| --- | --- |
| Guard-only pairs | 84 now (86 when measured; F5's repair moved 寶清51-13's two cases to a land-core match) |
| Pass the single rule | **22** (24 when measured) |
| Newly refused by the count rule | **62**; none of them reaches the gate |
| Gate-visible guard-only pairs | 3, all pass: no gate verdict changed |
| Admitted by `scripts/admit_unit_cases.py` | **7** in 6 projects (潭美579-2, 光華508-6, 雙連197 ×2, 雙連407, 大安590, 華興8's `09708111`); 14 read-only requests; backup `…_090954_admitcases` |
| `09012312` (長春559-5) | still refused: 69 is not among 80 and 83. The walk's `other_unit` record stays valid. |

**Payload effect of the 7 admissions** (re-emit):

| Measure | Before | After |
| --- | --- | --- |
| 相關連結 list entries | 2,023 | 2,030 |
| Node 北 badge ids | 1,484 | 1,484 (**no admitted case has a node**) |
| Nodes with two or more cases | 37 | 37 |
| Orphan-flag mentions (孤兒案件未達相似度門檻) | 17 | **24** (+7: one per admitted case) |

**What this shows.** The count rule and the orphan branch (S5) still disagree:
S5 refuses every admitted case at the 0.7 similarity gate, so each shows in the
list with a flag and no node. That is F2's open disagreement, now with 7 more
live instances. It is F1 phase 2's question (S5 adopts the rule or keeps its
own), not this change's. List entries with no badge (F8's count, superseded entries included): 26 before, **33** after (the sibling walk's 7 and 市府220-2's case all have a badge).

### F7 addendum — the D1 measurement (2026-11-15)

D1 chose rule C (equal count, or the name's `原N筆` equals the unit's count).
The change's first task was to measure what C adds. Same population as F1: all
675 projects, 3,080 case-name pairs, the **86 guard-only pairs** (the own-parcel
test accepts, the 0.7 similarity refuses). The count of the unit is the
`等N筆` of the cache's `land_core`. Reproduced first: 86 pairs, 49 projects, and 7
similarity-only pairs, as in F1.

| Question | Result |
| --- | --- |
| Pairs with an equal count (rule A) | **19** (13 held here, 6 held by no project) |
| Pairs that rule C adds: `原N筆` equals the unit's count | **0** |
| Guard-only pairs with a `原N筆` in the name | 7. Their `原N` is 25, 27, 23. The units hold 2 and 33. None equals. |
| Pairs the §8 gate can see (the id is named by a cached view page or recorded in `view_rejected`) | **3 of 86**. All 3 have an equal count, and all 3 are right (華中247 ×2, 吳興163-2). |
| Unequal-count pairs the gate can see | **0** of 67 |

**What this means.**

1. **On today's data, A and C give the same verdicts.** The `原N筆` tolerance
   adds 0 pairs to the own-parcel rule. The shipped three ids keep passing. No
   current verdict flips under A or C.
2. **The count condition guards the future, not the present.** The own-parcel
   rule runs only inside the §8 gate, and the gate sees only ids that a national
   view page names. 83 of the 86 pairs reach the graph by the search guard (S1)
   or the orphan branch (S5). Neither has a count test. A count condition
   changes them only if F1 phase 2 moves S5 onto this rule.
3. **`原N筆` is a real shape, but similarity already carries it.** In all 3,080
   pairs, 249 names have a `原N筆`. In 15 of them `原N` equals the unit's count:
   a later case of the same unit (大龍265's `30筆(原27筆)`, 振興707's
   `59筆(原57筆)`). All 15 pass the similarity route, because the first parcel
   matches. They are not guard-only, so rule C has nothing to add for them.
4. **The 6 大龍265-7 cases are not admitted by C.** Their `原25` and `原27`
   describe the 27-parcel unit, not the 2-parcel unit. C keeps them out. They
   stay cross-listed through the search guard's stem rule (F8), which has no
   count test.

**One variant C did not choose, measured for the record.** "The name's count
equals the count of *any approval* of the unit" adds **5** pairs (24 in all):

| Pair | Held | Reading |
| --- | --- | --- |
| 臨沂412 `10010221` (`414地號等11筆`, 概要; unit now 12) | here | A real earlier scope. The unit had 11 parcels. |
| 金華455-3 `09201071` (`508地號等11筆`; unit now 12) | here | Same shape. |
| 華興8 `09708111` (`18-1地號等13筆`; unit now 4) | **no project** | **Verified by one read-only header request (2026-11-15):** a **withdrawn 2008 predecessor**, not the 2013 case. State `事業計畫階段─實施者自行撤回`, 申請 2008/08/18, implementer 鴻愷建設 (the unit's implementer). The name's 13 parcels match the 2013 擬訂 node (node 1191: 13 parcels, `18-1` among them). The project holds `09902263` (擬訂, 2010 filing, approved 2013-07-05) and `09902264`. The search guard already rejected `09708111` (it sits in `search_rejected`). **Not one of the 6 equal-count pairs.** |
| 寶清51-13 `09906201`, `09906202` (`等1筆`) | here | An artifact: the cache's `land_core` lacks `地號等1筆` (F5), so the unit's count reads as none. |

**Effect on the decisions.**

- **D1 stays C, and C is safe.** It changes no verdict today. The change may
  state C as the rule and pin the 19 / 0 / 3 numbers above.
- **D2 gains a candidate.** 華興8's `09708111` is a seventh pair with a
  count the unit had at an earlier approval. It is not in the equal-count set of
  6, and no rule chosen so far admits it. The user may widen D2 to "equal to the
  count of any approval of the unit" (+1 held by no project, +4 already held,
  2 of them F5 artifacts). That is a new option (D2-D). The user chose it on
  2026-11-15. The case is a withdrawn predecessor filing. That is not a new
  kind: the caches already hold 139 cases in a 撤回 state, all in
  `city_case_ids`.
- **F5 blocks one reading.** Two caches whose `land_core` lacks the count
  (寶清51-13, 崇仁新村711-3) read as "no count". The third F5 cache has the wrong
  district, not a missing count. Repair them first (D5), or the count test refuses a correct
  case.

**Not measured:** the 53 held-by-no-project pairs were not sampled by hand (D2
says to sample 47). Names of cases that no route has fetched are not in this
population.

---

## F8 — the 北 badges and the 相關連結 list disagree (user, 2026-11-15)

**The question.** Does every case in a project's 相關連結 list have a 北
badge on the graph, and the reverse? The viewer builds the list from
`links.taipei` and draws one badge per case in each node's `links.taipei`
(plus one per drawn orphan node). Measured on all 675 projects: the list holds
**2,015** entries, the graph badges **1,990** distinct cases.

| Check | Result |
| --- | --- |
| A badged case missing from the list | **1** — `09609301` (市府220-2). A node still carries it; the project's list does not. This is F5's land-core defect. |
| One case badged on two nodes | 0 |
| A badge's `[X區]` label differs from the list's name | 0. Both read `candidate_names`, so they agree by construction. |
| A list entry with no badge | **26** |

The 26 split two ways.

| By structure | Entries |
| --- | --- |
| superseded: the list says "已由 … 取代" and no node is expected | 5 (expected) |
| no node and no orphan record | 17 |
| an orphan record with no name, so the viewer draws no node | 4 (`11412011`, `10203261`, `10203262`, `09210151`) |

All 17 with no node carry the payload flag 孤兒案件未達相似度門檻: the
system names them (F1, S5). The 4 nameless orphan records carry **no flag**.
That is the silent part: a case in the list, no node, no flag. Example of the
17: 華中247's `09305080`, the 概要 case, refused by the orphan-name branch at
0.45.

**Nine case ids are listed under two projects.**

| Ids | Projects | Cause |
| --- | --- | --- |
| `10908271`–`10908274`, `11411016`, `11411017` (6) | 大龍265-7 (2 parcels) and 大龍265 (27 parcels) | **Verified.** The 265-7 unit's first parcel is `265-7`. The search guard's legacy stem rule accepts a case that names the stem (`265地號等27筆`). The cases belong to the larger unit. |
| `10405043` | 玉成253-1 and 玉成253 | **Verified**, same stem rule (`253地號等9筆`). |
| `10203261`, `10203262` | 玉成166 and 玉成253-1 | **Not established.** 253-1's cache holds no name for them. |

The 大龍265-7 list shows six cases of the larger unit, each with no badge on
265-7. A reader sees links that the graph does not explain.

**What this means for F1.** The stem rule is one more variant of the
membership decision inside S1 (`_case_name_carries_parcel`, the "legacy mono
form"). It admits a larger neighbour's cases into a smaller unit. F1 phase 1
must pin it as its own named policy before any unification.

**Options:**

| Option | What |
| --- | --- |
| A | Draw a node for each held case (a ghost node for the 17 and the 4), so the list and the graph agree. Moves the graph; needs F1's decision on the orphan branch first. |
| B | Keep the list as the honest record of what the city returned, and mark a list entry that has no node ("no node: below the similarity gate") in the 相關連結 debug section. Viewer only. |
| C | Remove a cross-listed case from the wrong holder by decision (stem rule scoped by declared count, or a ledger entry per pair) |

**Option B done 2026-11-15 (Order step 9, direct fix, D9 = B).** The 相關連結 list
marks each entry the graph draws no node for with `圖中無節點` (a tooltip says the case
belongs to the project but no node anchors it). A superseded entry takes no second
note. `caseHasGraphNode` uses the graph's own filter (a node's badge, or a named
orphan with a stage and a track). 28 entries are marked on the live payload (33
without a badge, 5 of them superseded). Pins: a node test, a source test, a data pin
(28) and a smoke check (expected from the data, rendered in 675 projects; red on the
old viewer: 0 marked, 16 projects differ). Option C (remove a cross-listed case
from the wrong holder) still waits for F1.

**Recommendation: B now, C through F1.** B costs one viewer change and removes
the unexplained links. C removes the cause, but the stem rule's population is
**not measured**: only the 9 duplicated ids are visible, and a stem-admitted
case that no other project lists does not show as a duplicate.

**Not measured:** how many cases the stem rule admits in total, and the graph
effect of option A.

---

## F9 — section label drift in 文山區-木柵段三小段-623 (user, 2026-11-15)

**The project.** 4 gazette approvals, 9 city cases, 39 parcels in every
approval. The city names the sections in three different ways over time.
Each approval's city case was paired with its gazette record by the 核定日期
(the dates match exactly: 2021/04/15, 2023/12/21, 2026/07/29).

| Gazette approval | Gazette suffix | City case(s) | City label | 基地 |
| --- | --- | --- | --- | --- |
| 833 · 擬訂 事業計畫 · 2019-01-31 | none | `09907221`, `09907222`, `09907223` | A區, B區, C區 | A1, B, A2 |
| 588 · 擬訂 權利變換 · 2021-04-15 | (甲區段) | `10804121` | A區 | A1 |
| 285 · 變更 事業計畫、權利變換 · 2023-12-21 | (乙區段) | `10907091` | C區 | A2 |
| 29 · 變更 權利變換 · 2026-07-29 | (甲區段) | `11502011` | 甲區段 | A1 + B |
| not approved: 變更(第二次), under review | (甲區段) | `11509002`, `11509003`, `11509004` | none (基地 only) | A1 / A2 / B |

**Four kinds of drift, each measured.**

1. **The area letter is not the 基地 letter.** A區 = A1基地, B區 = B基地,
   C區 = A2基地. The gazette and the city both print a letter, and the two
   letters do not match for C區.
2. **The label 甲區段 names a different land set in each approval.** In 2021
   it is A1. In 2026-07 it is A1 + B. In the 2026-09 filings (under review) the
   three cases all read 甲區段 and cover A1, A2 and B. The label 乙區段 was A2
   in 2023. By 2026-09 A2 sits inside 甲區段. The section scheme was
   reorganised, and the label did not change with it.
3. **The vocabulary switches.** The city used `X區` (A to C) until 2023, then
   `甲區段` in 2026-07, then 基地 names alone in 2026-09. The gazette uses
   甲/乙區段 from 2021.
4. **The viewer reads only `X區`.** The badge label parser accepts one token
   shape (`[A-E北南東西]區`). The 2026-07 approval shows a plain 北 although it
   merges two sections. The 2026-09 approval shows **three identical plain 北
   badges**; only the tooltip's case id tells them apart.

The 國 badges follow the data: the national page names 5 of the 9 cases and
none of the 4 newest, and node 29 carries no 國. That is consistent.

**How common is it?** Measured over every case name in all 675 projects:

| Vocabulary | Projects |
| --- | --- |
| `X區` (A to E, 北南東西) | 20 |
| 基地 as a section token | 2 (木柵623 and 寶清353-2) |
| 甲乙…區段 | **1** (木柵623 only) |
| mixing two vocabularies across cases | **2** (木柵623, 寶清353-2) |

寶清353-2 shows the same last step: A區/B區 through 2025, then
`(A基地及道路用地)` and `(B基地)` on the 2026-10 filings (`11510014`,
`11510015`). In both projects the 基地 names sit only on the newest filings
(case ids `11509…` and `11510…`). That suggests a change in the city's
convention in late 2026. It is **not proven**: it rests on two projects. A
third project with a 基地 token (逸仙34) uses a historical site name
(原基隆路整宅B基地), not a section label.

**Not measured:** how the 區段 edges link the sections across these four
approvals, and what the graph shows for 甲區段 lineage. The label drift means
no single letter can follow one section through the project.

**Options:**

| Option | What |
| --- | --- |
| A | Extend the viewer's badge parser to read 基地 and 甲/乙區段 tokens (`[A1基地]`, `[甲區段]`). Viewer only; fixes the identical-badge problem for 2 projects. |
| B | Leave it. The population is 2 projects and the city's convention may settle. |
| C | The pipeline resolves a `section_label` per case once (the way `national_badges` is resolved), with a mapping table for the drifted projects. The viewer renders the field. |

**Option A done 2026-11-15 (Order step 8, direct fix, D10 = A).** `nodeAreaLabel` in
`viewer/app.js` keeps the area letter first (`[A區]`, unchanged) and then reads the
tail after the last 案: the 基地 name (`[A1基地]`, `[A1、B基地]`), then 甲/乙…區段
(`[甲區段]`). A historical site name before the 案 (逸仙34's `原基隆路整宅B基地`)
is not read. The row width follows the label. 木柵623's three 2026-09 filings (three
orphan nodes of one stage) now show `[A1基地]`, `[A2基地]`, `[B基地]`. Pins: node
tests of the label function and of the three-case row, a smoke check (green on the
new parser, red on the old: 2 sibling groups with empty labels) and a live pin of
the 6 sibling label groups. Option C stays open if the vocabulary stays.

**Recommendation: A now, C if the city keeps the new vocabulary.** A is small
and removes the three identical badges. C adds a mapping that someone must
maintain by hand, and the population does not yet pay for it. A mapping from
甲區段 to 基地 sets must also say which approval it speaks about, because the
set changes (finding 2).

---

## Order

| Step | Item | Priority | Form | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | **F3** — the residuals of the explicit dependency | **P1** | direct `fix:` + live pin | — | **Done 2026-11-15.** Everything below reads `own_parcels`; the pin is the guard |
| 2 | **F4** — the id-stem sibling sweep (懷生16 +7 ids) | **P1** | openspec change (`official-link-discovery`) | F3 | **Done 2026-11-15** (`unit-sibling-id-walk`): 7 ids added; `09012312` held for F7 (clear its `sibling_probed` record) |
| 3 | **F5** — repair 3 land cores; the gate reads the payload's core | **P2** | direct `fix:` + live pin, then a small change for the gate | — | **Done 2026-11-15**: A repaired 3 cores (`09609301` returned); B `gate-reads-project-land-core` |
| 4 | **F7** — the count condition | **P2** | openspec change (a delta on the shipped requirement) | decided (single count rule); **needs D8 and D5 first** | **Done 2026-11-15** (`unit-count-rule`): 22 pass, 62 refused, 7 admitted; S5 still refuses the 7 (flag, no node) |
| 5 | **F1 phase 1** — one predicate, behaviour-preserving, golden table | **P2** | refactor + tests, no spec change | F3 | **Done 2026-11-15**: `membership_verdict`, 5 policies, golden table, F2 tier 1 (4 strict xfails) |
| 6 | **F1 phase 2** — each unification, one decision at a time | **P3** | one openspec change per unification | F1 phase 1, the user | Each moves up to 86 pairs and needs its own measurement |
| 7 | **F2** tier 2 — the live pinned-list test | **P3** | pytest | F1 phase 2 | Lands with the list as the honest record |
| 8 | **F9** — the badge parser reads 基地 and 甲/乙區段 tokens | **P3** | direct `fix:` (viewer) + harness case | the user's decision (D10) | **Done 2026-11-15**: `nodeAreaLabel`; 2 projects; no pipeline change |
| 9 | **F8** option B — mark list entries that have no node | **P3** | direct `fix:` (viewer) | the user's decision (D9) | **Done 2026-11-15**: 28 entries marked `圖中無節點`; C waits for F1 |
| — | **F6** — re-run the unrecorded-id scan after each sweep | — | a command | E13's sweep | No change |

---

## Decisions to make

**Decided by the user, 2026-11-15** (all ten, by the options below). A decision
is not an order to open a change: each change still opens on the user's word.

| # | Decision | Differs from the recommendation? |
| --- | --- | --- |
| D1 | **Superseded 2026-11-15 by the single count rule (see below).** First choice was C — equal count, or `原N筆` equals the unit's count. The single rule contains C. | **Yes** (recommended A). **Measured 2026-11-15 (F7 addendum): C adds 0 pairs over A; 3 of 86 pairs reach the gate and all 3 are equal-count and right. C is safe and flips no verdict today.** |
| D2 | **C, widened (D2-D)** — admit the 6 equal-count pairs **and 華興8's `09708111`**, after D1: 7 pairs, 6 projects. The admission count test is the single count rule below (same as D1). | **Widened by the user, 2026-11-15** (after the F7 addendum measurement). Sample the other 46 by hand before any more. |
| D3 | **A** — extend the step-2 walk into a unit-level sibling sweep | No |
| D4 | **A** — accept a sibling by the §8 gate rule | No |
| D5 | **C** — rewrite 3 land cores, add a pin, the gate reads the payload's core | No |
| D6 | **A** — behaviour-preserving refactor first, then each unification | No |
| D7 | **A** — tier 1 with F1 phase 1, tier 2 last | No |
| D8 | **A** — backfill all 675, name the empty list, add a live pin | No |
| D9 | **B** now (viewer marks a list entry that has no node), **C** through F1 | No |
| D10 | **A** now (viewer reads 基地 and 甲/乙區段 tokens), **C** if the vocabulary stays | No |

**The single count rule (D1 and D2), decided by the user on 2026-11-15, on the
advisor's recommendation.** One rule serves the §8 gate (D1) and the admission
of held-by-no-project pairs (D2):

> A case name passes the count test when its count (`等N筆`), or one of its
> `原N筆` values, equals the unit's count at **any approval** of the unit.

Conditions that go with the rule:

1. **It contains rule C.** The latest approval's count is one of the unit's
   counts. Checked on all 675 caches: 673 pass. The 2 that fail (寶清51-13,
   崇仁新村711-3) have a `land_core` with no count (F5, D5).
2. **The earlier counts are required input, never optional.** The gate had an
   optional parcel list that 5 of 6 callers did not pass (華中247). The counts
   must not repeat that. Store them next to `own_parcels` in the D8 backfill, or
   read them from the payload (as D5 reads the land core).
3. **An empty count list is a named report state**, like `view_gate_no_parcels`
   (for example `view_gate_no_counts`). It is not a silent fallback to
   "equal count".
4. **Pin the measured numbers in a test:** 24 guard-only pairs pass, 3 of them
   reach the gate, and no gate verdict changes. A later widening then fails the
   test and names the pair.
5. **Known cost:** the rule is weaker for a unit with many approvals and many
   different counts.
6. **Order:** D8 (backfill with the counts) and D5 (the 2 caches with no count)
   come before this change.
7. **華興8's `09708111`** is admitted only by this rule. It is a verified
   withdrawn 2008 predecessor (F7 addendum). The admission is part of D2's
   change, not of D1's.

The table below keeps the options and the original recommendation as asked.

| # | Question | Options | Recommendation |
| --- | --- | --- | --- |
| D1 | F7: add a declared-count condition to the own-parcel rule? | A equal count · B keep · C equal count or `原N筆` | **A**, measure C first |
| D2 | F1: the 53 held-by-no-project candidates | A leave unheld · B admit through discovery passing `own_parcels` · C admit only the 6 equal-count pairs · **D (added by F7 addendum)** the 6 plus 華興8, by "equal to the count of any approval of the unit" | **C** after D1, then look at the other 47 by sample. **Decided: D.** |
| D3 | F4: the sibling source | A extend the step-2 walk · B new script · C ledger the 8 ids | **A** |
| D4 | F4: the probe's acceptance for a sibling | A the §8 gate rule (city name vs the unit) · B name plus date as today | **A** |
| D5 | F5: the land core | A rewrite 3 · B read the payload's core · C both | **C** |
| D6 | F1: phase the merge? | A refactor first, then each unification · B one big merge | **A** |
| D7 | F2: which tiers, in what order? | A tier 1 with F1 phase 1, tier 2 last · B tier 2 first with the 93-pair list | **A** |
| D8 | F3: widen the backfill and name the empty list? | A yes, all 675 plus a live pin · B only the view-holders (today) | **A** |
| D9 | F8: a list entry that has no node | A draw a node for each · B mark it in the debug list · C remove a cross-listed case from the wrong holder | **B** now, **C** through F1 |
| D11 | **New 2026-11-15 (advisor):** the search guard S1 accepts 62 pairs the count rule refuses, and a fresh discovery would re-accept the 46 held by no project (D8 item 2 against D2) | A S1's own-parcel form adopts the count rule (the first F1 phase 2 unification) · B discovery stops passing `own_parcels` to the guard (undoes part of F3) · C leave it, pinned | **A** |
| D10 | F9: section labels that are not `X區` | A the viewer reads 基地 and 甲/乙區段 · B leave · C a pipeline `section_label` with a mapping | **A** now, **C** if the new vocabulary stays |

---

### D11 — the search guard against the count rule (found 2026-11-15)

F3 made discovery pass `own_parcels` to the search guard (S1). S1's own-parcel form
has no count test. The 46 held-by-no-project pairs that D2 left out sit in
`search_rejected` only because discovery once ran without parcels. A **fresh**
discovery, or a refresh with a 5-part search key, would re-accept them. Measured
offline: of 1,085 `search_rejected` names, 72 pass S1's own-parcel form; the count
rule refuses 53 of those (46 held by no project, 7 held by another). Over all names
the pair set is 62 (46 held by no project, 9 held here, 7 held elsewhere), frozen in
`tests/fixtures/s1_accepts_count_rule_refuses.json`; a pin lets it shrink and never
grow. Nothing re-accepts them today: no fresh discovery has run since F3.

Options: **A** S1's own-parcel form adopts the count rule (the first F1 phase 2
unification; it moves the 9 held-here pairs only on a future fresh run, because a
refresh appends and never removes); **B** discovery stops passing the parcels to the
guard (undoes part of F3); **C** leave it, pinned. Recommendation: **A**. It is the
user's decision.

---

## Appendix — method

Every measurement reads `data/projects.json`, `data/.link_cache/*/result.json`
and `viewer/projects.data.js`. The scripts were ad-hoc and are not kept.

- **Own parcels of a project:** the anchor node's `first_parcel`, then its
  `parcels`, first parcel first.
- **Parseable name:** `extract_landcore_from_case_name(name)` returns a land
  core. Parcel-less names are not compared.
- **Names of a project's cases:** the union of `candidate_names`,
  `search_rejected` and `case_case_names`. This is a limit: these are the
  routes' own products.
- **Guard verdict (F1):** `_case_name_carries_parcel(name, own[0], own)` and the
  section text of the name's core equals the cache's core.
- **Similarity verdict:** `compute_landcore_similarity(cache core, name core) ≥ 0.7`.
- **Held status:** `city_case_ids` of this project; any other project's; none.
- **Interior id gap (F4):** per project, per 7-digit stem, the digits between the
  lowest and highest held digit (`city_case_ids` plus `view_rejected`) that no
  project's `city_case_ids` holds. Each probe is `fetch_taipei_case_header_api`.
  A hit is classified with `verify_view_verified_ids`, once without and once
  with the own parcels.
- **Land core against the project id (F5):** `pid.split("-", 2)` gives
  district, section and the rest; the expected core is their concatenation.
- **Unrecorded view ids (F6):** every `case_id=` value in a cache's
  `view.html` that is not in that cache's `city_case_ids`,
  `view_verified_case_ids` or `view_rejected`.
- **Day-one claim (F2):** the old gate is `verify_view_verified_ids` called
  without `own_parcels`, which is exactly its pre-change behaviour.
- **List against badges (F8):** the list is `links.taipei`. The badges are every
  node's `links.taipei` plus every orphan record that has a `case_name`, a
  `stage` and a `track` (the viewer draws a node only for those). A list entry
  with neither is "unbadged". Superseded ids are `links.superseded_by`.
- **Cross-listed ids (F8):** ids that appear in the `links.taipei` of two or
  more projects. The stem rule was tested by running the guard's three
  branches on the unit's first parcel: exact, legacy stem (`<mono>地號` or
  `<mono>等`), and the unit's own parcels.
- **Count test (F7 addendum):** the guard-only pairs of F1, each with the name's
  `等N筆` (the first count), its `(原N筆)` values, and the unit's count from the
  cache's `land_core`. "Any approval" counts are the `land_count` and
  `orig_count` of every node of the project. "Gate can see" means the case id
  is in `view_verified_case_ids`, in `view_rejected`, or named as `case_id=` in
  the cached `view.html`. The script is ad hoc (scratchpad `d1_measure.py`).
- **Label drift (F9):** the gazette suffix is the `案名` of each node; the city
  label is the suffix of `candidate_names`. The pairing is by the 核定日期 of
  the case's milestones against the node's date. Vocabularies are three
  regexes: `X區` (`[-(（]\s*[A-E北南東西]區`), `[甲乙丙丁戊]區段`, and
  `[A-Za-z]\d?基地`.
