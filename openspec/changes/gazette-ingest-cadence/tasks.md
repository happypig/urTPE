# Tasks — gazette-ingest-cadence

> The `rules` block for this project asks that a POC validate positional PDF parsing and
> calibrate the similarity threshold before the merge pipeline is built around them. That
> rule governs `pdf-tsv-extraction` and `case-merging`, and it is **not applicable here**:
> this change parses no PDF positionally, merges nothing, and touches no similarity
> threshold. Its empirical questions — whether a publisher timestamp detects a new gazette
> (D1), and what the date-order count really is (D7) — were measured directly against the
> live page and the three archived PDFs on 2026-10-05, and the measurements are recorded in
> `design.md`. No escape-hatch declaration is needed because §1 below is a test-writing
> group, which satisfies the test-first gate.

Order matters in two places. §1 must be fully complete before any implementation task is
marked complete. §4 depends on §3 because the ordering count needs a reader that reports
both calendars.

## 1. Tests — content-hash detection and re-upload (written first, deliberately failing)

- [ ] 1.1 Test that a PDF whose hash matches an archived member yields no ingestion and reports a re-upload
- [ ] 1.2 Test that a PDF whose hash matches nothing archived is ingested as a new gazette
- [ ] 1.3 Test that a publisher timestamp later than the archived entry, with an unchanged hash, does NOT create an entry
- [ ] 1.4 Test that the unchanged-hash-plus-newer-timestamp case records the timestamp as provenance
- [ ] 1.5 Test that a check finding nothing writes a dated record saying so
- [ ] 1.6 Test that a failed fetch writes a failure record distinguishable from a successful check that found nothing
- [ ] 1.7 Test that a gap in the record series is detectable without contacting the publisher
- [ ] 1.8 Test that the poller writes nothing into the emitted dataset tree
- [ ] 1.9 Test that an ingestion is refused when the offered PDF's hash does not match its archive entry
- [ ] 1.10 Test that an archive entry with no hash is reported as unverified rather than treated as verified
- [ ] 1.11 Test with a fixture page whose PDF link changes but whose bytes do not, and the converse

## 2. Implementation — the poller

- [ ] 2.1 `urtpe/poller.py`: fetch the page, compare against last-seen bytes, download and hash the PDF only when the page changed
- [ ] 2.2 Reuse the archive's existing SHA-256 rather than adding a second digest for the same document
- [ ] 2.3 Record a per-check outcome: `new_gazette`, `unchanged`, `reuploaded`, or `failed`, with the time
- [ ] 2.4 Record the publisher's reported timestamp as provenance on every outcome, and never consult it to decide
- [ ] 2.5 Archive a detected gazette and append its index entry; write nothing to the emitted dataset
- [ ] 2.6 `scripts/poll_gazette.py` entry point with `--dry-run`, and no code path that triggers an ingestion
- [ ] 2.7 Refuse to record an ingestion whose input hash does not match its archive entry
- [ ] 2.8 Make the cadence weekly and overridable by flag, without it being a correctness knob

## 3. Index schema — reader identity and acquisition provenance

- [ ] 3.1 Record first ingestion and re-read as distinct events rather than one entry per ingestion
- [ ] 3.2 Record the reader identity at a granularity that separates readers whose cell content could differ
- [ ] 3.3 Leave the twelve existing entries unmodified and expose them as unverified-reader; do not rewrite append-only history
- [ ] 3.4 Record acquisition provenance: fetched vs supplied-from-path, with the publisher timestamp where fetched
- [ ] 3.5 Make it readable how many publications are archived as against how many ingestions ran
- [ ] 3.6 Test that a re-read with a different reader does not overwrite the first ingestion's provenance

## 4. Date-order metric

- [ ] 4.1 Compute the count of departures from descending approval date, deduplicating on 編号 so a repeated page-head record is counted once
- [ ] 4.2 Accept both calendars; 1151002 is Gregorian and an ROC-only parser returns zero dated records
- [ ] 4.3 Record the dated-record count next to the violation count, so a zero-violation result with too few dated records is detectable
- [ ] 4.4 Store the count in the index entry per publication
- [ ] 4.5 Test against all three archived PDFs: 9, 9, 1
- [ ] 4.6 Test that the deduplication is what prevents the inflated count, using the known 246-page-head case
- [ ] 4.7 Test that a parser matching no dates reports an error rather than zero violations

## 5. Persisted reconciliation change set

- [ ] 5.1 Emit the comparison outcome as structured data alongside the existing human report
- [ ] 5.2 Persist it keyed by publication, so a re-ingestion does not create a second competing record
- [ ] 5.3 Record the project identities that gained an approval, not only counts
- [ ] 5.4 Record "no comparison possible" distinctly from an empty change set
- [ ] 5.5 Ensure a re-read does not silently recompute an earlier change set against a newer predecessor
- [ ] 5.6 Test that a change set is readable after the run that produced it has exited

## 6. Documentation and the parked record

- [ ] 6.1 Append a dated status section to `openspec/changes/archive/2026-10-05-robust-gazette-ingestion/parked.md`: items 1 and 2's `coverage.py` half resolved in `no-silent-data-loss`; item 3's withdrawn figure re-derived as 9/9/1; item 4 unblocked by the D1 measurement; items 2's remainder and 5 taken into this change
- [ ] 6.2 Record that the `1151002` date-sort's single violation is a re-dated historical row, not a sort failure
- [ ] 6.3 Correct the withdrawn `gazette-reconciliation` Purpose paragraph, which still says re-measuring requires an uncontaminated read of `1151002` — that read has now happened
- [ ] 6.4 Revise `docs/sync_architecture.md` §2, whose recno argument rests on the withdrawn affine `+5` model
- [ ] 6.5 Document the poller in `docs/cli_flow_v2.md`, including that it never ingests

## 7. Acceptance

- [ ] 7.1 A first poll against the live page reports a **re-upload**, not a new gazette — the acceptance test for D1, since the live page is known to be serving a re-uploaded `2026-09-24`
- [ ] 7.2 A second immediate poll reports `unchanged` and downloads nothing
- [ ] 7.3 No emitted dataset file is modified by either poll
- [ ] 7.4 Full suite green; `openspec validate gazette-ingest-cadence --strict` clean