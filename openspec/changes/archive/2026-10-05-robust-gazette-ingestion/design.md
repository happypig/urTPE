# Design — robust-gazette-ingestion

## Context

### Actors

| Actor | Concern |
|---|---|
| **Pipeline maintainer** (jeffw) | Runs ingestions; must not silently lose data or orphan caches |
| **Periodical updater** | Fetches the newest gazette; needs a cheap way to tell whether anything changed |
| **Reviewer** | Reads the review report after each run; must see applied corrections and unexplained changes |
| **臺北市都市更新處** (external) | Publishes the gazette; controls its layout, calendar, and column order |

### Domain events

- The city publishes a new gazette (new approvals prepended; layout may change without notice)
- A person corrects a record after reading the review report
- The reviewer accepts or rejects a change between two publications
- A schema of change the reader cannot interpret is encountered

### System boundary

```
IN SCOPE (this change)                OUT OF SCOPE
─────────────────────                ─────────────────────────────
gazette PDF → raw rows                portal (twur / Taipei ashx) discovery
cleansing rule application            the 28 h national-portal sweep
similarity merge (unchanged)          portal sync / event cascade
project identity (unchanged)          viewer UI beyond a label
archive + diff + tripwire
correction ledger
link_cache alias table (see below)
```

The last row was originally listed as out of scope: ".link_cache migration of
moved ids". That was wrong, and the work proved it. Reconciliation shipped and the
alias mechanism turned out to be a prerequisite for landing it — a reader change
that moves an identity strands the cache directory named after it, and the run
cannot complete while that is unhandled. It is in scope, and landed as
`scripts/build_project_aliases.py` + `data/project_aliases.json`, applied at
cache-load time rather than by renaming directories on disk, which would break the
single-writer rule and any in-flight run.

### The failure this design exists to prevent

The reader parsed gazette `1151002` without raising. It produced 1,681 rows of which **1,677 had an empty 案名**, **all** had `ymd=(0,0,0)`, and 行政區 contained the entire case name. Three independent causes:

```
(a) 核定日期  115/8/27  中山區     (ROC, separate cells)   → worked
(b) 核定日期  2026/9/24中山區                              → glued; strict fullmatch
                                                              failed → (0,0,0)
    then: pick_anchor() max(ymd) is a tie for every record
          → falls through to min(recno) → anchors OLDEST
          → 1,436 garbage project_ids → all 709 caches orphaned
          → coverage.py:51 set(before)&set(after) == ∅ → regressions={} → PASSES

(c) case-name column x0: 185.1 → 177.5, band edge is exactly 185
    → the whole 案名 column lands in the 行政區 band

(d) 編號 1 repeated in the header of all 245 remaining pages
    → 245 phantom anchors; record boundaries are midpoints between
      consecutive numbers, so each phantom TRUNCATES the page's last record
```

Cause (b) is the one that matters: **the reader had no way to report that it had failed.** The zero-date cascade into `project_id` is the reason a tripwire is a requirement and not a nicety.

## Decisions

### D1 — Cell boundaries come from ruling lines, not coordinates

**Decision.** Replace `BANDS` (`extract.py:19-27`) with `page.find_tables()` at `strategy="lines"`, taking each cell's text from the rectangle the table detector resolves.

**Rationale.** Measured on both publications:

| | 1150827 | 1151002 |
|---|---|---|
| pages yielding a table | 202/202 | 246/246 |
| distinct 編號 published | 1427 | 1436 |
| empty 案名 | 0 | 0 |
| empty 核定日期 | 0 | 0 |
| records emitted | 1422 | 1421 |
| excluded as publisher-truncated | 5 | 15 |

100% structural on both, including the file the positional reader fails on
completely. The column shift and the calendar change are both invisible to it
because neither is expressed as a coordinate it stored.

The emitted counts are **not** the published counts, and the difference is
deliberate: the publisher truncates a handful of 地號 cells at the row height, and
those records are excluded rather than emitted with a parcel set nobody can
verify (D10). Contiguity therefore holds with known exceptions rather than
absolutely — see D3.

**Alternative rejected — fix the bands.** The bands are 7 numbers tuned to one export. The city changed the calendar and shifted the columns in a single publication; the next change is equally unforecastable. Tuning constants against observed drift treats a moving target as a fixed one.

**Alternative rejected — `pymupdf_layout`.** Evaluated, not assumed. Process-isolated A/B over pages 1-3 of `1151002`, output written by separate processes and compared on disk:

