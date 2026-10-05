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

- [x] 1.1 **PASSES.** A hash matching an archived member yields `reuploaded`, no ingestion, and no new index entry.Test that a PDF whose hash matches an archived member yields no ingestion and reports a re-upload
- [x] 1.2 **PASSES.** An unheld hash is archived as a new gazette and appears in the index.Test that a PDF whose hash matches nothing archived is ingested as a new gazette
- [x] 1.3 **PASSES.** The live page's actual case: a stamp advanced to 115-10-20 over an unchanged hash leaves the index at one entry.Test that a publisher timestamp later than the archived entry, with an unchanged hash, does NOT create an entry
- [x] 1.4 **PASSES.** `publisher_stamp` carries the newer stamp, which is exactly what explains the page change.Test that the unchanged-hash-plus-newer-timestamp case records the timestamp as provenance
- [x] 1.5 **PASSES.** Every check writes a dated record, and a second identical check reports `unchanged` with zero PDF fetches.Test that a check finding nothing writes a dated record saying so
- [x] 1.6 **PASSES.** A transport failure records `status: failed` plus an `error` field, kept separate from the human-facing `detail`.Test that a failed fetch writes a failure record distinguishable from a successful check that found nothing
- [x] 1.7 **PASSES.** `max_gap_days` returns the longest interval and the time since the last; an empty series returns `None`, because missing history is not a gap in existing history.Test that a gap in the record series is detectable without contacting the publisher
- [x] 1.8 **PASSES.** The emitted directory is byte-identical after a detection, and the outcome carries `ingested: False` with the gazette named as `pending_gazette_id`.Test that the poller writes nothing into the emitted dataset tree
- [x] 1.9 **PASSES.** `archive.assert_matches_entry` raises when offered content matches no recorded digest, and when the entry carries none at all.Test that an ingestion is refused when the offered PDF's hash does not match its archive entry
- [x] 1.10 **PASSES.** `IndexEntry.is_verified()` requires both a digest and a precisely identified reader; `unverified_members()` names the publication.Test that an archive entry with no hash is reported as unverified rather than treated as verified
- [x] 1.11 **PASSES.** An unchanged page costs no download even with the link present; changed page bytes over an unchanged PDF report `reuploaded`.Test with a fixture page whose PDF link changes but whose bytes do not, and the converse

## 2. Implementation — the poller

- [x] 2.1 **PASSES.** `urtpe/poller.py` fetches the page, compares its digest, and fetches the PDF only when the page changed.`urtpe/poller.py`: fetch the page, compare against last-seen bytes, download and hash the PDF only when the page changed
- [x] 2.2 **PASSES.** Uses `archive.has_hash` and `_sha256`, the same SHA-256 already on every index entry. No second digest.Reuse the archive's existing SHA-256 rather than adding a second digest for the same document
- [x] 2.3 **PASSES.** `new_gazette` / `reuploaded` / `unchanged` / `failed` / `would_download` are recorded per check with `checked_at`.Record a per-check outcome: `new_gazette`, `unchanged`, `reuploaded`, or `failed`, with the time
- [x] 2.4 **PASSES.** The stamp is read from the page and recorded on every outcome, and `classify_offer` is pinned by a test to contain no reference to any timestamp field.Record the publisher's reported timestamp as provenance on every outcome, and never consult it to decide
- [x] 2.5 **PASSES.** A detected gazette is archived and indexed with `acquisition: fetched`; no emitted-dataset path is reachable from the poller.Archive a detected gazette and append its index entry; write nothing to the emitted dataset
- [x] 2.6 **PASSES.** `scripts/poll_gazette.py` supports `--dry-run`, which returns `would_download` and writes no state — otherwise the next real check would compare against a page it never saw.`scripts/poll_gazette.py` entry point with `--dry-run`, and no code path that triggers an ingestion
- [x] 2.7 **PASSES.** Covered by 1.9 and 1.10.Refuse to record an ingestion whose input hash does not match its archive entry
- [x] 2.8 **PASSES.** `--cadence-days` is a reporting input only: it drives the missed-check warning and nothing in detection.Make the cadence weekly and overridable by flag, without it being a correctness knob

## 3. Index schema — reader identity and acquisition provenance

- [x] 3.1 **PASSES.** `event` is `first_ingest` or `reread`; both stay readable and the re-read never claims the origin.Record first ingestion and re-read as distinct events rather than one entry per ingestion
- [x] 3.2 **PASSES.** `READER_VERSION` is now `table-lines-v2`, with `table-lines-v1` held in `LEGACY_READER_VERSIONS`. A digest alone is not provenance: an entry stamped v1 reports unverified, because that reader truncated cells.Record the reader identity at a granularity that separates readers whose cell content could differ
- [x] 3.3 **PASSES.** The twelve existing entries are untouched and read back through `unverified_members()`. Nothing rewrites append-only history.Leave the twelve existing entries unmodified and expose them as unverified-reader; do not rewrite append-only history
- [x] 3.4 **PASSES.** `acquisition` and `publisher_stamp` are recorded per entry; the stamp is stored and never read back for a decision.Record acquisition provenance: fetched vs supplied-from-path, with the publisher timestamp where fetched
- [x] 3.5 **PASSES.** `publication_count()` and `ingestion_count()` are separate, and a re-read does not increment the former. The twelve entries describing three publications are now legible as such.Make it readable how many publications are archived as against how many ingestions ran
- [x] 3.6 **PASSES.** A re-read appends alongside; the first ingestion's `reader_version` survives it.Test that a re-read with a different reader does not overwrite the first ingestion's provenance

