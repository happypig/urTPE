## Why

The operator running overnight batches of `scripts/fetch_remaining_national_portal.py` (the actor) re-churns the same known-absent candidates on every run: the script rebuilds its candidate list each run as "all projects missing twur", sorted newest-first, and a no-match result leaves the project on that list forever. Concrete event: the 2026-08-25 03:00 batch verified via live probes (通化段六小段218-1, 康寧段三小段821, 桃源段四小段154) that its first 44/373 candidates were genuine portal absences, correctly rejected by the strict matcher — yet future runs will probe these same 44 again before reaching any untried candidate. Without a memory of past negative results, each overnight window wastes its polite-fetch budget re-litigating dead heads instead of converging coverage (292/709 → target beyond).

Scope is provisional in one respect only: this change is confined to the fetch-script layer and touches no PDF parsing or similarity-merge logic, so no decision here depends on the POC findings; if the POC later changes what a `project_id` is, the ledger key follows whatever identity emerges — nothing else is gated.

## What Changes

- Persist a **no-match ledger** (`data/.link_cache/no_match_ledger.json`) recording `(project_id → {last_probed, view_ids_checked})` whenever targeted search finds no matching view for a candidate.
- On run start, **skip candidates probed recently** (default: within 14 days) so each batch spends its polite-fetch budget on untried or stale entries; log skipped counts.
- **Re-probe automatically** when the entry goes stale (older than the TTL), so portal additions are picked up without manual cache surgery.
- Clear a project's ledger entry when it gains a twur link (match found later), keeping the ledger consistent with reality.
- Surface ledger stats in the run summary (probed / skipped-as-recent / matched) so operators can see net progress per batch.

## Capabilities

### New Capabilities

### Modified Capabilities

- `fetch-remaining-portal`: candidate selection changes from "every project missing twur" to "missing twur AND not in the no-match ledger within the re-probe TTL"; no-match outcomes are recorded with a timestamp and expire after the TTL; matched projects have their ledger entries removed.

## Impact

- `scripts/fetch_remaining_national_portal.py` — candidate loading (`load_candidates`), the main loop's no-match branch (ledger write), run summary output.
- New small JSON state file under `data/.link_cache/` — must respect the single-writer rule (§17): only the fetch script writes it; discovery CLI ignores it.
- No schema/model/viewer changes; emitted datasets unaffected. Existing caches untouched.
- Overnight throughput improves from ~0 net progress (on exhausted heads) to full budget on fresh candidates.
