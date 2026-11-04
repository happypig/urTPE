# Design: resolve-recno-case

## Context

Actors: `attach_links_to_projects` (the only node-binding site), the per-node
case matcher `_match_case_by_date`, the positional fallback at
`urtpe/links.py:2514–2522`, the discovery result (`DiscoveryResult`: city_case_ids,
candidate_names, case_milestones, case_schedules, case_headers,
superseded_by), and the city ashx endpoints (`get_project168_top.ashx` for
headers, `Get_updcase_list.ashx` for the parcel search).

Flow: PDF → TSVs → merge → projects.json; on `--links`/`--from-js --links`,
discovery fills per-project caches, then `build_graph_document` calls
`attach_links_to_projects`, which binds each member record's node to a city
case: date match first (exact, then ±1 day), then the positional fallback by
track. The fallback bound 71 nodes on 51 projects to a case their own date
refutes (C6).

The user's rule (2026-11-04): every recno has a corresponding city case_id —
the resolver must find it, never guess by position. The user's area-split
rule (2026-11-03): one approved recno binds every same-date case of its area
split. The C6 user resolutions (2026-11-04) add two rules proven on live
data: a 無 case yields to an approved same-name sibling (東湖34), and the
案名 match runs before any date window, with 自行撤回 cases excluded
(吉林705).

Measured resolver performance over the whole corpus: 52 of 71 nodes bind by
name alone; 14 more need the same-day id probe (~230 read-only requests);
2 need the header's `uro_chk_date`/`uro_chk_date2`; 3 need a parcel search
on a non-first parcel. 70 bind on the exact date; 1 (康寧626) on stage + a
10-day drift.

Two facts the probe corrected, both now requirements:

1. **Case ids are a city-wide daily serial** (ROC filing date + one digit
   counted across the whole city, not per project). A same-day id is a
   candidate only; its CASE_NAME must name the node's land core. Measured:
   10203252 is 中山111; 10405042 is 玉成253-1, filed the same day as
   玉成253's 10405041.
2. **The city's data2 sometimes copies another case's approval date**
   (玉泉11's 09504263 header says 2013-08-20 while data2 says 2008/05/15;
   吉林705's 09307104 data2 copies 09307101's 2010/01/08). The header is the
   second approval source; S14 stores it per case.

## Decisions

### D1 — The resolver runs after `_match_case_by_date`, at the same site

`attach_links_to_projects` keeps its date-matcher call. When it returns "",
the node calls `resolve_node_cases(member, disc)` instead of falling back to
`city_case_ids[0/1]`. One binding site, one re-emit; the date matcher's 1,356
correct bindings are untouched.

### D2 — Name matching in three tiers, live-set filtering before tiers

Tier functions (pure, exported for tests):

- tier 1: exact after `re.sub(r"\s", "", ...)`.
- tier 2: loose — 擬定→擬訂, 案及→及, `土地更新`→`土地都市更新`, area-suffix
  strip (`-?[A-Z北南東西甲乙]區(段)?(\([^)]*\))?|\([^)]*區段\)`), strip
  `(原N筆)`, 等, trailing 案, `權利變換案`→`權利變換計畫案`.
- tier 3: (stage-with-ordinal, plan-type) — stage `擬訂`/`變更`/`變更(第N次)`,
  plan type 概/事/權 after removing `(含釐正圖冊)`.

Before comparing, the live set filters: drop schedules in
{自行撤回, 已駁回, 已失效}; if 2+ live cases remain and any approved
(核定/權變核定/概要核准) same-name case exists, 無 cases yield to it (東湖34).
Tier order: 1 → 2 → 3, stopping at the first tier that yields exactly one
live case or an area split.

Area split: every live match in the tier carries a distinct non-empty area
suffix → all bind. Anything else with 2+ survivors at every tier → no bind
from that tier (the next steps may still resolve).

### D3 — Same-day id probe: candidate generation and acceptance

Candidates: for each id the project already holds (cached `city_case_ids` +
`view_verified_case_ids`), the ten ids `<first7>0–9`. Skip ids the project
already knows. Probe `get_project168_top` (rate-limited: the caller passes a
`sleep` between requests; default 1.0 s, same as discovery).

