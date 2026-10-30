# Design — restore-2026-09-24-gazette

## Context

The pipeline reads a gazette PDF → positional ruled-table parse → raw.tsv → cleanse →
clean.tsv → similarity merge → merged.tsv → projects.json (+ viewer). Around that flow sit
two I/O adapters this change touches: the archive (`urtpe/archive.py`, append-only index +
PDF store outside the working tree) and the change-set store (`urtpe/changeset.py`, one
persisted comparison per publication transition). The actors: the maintainer who approves
the ingestion, the OpenCode session whose `--recover-truncated` recovery pass is invoked as
part of the acceptance run, and future reconciliations whose predecessor links depend on the
chain being complete.

What is on disk today (verified 2026-10-30, read-only probes):

- The quarantined file `urtpe-gazettes/skipped since abnormal SN/核定案件-2026-10-02.pdf`
  hashes to `5066b108…` — the digest the poller recorded for gazette 2026-09-24 on
  2026-10-06. Its 統計至 reads 115/9/24 (Gregorian); 246 pages; 1,436 distinct records
  after the reader's page-head dedup; 編號 1..1436, no gaps; 22 records publisher-truncated.
- The running-page-head defect: 編號 1 is restated as an **exact byte copy** of page 1's real
  row atop every page 2..246 (verified cells identical on pages 2, 50, 100, 150, 200, 246 —
  including the 實施者 column that looks different in a screenshot because the row below the
  head is a different record). 1,681 raw rows = 1,436 real + 245 head copies. The existing
  reader handles this by `_dedupe_by_recno` (first occurrence wins), and the v2→v3 reader
  history proves the safety boundary: dedup must key on 編號 **content**, never on row
  position — the v2 reader's positional skip deleted one real record per page on the
  *opposite* head shape (1151006, where the head row appears nowhere else).
- The live change-set chain: `2026-10-01.json` records `previous_id: 2026-08-27`
  (net +16). The superseded file `2026-10-01.superseded-with-09-24.json` from 2026-10-07
  records the true 09-24→10-01 comparison (+4 / 0 removed / 0 edited, blocking empty).
  `GazetteArchive.predecessor_of("2026-10-01")` returns 08-27 today and will return 09-24
  once the index gains the entry — the insertion *must* carry the re-derivation.
- The pre-rebuild index recorded 09-24 as 1,436 records / 692 projects — the acceptance
  targets already exist.
- `verify()` today reports 3 benign problems (10-13/10-23/10-30 on disk, unindexed; all
  re-uploads of held publications by digest). Out of scope to fix, but the superseded-digest
  work must not widen this noise.

## Goals / Non-Goals

Goals:

1. One approved act: re-file 09-24 under its publication name, ingest it dual-path
   (print completion + `--recover-truncated` residual), repair the two affected change
   sets, and land the boundary correction in the docs.
2. P3.7: a corrected re-upload is recorded, not silent — superseded digests live in the
   index, and `verify()` stops reporting recorded replacements as damage.
3. A reader regression test that pins the page-head + Gregorian shape so the quarantine
   verdict can never reproduce silently.

Non-Goals:

- Re-emitting the current dataset from the restored chain (see Open Questions — separate
  decision, ~23 MB diff).
- Fixing the three benign unindexed re-uploads (10-13/10-23/10-30) beyond what
  superseded-digest work incidentally improves.
- Touching the recovery matchers themselves — the OpenCode session owns that surface; this
  change only invokes it.
- Any poller scheduling decision (stalled since 2026-10-06; user decision recorded in
  `docs/inspection.md`).

## Decisions

### D1 — Restore is copy-out, quarantine stays

Re-filing copies `skipped since abnormal SN\核定案件-2026-10-02.pdf` to
`核定案件-2026-09-24.pdf` and leaves the quarantine directory untouched. The new index
entry's provenance names both paths. Rationale: the quarantine is evidence of the old
reader's failure; deleting it destroys the audit trail. Alternative rejected: `mv` in place
— cheap, but the run log becomes the only record and a later "why is 10-02 missing" question
has no on-disk answer.

### D2 — Digest chain on re-store, keyed by gazette_id

`store()` today: same `gazette_id` + different bytes → `os.replace`, silent. Change: before
replacing, append an index entry (`event: "re-store"`) carrying `supersedes: <old-sha>` and
the new `sha256`. `verify()` then treats a mismatch as damage **only when no entry names the
recorded digest as superseded**. Alternatives: (a) accept the noise with a comment — leaves
`verify()` blind to a real substitution *after* the first benign one teaches operators to
ignore the line; (b) suffixed gazette ids — breaks `predecessor_of` and the change-set
chain. The chain-on-index approach keeps the index append-only (spec constraint) and makes
`verify()` strictly more informative.

