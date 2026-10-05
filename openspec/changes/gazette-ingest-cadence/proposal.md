# Gazette ingest cadence, persisted reconciliation, and a usable sync manifest

## Why

Four items were deliberately parked during `robust-gazette-ingestion` because each was
blocked on something that did not exist yet. Two of those blockers have since been built
(`gazette-archival`, `gazette-reconciliation`), so the items can now move — but two of
them have also turned out to rest on a wrong premise, and neither the operator nor a
future reader can currently tell how close any of them is to being unblocked.

The operator needs the newest gazette to arrive without a human noticing a page. Today
that is a manual act, and nothing records that a check happened, so a missed publication
is indistinguishable from a quiet one.

The measurement recorded as "withdrawn" in `parked.md` — that date-order violations fell
from 9 to 1 between gazettes — turns out to be re-derivable and correct once read by the
corrected reader. It is not withdrawn; it was parked on the assumption that it was
unrecoverable.

Concretely, two facts make a naive poller wrong rather than merely early:

- The gazette page serves **no `ETag` and no `Last-Modified`**, so a conditional request
  cannot tell "unchanged" from "changed". A poll costs the page's full 86 KB.
- The city **re-uploads the same PDF and bumps its mtime**. On 2026-10-05 the page's
  `資料更新` read `115-09-29 13:55` while the newest gazette we hold is `2026-09-24`, and
  the served PDF was byte-identical (matching SHA-256) to our archived copy. **A poller
  keying on mtime re-ingests the same gazette every week and calls it new.** Change
  detection has to be content hash.

Meanwhile the reconciliation diff that the portal cascade was parked on is computed,
printed, and discarded — it exists only as console output, so "trusted across two
consecutive ingestions" is not a judgement anyone can currently make.

## What Changes

- **A weekly poller** that fetches the gazette page, compares it against the last-seen
  bytes, and downloads and archives the PDF **only when the page's bytes actually
  change**. Detection is by content hash; `Last-Modified` is recorded as provenance and
  never used to decide. A re-upload of an unchanged PDF is reported as such, not ingested
  again. Weekly, matching observed publication cadence (~2-4 approvals/week, PDF weekly
  to fortnightly) at a cost of ~86 KB per poll plus one 1.9 MB download per genuine change.
- **A persisted reconciliation change set**, written per ingestion, naming the projects
  that gained a node. This is the input the parked portal cascade was waiting on, and it
  is what makes reconciliation auditable after the fact rather than only at the terminal.
- **`gazette_index` extended once**, with portal-side state and a corrected
  `reader_version`, so the manifest is designed once rather than twice. The existing index
  records `table-lines-v1` on all twelve rows, including ingestions made with the
  pre-correction reader — it therefore cannot distinguish a contaminated read from a
  corrected one, which is the manifest's stated purpose and is currently unmet.
- **Date-order violations recorded per publication**, closing `parked.md` item 3 as a
  standing metric rather than a one-off question.

**BREAKING**: none to the emitted dataset. The poller writes only to the archive; no run
reaches the emission path without a page-change detection, and the single-writer lock still
governs any ingestion it triggers.

## Capabilities

### New Capabilities

- `gazette-cadence`: unattended weekly detection and acquisition of a newly published
  gazette, with content-hash change detection and a recorded outcome per poll.

### Modified Capabilities

- `gazette-reconciliation`: the per-gazette change set becomes persisted, durable output
  rather than console text, so a later run can consume "projects that gained a node" and
  an operator can audit what a past ingestion concluded.
- `gazette-archival`: the index carries a correct `reader_version` distinguishing
  pre- and post-correction reads, and gains portal-side state.

## Impact

- **New:** `urtpe/poller.py` (page fetch, byte comparison, hash-gated download),
  `scripts/poll_gazette.py` (entry point), and a poll-log under the archive root.
- **Changed:** `urtpe/reconcile.py` (emit a structured change set alongside the human
  report), `urtpe/archive.py` (index schema: corrected `reader_version`, portal-side
  state, poll provenance).
- **Unchanged:** extraction, cleansing, merge, emission, and the viewer. The poller never
  reaches them without an explicit ingestion.
- **External dependency:** one HTTP GET of the gazette page per week, and one PDF download
  per genuine change. No credentials, no authentication.
- **Operators:** an unattended run must not be able to overwrite a good dataset. The
  single-writer lock covers ingestion; the poller additionally writes nothing to the
  emission tree itself.