## Context

`refresh_project` (`urtpe/links.py:1786`) is the per-project repair path. It
repeats the parcel search, re-reads each case's milestones (data2) and header,
re-derives each case's status, re-runs the national view-page absorb, and
verifies the view-verified ids.

Three things it does not do are the three defects this change fixes.

**D7 — the merged projection is never re-derived.** `taipei_milestones` and
`milestones_source` are written only by the discovery path
(`urtpe/links.py:694-695`). The refresh rewrites `case_milestones[cid]`
(`urtpe/links.py:1890`) and, in the search step, appends a case id with an
empty entry (`urtpe/links.py:1845-1851`). Neither write re-merges. The
stale projection is what `attach_links_to_projects` copies into the project
(`urtpe/links.py:3077-3079`).

**D8 — the implementation layer is never re-fetched.** The refresh calls
`fetch` (data2) and `fetch_status` (the header). It never calls
`fetch_taipei_implementation_api` or `fetch_taipei_rewards_api`. The
non-fresh discovery path returns the cached object verbatim
(`urtpe/links.py:597-612`), so the standing CLI run cannot repair it either.

**D13 — an emptied case keeps its stale state.** The refresh treats an empty
header as no evidence (`urtpe/links.py:1895`) and an empty milestone reply as
"keep what you have" (`urtpe/links.py:1886-1887`). Both are right on their
own: one empty response can be a transient failure. The gap is that no rule
tells "the city emptied this id" from "the request failed". The measured shape
is **two** empty sources in the same refresh.

## Goals / Non-Goals

**Goals:**

- Re-derive the merged projection from the cases after the per-case pass.
- Re-fetch the implementation layer for the cases that lack it.
- Label a case the city emptied as 無, without claiming a removal.
- Keep a 無 case's stale payload from winning either selection layer.

**Non-Goals:**

- Changing the discovery path. It already re-derives the projection.
- Changing the per-case milestone rule (the withdrawn-approval conflict rule
  stays as it is).
- Changing the parcel-search behaviour or the supersede rule.
- Adding a retirement mechanism. The city states nothing about a removal, so
  the pipeline claims none: the case keeps its id and its cached data.

## Decisions

**D1 — The re-derivation projects the cases exactly (overwrite).**

The projection is rebuilt by the same merge the discovery path applies
(`merge_stage_milestones` over `city_case_ids`). A label no case carries any
more is dropped.

*Alternative considered:* keep a stored value when no case carries it. Rejected
— that is what the stored projection already does, and it is the defect: it
keeps `審議通過日期 = 2026/03/18` for `士林區-光華段四小段-282地號等2筆` when
the city re-dated it to `2026/09/23`.

The withdrawn-approval rule (`_APPROVAL_FIELDS`, the per-case conflict rule at
`urtpe/links.py:1879-1882`) is a **per-case** rule and is unchanged. It keeps
a withdrawn approval date on the case, because that date decides the node
binding. The projection is a different layer: it reports what the project's
cases currently say. The two layers disagree by design, and the emit-time
layer is the one that decides the binding.

**D2 — The re-derivation runs after the per-case pass and before the write.**

It must see the refreshed `case_milestones`, so it runs after the pass. It
must not see the view-absorb's own case ids unless those were appended to
`city_case_ids` — the absorb adds ids to `city_case_ids`
(`urtpe/links.py:789`), so a re-derivation after the absorb picks them up too.
The projection is therefore computed at the end, just before the cache is
written, over whatever `city_case_ids` holds at that moment.

**D3 — The implementation fetch is per case, selected by "live, approved, no
entry".**

The selection is: the case is not terminal, it is not labelled 無, it carries an
approval date (`_APPROVAL_FIELDS` — `核定日期` / `權變核定日期` / `概要核准日期`),
and the cache holds no implementation entry for it.

*Alternative considered:* per project — fetch only where the project's payload
is empty. Rejected: the per-project rule missed
`萬華區-青年段一小段-130地號等3筆`, whose payload holds entries for two of its
three cases, and it is the missing third that carries the dates.

The reply is stored only when it is non-empty. An empty reply is a genuine
answer ("this case has no implementation data"), and storing it as an empty
entry would make the case look fetched when it was not.

