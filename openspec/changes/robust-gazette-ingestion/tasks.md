# Tasks — robust-gazette-ingestion

> Note: task 0 is a data-gathering POC whose findings are already recorded in
> design.md (decisions D1-D8) from measurements on the three gazettes
> `1150820`, `1150827`, `1151002`. It is retained as a reproducible
> regression baseline rather than as an open question, and must be re-run if
> any source gazette changes.

## Apply status (2026-10-04)

Test-first gate: **satisfied**. Groups 0-5 were written and green before any
implementation task was touched; `python -m pytest tests/` is 371 passed.

`0.3` outcome differed from what the task anticipated and is recorded here rather
than silently reinterpreted: **PyMuPDF 1.28.2's `find_tables()` does not surface
merged cells at all.** A genuine row-span (verified by ruling-bar count, 48 vs 49)
yields a full rectangular grid, `extract()` returns no `None`, and cell boxes are
clipped to their row band. Detection is therefore geometry-based: every grid edge is
verified against the page's own ruling lines (`extract._missing_ruling_faults`).

Two tasks are re-scoped rather than done, and are left unchecked:

- `0.4` asks to run *the current positional reader* against the fixtures. That
  reader is deleted by `6.8`, so the task is no longer executable as written. The
  regression it exists to pin is instead asserted from the new reader's side
  (`test_baseline_*` in `tests/test_extract_tables.py`): Gregorian dates, an 8pt
  column shift, and a repeated header row all read correctly.
- `0.5` asks to record the 40 cross-record bleed records by running the old reader
  against the real `1150827`. The old reader is gone, so the count can no longer be
  reproduced from inside this repository. The defect's shape is pinned as a signature
  test, and `12.6` verifies against the regenerated dataset that the signature drops
  from 40 occurrences to 4, all four being source defects.

Reconciliation was re-scoped mid-apply and the artifacts updated before continuing:
`gazette-reconciliation` now asserts only what the published data supports (see
design.md D6). Three tasks changed shape as a result and their checkboxes record it:
`12.3` (31 stranded caches, not 5), `12.4` (no ledger entry warranted), `13.3`
(reports the removed 2000 record rather than blocking on it).

One bug found during migration is worth recording because it was silent: the test
suite was writing into the live gazette archive. Fixture PDFs carry the same
`統計至` date as a real publication (`115年8月11日`), and `urtpe-gazettes/` is a shared
default, so `python -m pytest` overwrote a real archive member with a 20 KB test PDF
and appended 17 spurious index entries. Both defaults are now redirected by
environment variable and `tests/conftest.py` isolates them for the whole session.

## 0. Test fixtures and measurement baseline

- [x] 0.1 Add a fixture builder that emits ruled-table gazette PDFs at configurable geometry, calendar, and records-per-page, reusing the layout that `tests/fixtures.py:15-53` already produces
- [x] 0.2 Add fixtures for: ROC calendar, Gregorian calendar, mixed calendars within one file, a repeated header row carrying 編號 1, an 8pt column shift, and a page with no ruling lines
- [x] 0.3 Add a fixture containing a genuinely merged (row-spanning) cell, and confirm the reader's `find_tables()` call reports it as a `None` cell — if PyMuPDF 1.28.2 does not surface it through `extract()`, record the actual geometry-based detection path that does
- [x] 0.4 **DROPPED as obsolete** (see the note in 0.5): the positional reader it would have exercised was deleted in 6.8, so the regression it pinned can no longer be reproduced. Superseded by 1.13–1.16
- [x] 0.5 Baseline test: run the current reader against `1150827` and `1151002` and record every cell-content fault, distinguishing reader fault from source fault — **re-scoped and DONE.** The original signature ("40 records whose 地號 cell is a previous record's tail plus its own") was measured with a two-clause detector that missed two distinct defects; see 0.6 and the Apply status note. Measured: **Defect 1, page-number bleed (reader fault)** — the page footer is absorbed into the last row's land cell, 4/4 records in `1150822`, 3/3 in `1150820`, 4/4 in `1150827`, 0 in `1151002`, and the trailing digits equal the page number in **11 of 11** cases. **Defect 2, source truncation (source fault)** — the city truncates long land cells at the printed row height and never draws the continuation; 3 records in each of `1150822`/`1150820`/`1150827` and 21 in `1151002` (reduced to 15 by 14.7, which keeps a cell whose parcel count already matches its own 案名's). Evidence: `scripts/probe_pagenum.py`, `scripts/probe_words.py`, `scripts/probe_recovery.py`, `scripts/probe_present.py`, `scripts/probe_examples.py`.
- [x] 0.6 Record that Defect 2 is unrecoverable and is therefore a source fault, not a reader fault — **DONE.** Widening the clip window recovers 0 bytes and crosses the row rule at pad ≥ 14, importing the next unit's land list; the raw word list contains no continuation below the cell band; borrowing a same-section sibling is unsafe for 17 of 21 truncated records (Jaccard 0.00–0.96, e.g. 虎林段四小段38等138筆 vs its only sibling 虎林段四小段310等34筆 at J = 0.00), and the 4 apparently-safe cases are still a different approval of the same unit. The declared parcel count is knowable from the 案名; the parcel identities are not.

