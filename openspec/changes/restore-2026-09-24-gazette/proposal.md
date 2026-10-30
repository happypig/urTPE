## Why

The archive is missing one publication, and the gap is lying to three different consumers.

On 2026-10-06 the poller recorded gazette 2026-09-24 (SHA-256 `5066b108…`). The file was
quarantined under its download name `skipped since abnormal SN\核定案件-2026-10-02.pdf` by a
reader verdict that is not reproducible today, the 2026-10-07 index rebuild then dropped its
index entry outright, and `AGENTS.md`/`openspec/config.yaml` mis-state the calendar boundary
because the document that carries it was never held. Measured against the archive: 08-27 is
the last ROC-dated document held, 09-24 already prints Gregorian — so the true ROC→Gregorian
boundary sits at 09-24, and every claim that it sits at 1151002 (2026-10-02) is an artifact
of this gap.

The humans involved are the maintainers who reconcile each new ingestion against its
predecessor (currently reconciling across the gap attributes one publication's changes to
another — the exact failure measured on 2026-10-07 with 09-24 absent), and the OpenCode
session whose `recover-truncated-rows-via-api` work shares the recovery surface this
restoration touches. Verified against the quarantined file itself: SHA-256 matches the
poller's record, 統計至 parses as 2026-09-24 (Gregorian), 246 pages, 1,436 distinct records
(編號 1..1436, no gaps after the reader's page-head dedup), 編號 1 restated as an exact-copy
running head on all 245 later pages, 22 records publisher-truncated and named.

## What Changes

- **Restore** the quarantined 2026-09-24 PDF into the archive under its publication name
  (`核定案件-2026-09-24.pdf`), with an index entry whose provenance names the quarantine.
- **Re-file, never rename in place first**: the quarantine directory is evidence; the
  restoration copies the file out and leaves the quarantine record intact in the run log.
- **Ingest it once, dual-path**: corpus completion from print (the reader's existing
  bounded-completion path) plus the `--recover-truncated` API pass on the residual marked
  rows. One ingestion, so the restored gazette enters the dataset as completely as the
  evidence allows. Measured chain this enables: 10-15's truncated 編號 1005 (雙園段二小段505,
  76 of 77 parcels) completes from print via 09-24's 編號 1105, which carries all 77 parcels
  with its closing phrase — print beats the current 75-parcel partial API recovery.
- **Record superseded digests (P3.7)**: when `archive.store()` replaces content under a
  `gazette_id`, the new index entry names the digest it replaced, and `verify()` accepts any
  digest ever recorded for that id — a corrected re-upload stops poisoning the digest check.
- **Re-derive the affected change sets**: restoring 09-24 inserts a link into the chain, so
  08-27→09-24 must be created and the live 09-24→10-01 comparison must be re-derived
  (the superseded file from 2026-10-07 already records the expected +4/0/0 as a cross-check).
- **Correct the calendar boundary**: `AGENTS.md` and `openspec/config.yaml` state the
  boundary as 1151002; the held-document evidence says 09-24. The correction is bundled here
  because this change is what makes the evidence complete.

## Capabilities

### New Capabilities

(none — this change restores a publication and repairs archival bookkeeping; no new
behavioural surface is introduced)

### Modified Capabilities

- `gazette-archival`: a re-stored publication whose content differs records the superseded
  digest chain instead of silently replacing content, and `verify()` accepts any digest ever
  recorded for a `gazette_id`; a quarantined-but-verified member can be re-filed into the
  archive with provenance naming the quarantine.
- `gazette-cadence`: ingestion of a restored publication re-derives the change sets its
  insertion invalidates (predecessor link moved), superseding the stale change-set files
  rather than leaving contradictory records.

## Impact

- `urtpe/archive.py` — `store()` superseded-digest recording; `verify()` digest acceptance.
- `urtpe/cli.py` — no code change expected for the ingestion itself (dual-path composition
  already exists: corpus completion at read, recovery pass after); the run is an invocation,
  not a feature.
- The gazette archive (`urtpe-gazettes/`) — one file re-filed, index entries appended,
  `change_sets/` re-derived for two transitions.
- `data/` + `viewer/projects.data.js` — the ~23 MB emission diff from one full re-ingestion
  (09-24 becomes comparable; the emitted dataset itself is re-emitted only if the restored
  chain is re-ingested forward — see design: this change ingests 09-24 and repairs the chain;
  re-emitting the current dataset is a separate decision recorded as an open question).
- `AGENTS.md:105`, `openspec/config.yaml:18` — calendar-boundary wording.
- Coordination: the OpenCode session's `recover-truncated-rows-via-api` surface is invoked
  (opt-in flag) inside this change's acceptance run; sequence the two or let that session
  run the ingestion, but do not parallel-edit the archive.
- Constraints honored: single-writer lock for the ingestion; 編號 never used as a durable key
  (the 1005↔1105 completion is land-core keyed); the 22 truncated rows are recovered or named
  residual, never repaired by inference.