### D3 — The boundary regression test pins content-dedup, not position

New test (test-first) in `tests/test_extract_tables.py` using the existing fixture knobs:
`write_gazette(..., repeat_header_row=True, calendar="gregorian")` with a corpus lineage
mixed across the boundary (late rows ROC, the newest row Gregorian). Asserts, through the
reader: every 編號 read exactly once (head dropped), all dates parse, contiguity 1..N holds
so the tripwire passes. The test additionally asserts the head row was dropped **because its
編號 duplicates a read record** — the guard against anyone re-introducing a positional skip.
Second test pins the real quarantined file's acceptance shape: 統計至 2026-09-24, 1,436
records / 692 projects, run under the session temp archive (conftest repoints the archive
root; the fixture carries a real 統計至 and would otherwise touch the live archive).

### D4 — Dual-path ingestion composes because the funnel already orders it

`_ingest_pdf` runs corpus completion inside the reader (three checks: same unit, literal
prefix, count closes) and the recovery pass afterwards on rows still marked. No code change
is needed for the composition — verified: 09-24's 編號 1005 is a different unit (26 筆,
emitted, closing phrase present) so it is never marked; 10-15's truncated 雙園段505 row
completes from 09-24's 編號 1105 **once 09-24 is in the corpus**, via land-core matching,
not 編號 (the coordinate invariant doing its job). The ingestion therefore runs with
`--recover-truncated` so 09-24's own 22 truncated rows resolve: corpus-completable ones from
print, the residual through the API pass, each residual named rather than repaired.

### D5 — Change-set repair is re-derive-then-supersede, in the same run

Sequence inside the one ingestion: re-file → index → ingest 09-24 (reconciles against
08-27, the chain's new link; calendar change ROC→Gregorian is reported, not blocking per
`gazette-reconciliation`) → re-ingest 10-01 under the lock so its comparison re-derives
against 09-24 → supersede the live `2026-10-01.json` (rename to
`2026-10-01.superseded-pre-09-24-restore.json`, preserving content — the naming pattern
exists) → cross-check the new 09-24→10-01 counts against the 2026-10-07 superseded file
(+4/0/0 expected; a divergence is a finding, not an error to force-match: the old read was
v1-era). The 08-27→09-24 change set is created by the 09-24 ingestion itself.

### D6 — Calendar correction lands where the claim lives

`AGENTS.md:105` ("ROC (115/8/27) until the 1151002 gazette, Gregorian after") becomes
"ROC until the 2026-08-27 gazette; Gregorian from 2026-09-24 onward — the 09-24 document was
quarantined on release, which is why the boundary was once mislabelled 1151002."
`openspec/config.yaml:18` has the same fix (it currently names 1151002 while giving the
09-24 date — self-contradictory). No live spec pins the boundary, so no spec delta carries
it; the reconciliation spec's 1151002 mentions are measured facts about ordering, left alone.

## Risks / Trade-offs

- **~23 MB emission diff from re-ingesting 10-01.** The re-ingestion is required by D5 (the
  comparison must be re-derived under the current reader). Mitigation: run under the lock,
  stage deliberately; the diff is the price of an honest chain. Accepted by the maintainer
  as part of approving this change.
- **The recovery pass sends API traffic for 09-24's residual rows.** The probes measured no
  WAF at ~4 req/s and the pass degrades per-row to residual on failure; worst case is the
  plain exclusion path. Accepted.
- **A divergence between the re-derived 09-24→10-01 counts and the 2026-10-07 superseded
  file.** Expected to agree at +4 net; if it does not, the current reader's read wins and
  the divergence is documented in the change-set note — the old file was a v1-era
  measurement.
- **Coordination with the OpenCode session.** Both changes touch the recovery surface and
  the archive. This change's acceptance run *invokes* their pass; it does not modify it.
  Sequence: their spec work lands first, or the same session executes this change's
  ingestion. Do not run the two concurrently over one output tree (single-writer rule).

## Open Questions

1. ~~**Re-emit forward?**~~ **RESOLVED 2026-10-30**: the maintainer approved re-ingesting
   10-06/10-15 forward so the emitted dataset reflects the completed 1005 (77 from print,
   superseding the 75-parcel partial API recovery). Scoped into tasks group 6, executed
   after the chain repair (group 4) lands, under the same single-writer lock.
2. **The three benign unindexed re-uploads** (10-13/10-23/10-30): index them as re-uploads
   (source provenance exists for this pattern) or leave the `verify()` noise? Default: leave;
   the noise is small and honest.