Accept a probed header **only when both**:
- its `CASE_NAME` equals the node's 案名 (tier 1 or 2 name comparison
  against the node — the serial-number fact makes any weaker check unsafe),
- and its approval date (`uro_chk_date`/`uro_chk_date2`, the S14 source)
  matches the node's date exactly, or the case's stage matches the node's
  tier-3 stage and the date falls within the C8-observed window (exact only
  in v1: all 14 probe finds matched exactly).

On acceptance the case joins the cache in place: appended to
`city_case_ids`, its `case_milestones` fetched via the standing milestone
adapter, `candidate_names[cid] = CASE_NAME`, `case_headers[cid] = NAME`.
The probe result is recorded so a second run skips the probing (the
`case_milestones` presence is the memo).

### D4 — Header dates as the second approval source

`refresh_project` and the probe persist `uro_chk_date`/`uro_chk_date2`
per case into `case_headers` as `{cid: NAME}` — extended to a dict
`{cid: {"NAME": …, "uro_chk_date": …, "uro_chk_date2": …}}` **only for new
writes**; readers accept both shapes (a bare string is the old `NAME`
value). Step 3 of the resolver reads the header dates of cached cases:
a case whose header approves on the node's exact date binds even when data2
carries a different (plan-case) date. Bounded drift: when the header date
misses exactly but the case's stage equals the node's tier-3 stage and the
header date is within 10 days, it binds (康寧626: 2016-11-12 header vs the
node's 2016-11-02, the only measured case). The 10-day bound is a measured
constant, not a threshold to tune.

### D5 — All-parcel search last, accepted on name + date

For each parcel in `member.parcels` (the node's own list, not only
`first_parcel`), run the standing `search_taipei_cases_api`. Accept a result
case when its name matches the node (tier 1 or 2) and its header/milestone
approval date matches the node's date. On acceptance, join the cache as in
D3. The step runs at most once per node and stops at the first accepted
case; the searched parcels are recorded in the run report.

### D6 — Unplaced nodes are reported, never silently unbound

A node that every step misses keeps its existing binding (today's payload
value rides through `--from-js`) and gains a review flag
`節點未能對應平台案件(案名:…, 日期:…)` on the member record, and the run
report counts it. The measured corpus resolves all 71, so the flag asserts
nothing today; it exists so a future corpus change is visible.

### D7 — Where the resolver lives

`urtpe/links.py`, next to `_match_case_by_date`: `node_name_key`,
`node_name_loose`, `node_stage_kind`, `filter_live_cases`,
`resolve_node_cases(member, disc, fetch_header=None, fetch_milestones=None,
search=None, sleep=None, probe_headers=None)`. Network adapters are injected
parameters so unit tests run offline.

**The emission-side attach stays offline.** `attach_links_to_projects` never
issues a request: at emit time the resolver reads the caches' own
`case_headers` (steps 1 and 3) and the `probe_headers` memo (step 2's finds
persisted by earlier runs). The live probe and the all-parcel search run in
the discovery/refresh layer (the one-off sweep driver in task 3.3, then R),
which writes their finds into the caches; the next emission binds offline.
This matches D5's advisory design: an emission must not turn into an
unannounced crawl (~230 requests once is a sweep decision, not an emission
side effect). `probe_headers=None` therefore means "use only the memo the
caches carry" — no live probing at all in production attach; the adapters'
defaults exist for the sweep driver and the tests.

### D8 — Absorbed steps

S8 (area-split tie by date) is superseded: the name matcher's area-split
rule binds the same 31 nodes/56 cases without the date-tie exception.
S12 (same-day probe for missing plan cases) is D3. S14 (header dates) is
D4. All three had targeted the same fallback line.

## Consequences

- The positional fallback disappears from the binding site; the
  `cache-freshness` requirement that named it ("binds by index") keeps the
  list-order contract for appends but no longer describes a binding
  behaviour.
- ~230 one-off gis.uro requests run once during this change's discovery;
  later runs hit the cache (the probe's finds persist in the caches).
- `pick_implementation_payload` (S11) then sees the newly cached 擬訂 plan
  cases; its second run recovers the 3 remaining construction-date projects.