```
plain  臺北市中山區長春段一小段 764、764-1 地號等2筆土地
layout 臺北市中山區長春段 一小段 764、764 -1 地號等2筆土地
                 ▲                      ▲
      space inside 段小段        space before every sub-parcel
```

**17 of 18 records corrupted.** The GNN's whitespace normalization is correct for prose and destructive for an identifier stream:

- `長春段一小段` → `段 一小段` breaks `SECTION_RE` → `section` empty → `slug_for()` garbage
- `764-1` → `764 -1` breaks `ALIAS_RE` (the `689地號(原726地號)` renumbering bridge at `cleanse.py:24`)
- record 7's `231-3` → `231\n-\n3`, the hyphen isolated on its own line

It is also proprietary ("may not be copied, modified or distributed except as expressly authorized"), pinned to `pymupdf==1.28.2` exactly, and ~35× slower per page (0.06 s → 2.19 s). Rejected on correctness; the cost arguments are secondary.

### D2 — Reject spans; never fall back to text strategy

**Decision.** A cell spanning more than one row or column aborts the run with its location. A page yielding no table aborts the run. No positional or whitespace-aligned fallback exists in the new reader.

**Rationale.** PyMuPDF models spans explicitly:

```
SpanCell  "One reconstructed table cell after span resolution… colspan/rowspan
           how many grid columns/rows it covers."
to_markdown(clean=False, fill_empty=True)
          "If fill_empty then cell content None is replaced by the values…"
table.py:1756   # replace None cells with empty string
```

`extract()` returns `None` at grid positions owned by a span anchored elsewhere, and `fill_empty=True` is the **default** in `to_markdown()` — the library fills spans because the correct answer is not derivable from geometry. Fill forward or fill down? Genuinely undecidable.

In this domain it is decidable, and the answer is to refuse: a 地號 cell spanning two printed rows means we cannot know which approval owns those parcels, and `first_parcel` feeds `slug_for` → `project_id` → the `.link_cache` directory name. A guess orphans a cache and mints a bogus id — the same failure class as D1, arrived at from a different direction.

Empirically this costs nothing today: **0 `None` cells across 23,177 cells** in both publications (11,403 + 11,774), every row exactly 7 cells. It is insurance against a structure we have not yet seen, and it fails loudly when it triggers.

`strategy="text"` is specifically excluded because it was measured to be destructive on a ruled table: it collapsed a 4-column grid to 2 and merged two cells into one field (`'10 SPAN'`). If ruling lines ever vanish, text strategy would corrupt 編號 — the one field everything keys on.

### D3 — Completeness tripwire, evaluated before any write

**Decision.** Every emission is gated on: every 核定日期 parsed; exactly one table per page; no `None` cells; no row-shape mismatch; duplicate-編號 count within the known header-artifact tolerance; and 編號 contiguous from 1 to max **apart from exclusions the reader has declared and the caller has been told about**.

**Rationale.** 編號 is contiguous as published, with no gaps. That makes "no gaps" a three-line, format-agnostic assertion that catches a whole class of silent truncation — including a page the reader failed on entirely, which under D2 aborts anyway.

The qualification exists because D10 introduces declared exclusions. An exclusion and a lost page look identical to a contiguity check, so the tripwire takes the excluded 編號 as input: a gap that is fully explained passes, and any other gap still aborts. Carrying them separately also keeps the two failure modes distinguishable in the run report rather than collapsed into one number.

Critically, the gate must run **before any artifact is written**. The 2026-08-24 incident (four concurrent writers, 47 caches wiped) and the current `coverage.py` blind spot have the same shape: a check that runs after the damage, or that cannot see the failure. `coverage.py:46-59` diffs only `set(before) & set(after)`; a total re-key empties that intersection, so the guard passes while every cache is orphaned. The tripwire must be upstream of the write, and reconciliation (D6) must special-case total re-keying.

**Provisional.** The duplicate-編號 tolerance and expected records-per-page are calibrated against three gazettes and may need adjustment at the next ingestion.

### D4 — Calendar sniffed per cell, normalized once at the boundary

**Decision.** Replace `roc_to_iso` with a `to_iso` that reads a 1-to-4-digit year and adds 1911 when below 1911, applied per cell. All downstream comparison uses ISO.

**Rationale.** ROC began in 1912, so no ROC year reaches 1911 and `y < 1911` is an unambiguous discriminator. Deciding per cell means a publication that mixes calendars — plausible mid-transition — is handled without a special case.

Normalization happens once in `cleanse`, so `ymd`, `pick_anchor`, the viewer's year facet (`app.js:543-551` slices `node.date`), and `_match_case_by_date` (`links.py:1149-1184`) all compare like with like. `graph.py:22` already emits `date` as ISO, so **the viewer needs no code change**.

