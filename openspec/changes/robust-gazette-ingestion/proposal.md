## Why

The gazette PDF is re-published periodically and its layout is not stable: between the 1150827 and 1151002 publications the city changed the date column from ROC (`115/8/27`) to Gregorian (`2026/9/24`) and glued it to the 行政區 cell, shifted every column ~8pt left, and began repeating the row for 編號 1 in the page header on all 245 remaining pages. The current positional reader (`urtpe/extract.py`, seven hardcoded x-coordinate bands) parsed the 1151002 file without raising an error and emitted 1,681 rows of which **1,677 had an empty 案名**, all 1,681 had `ymd=(0,0,0)`, and 行政區 contained the full case name. Because `merge.py:131` selects each project's anchor by newest 核定日期, zero dates silently inverted the anchor rule to *oldest*, so `slug_for()` minted 1,436 garbage `project_id`s — every one of the 709 `data/.link_cache/<project_id>/` directories would be orphaned, and `coverage.py:51` would report `regressions={}` because it only diffs `set(before) & set(after)`, which is empty under a total re-key. The same parser also corrupts cells on the *currently trusted* file. Two distinct faults were measured on `1150827`, and separating them is what shaped the design:

- **Page-number bleed (the reader's fault).** The city's layout prints the page number inside the last row's 地號 cell; a reader that trusts the cell rectangle absorbs it, leaving a land cell ending in a bare integer. The trailing digits equalled the page the row sat on in **11 of 11** occurrences across `1150822`, `1150820` and `1150827`.
- **Publisher truncation (not the reader's fault).** The city stops drawing the parcel list at the printed row height and never draws the remainder, so a 地號 cell ends mid-enumeration — 3 records in each of the three earlier gazettes, 15 in `1151002`. The missing text is absent from the PDF: widening the text window recovers nothing and crosses the row rule, importing the next unit's land list.

An earlier measurement attributed 40 records on `1150827` to cross-record bleed. That signature was measured with a two-clause detector blind to both faults above, and is withdrawn; see `tasks.md` 0.5 and 12.6.

Alongside this, the pipeline keeps no history: `data/**` is gitignored, the only PDF in the repo is `source.pdf` (統計至 115-8-11, older than the data being shipped), and there is no archive, so a change diff against the previous gazette cannot be computed at all. Manual corrections are held in ~18 dated one-off scripts that patch emitted JSON in place — `scripts/repair_621_track_2026_08_26.py` states outright that it compensates for a `cleanse.py` rule added after the last regeneration, so a full rebuild silently reverts it.

## What Changes

- **BREAKING** Replace positional x-band extraction with ruled-table cell extraction (`page.find_tables()`, `strategy="lines"`). All seven cell boundaries come from the document's own ruling lines instead of hardcoded coordinates.
- **BREAKING** Reject, rather than repair, any table structure the reader cannot interpret exactly: merged/row-spanning cells (`extract()` yielding `None`), pages where no table is detected, and a text-strategy fallback. Each aborts the run with a located error.
- Add per-cell calendar sniffing so ROC (`115/8/27`) and Gregorian (`2026/9/24`) inputs both normalize to ISO-8601, decided per cell so a single file may mix calendars.
- **BREAKING** Read `統計至` from the document instead of the hardcoded `"統計至 115年8月11日"` constant at `extract.py:62-73`, which currently stamps every ingest with 8/11 regardless of input.
- Add a structural tripwire that refuses to emit when the extraction is not provably complete: 編號 contiguous from 1, every date parsed, every page yielding exactly one table, no spans, no duplicate-編號 beyond the known header artifact, calendar mix reported.
- Add a gazette archive retaining every ingested PDF plus an append-only index, stored **outside** git.
- Add reconciliation against the previously archived gazette, reporting the authoritative signals — approvals newer than the predecessor's maximum date, net change in total records, and calendar mix — alongside historical row movement as its own counted, non-blocking signal. Refusing to complete is reserved for what can actually be established: a shrinking list, a withdrawn newest cohort, or a total re-key. A per-record deletion cannot be asserted against this source, because in the published data a deletion and an edit are the same observation.
- Add an append-only correction ledger, keyed on `land_core` + `核定日期` rather than 編號, applied after cleansing and before merge, with applied corrections reported in the review report.

### Non-Goals

One item was declared out of scope here and then built anyway, because it turned out not to be blocked:

- Migrating the `project_id` cache directories that move when the reader changes was listed as parked on reconciliation output. Reconciliation shipped, and the alias mechanism was needed to land it: `scripts/build_project_aliases.py` emits `data/project_aliases.json`, applied at cache-load time. Measured against the corrected reader it pairs **0** aliases and leaves **2** stranded directories, both of them the projects whose sole record the publisher truncated — so no alias exists for them and none should be invented.

Still parked, with their prerequisites and un-parking triggers:

- Portal sync / event cascade (blocked on reconciliation providing a reliable per-gazette change diff).

## Capabilities

### New Capabilities

- `gazette-archival`: Retain every ingested gazette PDF and an append-only index recording what each file yielded, so that any two publications can be compared and any past gazette can be re-read with the current reader.
- `gazette-reconciliation`: Compare a newly ingested gazette against the previously archived one and report added/removed records, moved project identities, and calendar mix, refusing to complete on any change the system cannot explain.
- `correction-ledger`: Record manual data corrections as durable, append-only, attributed entries keyed on stable content rather than the per-gazette 編號, and re-apply them on every rebuild.

### Modified Capabilities

- `pdf-tsv-extraction`: Cell boundaries SHALL come from the document's table structure rather than hardcoded coordinates; both ROC and Gregorian calendars SHALL be accepted and normalized to ISO-8601; `published_date` SHALL be read from the document rather than hardcoded; and any structure the reader cannot interpret exactly SHALL abort the run instead of producing partial or corrupt output.

## Impact

**Code**

- `urtpe/extract.py` — replace `BANDS` (lines 19-27), `column_band`, `is_furniture`, `page_words`, `_anchors`, `assemble_records`; replace the hardcoded `extract_published_date_from_page`; add span detection and per-cell calendar sniffing.
- `urtpe/cleanse.py` — `roc_to_iso` becomes a calendar-agnostic `to_iso`; correction-ledger application point added between `cleanse_all` and `merge`.
- `urtpe/cli.py` — wire archival, tripwire, reconciliation, and ledger; the PDF remains a positional argument.
- New modules for archival, the tripwire, reconciliation, and the ledger.

**Unchanged on purpose**

- `urtpe/merge.py` scoring, thresholds, and clustering — untouched.
- `urtpe/graph.py` — `date` is already emitted as ISO, so no graph change is required.
- The viewer — its header reads `counts` and `published_date` out of the data rather than hardcoding them. What did change is that the data file is now refreshed by any run against this repository, its asset version is derived from the dataset rather than hand-maintained, and a guard reports a viewer that disagrees with `projects.json`; all three because the page was found serving a dataset the pipeline had abandoned.
- `.link_cache/<project_id>/` layout — untouched. 2 of 709 directories are stranded, both traceable to a record the publisher truncated.

**Data**

- New `gazettes/` archive directory outside the repo working tree, referenced by an index file.
- New append-only correction ledger.
- `data/raw.tsv` and `data/clean.tsv` gain a `gazette_id` column so emitted rows are attributable to a publication.

**Dependencies**

- No new runtime dependency. PyMuPDF's `find_tables()` is used as shipped in 1.28.2. `pymupdf_layout` was evaluated and rejected: process-isolated A/B on pages 1-3 of 1151002 corrupted 17 of 18 records by inserting whitespace inside `段小段` tokens and before sub-parcel hyphens (`764-1` → `764 -1`), which breaks `SECTION_RE` and `ALIAS_RE` and would change `project_id`; it is also proprietary, pinned to an exact PyMuPDF version, and ~35× slower per page.

**Gated on further POC**

- The tripwire thresholds (duplicate-編號 tolerance, expected records-per-page) are provisional, calibrated against the three gazettes measured so far and may need adjustment when the next publication is ingested.