*Measured scope:* **37 cases in 32 projects** (offline, 2026-11-06). The
board's earlier count of 26 in 22 came from a probe whose approval list was
`核定日期 / 核准日期 / 核備日期 / 審議通過日期` — the platform's field names. It
therefore missed 13 cases the pipeline's own approval list holds:
`權變核定日期` (a change-of-rights approval — 7 cases) and `概要核准日期` (an
outline approval — 6 cases). Two cases the board's list holds and the
pipeline's does not are in-review (their only "approval" is
`審議通過日期`, a deliberation-pass date, and their state is 審查中) — those are
correctly not selected. The scope is therefore 37, and each of the 13 extra
cases is a real approval the city published.

*Cost:* 37 × 2 requests (data3 + data4), at ≥1 s spacing.

**D4 — The 無 label needs two empty sources.**

A case is labelled 無 when the refresh reads an empty header row **and** empty
milestones for it. One empty source is not enough: one empty response can be
a transient failure, which is why the header rule alone treats an empty row as
no evidence.

The rule reads the **header** and the **milestones**, both of which the
refresh already fetches per case. It does not need the implementation reply,
so the label does not depend on the fetch order.

*Alternative considered:* also require that the parcel search no longer returns
the id. Rejected: the search omits approved ids for known reasons
(`10708311`, `11412011`), so its absence is no evidence — and the rule claims
no removal anyway.

**D5 — The 無 label replaces the state; it does not remove anything.**

The case keeps its id, stays in `city_case_ids`, keeps its `case_milestones`,
and no successor is recorded for it. The state's job is to say what the case
currently is; 無 says "nothing". The existing `filter_live_cases` rule then
lets a live same-name sibling bind the node
(`信義區-虎林段四小段-38地號等138筆`'s `11502012`).

*Alternative considered:* record `superseded_by`. Rejected — that asserts the
city re-filed the case, which the empty responses do not say.

**D6 — The 無 exclusion applies at both selection layers.**

`select_best_payload` picks by key count; `pick_implementation_payload` also
collects dates over every 擬訂 plan case and falls back to the key-count pick
for a field no plan case carries. A 無 case must be excluded from both, or the
stale copy still supplies a date.

The exclusion is implemented by giving the selection functions the set of
excluded case ids, rather than by filtering the payload dict at the call site:
the two functions are called from several places, and a call site that forgets
the filter would reintroduce the defect silently.

*Alternative considered:* keep the exclusion inside the payload dict by
dropping the 無 case's entry when the cache is written. Rejected: the case
keeps its cached data (the user's decision), and the cache is the record of
what the pipeline holds.

**D7 — The near-empty live payload wins, and the report names the shrink.**

The decided rule would replace `信義區-雅祥段一小段-227-4地號等10筆`'s 26-key
payload with the live sibling's 1-key payload. The rule applies, and the
refresh report names the case, the before size and the after size.

*Alternative considered:* keep the 無 case's payload when the live one is
smaller. Rejected: the stale copy would keep winning, which is the defect.

## Risks / Trade-offs

- **[The projection changes on 85 caches]** → The change is the point: 84 of
  them lose or alter a label and 66 carry a conflicting value today. The
  re-emit's diff is measured against the pre-refresh payload and reported.

- **[The implementation fetch costs 26 × 2 requests]** → The endpoint is
  WAF-capped, so the fetch is per case and the pass is sliced and resumable.

- **[A case's implementation payload is genuinely empty]** → No entry is
  stored, and the case is not re-fetched on the next pass (the "no entry" test
  would select it again — so the pass must record that it was fetched). The
  refresh report counts the fetch, so "fetched and empty" never reads as
  "not fetched".

- **[The 無 label clears a state that was right]** → Two empty sources in one
  refresh is the measured shape of a moved case, and the label is the honest
  reading of an emptied id. The report names every labelled case, and the
  label is reversible by the next refresh (a case that comes back reads its
  header again).

## Migration Plan

1. Land the code change and the tests (no output changes).
2. Run the cache pass over the affected projects (one slice, under the
   single-writer lock).
3. Read the refresh report: the list of cases labelled 無, the before/after
   payload sizes, the projection changes.
4. One re-emit through the standing `--from-js` path.
5. Rollback: revert the code change and restore the cache directories from the
   backup the pass takes.
