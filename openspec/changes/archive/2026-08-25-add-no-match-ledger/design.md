## Context

System boundary and flow: the batch pipeline runs PDF (gov.taipei) → positional parse → raw.tsv → cleanse → clean.tsv → similarity merge → merged.tsv → projects.json (+ viewer); downstream of the viewer, the targeted-fetch campaign (`scripts/fetch_remaining_national_portal.py`) closes the loop — viewer/projects.data.js → candidate selection → sequential polite fetch from the national portal (WAF-protected external system) → per-project cache writes in `data/.link_cache/` → viewer regeneration. Domain events at this boundary are per-project probes: a probe either matches a portal view page (cache gains twur + milestones) or does not (nothing recorded today).

The campaign is one of two writers on `.link_cache` under the single-writer rule (§17); `urtpe.cli --links` is the other. The 2026-08-25 03:00 run demonstrated that the queue head can be entirely genuine no-matches (44/374 rejected correctly), and the script has no memory across runs — every batch rebuilds candidates as "all projects missing twur" and re-probes them. See proposal.md for motivation.

Per the port/adapter split: ledger persistence is an I/O adapter (JSON file read/write), while TTL filtering of candidates stays pure logic over in-memory entries — testable without touching the filesystem.

## Goals / Non-Goals

**Goals:**
- Each overnight batch makes net progress: budget spent on untried or stale candidates, not known-absent ones.
- Portal additions are still picked up: exclusions expire after a TTL and re-enter probing.
- Ledger stays truthful: cleared on match; consistent with caches after any run.
- Operator-visible progress: summary shows processed / updated / skipped-as-recent.

**Non-Goals:**
- No change to matching logic itself (strict matcher stays as-is).
- No change to discovery CLI behavior or emitted data schemas.
- No backfill of historical probes — only outcomes observed from the first ledger-enabled run onward are recorded.
- No coordination protocol with the CLI beyond the existing single-writer rule.

## Decisions

**D1: Ledger as a standalone JSON sidecar, not inside result.json.**
`data/.link_cache/no_match_ledger.json` keyed by project_id:
`{ "<project_id>": { "last_probed": "ISO-8601", "view_ids_checked": ["123", ...] } }`.
Rationale: result.json is owned by the discovery schema (`DiscoveryResult(**data)` round-trip at `links.py:784-793` would choke on unknown keys unless defaults exist); the ledger is campaign-scoped operational state. Alternative rejected: embedding `no_match_at` into each cache file — couples pipeline schema to fetch-script bookkeeping.

**D2: Filter at candidate-load time, not in the fetch loop.**
`load_candidates()` drops projects whose ledger entry has `last_probed` within TTL (default 14 days, `--reprobe-days` override). Rationale: keeps the main loop untouched except for ledger writes; skipped counts come free from comparing list lengths before/after filtering. Alternative rejected: runtime skip-and-sleep — wastes loop iterations and muddies deadline accounting.

**D3: Write ledger entry immediately after each no-match, not batch-at-exit.**
The script can die at deadline mid-loop; a crash must not lose the night's negative results. Atomic-ish write (write temp + `os.replace`) since §17 showed torn reads are real in this directory.

**D4: Clear-on-match via the same update path.**
When `update_project_cache` succeeds, delete the project's ledger entry in the same critical section. Also sweep at run start: drop entries whose project now has twur in its cache (self-healing if a match came from another writer).

**D5: Malformed ledger degrades to empty, loudly.**
On JSON decode failure: rename to `.corrupt`, start fresh, print a warning. Same precedent as poison-cache handling (§17 rule 4). A lost ledger costs re-probing; a crash-looping script costs nights.

**D6: Summary counts derived from filtering.**
`skipped = len(all_missing_twur) - len(filtered_candidates)`; printed alongside existing Processed/Updated/Failed lines.

## Risks / Trade-offs

- [Portal publishes a case during TTL window; we report it absent for up to 14 days] → acceptable staleness; `--reprobe-days 0` forces full re-probe when wanted.
- [Ledger grows unbounded (~373 entries max, tiny)] → non-issue at this scale.
- [Two writers race the ledger if someone violates the single-writer rule] → out of scope; §17 already forbids concurrent writers, D3's atomic replace limits blast radius.
- [project_id drifts across gazettes (recno shifts)] → ledger keys on project_id like everything else cross-run; stale entries age out via TTL.

## Migration Plan

Deploy alongside the next overnight batch: no data migration (ledger starts empty), rollback = delete the JSON file and revert the script; behavior returns to today's churn-everything mode.