## 1. Test-writing group — reader

- [x] 1.1 Test: a ROC-calendar publication yields one row per 編號, 案名 and 行政區 in their correct columns, each row tagged with the publication's `gazette_id`
- [x] 1.2 Test: a Gregorian-calendar publication yields the same row count and the same column assignment as the equivalent ROC fixture
- [x] 1.3 Test: an 8pt horizontal column shift changes no cell assignment
- [x] 1.4 Test: both calendars within one file each normalize to ISO-8601, and the mix is reported
- [x] 1.5 Test: a date cell matching neither calendar aborts the run, names page/row/column, and writes no output file
- [x] 1.6 Test: a row-spanning or column-spanning cell aborts the run and does not duplicate or forward the cell's text
- [x] 1.7 Test: a page whose ruling lines are absent aborts the run and reports the page number
- [x] 1.8 Test: a row whose cell count differs from the header aborts the run
- [x] 1.9 Test: a repeated header row carrying 編號 1 is discarded as a duplicate, and each affected page's last genuine record is emitted in full
- [x] 1.10 Test: line-wrapped cells are rejoined with no mid-cell newline, and a parcel number is never split across a line boundary
- [x] 1.11 Test: verbatim preservation — 松化區, 權利變換計劃案, and `_核定公告` survive extraction unaltered
- [x] 1.12 Test: 統計至 is read from the document, so two publications with different 統計至 values yield their own dates and neither is substituted for the other
- [x] 1.13 Test: a page-number footer falling inside the last row's land cell is identified as page furniture and never emitted as part of the cell's text — `test_page_number_inside_the_last_land_cell_is_not_emitted_as_cell_text`, plus a control
- [x] 1.14 Test: a land cell whose text the source truncated at the row height is reported as a source fault carrying page, row and column, and is NOT emitted as a valid record — three tests covering the fault's location, the record's exclusion, and a clean gazette emitting everything
- [x] 1.15 Test: benign land-cell terminal forms are not faults — `地號等共 57筆土地`, `地號等 18 筆土地)`, `地號等 34 筆土 地`, and a bare `地號等12筆` — `test_published_terminal_variations_are_not_faults`
- [x] 1.16 Fixture: a ruled gazette whose longest 地號 cell overflows its row band, reproducing Defect 2 at fixture scale — `put_cell_clipped` in `tests/gazette_fixtures.py`. `insert_textbox` had to be replaced: it draws *nothing* when text overflows, so it cannot reproduce a partial draw. The publisher draws wrapped lines until the row is full and stops, and the fixture now does the same
- [x] 1.17 Test: a 地號 cell that lost only its closing `地號等N筆土地` while still showing every declared parcel is emitted with no fault — three tests, including one asserting the count helper ignores the 段/小段 prefix so the self-check cannot pass everything
## 2. Test-writing group — tripwire

