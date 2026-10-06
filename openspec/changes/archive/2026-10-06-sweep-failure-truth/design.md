# Design — sweep-failure-truth

## Context

`scripts/fetch_remaining_national_portal.py`, `find_matching_view` (lines 376–397):

```python
for vid in vids[:limit]:
    checked.append(vid)
    try:
        html = fetch_url(url, None, True)
        if view_page_matches(html, section, parcel, count):
            return vid, milestones, city_ids, html, checked
    except Exception as e:
        print(f"  Error checking view/{vid}: {e}")
        continue
...
return "", {}, [], "", checked     # <- identical for "missed" and "all fetches failed"
```

The caller (lines 570–575) sees an empty view id, prints "No matching view_id found",
and calls `record_no_match`. That stamps `last_probed`, which is what excludes the project
for 14 days. One transient failure costs a project two weeks, and the record is
indistinguishable from a real miss.

Measured context for the run that prompted this: 62 candidates queued, all 147 existing
ledger entries aged 38–42 days, so the 14-day TTL currently excludes nothing and every
queued project is being probed cold. The portal's own politeness requirement is 3–5 minute
intervals (the code now uses 60–180 s), which is what a flaky third-party endpoint looks
like in practice.

## Goals

- A failed probe run never produces a TTL-excluding negative.
- The ledger distinguishes "could not reach the portal" from "the portal does not list this
  parcel".
- The stop time is a launch-time option, and the 06:30/07:00 disagreement is gone.

## Decisions

### D1 — Distinguish three outcomes, not two

`find_matching_view` already separates the interesting cases; the caller collapses them.
Add a third return value rather than inferring from the empty string:

| outcome | condition | ledger class | TTL exclusion |
|---|---|---|---|
| **match** | a probe returned a satisfying page | entry removed | none |
| **miss** | all probes returned, none satisfied | `recoverable` / `never-approved` as today | 14 days |
| **error** | every probe raised | `error` | **none** |

Inferring from the empty string cannot work: `return "", {}, ...` is already the miss
path, so the error case has to be reported explicitly at the point where it is still known —
inside the loop, by counting raises.

### D2 — `error` carries no timestamp-based exclusion

The tempting minimal fix is to record the error but leave `last_probed` unset. That fails:
`filter_candidates` skips on "parseable `last_probed` newer than cutoff", and the entry
would then be *permanently* eligible rather than merely retryable — a project the portal
genuinely does list would be re-probed on every single run forever, at the politeness cost
of a full sweep each time.

So `last_probed` stays (it is evidence of when the failure happened) and eligibility moves
to the class: `error` is never TTL-excluded. Re-probe pacing for a failing project is
governed by the crawl's politeness policy, which is the correct control for it.

### D3 — Leave the 147 existing entries alone

They were written under the old rule and carry no signal about which were errors. They stay
as they are and remain TTL-excluded. Retro-fitting a class would be guessing, and guessing
here means either re-probing 62 projects unnecessarily or burying unknown numbers of real
matches for another 14 days.

### D4 — `--deadline HH:MM`, defaulting to 06:30

The stop time becomes a flag. It resolves to the first occurrence *after* launch, preserving
the existing `_next_deadline` behaviour that stops a post-deadline launch from exiting
instantly.

Two details that are easy to get wrong:

- **Malformed input must refuse the run**, not fall back to a default. Silently substituting
  06:30 for a typo means a sweep runs overnight against a portal the user meant to protect.
- **The resolved time is printed in the summary.** A hardcoded 07:00 meant the effective
  window was invisible after the fact; the run summary already reports counts, so the
  window belongs there.

### D5 — Partial failure that still matched is a match

If some probes raise and a later one satisfies the matcher, the project is found. Recording
an error there would be wrong in the opposite direction — it would discard a real match.
The error class is only for runs where **no** probe produced an answer.

## Risks

- **Retry exhaustion is the common path, not the rare one.** Three retries with 2/4/8 s
  backoff against a portal that was originally calibrated at 3–5 min intervals means a
  genuinely slow portal produces errors rather than misses. That is the correct outcome —
  slow and absent are different facts — but it will mean more `error` entries than a naive
  reading of the current 147-entry ledger suggests.
- **A project can now be re-probed repeatedly** if the portal stays unreachable. Bounded by
  the politeness interval and the run's own stop time, so this costs time rather than
  correctness.
- **Existing entries are not reclassified** (D3), so the first run after this change still
  carries whatever the old rule produced.

## Migration

None. New entries carry the new class; existing entries are untouched. The default stop
time is unchanged from what the requirement always said (06:30), which means the first run
that does not pass `--deadline` will stop six minutes earlier than before — a deliberate
correction of the drift, not a regression.