The old failure is the argument for this: the glued `2026/9/24中山區` failed `re.fullmatch` and silently produced `(0,0,0)` for every record. A sniffing parser that cannot interpret a cell now aborts instead.

### D5 — Publication date read from the document

**Decision.** Delete the hardcoded return at `extract.py:62-73` and use the `統計至` pattern already present at `extract.py:37`.

**Rationale.** The function ignores its `page` argument and returns `"統計至 115年8月11日"` for any input. Measured: `1150827` → `統計至115年8月27日`, `1151002` → `統計至115年9月24日`, both extract cleanly. `projects.json` currently stamps 8/11 after ingesting a 9/24 publication — the header lies about its own vintage.

This also means the existing spec requirement (`pdf-tsv-extraction/spec.md:41-53`), which names `115年8月11日` as the expected value, must be replaced rather than supplemented.

### D6 — Reconciliation reports additions authoritatively and historical movement as a separate signal

**Decision.** Match the newest-approval cohort by content and count it; report historical
row movement (re-dated, edited) as its own counted signal; block only when the total
record count shrinks or the previous newest cohort is withdrawn. `--strict-reconcile`
promotes historical disappearance to blocking, satisfiable by a ledger acceptance.

**Rationale — the recno model no longer holds.** The shift is not affine:

```
1150820 → 1150827   every one of 1,421 matched records moved exactly +5   (uniform)
1150827 → 1151002   old#1 → +8    old#100 → +6    old#300 → +5
                     old#1000 → −13 ◄── moved UP past 13 records
                     old#1420 → +10
```

Non-monotonic. So recno is a coordinate in a mutable list, not a rank with an offset, and
any remap keyed on it is arithmetic on an unknown function.

The shape of that non-affinity was measured on a **contaminated read** — see the
withdrawn note below — so the specific per-record offsets and the "date-order
violations fell from 9 to 1" figure are not cited. The non-affinity itself is not in
doubt: `1150820 → 1150827` was uniform at +5 across all 1,421 matched records, and
`1150827 → 1151002` moved records in both directions.

**Rationale — why per-record content diffing was rejected.** An early implementation
matched on `(行政區, land, ISO date)` and reported **74 removals** for 1151002. Every one
was a false positive. The two causes originally given for that — the new export
re-dates history, and the city edits historical cells — are real properties of the
source, but they were **not** the cause of those 74. The cause was the reader: a
page-number footer absorbed into a 地號 cell, and long cells truncated at the row
height, both of which change a row's text and so make it look added and removed at
once. With the reader corrected, the pre-cutoff record set is **identical** across
`1150822`, `1150820` and `1150827` at 1412 records — 0 lost, 0 gained (D10).

The re-dating and editing properties still stand, and still mean a per-record
deletion cannot be asserted against this source: in the published data a deletion and
an edit are the same observation. Only three things survive that:

| Signal | 0820→0827 | 0827→1002 | Authoritative |
|---|---|---|---|
| approvals newer than the previous maximum date | 5 | 8 | yes |
| net change in total records | +5 | +9 | yes |
| calendar | unchanged | roc → gregorian | yes |

This is the same constraint `openspec/config.yaml` already states for the merge stage —
*"parcel coverage changes and parcel renumbering break exact-key matching, so unit
identity must be found by similarity, not equality"* — applied here as a scoping
decision rather than a scoring strategy. Similarity matching was considered and
rejected: ~1400² comparisons per run to resolve rows that are, in the cases that
matter, genuinely ambiguous.

**Consequence, recorded honestly.** The disappearance of
`大安區仁愛段四小段114地號等6筆`, a 2000-vintage row, was originally read as a genuine city
deletion and made the subject of a blocking rule. It is no longer treated as
established. It falls in the historical signal, is reported prominently with its
district and land description, and does not stop a run — and the specific figures once
attached to it (`89/9/29`, and the per-cell counts behind them) came from the
contaminated read and are withdrawn. Task 13.3's original wording ("aborts on the
removed 2000 record") is therefore not satisfiable as written and was revised; a
per-record deletion assertion cannot be made against this source.

**Blocking conditions, and why each is sound:**

- *Total record count shrinks.* Arithmetic on a quantity the reader has already proven
  contiguous via the tripwire.
- *Previous newest cohort withdrawn from the current newest cohort.* Both cohorts are
  bounded by a date the reader parsed, so absence is meaningful here in a way it is not
  for edited historical rows.