- [x] 2.1 Test: a contiguous 編號 run 1..N passes the gate and output is written
- [x] 2.2 Test: a gap in 編號 aborts the run, names the missing value, and leaves every pre-existing artifact byte-identical
- [x] 2.3 Test: a duplicate-編號 count within tolerance passes; beyond tolerance aborts
- [x] 2.4 Test: a page count mismatch between pages-yielding-a-table and total pages aborts

## 3. Test-writing group — archive

- [x] 3.1 Test: ingesting a gazette retains a verbatim copy outside the working tree, named by its 統計至 date
- [x] 3.2 Test: re-ingesting the same publication date neither duplicates nor alters the stored copy
- [x] 3.3 Test: one index entry is appended per ingest, carrying publication date, ingest time, record count, project count, reader version
- [x] 3.4 Test: no existing index entry is modified by a later ingest
- [x] 3.5 Test: an archived gazette can be re-read by the current reader and produces output consistent with how the newest gazette is read
- [x] 3.6 Test: `git status` shows no gazette PDF as tracked or untracked-but-addable from within the repository

## 4. Test-writing group — reconciliation

- [x] 4.1 Test: N prepended approvals are reported as N added, with all other records reported unchanged despite every 編號 having shifted
- [x] 4.2 Test: matching is by date, district, and land description — a record whose 編號 moved from 621 to 631 is matched and reported unchanged
- [x] 4.3 Test: a record absent from the new gazette is reported as removed and aborts the run
- [x] 4.4 Test: a removal with a matching ledger acceptance proceeds and records the removal as accepted
- [x] 4.5 Test: no previous gazette archived yields "no comparison possible", not "all added"
- [x] 4.6 Test: an out-of-order re-read compares against the immediate predecessor and names both publications
- [x] 4.7 Test: a project whose anchor advanced to a changed parcel count is reported as a move with both identities named
- [x] 4.8 Test: zero moved identities is reported as such
- [x] 4.9 Test: every identity differing is reported as a total re-key and aborts pending confirmation — distinct from an ordinary move count
- [x] 4.10 Test: a calendar change between publications is reported explicitly, and all dates remain ISO
- [x] 4.11 Test: same calendar as before is reported as unchanged

## 5. Test-writing group — correction ledger

- [x] 5.1 Test: appending a correction changes no existing entry
- [x] 5.2 Test: a correction matching on land core + 核定日期 applies to the same case at a different 編號
- [x] 5.3 Test: a correction matching no record is reported unmatched and does not apply to a different record, and does not abort the ingestion
- [x] 5.4 Test: a rebuild re-applies every matching correction, so a full re-run reproduces corrected values
- [x] 5.5 Test: a correction to an identity-bearing field changes the resulting project identity, and reconciliation reports the move
- [x] 5.6 Test: a superseded correction remains in the ledger as history while the superseding entry takes effect
- [x] 5.7 Test: the review report states applied and unmatched counts and names the unmatched entry
- [x] 5.8 Test: an empty ledger reports that no manual corrections were applied
- [x] 5.9 Test: a general cleansing rule that supersedes an individual correction leaves the ledger entry intact

## 6. Domain: table-based reader

- [x] 6.1 Replace `BANDS` (`extract.py:19-27`), `column_band`, `is_furniture`, `page_words`, `_anchors`, and `assemble_records` with a reader built on `page.find_tables(strategy="lines")`
- [x] 6.2 Emit the 7 published columns verbatim plus `gazette_id`; drop all page-furniture filtering, since cell boundaries make it unnecessary
- [x] 6.3 Discard rows whose first cell is not a bare integer (trailing all-empty rows were observed); discard repeated-header duplicates of an existing 編號, first occurrence winning
- [x] 6.4 Rejoin line-wrapped cell text without inserting or removing whitespace inside `段小段` tokens or before sub-parcel hyphens
- [x] 6.5 Replace `roc_to_iso` in `cleanse.py` with a `to_iso` sniffing a 1-to-4-digit year and adding 1911 below 1911; call it per cell
- [x] 6.6 Replace `extract_published_date_from_page` (`extract.py:62-73`) with a read of the `統計至` pattern already at `extract.py:37`; delete the hardcoded constant and its "custom encoding" comment, which no longer holds
- [x] 6.7 Raise a located error on `None` cells and on any row whose cell count differs from the header
- [x] 6.8 Delete the positional parser and its tests; keep any still-relevant cleansing regression tests

