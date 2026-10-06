# A failed portal search must not be recorded as a negative

## Why

`sweep-failure-truth` stopped a *probe* failure from being recorded as a 14-day negative.
The same conflation survives one level up, and I missed it because I reasoned about the
empty-result path instead of measuring it.

`search_portal` catches every exception, prints to stderr, and returns `[]` (lines 346–350).
The caller cannot distinguish that from a search that succeeded and found nothing, so it
records a miss:

```
search_portal raises  ->  []  ->  OUTCOME_MISS  ->  14-day negative
```

My own design note in `sweep-failure-truth` justified this as *"there was nothing to fetch
and therefore nothing that could have failed"* — which is true of a real empty result and
false when the request itself failed. A brief portal outage during a search phase now buries
every project it touched for a fortnight, and the ledger entry is indistinguishable from a
genuine "the portal has nothing for this 段/小段".

Measured exposure: **14 of 75** ledger entries carry `view_ids_checked: []`, i.e. their
search returned nothing. Nine of those are sections where the portal genuinely has no
listing. The remaining distinction is not recorded anywhere, so those 14 cannot be told apart
today.

The live 2026-10-06 run did not exercise this path — stderr was empty, so no search failed —
which is the only reason the fix is not more urgent than it looks.

## What Changes

- **A failed search request and an empty search result are different outcomes.** A request
  that raised records an error and carries no re-probe exclusion, exactly as a failed probe
  run does. A request that succeeded with no results remains a miss.
- **The 14 existing zero-result entries are left alone.** They were written under the old
  rule and carry no signal about which cause applied.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fetch-remaining-portal`: a search that could not be performed is an error, not a
  negative; only a search that ran and found nothing is a miss.

## Impact

- **Changed:** `scripts/fetch_remaining_national_portal.py` — `search_portal` reports a
  transport failure distinctly from an empty result, and `find_matching_view_with_outcome`
  maps that to the error outcome.
- **Data:** the 14 existing `view_ids_checked: []` entries are untouched and remain
  indistinguishable. Retrospecting them would be guessing.
- **Behaviour:** no change for a run where the portal is reachable, which is every run
  observed so far.

## What this change deliberately does not do

It does not chase the 48 `has-approved` / `mixed/other` projects. That was the larger goal,
and measurement killed it — recorded in `design.md` because a negative result worth having
is worth writing down rather than leaving as an assumption.