## 4. Date-order metric

- [x] 4.1 **PASSES.** `date_order_report` deduplicates on 編號 before counting. Against 1150820/1150827/1151002 it reports 9 / 9 / 1, and 1151002 yields 1421 distinct 編號 rather than the 1681 a raw scan sees.Compute the count of departures from descending approval date, deduplicating on 編号 so a repeated page-head record is counted once
- [x] 4.2 **PASSES.** Dates go through the reader's `to_iso`, which accepts both calendars per cell. 1151002 is Gregorian and reads 1421 dated records, not zero.Accept both calendars; 1151002 is Gregorian and an ROC-only parser returns zero dated records
- [x] 4.3 **PASSES.** `dated_records` is carried beside `violations`, and `unmeasurable` is set below a 0.9 dated share. `describe()` says UNMEASURABLE in words rather than printing a bare zero.Record the dated-record count next to the violation count, so a zero-violation result with too few dated records is detectable
- [x] 4.4 **PASSES.** `archive.record_ordering` appends the pair to the publication's own entry; an entry never measured holds -1, which is distinct from a measured zero. Appending rather than mutating, per D6.Store the count in the index entry per publication
- [x] 4.5 **PASSES.** Verified against all three archived PDFs: **9 / 9 / 1**, largest inversion 1820 / 1820 / 113 days. The 1151002 inversion is the re-dated 編號 109 above 110.Test against all three archived PDFs: 9, 9, 1
- [x] 4.6 **PASSES.** Demonstrated at the layer where the inflation actually occurs — a raw `find_tables` scan sees every repeated page head and manufactures an ascent per head, while `date_order_report` reports 0. Worth stating precisely: the reader already deduplicates, so the 1681-row figure came from a raw scan, and this test pins that layer rather than implying the report was at risk.Test that the deduplication is what prevents the inflated count, using the known 246-page-head case
- [x] 4.7 **PASSES.** Zero dated records sets `unmeasurable`, as does a single dated record, whose `is_sorted` is False because one record is not evidence of an ordering in either direction.Test that a parser matching no dates reports an error rather than zero violations

## 5. Persisted reconciliation change set

- [x] 5.1 **PASSES.** `urtpe/changeset.py` builds a structured payload beside the human report, and `cli.py` writes it and prints the path.Emit the comparison outcome as structured data alongside the existing human report
- [x] 5.2 **PASSES.** Keyed by publication; two writes over one publication leave one file, verified by counting files and records.Persist it keyed by publication, so a re-ingestion does not create a second competing record
- [x] 5.3 **PASSES.** `gained_project_ids` names the projects, not just the count. `reconcile` now carries `new_approval_labels`, and the writer falls back to it when the merge has not run yet.Record the project identities that gained an approval, not only counts
- [x] 5.4 **PASSES.** `comparable: false` plus a `note`, with `gained_project_ids` empty. The flag is what distinguishes 'not measured' from 'nothing gained', and a test asserts both halves.Record "no comparison possible" distinctly from an empty change set
- [x] 5.5 **PASSES.** A re-read is appended under `events` with the predecessor it used; the file's top level still names the original comparison. Verified end to end: two ingestions of the same publication leave one file.Ensure a re-read does not silently recompute an earlier change set against a newer predecessor
- [x] 5.6 **PASSES.** `ChangeSetStore.load` reads the conclusion with no ingestion and no reconciliation run.Test that a change set is readable after the run that produced it has exited

## 6. Documentation and the parked record

