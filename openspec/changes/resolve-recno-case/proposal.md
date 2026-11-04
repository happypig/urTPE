# Proposal: resolve-recno-case (S10 — C6 types 1–6 + C8b)

## Why

`attach_links_to_projects` binds each gazette node to a city case by date
(`_match_case_by_date`) and falls back to `disc.city_case_ids[0/1]` by track
position when no date matches (`urtpe/links.py:2514–2522`). Re-running the
pipeline's own matcher over the payload measured **71 nodes on 51 projects
bound by that positional fallback, unmarked** — the 北 badge, the 相關連結
label and the per-node timeline all read from a case the node's own date
refutes. The user's rule (2026-11-04): **every recno has a corresponding
city case_id, so the fallback must find it, never guess by position.**

The 71 nodes split by measured cause (Batch C, C6):

| Cause | Nodes | Example |
| --- | --- | --- |
| Area-split tie — the city filed one approval as 2+ area cases (A區/B區, 北區/南區), the gazette prints one row | 31 | 吉林508 recno 259 → 11011241 A區 + 11011242 B區 |
| Tie, other shape (2 same-date cases, one superseded/無) | 5 | 東湖34 recno 73: 11302181 (無) yields to 11502008 (approved) |
| Name resolves, date drifts 2–7 days | 5 | 瑞安838 recno 590 → 10611204 |
| Name resolves, date drifts 8–60 days | 5 | 康寧626 recno 1019 → 09712204 (header date, 10 days off) |
| Right case missing from the cache | 24 | 犁和302 recno 281 → 10203253 (found by same-day id probe) |
| No approval date on any cached case | 1 | 玉成253 recno 508 → 10405041 (same-day probe) |

A simulated 4-step resolver over all 71 nodes (measured 2026-11-04, scratch
scripts + ~230 read-only gis.uro requests) finds a case for **all 71** — 52 by
name over cached cases, 14 by a same-day id probe, 2 by header approval
dates, 3 by searching every parcel of the node. It also recovers the missing
擬訂 plan cases C8(b) lists (新光101 09703181, 寶清599 09303270,
敦化585-11 10210171, 南港19-1 10111131, 南港601 10406241, 玉成253 10405041,
敦化449-12 10209291), which lets S11's second run emit their construction
dates.

Absorbs S8 (the area-split rule, user decision 2026-11-03), S12 (the
same-day probe) and S14 (header dates as an approval source) — all four
would edit the same line.

## What changes

- `urtpe/links.py`: a new `resolve_node_cases` resolver replaces the
  positional fallback in `attach_links_to_projects`. Four steps, in order:
  1. **案名 match over cached cases** — tier 1 exact (spaces ignored), tier 2
     loose (等, `(原N筆)`, 案及/擬定↔擬訂, area suffix), tier 3 stage-with-ordinal
     + plan type. Skips 自行撤回/已失效 cases; a 無 case yields to an approved
     same-name sibling; distinct area suffixes on every match = an area split
     and **all** its cases bind to the node (the user's 吉林508/榮星53 rule).
  2. **Same-day id probe** — `get_project168_top` on `<first 7 digits>0–9` of
     every known id (cached + national 相關連結). Case ids are a city-wide
     daily serial, not a per-project batch, so a probe hit is accepted **only
     on CASE_NAME matching the node's land core + header date matching the
     node's date** (exact, or the stage matching with the node's tier-3 name).
     A newly proven id joins the cache (city_case_ids appended,
     case_milestones/candidate_names/case_headers filled).
  3. **Header approval date** — a cached case whose header
     (`case_headers`, S14: store `uro_chk_date`/`uro_chk_date2`) approves on
     the node's date while data2 carries another case's date (玉泉11 09504263
     shape) binds. Accepts a bounded drift (10 days) when the stage matches
     exactly (康寧626 shape).
  4. **All-parcel search** — `Get_updcase_list` on every parcel of the node,
     not only `first_parcel` (南港566's plan case hides under parcel 567,
     金華455-3's under its old first parcel 508). Accepted on name + date.
- A node the resolver still cannot place is **reported by name** in the run
  report (none in the measured corpus) — never silently unbound.
- Spec deltas: `official-link-discovery` (the node-binding requirement gains
  the resolver; the positional fallback is removed) and `cache-freshness`
  (the case-discovery requirement names the resolver as the caller of the
  probe and the all-parcel search).

## What does not change

- The payload shape: `node.links.taipei` is already a list; an area split
  appends its 2+ case ids.
- `_match_case_by_date` stays the first binder: the resolver runs only for
  nodes the date matcher cannot place.
- The orphan gate, view-verified verification and the §8 rejection records
  are untouched.
- No positional case id is ever removed from `city_case_ids` (append-only;
  the refresh and the offer step rely on the order).

## Capabilities

### Modifications

- `official-link-discovery`: MODIFIED — the "Join links to projects by
  land-identity core" requirement's node binding gains the 4-step resolver
  and drops the positional fallback; a new scenario set pins the area-split
  rule, the 無-yields rule, the same-day probe acceptance (CASE_NAME + date),
  the header-date step and the all-parcel search.
- `cache-freshness`: MODIFIED — the "targeted refresh" requirement's new-case
  append cites the resolver (R reuses it); the positional-fallback-by-index
  wording stays (the list order contract is unchanged) but the binding-side
  fallback is gone.

## Risks

- The probe costs ~1 header request per candidate sibling id (10 per known
  id batch, bounded to ids sharing the node's date-implied filing day is not
  possible offline — the probe is bounded to `<first7>0–9` of ids the project
  already holds, measured ≈230 requests for the whole corpus, one-off).
- Tier-2 loose matching could over-match a same-stage sibling with a
  different parcel count; the tier comparison strips count noise, so the
  risk is a genuinely different unit with an identical name — measured 0
  cases; the land-core check in step 2 and the accepted-on-name-only rule in
  steps 3–4 keep the binding date-anchored.