- *Total re-keying.* `coverage.py` cannot express it (see D3).

**Also measured, and not defects:** the source carries long-standing typos that are
identical in both publications — `臺北市投區崇仰段` (missing 北), `臺北大安區辛亥段`
(missing 市), and two rows whose 案名 leaks into the 地號 cell. `cleanse.py:16` already
handles the `松化區` district typo; the others are untreated and become unreconcilable
noise. Recorded for a separate cleansing change rather than fixed here.

### D7 — Corrections are ledger rows keyed on land core + date

**Decision.** Replace dated patch scripts with an append-only ledger, applied after `cleanse_all` and before `merge`.

**Rationale.** `scripts/repair_621_track_2026_08_26.py` documents its own problem:

> *"The cleanse.py normalization (事業換計畫 → 事業計畫) landed after the last `--from-js` regeneration… This script patches the emitted data to exactly what the next full PDF build will produce."*

It compensates for a fix already in code, because artifacts and code drifted apart. Worse, it patches by `recno 621` — a coordinate that under Option A becomes a different row next gazette, at which point it silently no-ops or patches the wrong record.

Keying on `land_core` + `核定日期` makes corrections position-independent: the same case at 編號 621 in one publication and 631 in the next still matches. Applying post-cleansing, pre-merge means a correction to an identity-bearing field propagates into `project_id`, which reconciliation then reports. Reporting applied/unmatched counts in the review report makes corrections visible in normal operation rather than only in the ledger file.

Unmatched entries are reported, not fatal — a correction for a record that has not been re-published yet is normal, not an error.

### D8 — Archive outside git

**Decision.** Store gazettes outside the working tree, referenced by an append-only index. Add an explicit `.gitignore` entry as a guard against accidental staging.

**Rationale.** `.gitignore` already carries `data/**` and `data_test/**`, so `data/` is untracked and git history holds 14 commits of `projects.json` but only 2 of `clean.tsv` — no gazette dimension at all. The PDFs are upstream artifacts, roughly 2 MB each, about 100 MB/year.

The deciding factor is durability of the *old* ones: the city's URL is version-specific (`www-ws.gov.taipei/001/Upload/459/relfile/18558/10496/c5ff4f68-….pdf`, a UUID path), so only the newest is reachable. Older gazettes must be kept locally or they are gone. Keeping them out of git avoids repo growth for artifacts that are, by construction, re-downloadable only while the city still serves them.

Cost: the archive is a separate durability concern from the repo. Mitigated by the index recording what each file yielded, so a missing archive member is detectable rather than silent.

### D9 — Rebuild layers 0–2 in full; keep layer 3 incremental

**Decision.** Full rebuild of parse → cleanse → merge on every ingestion. No incremental path for the PDF-derived layers.

**Rationale.** Measured cost of a full rebuild: `find_tables()` over 448 pages ≈ 42 s, cleanse + merge ≈ 0.3 s, graph emit ≈ 2 s. Roughly **45 seconds**. Incremental would buy nothing and would guarantee the failure mode that produced `repair_621`: 2019 records parsed under old rules, 2026 under new, in one dataset. Full rebuild is the only way a reader change reaches historical records uniformly.

The portal layer is the opposite and is already correct: `.link_cache/<project_id>/` is keyed on an identity that survives. Against the corrected reader, migrating three publications strands **2** of 709 directories, needs **0** aliases, and has **0** ambiguous pairs — and both stranded directories are the projects whose sole record the publisher truncated, so no identity pairs them. The earlier figure of 5 moves (704 of 709 unchanged) was measured with the old reader and is withdrawn. Caches are consulted, not rebuilt.

### D10 — A fault in a cell is classified by who caused it

**Decision.** Faults found in cell text are sorted by cause, and the two demand opposite responses. A fault the reader could have prevented is fixed, and if it cannot be fixed with certainty the run aborts. A fault the publisher introduced, which no reading of the document can repair, does not abort: the record is excluded, named with page, row and column, and counted, so a gazette missing records is never presented as a faithful copy.

**Rationale.** The measurement that forced this is that the same symptom has two
unrelated causes. A 地號 cell ending in a bare integer was, in every observed case,
the page-number footer printed inside the last row's cell — 11 of 11 times the digits
equalled the page the row sat on. A 地號 cell ending mid-enumeration was the
publisher stopping at the row height, and the missing text is **not in the PDF**:
widening the text window recovered nothing at pad 0, 6 or 14, and at pad 14 the window
crossed the row rule and returned the next unit's land list; the raw word list holds no
continuation below the cell band; and borrowing a same-section sibling is unsafe for 17
of 21 truncated records (Jaccard 0.00–0.96, one case at 0.00 against a same-section
sibling that is a different project entirely). A reader that treated both as "bad cell"
would either abort on every gazette forever or invent parcel data.

