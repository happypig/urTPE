# Design — wire-standing-checks

## Context

The flow: PDF → positional parse → raw.tsv → cleanse → clean.tsv → similarity
merge → merged.tsv → projects.json (+ viewer). Two checks exist on paper and not
in the code path: `emission.emission_faults` (imported, never called) and the
audit's partition census (asserted in the audit's own Appendix A script, nowhere
in the pipeline). The tripwire (`urtpe/tripwire.py`) is the established
pre-write gate; the census belongs beside it because the two share the contract —
evaluate before any artifact, block on corruption, never block on absence.

Actors: the maintainer re-running the pipeline (the default no-`--links` path
must report honestly); the analyst reading `review_report.txt`; future openspec
changes that assume the emission is conforming.

## Goals / Non-Goals

Goals:

1. `emission_faults` runs on every emission path, reporting through
   `review_report.txt` + console, warning-only.
2. A census check (partition total + disjoint + count agreement) runs beside the
   tripwire, blocking, before any write.
3. Both checks test-first; neither changes the emission format.

Non-Goals:

- No CLI flag, no `--strict-<x>` escape hatch (AGENTS.md: fix the gate, don't
  bypass it).
- No change to `--links` advisory status (D5).
- No per-node-level census (the family-level partition is the audited property;
  node payloads are covered by the graph tests).

## Decisions

### D1 — The census lives in `tripwire.py`, not a new module

`Tripwire` is the pre-write completeness gate; a partition violation is a
completeness failure of exactly its kind. A new `Tripwire.check_partition(clean,
projects)` method returns the same `faults` list shape, so `_ingest_pdf` wires it
identically to the existing check and inherits the exit-4 contract. Alternative
rejected: a new `census.py` module — same behaviour, one more import seam, and
the spec places the property on the emitted document (history-graph), which the
tripwire already guards.

### D2 — Census inputs are `clean` and `projects`, taken after ledger re-merge

`_ingest_pdf` re-merges after ledger application (`projects = merge(clean)`); the
census runs on that final pair, before `result` is returned to `_run_locked`.
The check is pure (no I/O), matching the domain/adapter split: inputs are the two
domain objects, output is a fault list.

### D3 — Count agreement includes the named exclusions

The emitted record count equals `len(clean)`; the tripwire's `excluded_recnos`
already accounts for publisher truncations upstream of cleanse. The census
therefore asserts `doc.counts.records == len(clean)` and
`sum(len(p.members)) == len(clean)` — not a PDF-rows comparison, which the
tripwire's contiguity check already covers. Alternative rejected: comparing
against `raw_recs` — that re-states contiguity and would double-report the same
fault.

### D4 — Emission-fault call sits after `build_graph_document`, before `write_json`

Exactly where link data has been attached (or observably not) and nothing has
been written. The faults are printed and appended to `review_report.txt` via the
existing `report_mod.review_report` path (a new `emission=` parameter, mirroring
`recovery=`), so the report carries them without a format change.

## Risks / Trade-offs

- **The census gate blocks a run it shouldn't.** Mitigated by test-first: the
  green-path test asserts the current healthy payload shape passes; the census
  was verified clean on this emission (restoration task 6.4). If it ever fires
  falsely, the fault names the records, so the fix is local.
- **Double-reporting with the tripwire.** The census overlaps contiguity only in
  spirit (records vs 編號); D3 keeps the inputs disjoint. If a fault appears in
  both, the report shows it twice — acceptable noise for a corruption signal.

## Open Questions

(none — both checks are specified by existing documents)
