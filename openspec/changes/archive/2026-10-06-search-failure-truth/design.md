# Design — search-failure-truth

## Context

`sweep-failure-truth` split a targeted search into three outcomes: match, miss, error. It
covered the *probe* loop. The *search* that produces the candidate view ids still collapses
two different things:

```python
# scripts/fetch_remaining_national_portal.py:346-350
try:
    html = fetch_url(url, None, True)
except Exception as e:
    print(f"  search failed: {e}", file=sys.stderr)
    return []
```

A request that failed and a search that succeeded with no results both return `[]`. The
caller reads that as `OUTCOME_MISS`, so a brief outage during the search phase suppresses
every project it touched for 14 days.

## Goals

- A search that could not be performed is an error; a search that ran and found nothing is a
  miss.
- The two existing empty-result populations become distinguishable going forward.

## Decisions

### D1 — The search returns a result, not a list

Returning `[]` for both causes is the root of it. `search_portal` returns
`(outcome, view_ids)` so the distinction is made where it is still known, at the point the
exception was caught. Inferring it later is impossible: both cases look like an empty list.

This is the same reasoning as `find_matching_view_with_outcome` in the previous change, one
level up, and it was missed there because the empty-search path was described from memory
rather than measured.

### D2 — An error search means no candidate, not a negative

A project whose search failed is neither found nor absent. It is recorded as an error, which
carries no re-probe exclusion, so it returns to the next run's queue. This is the behaviour
`sweep-failure-truth` established for failed probes.

### D3 — The 14 existing empty-result entries stay as they are

Of the 14 entries with `view_ids_checked: []`, nine are sections where the portal genuinely
has no listing — those are correct as misses. The other five may or may not have been
transport failures. Nothing in the record distinguishes them, so re-classifying means
guessing, and guessing wrong either re-probes nine projects for nothing or buries five real
ones for another fortnight.

They will age out of their TTL naturally, at which point the fix applies.

## The 48 recoverable projects: measured, and abandoned

The larger goal behind this work was to raise the twur coverage rate by chasing the 48
projects classified `has-approved` or `mixed/other` — 16 and 32 respectively. The spec for
*Classify ledger negatives* says such projects *"re-enter the targeted queue with the case's
own 案名 fragments as search keys"*, and no code implements that.

Before building it, three measurements:

**1. The portal does not respond to 案名 search at all.** Same endpoint, same project:

| search term | view ids returned |
|---|---|
| `桃源段四小段` (section) | `['793']` |
| full 案名 | *(none)* |

| search term | view ids returned |
|---|---|
| `通化段六小段` (section) | `['1037', '892']` |
| full 案名 | *(none)* |

| search term | view ids returned |
|---|---|
| `通化段五小段` (section) | `['1109', '1012', '822', '699']` |
| full 案名 | *(none)* |

Three for three, the specific key returns *less* than the section key. The portal's `title`
search matches on something else entirely. Building case-name search would have produced
zero additional candidates.

**2. Where the portal does return pages, they belong to other projects.** Inspecting titles
directly:

| our project | portal pages returned | what they actually are |
|---|---|---|
| 通化段六小段202等7筆 | `1037`, `892` | 665地號等31筆, 497地號等22筆 |
| 通化段五小段447等5筆 | `1109`, `1012`, `822`, `699` | 191-4等24筆, 191-1等6筆, 242等10筆, 416等13筆 |

Right 段/小段, wrong parcel. `view_page_matches` is correct to reject them, and its
section-parcel-count test is doing its job.

**3. Across the whole population.** Of the 48:

- **9** have a section search that returned nothing at all — the portal has no listing for
  that 段/小段.
- **39** did return pages, and the sweep's own record shows all **162** probed view ids
  rejected on parcel/count. Every one is a different project in the same 段/小段.

So the twur portal genuinely does not list these units. `has-approved` is a fact about the
*Taipei* case system (`get_project168_top.ashx`), not about twur's coverage — a unit can
have a city-approved case and still never appear on the national portal. The `recoverable`
class was being read as "recoverable on twur", which is a stronger claim than the data
supports.

Conclusion: the headroom is in the **20 unprobed view ids** left behind by 10 projects that
hit `--max-probe 8`, and that is one flag rather than a feature. Everything else is already
correctly excluded.

## Risks

- **`search_portal` gains a return-shape change.** Two call sites in tests plus the crawl
  loop; all updated, and the shape is pinned by a test that walks every return path.
- **More `error` entries in a real outage.** Correct, and intended: the alternative is
  silently suppressing a whole sweep's worth of projects for a fortnight.

## Migration

None. New outcomes apply to new entries; the 14 existing zero-result entries are untouched
(D3).