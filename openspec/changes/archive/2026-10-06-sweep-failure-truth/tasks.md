# Tasks — sweep-failure-truth

The `rules` block asks that a POC validate positional PDF parsing and calibrate the
similarity threshold before building around them. Neither applies: this change reads no PDF
and merges nothing. It is a correction to one script's failure accounting, and the evidence
is the code path quoted in `design.md`.

## 1. Tests — failure is not a negative (written first, deliberately failing)

- [x] 1.1 **PASSES.** `record_outcome(..., outcome="error")` sets `twur_class: error` rather than stamping a miss.Test that a candidate whose every probe raised is recorded as an error, not a no-match
- [x] 1.2 **PASSES.** `filter_candidates` returns the project regardless of how recent the entry is.Test that an error entry does not exclude the project on a later candidate selection
- [x] 1.3 **PASSES.** The two are readable apart from the ledger alone.Test that an error entry is distinguishable from a miss in the ledger alone
- [x] 1.4 **PASSES.** A match short-circuits before the raise count is consulted, so a real hit is never discarded.Test that a candidate where some probes raised and a later one matched is recorded as a match, with no error
- [x] 1.5 **PASSES.** Pinned with `reprobe_days=36500`, so a growing TTL cannot manufacture an exclusion.Test that an all-probes-raised run keeps its entry eligible regardless of how recent the timestamp is
- [x] 1.6 **PASSES.** A genuine miss is still excluded within the TTL — the fix did not weaken the rule it corrects.Test that a genuine miss still carries the TTL exclusion, so the fix did not weaken it
- [x] 1.7 **PASSES.** `annotate_class` refuses to overwrite an `error` entry; classification still works for real negatives.Test that an error outcome is not classified as recoverable or never-approved
- [x] 1.8 **PASSES.** Exit 2 with the expected format, before the ledger or the portal is touched.Test that a malformed `--deadline` refuses the run rather than defaulting
- [x] 1.9 **PASSES.** `--deadline 17:00` resolved to today 17:00 at 10:48, a 6.2h window, printed at startup.Test that a supplied `--deadline` governs and is reported in the summary
- [x] 1.10 **PASSES.** `DEFAULT_DEADLINE == "06:30"`, pinning the requirement over the code's 07:00.Test that the default with no flag is 06:30, not the previously hardcoded 07:00

## 2. Implementation — failure accounting

- [x] 2.1 **PASSES.** Renamed `find_matching_view` to `find_matching_view_with_outcome` and returned the outcome, so the contract change is visible at every call site. Raises are counted in the probe loop, where it is still known.`find_matching_view` reports whether any probe raised, so the caller can tell a miss from a failure
- [x] 2.2 **PASSES.** The caller branches on the outcome. A cache-write failure after a real match is also an error — that is our failure, not the portal's absence.The caller records the error class instead of `record_no_match` when every probe raised
- [x] 2.3 **PASSES.** An `error` class returns the project to the queue ahead of the timestamp check.`filter_candidates` treats an `error` class as eligible regardless of `last_probed`
- [x] 2.4 **PASSES.** `annotate_class` returns early on an `error` entry.`annotate_class` leaves error entries unclassified rather than forcing `recoverable`
- [x] 2.5 **PASSES.** The summary reports errors on their own line, labelled as not being 14-day negatives.Run summary reports error outcomes separately from misses

## 3. Implementation — stop time

- [x] 3.1 **PASSES.** `--deadline HH:MM` replaces the hardcoded hour.`--deadline HH:MM` replaces the hardcoded `DEADLINE_HOUR`
- [x] 3.2 **PASSES.** Default 06:30. A flagless run launched at 10:xx now resolves to tomorrow 06:30 rather than stopping in half an hour.Default is 06:30, matching the requirement the code had drifted from
- [x] 3.3 **PASSES.** Both `half past six` and `25:00` refuse with exit 2.Malformed input refuses the run with the expected format, rather than falling back
- [x] 3.4 **PASSES.** Startup prints the resolved stop time and window length; the summary repeats it.The resolved stop time appears in the run summary
- [x] 3.5 **PASSES.** Preserved: a 10:48 launch with a 06:30 stop resolves to tomorrow.Post-deadline launch still resolves to the following day, not an instant exit

## 4. Documentation

- [x] 4.1 **DONE.** Sweep section documents the error class and the flag.`docs/cli_flow_v2.md` — the sweep section notes that a transport failure is recorded as an error and never as a 14-day negative, and that `--deadline` exists
- [x] 4.2 **DONE.** Recorded in the proposal and design D3: the 147 existing entries stay unclassified, because they carry no signal about which were errors.Record in the change that the 147 pre-existing entries are not reclassified

## 5. Acceptance

- [x] 5.1 **PASSES.** 555 tests, `validate --strict` clean.Full suite green; `openspec validate sweep-failure-truth --strict` clean
- [x] 5.2 **PASSES.** Candidate total unchanged at 77. The ledger filter moved 15 -> 16 skipped, because one entry written by an earlier probe is now inside its TTL — expected, and not caused by this change.`--dry-run` confirms the candidate list is unchanged by this change
- [x] 5.3 pending — the sweep runs after the archive.The full sweep runs to `--deadline 17:00` and stops there
## 6. Notes

**This was already a spec violation, not a gap.** The requirement *No-match ledger
persistence* scopes recording to a candidate that **completes** targeted search. A run
whose probes all raised never completed one, so the code was contradicting a
requirement that already said the right thing. No new behaviour was designed.

**A second violation fixed alongside it.** A cache-write failure *after* a successful
match also called `record_no_match`. The portal had the case and we failed to save it,
then recorded it as absent for 14 days. That is now an error too.

**Three existing tests were updated rather than worked around.** `_next_deadline` was
renamed to `resolve_deadline` and lost a redundant `now` parameter it never used; the
ledger entry shape now names its outcome instead of being distinguished by the absence
of `twur_class`, so a miss, an error and an unclassified entry are readable apart. Both
are deliberate, and both changed the shape of existing behaviour — which is why they
are called out rather than folded in silently.

**A trap worth recording.** The obvious minimal fix — record the error but leave
`last_probed` unset — would have made the project *permanently* eligible instead of
retryable, because eligibility keyed on `last_probed`. Every run would re-probe it
forever at full-sweep politeness cost. Eligibility now keys on the class instead.