- [x] 6.1 **DONE.** Dated status section appended to the archived `parked.md`, with a per-item table. The file is left as the record of what was believed then, and the corrections are appended rather than folded in silently.Append a dated status section to `openspec/changes/archive/2026-10-05-robust-gazette-ingestion/parked.md`: items 1 and 2's `coverage.py` half resolved in `no-silent-data-loss`; item 3's withdrawn figure re-derived as 9/9/1; item 4 unblocked by the D1 measurement; items 2's remainder and 5 taken into this change
- [x] 6.2 **DONE.** Recorded: the lone 1151002 departure is 編號 109 (2025-08-05) above 編號 110 (2025-11-26), the same unit's 第二次 and 第三次 權利變換 — a re-dated historical row, not a failure to sort.Record that the `1151002` date-sort's single violation is a re-dated historical row, not a sort failure
- [x] 6.3 **DONE.** The Purpose paragraph said re-measuring "requires an uncontaminated read of `1151002`". That read has happened, so it now states the measured 9 / 9 / 1, and records *why* the figure was withdrawn: for want of a read, not for doubt about the number.Correct the withdrawn `gazette-reconciliation` Purpose paragraph, which still says re-measuring requires an uncontaminated read of `1151002` — that read has now happened
- [x] 6.4 **DONE.** `docs/sync_architecture.md` §2 no longer presents the `+5` offset as general. It states the shift is not affine — 1150827→1151002 moves records both ways — and adds the ordering finding, so nothing in the file reads the list positionally.Revise `docs/sync_architecture.md` §2, whose recno argument rests on the withdrawn affine `+5` model
- [x] 6.5 **DONE.** `docs/cli_flow_v2.md` gains a poller section covering hash-not-timestamp detection, the 86 KB steady state, the per-check record, and the fact that it never ingests.Document the poller in `docs/cli_flow_v2.md`, including that it never ingests

## 7. Acceptance

- [x] 7.1 **PASSES.** Against the live page: `reuploaded`, gazette `2026-09-24`, sha256 `5066b108…8a92a`, matching the archived copy exactly. The known-broken live state is the acceptance test.A first poll against the live page reports a **re-upload**, not a new gazette — the acceptance test for D1, since the live page is known to be serving a re-uploaded `2026-09-24`
- [x] 7.2 **PASSES, after fixing a real bug this found.** A second poll reports `unchanged` and downloads nothing. It did not at first: see below.A second immediate poll reports `unchanged` and downloads nothing
- [x] 7.3 **PASSES.** All five emitted files byte-identical before and after two polls; the archive index stayed at 12 rows.No emitted dataset file is modified by either poll
- [x] 7.4 Full suite green; **PASSES.** 528 tests, openspec validate --strict clean, viewer smoke all checks passed. `openspec validate gazette-ingest-cadence --strict` clean
## 8. Progress notes

**Test-first gate satisfied.** §1 and §4 were written before their implementation
and both are complete, so implementation tasks in §2 and §3 were eligible to be
marked. Every marked task has a test behind it.

**Corrected during implementation.** Two assertions I wrote were wrong about the
reader's behaviour, and the tests were right to fail:

- I assumed `date_order_report` was itself at risk from the repeated page head. It is
  not — the reader already deduplicates. The inflation belongs to a *raw* `find_tables`
  scan, which is also how the 1681 figure was obtained, so task 4.6 now demonstrates it
  there. The trap is real; my first description of where it bit was not.
- I asserted `is_sorted` for a single dated record. It should be False: one record is
  not evidence of an ordering in either direction, and reporting otherwise is how an
  unreadable publication comes to look perfectly ordered.

**A dry run cannot claim to have classified content it never downloaded.** `--dry-run`
returns `would_download` rather than `new_gazette`, and writes no state — otherwise the
next real check would compare against a page it never saw.

**Measured against the real archive.** Dated records come out as 1417 / 1422 / 1421
against total rows of 1417 / 1422 / 1421, so every retained row carried a date and no
publication is flagged unmeasurable.

**A property is not a field.** `net_change` is computed on `ReconcileResult`, so it is
absent from `asdict` and the first persisted record carried `"net_change": null` — a
null where a count belongs, which reads as a gap rather than a zero. Now computed
explicitly and pinned by a test.

## 9. Acceptance found a real bug — the page is not byte-stable

Task 7.2 failed on first run, and it was worth having been written.

`urtpe/poller.py` compared the gazette page's raw bytes to decide whether to spend
the 1.9 MB PDF download. The live page is **not** byte-stable: it carries a view
counter, `id="hitcount"`, measured at 153284 before the first poll and 153285 after it.
Two fetches seconds apart match; two minutes apart do not.

So the comparison reported a page change on nearly every check, and every check spent
the download to learn nothing — defeating the saving design D2 exists to provide, while
looking like a working poller. It was intermittent, which is the worse way to fail: an
intermittent extra download reads as normal traffic.

The fix masks volatile spans before hashing rather than ignoring them: the view
counter, the timestamped AJAX nonce, and cache-busting query parameters. Masking, not
ignoring, so a genuine publication still registers — a real publication moves the
stamp or the link, and both are compared. Two tests pin it: a counter tick alone must
read as `unchanged` with one fetch, and a counter tick *alongside* a real change must
still read as `new_gazette` with two.

Design D2 is unchanged in intent and corrected in method. The measured cost is now
86 KB per week in the steady state, plus 1.9 MB per genuine change.

**Worth noting about the acceptance criteria themselves.** 7.1 and 7.2 were written
against the live page precisely because a known-broken real state is a better test than
a synthetic one. The first poll correctly reported the re-upload. The second poll
supposed to be `unchanged` and was not — and no fixture I had written would have shown
it, because none of them had a counter that ticks.
