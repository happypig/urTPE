# Design — gazette-ingest-cadence

## Context

Four items were parked in `robust-gazette-ingestion`. Two of their blockers have since
shipped; two were parked on premises that measurement has since overturned. This change
takes the parts that are genuinely unbuilt, and folds them into one so the sync manifest is
designed once rather than twice — the explicit instruction in the parked item that wanted it.

Measured on 2026-10-05, against the gazette page
`uro.gov.taipei/cp.aspx?n=963B15B39CADB94E`:

| probe | result |
|---|---|
| page `ETag` | absent |
| page `Last-Modified` | absent |
| page `Cache-Control` | `no-cache` |
| page size | 86,586 bytes |
| page `資料更新` | `115-09-29 13:55` |
| newest gazette held | `2026-09-24` |
| PDF `ETag` | `"78d49422d74fdd1:0"` |
| PDF `Last-Modified` | `Tue, 29 Sep 2026 05:55:30 GMT` |
| SHA-256 of served PDF | `5066b108…8a92a` |
| SHA-256 of archived `2026-09-24` | `5066b108…8a92a` — **identical** |

## Goals

- Weekly unattended detection that cannot mistake a re-upload for a publication.
- A persisted reconciliation change set, so "trusted across two consecutive ingestions"
  becomes a judgement anyone can make.
- One index schema carrying reader identity, acquisition provenance, and portal-side state.
- Date-order violations recorded per publication.

## Decisions

### D1 — Change detection is by content hash; timestamps are provenance only

The page offers no validators, so a poll costs its full 86 KB. That is acceptable at weekly
cadence and is not the reason for this decision. The reason is the second row of the table:
the page advertised `115-09-29` while the newest gazette in hand was `2026-09-24`, and the
served PDF was byte-identical to the archived copy. **The publisher re-uploads unchanged
content under a later timestamp.**

A poller keyed on `Last-Modified` therefore re-ingests the same gazette weekly, and — worse
— cannot distinguish that from a genuine re-publication of an amended document. Detection
hashes the PDF. A timestamp delta with an unchanged hash is recorded as a re-upload and
ingests nothing.

The hash is the whole detection mechanism, so it must be the archive's existing SHA-256
rather than a second digest invented here. One identity for one document.

### D2 — Compare page bytes first, hash the PDF only when the page changed

Hashing an 86 KB page is cheap; hashing a 1.9 MB PDF every week is not. The poll compares
the page against its last-seen bytes and downloads the PDF **only** when they differ. This
keeps the steady-state cost at one GET of 86 KB, with the 1.9 MB spent once per genuine
change.

The trade-off is deliberate: a publication that changed the PDF while leaving the page
byte-identical would be missed. That is acceptable because the page is where the link and
the `資料更新` stamp live — a changed PDF behind an unchanged page is not a state this
publisher presents.

### D3 — Cadence weekly, and a missed check must be visible

Observed cadence is ~2-4 approvals per week with the PDF published weekly to fortnightly.
Weekly matches it. The cost of weekly is that a gazette published on Monday may sit until
the next check; the cost of daily is 86 KB/day and no change in what is detected, since
publication is not intraday.

Weekly therefore costs at most a few days of staleness and nothing else. **This is not a
correctness decision and should not be revisited as one** — if a gazette is missed, the fix
is to check sooner, not to change the detection rule.

A check that finds nothing writes a record saying so. Without that, a missed publication
and a quiet week are indistinguishable from the index alone — the same failure shape as the
`coverage.py` total re-key already fixed: a check that cannot observe the failure it exists
to catch.

### D4 — Acquisition and ingestion are separate acts

The poller writes only to the archive. It never reads, rewrites or replaces an emitted
dataset, and never initiates an ingestion. Ingesting an archived gazette remains an explicit
act under the single-writer lock.

An unattended run that could ingest is an unattended run that can overwrite a good dataset
with a bad one, and the single-writer lock serialises writers without deciding *which*
writer is correct. The 2026-08-24 incident is the reason to be conservative here.

The consequence is that a detected gazette waits for a human. That is the intended state:
the automation removes the need to *watch*, not the need to *decide*.

### D5 — The change set is persisted per publication, keyed by publication not by run

Reconciliation currently prints and discards. Persisting it makes two things possible: an
operator can audit what a past ingestion concluded, and a consumer can ask which projects
gained an approval.

Keyed by publication, not by run, so a re-ingestion does not produce a second competing
record for the same comparison. A re-read is recorded as a re-read (D6), and the change set
describes the comparison that was actually made — it is not silently recomputed against
whatever predecessor exists now.

### D6 — The index records first-ingestion and re-read separately

`robust-gazette-ingestion` appends an entry per ingestion, so twelve entries currently
describe three publications, and `reader_version` reads `table-lines-v1` on all twelve —
including ingestions made with the reader that absorbed page footers and truncated cells.
The index therefore cannot distinguish a contaminated read from a corrected one, which is
the manifest's stated purpose and is currently unmet.

A re-read with a different reader must not overwrite the provenance of the first ingestion,
so the two are recorded separately. This is a schema change to an append-only index, so it
is additive: existing entries are left as they are and reported as having an unverified
reader rather than being rewritten, because rewriting append-only history to look correct
is the failure this project keeps paying for.

### D7 — Date-order violations are computed from recno-deduplicated rows

Re-measured with the corrected reader:

| publication | dated records | violations |
|---|---|---|
| 1150820 | 1422 | 9 |
| 1150827 | 1427 | 9 |
| 1151002 | 1436 | 1 |

**The withdrawn "9 to 1" is confirmed.** It was parked on the belief that it could not be
re-derived, not because it was wrong.

Two measurement traps, both of which produced a confidently wrong answer before being caught:

- **1151002 repeats 編號 1 as a running page head on all 246 pages.** Counting rows without
  deduplicating gives 1681 records instead of 1436, and inflates violations from 1 to 246.
- **1151002 uses Gregorian dates** (`2026/9/24`). An ROC-only parser returns *zero* dated
  records for the whole file, which reports as "0 violations" — the most dangerous possible
  failure for a metric whose job is to detect an ordering change, because a broken metric
  looks like a healthy one.

The single 1151002 violation is a re-date, not a sort failure: 編號 109 (2025-08-05) sits
above 編號 110 (2025-11-26), the same unit's 第二次 and 第三次 權利變換. So the publisher does
sort by date while re-dating historical rows afterwards. Permanence still needs two more
publications; recording the metric per publication is what makes that question answerable
without re-deriving anything by hand.

## Risks

- **A publication changes the PDF behind an unchanged page** and is missed (D2). Mitigation:
  the poll records what it saw, so the gap is visible rather than silent.
- **A metric that silently reads zero.** D7 exists because a date parser returning nothing
  is indistinguishable from a well-ordered publication. The ordering count is computed with
  both calendars and its dated-record count is recorded alongside it, so a zero-violation
  result with a suspiciously low dated-record count is detectable.
- **Index schema change touching an append-only file.** Mitigated by D6: additive only,
  never rewriting existing entries.

## Migration

None. The poller is new and additive; the index gains fields without losing any; the
existing twelve entries keep their current shape and are reported as unverified-reader
rather than migrated. A first poll against the current live gazette is expected to report a
re-upload, not a new gazette — that is the correct outcome and is the acceptance test for
D1.