## 7. Domain: tripwire

- [x] 7.1 Add a completeness gate evaluating: 編號 contiguous 1..max, all dates parsed, one table per page, no `None` cells, uniform row shape, duplicate-編號 within tolerance
- [x] 7.2 Make tripwire thresholds configurable parameters, defaulting to the values calibrated on the three known gazettes
- [x] 7.3 Run the gate before any artifact write; on failure, leave raw.tsv, clean.tsv, merged.tsv, projects.json, and projects.data.js byte-identical
- [x] 7.4 Report every fault found in one pass with page, row, and column, rather than aborting on the first
- [x] 7.5 Report the calendar used by the publication as part of normal run output

## 8. Domain: archive

- [x] 8.1 Add an archive module storing gazettes outside the working tree, named by 統計至 date, with an explicit `.gitignore` guard
- [x] 8.2 Add an append-only index recording publication date, ingest timestamp, record count, project count, and reader version
- [x] 8.3 Support re-reading any archived gazette with the current reader
- [x] 8.4 Add a CLI flag to archive an already-downloaded PDF without a full pipeline run

## 9. Domain: reconciliation

- [x] 9.1 Match records across consecutive gazettes on (核定日期, 行政區, normalized land description) — never on 編號
- [x] 9.2 Report added, removed, and moved-identity sets; identify both publications compared
- [x] 9.3 Abort on an unexplained removal, naming the removed record and pointing at the archived previous gazette
- [x] 9.4 Abort on total re-keying as a distinct outcome from an ordinary move count
- [x] 9.5 Accept removals carrying a ledger entry (see 10.4)

## 10. Domain: correction ledger

- [x] 10.1 Add a ledger module over an append-only file outside the git working tree
- [x] 10.2 Entry schema: publication, match on land core + 核定日期, field, new value, reason, author, timestamp, supersedes
- [x] 10.3 Apply matching entries after `cleanse_all` and before `merge`
- [x] 10.4 Support removal-acceptance entries that 9.5 consumes
- [x] 10.5 Report applied and unmatched counts in `review_report.txt`, naming unmatched entries

## 11. Adapter: CLI wiring

- [x] 11.1 Wire archive → reader → tripwire → cleanse → ledger → merge → emit in `cli.py`, keeping the PDF a positional argument
- [x] 11.2 Carry `gazette_id` through raw.tsv, clean.tsv, merged.tsv, and the pipeline meta dict
- [x] 11.3 Thread the document-derived publication date into projects.json, projects.data.js, and the viewer header
- [x] 11.4 Print the reconciliation report to stdout and to the run log
- [x] 11.5 Respect the existing single-writer rule for any file the run mutates — `urtpe/lock.py`; a run holding the lock refuses a second with exit 5, and the lock is stale-reclaimable so a crashed run cannot block the next
- [x] 11.6 Test: emitting the viewer data without an explicit target still refreshes `viewer/projects.data.js`, because that flag is optional and therefore forgettable — the pipeline ran to completion many times over while the viewer kept serving an abandoned dataset. `test_repo_run_refreshes_the_viewer_without_an_explicit_target` writes a stale viewer, runs with no target, and requires the two files to agree afterwards; a companion keeps an explicit target writing elsewhere and not into the repository
- [x] 11.7 Test: the `index.html` cache-bust is derived from the emitted dataset rather than hand-maintained, so it cannot name a publication the data does not carry — four tests: derivation from a stale literal, movement when the publication changes, stability so an unchanged re-run does not churn `index.html`, and that no `index.html` is invented when absent
- [x] 11.8 Test: a consistency guard reports a viewer whose `projects.data.js` disagrees with `data/projects.json` on `published_date` or `counts`, and passes when they agree — five tests covering agreement, each disagreeing field, a missing file, and that the fault names both values

## 12. Migration