Two consequences worth stating plainly:

- **The declared parcel count is knowable; the parcel identities are not.** A 案名
  reading `等138筆` tells you how many parcels should be there. It cannot tell you which.
- **Completeness has a self-check.** When a truncated cell still shows exactly as many
  parcels as its own row's 案名 declares, the list is provably whole and only the closing
  phrase was lost, so the record is kept. This is a same-row comparison and imports
  nothing from another approval; without it, two sound 110-parcel records were being
  discarded for want of a closing `地號等110筆土地`.

Stripping the page number is done only when the digits equal the page the cell sits on.
A trailing number that does not match is not discarded on a guess.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| A future publication has no ruling lines | Low | D2 hard-fails; no unsafe fallback exists. Re-evaluate `pymupdf_layout` **only** at that point, when whitespace heuristics are the only alternative |
| Tripwire thresholds too strict, blocking a valid ingestion | Medium | Thresholds are parameters, not constants; a blocked run names the failing check |
| Archive diverges from index | Low | Index records what each file yielded; a missing member is detectable |
| **A declared exclusion masks a reader fault** | **Realised — this is how 1151002's 15 truncations shipped** | **D10.** Once the reader began excluding records on purpose, a contiguity check could no longer distinguish "we chose to drop this" from "we lost this". Every exclusion is therefore named with page, row and column, counted in the run report, and listed in the extraction metadata; a reviewer can audit the exclusion set rather than trusting a count |
| **A reader fault is misattributed to the publisher** | **Realised** | **D10.** Both faults looked alike — a cell ending oddly — and the page-number bleed was invisible to a detector aimed at truncation. A footer is stripped only on an exact page-number match; anything else stays a fault |
| The viewer keeps serving a dataset the pipeline abandoned | Realised | The viewer file is refreshed by any run against this tree, its asset version is derived from the data, and a guard reports a viewer that disagrees with `projects.json` |
| Ledger grows unwieldy | Low | Append-only, content-keyed, superseded entries retained as history |
| Records dropped by a reader bug never reach the tripwire | Medium | D3 catches unexplained gaps. It does **not** catch a fault that declares its own exclusions — see the two realised rows above |
| `coverage.py` cannot see a total re-key | **Realised, unfixed** | `coverage.py:51` diffs only `set(before) & set(after)`; under a total re-key that intersection is empty, so `regressions={}` and the guard passes while every cache is orphaned. The 2026-08-24 incident has the same shape. **Not fixed by this change** — see `parked.md` item 2 |

## Migration

```
1  Archive the three known gazettes (1150820, 1150827, 1151002) under their
   統計至 dates; append index entries. Nothing is derived from them yet.
2  Swap the reader. Regenerate. NOTE: the newest gazette is not necessarily the
   one to build from — see step 2a.
2a Build from 1150827, not 1151002. 1151002 is the newest publication and is
   archived and readable, but it carries 15 publisher-truncated 地號 cells
   against 1150827's 5, so building from it would emit a dataset 14 records
   smaller and less trustworthy than the one it replaces. Choosing the source
   gazette is a judgement, not a max().
3  Reconciliation reports against the previous gazette. Cache directories that
   move with the reader are absorbed through the alias table rather than by
   renaming on disk. Measured: 0 aliases, 2 stranded, both traceable to a
   truncated record.
4  Convert repair_621_track and any other emitted-data patch script into
   ledger entries, then delete the script.
5  From here: periodical fetcher compares 統計至 against the index and runs
   the full pipeline only when the publication actually changed.
```

Step 1 first: without an archive there is nothing to reconcile against, and the first reconciliation would be against a single stale `source.pdf` (統計至 115-8-11, older than the data currently shipped).

## Open questions

- The city's gazette page (`uro.gov.taipei/cp.aspx?n=963B15B39CADB94E`) exposes a 資料更新 timestamp and links only the newest PDF; whether it supports conditional requests (`ETag`/`If-Modified-Since`) is untested and determines fetch cost.
- Should the ledger be a single JSONL file or per-entry files? JSONL chosen for append-only simplicity; revisit if concurrent writers appear (the single-writer rule currently covers `.link_cache` only).
- Whether re-reading archived gazettes under the current reader should also rewrite the emitted dataset, or produce a parallel "as-of" dataset. Deferred — no current requirement for historical views.