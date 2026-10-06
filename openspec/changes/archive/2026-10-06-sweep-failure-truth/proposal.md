# Sweep failures must not be recorded as portal negatives

## Why

`scripts/fetch_remaining_national_portal.py` catches every exception per view-page probe,
continues to the next probe, and returns an empty view id when all of them fail. The caller
reads that as "no match" and calls `record_no_match`, which stamps `last_probed` into
`no_match_ledger.json` — the record that excludes the project from probing for 14 days.

So **one transient network failure buries a project for two weeks**, and the resulting
ledger entry is byte-identical to a genuine "the portal has no case for this parcel". The
two cannot be told apart afterwards.

This is not new behaviour to be designed. It is already a violation: the requirement
*No-match ledger persistence* scopes recording to a candidate that **completes targeted
search**. A run whose probes all raised never completed the search, so it was never a
qualifying negative. The code contradicts a requirement that already says the right thing.

The sweep also has no configurable stop time. `DEADLINE_HOUR = 7` is hardcoded, and
`_next_deadline` resolves to the first 07:00 after launch — so a run started at 10:28 stops
tomorrow morning, and a run started at 06:50 gets ten minutes. The governing requirement
says **06:30** while the code says **07:00**, so the spec and the implementation already
disagree about when the window closes.

## What Changes

- **A run in which view-page fetches failed does not record a negative.** The ledger gains
  an entry classed as an error rather than a no-match, and that class carries no re-probe
  exclusion, so the project returns to the next run's queue.
- **The error class is distinguishable in the ledger**, so a reader can tell "could not
  reach the portal" from "the portal does not list this parcel" without inferring it from
  timing.
- **The stop time becomes a flag**, replacing the hardcoded hour, which also resolves the
  06:30/07:00 disagreement between the requirement and the implementation.

No change to candidate selection, matching, or the politeness interval. No change to the
crawl's rate against the portal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fetch-remaining-portal`: a failed probe run no longer produces a TTL-excluding ledger
  negative; an error class is recorded instead and stays eligible. The execution stop time
  becomes configurable rather than hardcoded.

## Impact

- **Changed:** `scripts/fetch_remaining_national_portal.py` — probe-error tracking through
  `find_matching_view`, the caller's record-vs-error decision, `filter_candidates`'s
  eligibility rule, and a new `--deadline` flag replacing `DEADLINE_HOUR`.
- **Unchanged:** `urtpe/links.py`, the per-project cache format, the viewer, and the
  emitted dataset.
- **Data:** the existing 147 ledger entries are left as they are. They were written under
  the old rule and cannot be re-classified after the fact, since the record does not say
  which entries were errors.
- **Operational:** the sweep takes no single-writer lock and writes `.link_cache/` directly,
  so it must not overlap a pipeline run.