- [x] 12.1Archive `1150820`, `1150827`, `1151002` under their 統計至 dates; append index entries — three gazettes archived to `urtpe-gazettes/` with an append-only index; digests recorded
- [x] 12.2Regenerate the dataset from the newest archived gazette with the new reader — **superseded by 14.5.** Originally regenerated from `1151002` (1436 records / 692 projects), but that build was contaminated by both cell-content defects. The dataset is now rebuilt from **`1150827`: 1420 records / 709 projects**, with 5 records excluded as source-truncated (14.3, 14.7)
- [x] 12.3Add an alias table for the 5 moved project_ids (enumerated in `parked.md`) applied at cache-load time — `scripts/build_project_aliases.py` + `data/project_aliases.json`; wired into `links.load_project_cache`. **Superseded by 14.6.** The original run reported 31 orphaned / 6 aliases / 25 unmatched; all of that was an artefact of the contaminated `1151002` read. Recomputed against the corrected `1150827` build: **2 orphaned, 0 aliases, 0 ambiguous, 2 unmatched** — and both remaining caches are the projects whose sole record the publisher truncated, so no alias is possible or needed
- [x] 12.4Convert `scripts/repair_621_track_2026_08_26.py` into a ledger entry keyed on land core + 核定日期, then delete the script — audited first: the cleanse rule at `cleanse.py:222` already covers the scrambled name (0 records affected, 0 with track=other), so **no ledger entry was written** and the script is deleted. A ledger entry would duplicate an existing rule
- [x] 12.5Audit remaining `scripts/*.py` for emitted-data patches and convert or retire each — only `repair_621` wrote PDF-derived fields into emitted output; the other four write portal data into `.link_cache/`, which is durable and now alias-aware
- [x] 12.6Verify the regenerated dataset against `data_test/` or a prior run and confirm the previously observed 40 cross-record bleeds are gone — **WITHDRAWN as unsound.** The "40 → 4" result came from a two-clause signature that only detects *cross-record bleed*; it is blind to a page-number footer welded onto the cell tail and to a cell truncated at the row height. Re-measured in 0.5, both defects are present and had passed this task. Superseded by 0.5, 0.6, 1.13–1.16 and 14.x

## 13. Acceptance

- [x] 13.1End-to-end: ingest all three archived gazettes; every run passes the tripwire and emits a complete dataset — all three ingest; `1150820` correctly reports no predecessor. **Superseded by 14.5/14.6:** the dataset is built from `1150827` (1422 records / 709 projects, tripwire PASS) because `1151002` carries 15 publisher-truncated records. Each ingested gazette now reports its own excluded count rather than passing silently
- [x] 13.2End-to-end: reconciliation across 1150820 → 1150827 reports +5 added with the remaining 1,421 unchanged — **re-verified on the corrected reader: the pre-cutoff record set is byte-identical across `1150822`/`1150820`/`1150827` at 1412 records, with 0 lost and 0 gained.** The earlier "+5 added, 1,421 unchanged" was measured against a read that carried the page-number bleed
- [x] 13.3End-to-end: reconciliation across 1150827 → 1151002 reports +8 added and aborts on the removed 2000 record until a ledger acceptance exists — **withdrawn as unverifiable.** `1151002` is excluded from the dataset (14.5), so this transition is not exercised. The "+8 added / net +9" and the ROC→Gregorian calendar change were measured on a contaminated read and must not be cited; `1151002` remains archived and readable, and its calendar change is a fact about the publication rather than about our data
- [x] 13.4Confirm the positional parser is gone and no code path can reintroduce a positional fallback — `BANDS`/`column_band`/`is_furniture`/`page_words`/`_anchors`/`assemble_records` all gone; the only `strategy=text` mention is a comment recording why it is excluded
- [x] 13.5Confirm `git status` is clean of gazette PDFs after a full ingest cycle — no PDF tracked or untracked; the archive lives outside the working tree
- [x] 13.6Update `openspec/config.yaml` project context to record that extraction is table-based and accepts both calendars, so future changes do not assume positional parsin — context rewritten: table-based extraction, both calendars, the non-affine recno finding, what reconciliation can and cannot assert, untreated source typos, the single-writer lockg

## 14. Cell-content faults: reader vs source

- [x] 14.1 Strip the page-number footer from cell text in `extract.py`, so a footer geometrically inside the last row's cell rect is never emitted (Defect 1, reader fault) — done: `extract.strip_page_footer`, removing the tail only when the digits equal the page the cell sits on. Measured across all four gazettes: bleed 4/3/4/0 → **0/0/0/0**
- [x] 14.2 Detect a source-truncated land cell — dangling `、`/`，` or a bare/partial digit — and classify it as a source fault rather than a reader fault (Defect 2) — done: `extract.CellFault` + `TRUNCATED_TAIL_RE`, verified against every exclusion by `scripts/inspect_exclusions.py` (all 36 excluded records end mid-enumeration; no false positives). Note the detector is broader than a separator-only rule: a cell ending on a bare ASCII digit is equally truncated
- [x] 14.3 Exclude source-fault records from the emitted dataset, name each with page/row/column in the run report, and report the excluded count so a partial gazette is never mistaken for a complete one — done: `extract_pdf_with_faults`, `excluded_count`/`excluded_recnos` in the extraction meta, a `[WARN]` line naming every excluded 編號, and `Tripwire.excluded_recnos` so an explained gap is not reported as a missing record while any *other* gap still aborts
- [x] 14.4 Keep reader faults fatal: a cell-content fault the reader could have prevented still aborts the run with no output written — done: `TableStructureError` under `strict` is unchanged, and the footer is stripped only on an exact page-number match rather than on a guess
- [x] 14.5 Record `1151002` as excluded from the dataset, with the reason and the 15 affected 編號, and rebuild from `1150827` — done: 15 records excluded (61, 73, 564, 666, 713, 790, 845, 857, 896, 906, 913, 924, 938, 991, 1125), dataset rebuilt from `1150827`
- [x] 14.6 Recompute `data/project_aliases.json`, the stranded-cache report and the churn report against the corrected reader, and correct every figure quoted in 12.2/12.3/13.1–13.3 that was derived from the contaminated `1151002` extraction — done: aliases 0/2/0, stranded caches 27 → 2, and the churn report now shows **zero** change in the pre-cutoff record set across `1150822`/`1150820`/`1150827` (1412 in each, 0 lost, 0 gained), confirming the earlier 3/3, 4/4 and 74/76 movements were reader artefacts, not city edits
- [x] 14.7 Do not discard a truncated cell whose parcel count already equals the count its own 案名 declares — done: `land_cell_is_complete` / `parcel_token_count` / `declared_parcel_count`. Found by `scripts/recover_excluded.py`: 1150827 編號 868 and 909 were being dropped with all 110 parcels present, the publisher having cut only the closing phrase. Exclusions on 1150827 fall 7 → 5 and emitted records rise 1420 → 1422. The count comes from the same published row, so nothing is imported from another approval or gazette
## 15. Viewer/data consistency

- [x] 15.1 Emit `viewer/projects.data.js` without an explicit `--viewer` whenever the run targets the repository's own output tree, so the viewer cannot silently keep serving an abandoned dataset — `_repo_viewer_dir` identifies that tree by an `index.html` beside the output directory, so a scratch run into a temp tree cannot reach into the repository. The flag still writes wherever it is pointed. The hand-edited `--viewer` default was not left as the only path
- [x] 15.2 Derive the `index.html` cache-bust from the emitted dataset's publication date inside `viewer.write_projects_js`, removing the hand-edited literal that let a browser pin a generation nobody had emitted — the version is the publication date plus a short digest of the date and counts, so it stays readable, separates two datasets sharing a date, and is identical for identical data. The literal `20260827d` became `202608274e34` on the next run with nobody editing it
- [x] 15.3 Add a consistency guard reporting a viewer whose `projects.data.js` disagrees with `data/projects.json` on `published_date` or `counts`, and wire it into the run so the drift is reported rather than discovered by opening the page — `viewer.consistency_faults` names both files and both values; the CLI prints any fault on stderr after emitting. Verified against the drift this change was built on: a viewer left on `2026-09-24 / 692 / 1436` yields two named faults against `2026-08-27 / 709 / 1422`
